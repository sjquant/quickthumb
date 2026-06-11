from typing import TYPE_CHECKING

from PIL import Image, ImageStat

from quickthumb._base import (
    DEFAULT_TEXT_COLOR,
    DEFAULT_TEXT_SIZE,
    RenderContext,
    apply_alignment,
    parse_coordinate,
)
from quickthumb._effects import EffectsEngine
from quickthumb._fonts import FontEngine
from quickthumb._groups import GroupEngine
from quickthumb._text import TextEngine

if TYPE_CHECKING:
    from quickthumb.canvas import Canvas
from quickthumb.models import (
    Diagnostic,
    GroupLayer,
    ImageLayer,
    ShapeLayer,
    SvgLayer,
    TextLayer,
)

TINY_TEXT_RATIO = 0.025
LOW_CONTRAST_THRESHOLD = 2.0


def _relative_luminance(rgb: tuple[float, ...]) -> float:
    channels = []
    for value in rgb:
        c = value / 255
        channels.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    r, g, b = channels[:3]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast_ratio(rgb_a: tuple[float, ...], rgb_b: tuple[float, ...]) -> float:
    lum_a = _relative_luminance(rgb_a)
    lum_b = _relative_luminance(rgb_b)
    lighter, darker = max(lum_a, lum_b), min(lum_a, lum_b)
    return (lighter + 0.05) / (darker + 0.05)


class DiagnosticsEngine:
    """Pre-render legibility and layout checks over a canvas's layers."""

    def __init__(
        self,
        ctx: RenderContext,
        canvas: "Canvas",
        effects: EffectsEngine,
        fonts: FontEngine,
        text: TextEngine,
        groups: GroupEngine,
    ):
        self._ctx = ctx
        self._canvas = canvas
        self._effects = effects
        self._fonts = fonts
        self._text = text
        self._groups = groups

    def diagnose(self) -> list[Diagnostic]:
        """Check layers for layout and legibility issues without producing an output file.

        Returns structured findings (off-canvas, tiny-text, text-overflow, low-contrast)
        that an agent or human can act on before rendering.
        """
        self._canvas._validate_image_paths()
        self._ctx.svg_raster_cache.clear()

        diagnostics: list[Diagnostic] = []
        running = self._canvas._create_canvas()
        for index, layer in enumerate(self._canvas.layers):
            if isinstance(layer, TextLayer):
                diagnostics.extend(self._diagnose_text_layer(running, layer, index))

            box = self._layer_bbox(layer)
            if box is not None:
                finding = self._diagnose_off_canvas(box, index, layer)
                if finding is not None:
                    diagnostics.append(finding)

            self._canvas._render_layer(running, layer)

        return diagnostics

    def _layer_bbox(self, layer) -> tuple[int, int, int, int] | None:
        """Compute the unrotated bounding box a layer will occupy on the canvas."""
        if isinstance(layer, GroupLayer):
            _, box = self._groups.layout_group(layer)
            return box

        if isinstance(layer, (ImageLayer, SvgLayer, ShapeLayer)):
            w, h = self._groups.measure_group_child(layer)
            x = parse_coordinate(layer.position[0], self._ctx.width)
            y = parse_coordinate(layer.position[1], self._ctx.height)
            if layer.align:
                x, y = apply_alignment(x, y, (w, h), layer.align)
            return x, y, w, h

        if isinstance(layer, TextLayer):
            w, h = self._groups.measure_group_child(layer)
            base_x, base_y = self._text.get_text_base_position(layer)
            x = self._text.get_horizontal_start_x(base_x, w, layer.align)
            y = self._text.get_vertical_start_y(base_y, h, layer.align)
            return x, y, w, h

        return None

    def _diagnose_off_canvas(self, box, index: int, layer) -> Diagnostic | None:
        x, y, w, h = box
        if w <= 0 or h <= 0:
            return None

        fully_outside = x + w <= 0 or y + h <= 0 or x >= self._ctx.width or y >= self._ctx.height
        partially_outside = x < 0 or y < 0 or x + w > self._ctx.width or y + h > self._ctx.height

        if fully_outside:
            return Diagnostic(
                code="off-canvas",
                severity="error",
                layer_index=index,
                message=(
                    f"{layer.type} layer at ({x}, {y}) size {w}x{h} is entirely outside "
                    f"the {self._ctx.width}x{self._ctx.height} canvas"
                ),
            )
        if partially_outside:
            return Diagnostic(
                code="off-canvas",
                severity="warning",
                layer_index=index,
                message=(
                    f"{layer.type} layer at ({x}, {y}) size {w}x{h} extends past the edge "
                    f"of the {self._ctx.width}x{self._ctx.height} canvas"
                ),
            )
        return None

    def _diagnose_text_layer(
        self, running: Image.Image, layer: TextLayer, index: int
    ) -> list[Diagnostic]:
        findings: list[Diagnostic] = []

        if isinstance(layer.content, list):
            size = min(self._text.resolve_size(part, layer) for part in layer.content)
        else:
            size = layer.size or DEFAULT_TEXT_SIZE
        tiny_threshold = self._ctx.height * TINY_TEXT_RATIO
        if size < tiny_threshold:
            findings.append(
                Diagnostic(
                    code="tiny-text",
                    severity="warning",
                    layer_index=index,
                    message=(
                        f"text size {size}px is below {tiny_threshold:.0f}px "
                        f"({TINY_TEXT_RATIO:.1%} of canvas height) and may be illegible "
                        "at thumbnail display sizes"
                    ),
                )
            )

        overflow = self._find_overflowing_word(layer)
        if overflow is not None:
            findings.append(
                Diagnostic(
                    code="text-overflow",
                    severity="warning",
                    layer_index=index,
                    message=(
                        f"word '{overflow}' is wider than max_width={layer.max_width} "
                        "and cannot be wrapped"
                    ),
                )
            )

        contrast = self._text_background_contrast(running, layer)
        if contrast is not None and contrast < LOW_CONTRAST_THRESHOLD:
            findings.append(
                Diagnostic(
                    code="low-contrast",
                    severity="warning",
                    layer_index=index,
                    message=(
                        f"text contrast ratio {contrast:.2f} against the layers below it "
                        f"is under {LOW_CONTRAST_THRESHOLD}; the text may be hard to read"
                    ),
                )
            )

        return findings

    def _find_overflowing_word(self, layer: TextLayer) -> str | None:
        if not layer.max_width:
            return None

        max_width_px = parse_coordinate(layer.max_width, self._ctx.width)

        if isinstance(layer.content, str):
            font = self._fonts.load_font(layer)
            return self._first_word_wider_than(
                layer.content, font, layer.letter_spacing or 0, max_width_px
            )

        for part in layer.content:
            font = self._fonts.load_font_variant(
                part.font or layer.font,
                self._text.resolve_size(part, layer),
                self._text.resolve_bold(part, layer),
                self._text.resolve_italic(part, layer),
                self._text.resolve_weight(part, layer),
            )
            word = self._first_word_wider_than(
                part.text, font, self._text.resolve_letter_spacing(part, layer), max_width_px
            )
            if word is not None:
                return word
        return None

    def _first_word_wider_than(
        self, text: str, font, letter_spacing: int, max_width_px: int
    ) -> str | None:
        for word in text.split():
            width, _ = self._text.measure_text_bounds(word, font, letter_spacing)
            if width > max_width_px:
                return word
        return None

    def _text_background_contrast(self, running: Image.Image, layer: TextLayer) -> float | None:
        """Contrast ratio between the layer's text color and the composited area below it."""
        text_color = self._effects.parse_color(layer.color) if layer.color else DEFAULT_TEXT_COLOR

        box = self._layer_bbox(layer)
        if box is None:
            return None
        x, y, w, h = box
        left, top = max(0, x), max(0, y)
        right, bottom = min(self._ctx.width, x + w), min(self._ctx.height, y + h)
        if right <= left or bottom <= top:
            return None

        region = running.crop((left, top, right, bottom))
        mean_r, mean_g, mean_b, mean_a = ImageStat.Stat(region).mean

        # Transparent areas read as white, matching JPEG export and typical viewers.
        alpha = mean_a / 255
        background = tuple(
            channel * alpha + 255 * (1 - alpha) for channel in (mean_r, mean_g, mean_b)
        )

        return _contrast_ratio(tuple(float(c) for c in text_color[:3]), background)
