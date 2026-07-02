from typing import TYPE_CHECKING

from PIL import Image, ImageStat

from quickthumb._base import (
    DEFAULT_TEXT_COLOR,
    DEFAULT_TEXT_SIZE,
    RenderContext,
    parse_coordinate,
)
from quickthumb._effects import EffectsEngine
from quickthumb._fonts import FontEngine
from quickthumb._groups import GroupEngine
from quickthumb._measurements import LayerMeasurement, measure_layers
from quickthumb._text import TextEngine

if TYPE_CHECKING:
    from quickthumb.canvas import Canvas
from quickthumb.models import Diagnostic, GroupLayer, TextLayer

TINY_TEXT_RATIO = 0.025
LOW_CONTRAST_THRESHOLD = 2.0
MIN_PARTIAL_OVERLAP_RATIO = 0.2
BACKDROP_COVERAGE_RATIO = 0.95
OVERLAP_CLEARANCE_PX = 8


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
        self._ctx.begin_render_pass()

        diagnostics: list[Diagnostic] = []
        measurements = measure_layers(self._canvas)
        running = self._canvas._create_canvas()
        for measured in measurements:
            if measured.visible:
                layer = measured.raw_layer
                if isinstance(layer, TextLayer):
                    diagnostics.extend(self._diagnose_text_layer(running, measured))
                elif isinstance(layer, GroupLayer):
                    for child in measured.text_descendants():
                        if child.visible:
                            diagnostics.extend(self._diagnose_text_layer(running, child))

                if measured.bbox is not None:
                    finding = self._diagnose_off_canvas(measured)
                    if finding is not None:
                        diagnostics.append(finding)

            self._canvas._render_layer(running, measured.raw_layer)

        diagnostics.extend(self._diagnose_layer_overlaps(measurements))

        return diagnostics

    def _diagnose_layer_overlaps(self, measurements: list[LayerMeasurement]) -> list[Diagnostic]:
        candidates = self._overlap_candidates(measurements)
        findings: list[Diagnostic] = []
        for lower_index, lower in enumerate(candidates):
            for upper in candidates[lower_index + 1 :]:
                finding = self._diagnose_candidate_overlap(lower, upper)
                if finding is not None:
                    findings.append(finding)
        return findings

    def _overlap_candidates(self, measurements: list[LayerMeasurement]) -> list[LayerMeasurement]:
        candidates: list[LayerMeasurement] = []
        for measured in measurements:
            self._append_overlap_candidates(candidates, measured)
        return candidates

    def _append_overlap_candidates(
        self, candidates: list[LayerMeasurement], measured: LayerMeasurement
    ) -> None:
        if measured.children:
            for child in measured.children:
                self._append_overlap_candidates(candidates, child)
            return

        if measured.visible and measured.bbox is not None and not measured.bbox.is_empty:
            candidates.append(measured)

    def _diagnose_candidate_overlap(
        self, lower: LayerMeasurement, upper: LayerMeasurement
    ) -> Diagnostic | None:
        lower_box = lower.bbox
        upper_box = upper.bbox
        if lower_box is None or upper_box is None:
            return None

        overlap = lower_box.intersection(upper_box)
        if overlap is None:
            return None

        if not self._is_suspicious_overlap(lower, upper, overlap.area):
            return None

        lower_pct = overlap.area / lower_box.area
        upper_pct = overlap.area / upper_box.area
        suggestion = self._overlap_suggestion(upper, lower)
        return Diagnostic(
            code="layer-overlap",
            severity="warning",
            layer_index=upper.index,
            message=(
                f"{self._layer_label(upper)} (order {upper.order}) "
                f"overlaps {self._layer_label(lower)} "
                f"(order {lower.order}) by {overlap.area}px "
                f"({upper_pct:.0%} of upper, {lower_pct:.0%} of lower); {suggestion}"
            ),
        )

    def _is_suspicious_overlap(
        self, lower: LayerMeasurement, upper: LayerMeasurement, overlap_area: int
    ) -> bool:
        if lower.layer_type == "text" and upper.layer_type == "text":
            return True

        if self._is_text_on_backdrop(lower, upper, overlap_area):
            return False

        lower_area = lower.bbox.area if lower.bbox is not None else 0
        upper_area = upper.bbox.area if upper.bbox is not None else 0
        smaller_area = min(lower_area, upper_area)
        if smaller_area == 0:
            return False

        overlap_ratio = overlap_area / smaller_area
        return (
            0 < overlap_ratio < BACKDROP_COVERAGE_RATIO
            and overlap_ratio >= MIN_PARTIAL_OVERLAP_RATIO
        )

    def _is_text_on_backdrop(
        self, lower: LayerMeasurement, upper: LayerMeasurement, overlap_area: int
    ) -> bool:
        if lower.layer_type == "text" or upper.layer_type != "text" or upper.bbox is None:
            return False
        return overlap_area / upper.bbox.area >= BACKDROP_COVERAGE_RATIO

    def _overlap_suggestion(self, upper: LayerMeasurement, lower: LayerMeasurement) -> str:
        upper_box = upper.bbox
        lower_box = lower.bbox
        if upper_box is None or lower_box is None:
            return f"move layer {upper.index} to clear the overlap"

        below_y = lower_box.bottom + OVERLAP_CLEARANCE_PX
        if below_y + upper_box.height <= self._ctx.height:
            return f"move layer {upper.index} to y={below_y} to clear the overlap"

        above_y = lower_box.y - upper_box.height - OVERLAP_CLEARANCE_PX
        if above_y >= 0:
            return f"move layer {upper.index} to y={above_y} to clear the overlap"

        right_x = lower_box.right + OVERLAP_CLEARANCE_PX
        if right_x + upper_box.width <= self._ctx.width:
            return f"move layer {upper.index} to x={right_x} to clear the overlap"

        left_x = lower_box.x - upper_box.width - OVERLAP_CLEARANCE_PX
        if left_x >= 0:
            return f"move layer {upper.index} to x={left_x} to clear the overlap"

        return f"move or resize layer {upper.index} to clear the overlap"

    @staticmethod
    def _layer_label(measured: LayerMeasurement) -> str:
        return f"{measured.layer_type} layer {measured.layer_id}"

    def _diagnose_off_canvas(self, measured: LayerMeasurement) -> Diagnostic | None:
        box = measured.bbox
        if box is None or box.is_empty:
            return None
        x, y, w, h = box.as_tuple()
        layer_type = measured.layer_type

        if box.is_fully_outside(self._ctx.width, self._ctx.height):
            return Diagnostic(
                code="off-canvas",
                severity="error",
                layer_index=measured.index,
                message=(
                    f"{layer_type} layer at ({x}, {y}) size {w}x{h} is entirely outside "
                    f"the {self._ctx.width}x{self._ctx.height} canvas"
                ),
            )
        if box.is_partially_outside(self._ctx.width, self._ctx.height):
            return Diagnostic(
                code="off-canvas",
                severity="warning",
                layer_index=measured.index,
                message=(
                    f"{layer_type} layer at ({x}, {y}) size {w}x{h} extends past the edge "
                    f"of the {self._ctx.width}x{self._ctx.height} canvas"
                ),
            )
        return None

    def _diagnose_text_layer(
        self, running: Image.Image, measured: LayerMeasurement
    ) -> list[Diagnostic]:
        findings: list[Diagnostic] = []
        layer = measured.effective_text_layer
        if layer is None:
            return findings

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
                    layer_index=measured.index,
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
                    layer_index=measured.index,
                    message=(
                        f"word '{overflow}' is wider than max_width={layer.max_width} "
                        "and cannot be wrapped"
                    ),
                )
            )

        contrast = self._text_background_contrast(running, measured)
        if contrast is not None and contrast < LOW_CONTRAST_THRESHOLD:
            findings.append(
                Diagnostic(
                    code="low-contrast",
                    severity="warning",
                    layer_index=measured.index,
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

    def _text_background_contrast(
        self, running: Image.Image, measured: LayerMeasurement
    ) -> float | None:
        """Worst contrast ratio between the layer's text colors and the area below it."""
        layer = measured.effective_text_layer
        if layer is None:
            return None

        if isinstance(layer.content, list):
            text_colors = {self._text.resolve_color(part, layer) for part in layer.content}
        elif layer.color:
            text_colors = {self._effects.parse_color(layer.color)}
        else:
            text_colors = {DEFAULT_TEXT_COLOR}

        box = measured.bbox
        if box is None:
            return None
        clamped = box.clamped_to(self._ctx.width, self._ctx.height)
        if clamped is None:
            return None

        region = running.crop((clamped.x, clamped.y, clamped.right, clamped.bottom))
        mean_r, mean_g, mean_b, mean_a = ImageStat.Stat(region).mean

        # Transparent areas read as white, matching JPEG export and typical viewers.
        alpha = mean_a / 255
        background = tuple(
            channel * alpha + 255 * (1 - alpha) for channel in (mean_r, mean_g, mean_b)
        )

        return min(
            _contrast_ratio(tuple(float(c) for c in color[:3]), background) for color in text_colors
        )
