from math import ceil
from typing import TYPE_CHECKING

from PIL import Image

from quickthumb._base import (
    DEFAULT_TEXT_COLOR,
    DEFAULT_TEXT_SIZE,
    RenderContext,
    parse_coordinate,
)
from quickthumb._diagnostic_rules import (
    LayerAlphaCache,
    OverlapMeasurement,
    average_visible_background,
    bbox_payload,
    clear_overlap_suggestion,
    contrast_ratio,
    diagnostic_context,
    layer_label,
    move_inside_canvas_suggestion,
    overlap_pairs,
    require_bbox,
    visible_leaf_layers,
)
from quickthumb._effects import EffectsEngine
from quickthumb._fonts import FontEngine
from quickthumb._groups import GroupEngine
from quickthumb._images import ImageEngine
from quickthumb._measurements import LayerMeasurement, measure_layers
from quickthumb._shapes import ShapeEngine
from quickthumb._text import TextEngine

if TYPE_CHECKING:
    from quickthumb.canvas import Canvas
from quickthumb.models import (
    Diagnostic,
    DiagnosticBBox,
    GroupLayer,
    ImageLayer,
    ShapeLayer,
    SvgLayer,
    TextLayer,
)

TINY_TEXT_RATIO = 0.025
LOW_CONTRAST_THRESHOLD = 2.0
MIN_PARTIAL_OVERLAP_RATIO = 0.2
BACKDROP_COVERAGE_RATIO = 0.95
OVERLAP_CLEARANCE_PX = 8


class DiagnosticsEngine:
    """Pre-render legibility and layout checks over a canvas's layers."""

    def __init__(
        self,
        ctx: RenderContext,
        canvas: "Canvas",
        effects: EffectsEngine,
        fonts: FontEngine,
        images: ImageEngine,
        shapes: ShapeEngine,
        text: TextEngine,
        groups: GroupEngine,
    ):
        self._ctx = ctx
        self._canvas = canvas
        self._effects = effects
        self._fonts = fonts
        self._images = images
        self._shapes = shapes
        self._text = text
        self._groups = groups
        self._alpha_cache = LayerAlphaCache(
            self._has_opaque_rectangle_mask, self._render_layer_alpha_mask
        )

    def diagnose(self) -> list[Diagnostic]:
        """Check layers for layout and legibility issues without producing an output file.

        Returns structured findings (off-canvas, tiny-text, text-overflow,
        low-contrast, layer-overlap) that an agent or human can act on before
        rendering.
        """
        self._alpha_cache.clear()
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
        findings: list[Diagnostic] = []
        candidates = list(visible_leaf_layers(measurements))
        for lower, upper in overlap_pairs(candidates):
            finding = self._diagnose_candidate_overlap(lower, upper)
            if finding is not None:
                findings.append(finding)
        return findings

    def _diagnose_candidate_overlap(
        self, lower: LayerMeasurement, upper: LayerMeasurement
    ) -> Diagnostic | None:
        lower_box = require_bbox(lower)
        upper_box = require_bbox(upper)
        overlap = lower_box.intersection(upper_box)
        if overlap is None:
            return None

        measured_overlap = self._alpha_cache.measure(lower, upper, overlap)
        if measured_overlap is None:
            return None

        if not self._is_suspicious_overlap(lower, upper, measured_overlap):
            return None

        suggestion = clear_overlap_suggestion(
            upper,
            lower,
            canvas_width=self._ctx.width,
            canvas_height=self._ctx.height,
            clearance=OVERLAP_CLEARANCE_PX,
        )
        return Diagnostic(
            code="layer-overlap",
            severity="warning",
            layer_index=upper.index,
            message=(
                f"{layer_label(upper)} (order {upper.order}) "
                f"overlaps {layer_label(lower)} "
                f"(order {lower.order}); bbox_overlap={measured_overlap.bbox_area}px "
                f"(bbox_overlap_pct={measured_overlap.upper_bbox_pct:.0%} of upper, "
                f"{measured_overlap.lower_bbox_pct:.0%} of lower), "
                f"visible_overlap={measured_overlap.visible_area}px "
                f"(visible_overlap_pct={measured_overlap.upper_visible_pct:.0%} of upper, "
                f"{measured_overlap.lower_visible_pct:.0%} of lower); {suggestion}"
            ),
            layer_id=upper.layer_id,
            layer_name=upper.name,
            bbox=DiagnosticBBox(**bbox_payload(overlap)),
            related_layers=[upper.layer_id, lower.layer_id],
            measured={
                "lower_layer_id": lower.layer_id,
                "upper_layer_id": upper.layer_id,
                "lower_bbox": bbox_payload(lower_box),
                "upper_bbox": bbox_payload(upper_box),
                "overlap_bbox": bbox_payload(overlap),
                "bbox_overlap": measured_overlap.bbox_area,
                "bbox_overlap_pct_lower": measured_overlap.lower_bbox_pct,
                "bbox_overlap_pct_upper": measured_overlap.upper_bbox_pct,
                "visible_overlap": measured_overlap.visible_area,
                "visible_overlap_pct_lower": measured_overlap.lower_visible_pct,
                "visible_overlap_pct_upper": measured_overlap.upper_visible_pct,
            },
            suggestion=suggestion,
        )

    def _is_suspicious_overlap(
        self, lower: LayerMeasurement, upper: LayerMeasurement, overlap: OverlapMeasurement
    ) -> bool:
        if lower.layer_type == "text" and upper.layer_type == "text":
            return True

        if lower.layer_type == "text":
            return overlap.lower_visible_pct >= MIN_PARTIAL_OVERLAP_RATIO

        if self._is_text_on_backdrop(lower, upper, overlap):
            return False

        if max(overlap.lower_visible_pct, overlap.upper_visible_pct) >= BACKDROP_COVERAGE_RATIO:
            return True

        overlap_ratio = min(overlap.lower_visible_pct, overlap.upper_visible_pct)
        return overlap_ratio >= MIN_PARTIAL_OVERLAP_RATIO

    def _is_text_on_backdrop(
        self, lower: LayerMeasurement, upper: LayerMeasurement, overlap: OverlapMeasurement
    ) -> bool:
        if lower.layer_type == "text" or upper.layer_type != "text":
            return False
        return overlap.upper_visible_pct >= BACKDROP_COVERAGE_RATIO

    def _has_opaque_rectangle_mask(self, measured: LayerMeasurement) -> bool:
        layer = measured.raw_layer
        return (
            isinstance(layer, ShapeLayer)
            and layer.shape == "rectangle"
            and layer.border_radius == 0
            and layer.rotation == 0
            and layer.opacity == 1.0
            and not layer.effects
        )

    def _render_layer_alpha_mask(self, measured: LayerMeasurement) -> Image.Image:
        box = require_bbox(measured)
        image = Image.new("RGBA", (self._ctx.width, self._ctx.height), (0, 0, 0, 0))
        layer = measured.raw_layer
        if isinstance(layer, TextLayer):
            self._text.render_text_layer(image, layer)
        elif isinstance(layer, ImageLayer):
            self._images.render_image_layer(image, layer)
        elif isinstance(layer, SvgLayer):
            self._images.render_svg_layer(image, layer)
        elif isinstance(layer, ShapeLayer):
            self._shapes.render_shape_layer(image, layer)
        else:
            return Image.new("L", (box.width, box.height), 0)
        return (
            image.getchannel("A")
            .crop((box.x, box.y, box.right, box.bottom))
            .point(lambda value: 255 if value else 0)
        )

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
                measured={
                    "layer_type": layer_type,
                    "canvas_width": self._ctx.width,
                    "canvas_height": self._ctx.height,
                    "outside": "fully",
                },
                suggestion=move_inside_canvas_suggestion(
                    measured,
                    canvas_width=self._ctx.width,
                    canvas_height=self._ctx.height,
                ),
                **diagnostic_context(measured),
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
                measured={
                    "layer_type": layer_type,
                    "canvas_width": self._ctx.width,
                    "canvas_height": self._ctx.height,
                    "outside": "partially",
                },
                suggestion=move_inside_canvas_suggestion(
                    measured,
                    canvas_width=self._ctx.width,
                    canvas_height=self._ctx.height,
                ),
                **diagnostic_context(measured),
            )
        return None

    def _diagnose_text_layer(
        self, running: Image.Image, measured: LayerMeasurement
    ) -> list[Diagnostic]:
        findings: list[Diagnostic] = []
        layer = measured.effective_text_layer
        if layer is None:
            return findings

        size = self._minimum_text_size(layer)
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
                    measured={
                        "font_size": size,
                        "threshold": tiny_threshold,
                        "threshold_ratio": TINY_TEXT_RATIO,
                        "canvas_height": self._ctx.height,
                    },
                    suggestion=f"increase text size to at least {ceil(tiny_threshold)}px",
                    **diagnostic_context(measured),
                )
            )

        overflow = self._find_overflowing_word(layer)
        if overflow is not None:
            word, word_width, max_width = overflow
            findings.append(
                Diagnostic(
                    code="text-overflow",
                    severity="warning",
                    layer_index=measured.index,
                    message=(
                        f"word '{word}' is wider than max_width={layer.max_width} "
                        "and cannot be wrapped"
                    ),
                    measured={
                        "word": word,
                        "word_width": word_width,
                        "max_width": max_width,
                    },
                    suggestion=(
                        f"increase max_width to at least {word_width}px or enable auto_scale"
                    ),
                    **diagnostic_context(measured),
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
                    measured={
                        "contrast": contrast,
                        "threshold": LOW_CONTRAST_THRESHOLD,
                    },
                    suggestion=(
                        f"increase foreground/background contrast to at least "
                        f"{LOW_CONTRAST_THRESHOLD}:1"
                    ),
                    **diagnostic_context(measured),
                )
            )

        return findings

    def _minimum_text_size(self, layer: TextLayer) -> int:
        if isinstance(layer.content, list):
            return min(self._text.resolve_size(part, layer) for part in layer.content)
        return layer.size or DEFAULT_TEXT_SIZE

    def _find_overflowing_word(self, layer: TextLayer) -> tuple[str, int, int] | None:
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
    ) -> tuple[str, int, int] | None:
        for word in text.split():
            width, _ = self._text.measure_text_bounds(word, font, letter_spacing)
            if width > max_width_px:
                return word, width, max_width_px
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

        background = average_visible_background(running, clamped)

        return min(
            contrast_ratio(tuple(float(c) for c in color[:3]), background) for color in text_colors
        )
