from collections.abc import Iterable
from dataclasses import dataclass
from math import ceil
from typing import TYPE_CHECKING, Any

from PIL import Image, ImageChops, ImageStat

from quickthumb._base import (
    DEFAULT_TEXT_COLOR,
    DEFAULT_TEXT_SIZE,
    RenderContext,
    parse_coordinate,
)
from quickthumb._effects import EffectsEngine
from quickthumb._fonts import FontEngine
from quickthumb._groups import GroupEngine
from quickthumb._images import ImageEngine
from quickthumb._measurements import BBox, LayerMeasurement, measure_layers
from quickthumb._shapes import ShapeEngine
from quickthumb._text import TextEngine

if TYPE_CHECKING:
    from quickthumb.canvas import Canvas
from quickthumb.models import (
    Align,
    Diagnostic,
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


@dataclass(frozen=True)
class _LayerAlpha:
    visible_area: int
    mask: Image.Image | None = None


@dataclass(frozen=True)
class _OverlapMeasurement:
    bbox_area: int
    visible_area: int
    lower_bbox_pct: float
    upper_bbox_pct: float
    lower_visible_pct: float
    upper_visible_pct: float


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
        self._alpha_cache: dict[str, _LayerAlpha] = {}

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
        candidates = list(self._iter_overlap_candidates(measurements))
        for lower, upper in self._candidate_overlap_pairs(candidates):
            finding = self._diagnose_candidate_overlap(lower, upper)
            if finding is not None:
                findings.append(finding)
        return findings

    def _iter_overlap_candidates(
        self, measurements: Iterable[LayerMeasurement]
    ) -> Iterable[LayerMeasurement]:
        for measured in measurements:
            if measured.children:
                yield from self._iter_overlap_candidates(measured.children)
            elif measured.visible and measured.bbox is not None and not measured.bbox.is_empty:
                yield measured

    def _candidate_overlap_pairs(
        self, candidates: list[LayerMeasurement]
    ) -> Iterable[tuple[LayerMeasurement, LayerMeasurement]]:
        active: list[tuple[int, LayerMeasurement]] = []
        pairs: list[tuple[int, int, LayerMeasurement, LayerMeasurement]] = []
        by_left_edge = sorted(
            enumerate(candidates),
            key=lambda item: self._bbox(item[1]).x,
        )

        for candidate_order, candidate in by_left_edge:
            candidate_box = self._bbox(candidate)
            active = [
                (other_order, other)
                for other_order, other in active
                if self._bbox(other).right > candidate_box.x
            ]
            for other_order, other in active:
                if other_order < candidate_order:
                    lower_order, upper_order = other_order, candidate_order
                    lower, upper = other, candidate
                else:
                    lower_order, upper_order = candidate_order, other_order
                    lower, upper = candidate, other
                pairs.append((lower_order, upper_order, lower, upper))
            active.append((candidate_order, candidate))

        for _, _, lower, upper in sorted(pairs, key=lambda item: (item[0], item[1])):
            yield lower, upper

    def _diagnose_candidate_overlap(
        self, lower: LayerMeasurement, upper: LayerMeasurement
    ) -> Diagnostic | None:
        lower_box = self._bbox(lower)
        upper_box = self._bbox(upper)
        overlap = lower_box.intersection(upper_box)
        if overlap is None:
            return None

        measured_overlap = self._measure_visible_overlap(lower, upper, overlap)
        if measured_overlap is None:
            return None

        if not self._is_suspicious_overlap(lower, upper, measured_overlap):
            return None

        suggestion = self._overlap_suggestion(upper, lower)
        return Diagnostic(
            code="layer-overlap",
            severity="warning",
            layer_index=upper.index,
            message=(
                f"{self._layer_label(upper)} (order {upper.order}) "
                f"overlaps {self._layer_label(lower)} "
                f"(order {lower.order}); bbox_overlap={measured_overlap.bbox_area}px "
                f"(bbox_overlap_pct={measured_overlap.upper_bbox_pct:.0%} of upper, "
                f"{measured_overlap.lower_bbox_pct:.0%} of lower), "
                f"visible_overlap={measured_overlap.visible_area}px "
                f"(visible_overlap_pct={measured_overlap.upper_visible_pct:.0%} of upper, "
                f"{measured_overlap.lower_visible_pct:.0%} of lower); {suggestion}"
            ),
            layer_id=upper.layer_id,
            layer_name=upper.name,
            bbox=self._bbox_to_payload(overlap),
            related_layers=[upper.layer_id, lower.layer_id],
            measured={
                "lower_layer_id": lower.layer_id,
                "upper_layer_id": upper.layer_id,
                "lower_bbox": self._bbox_to_payload(lower_box),
                "upper_bbox": self._bbox_to_payload(upper_box),
                "overlap_bbox": self._bbox_to_payload(overlap),
                "bbox_overlap": measured_overlap.bbox_area,
                "bbox_overlap_pct_lower": measured_overlap.lower_bbox_pct,
                "bbox_overlap_pct_upper": measured_overlap.upper_bbox_pct,
                "visible_overlap": measured_overlap.visible_area,
                "visible_overlap_pct_lower": measured_overlap.lower_visible_pct,
                "visible_overlap_pct_upper": measured_overlap.upper_visible_pct,
            },
            suggestion=suggestion,
        )

    @staticmethod
    def _bbox_to_payload(box: BBox) -> dict[str, int]:
        return {
            "x": box.x,
            "y": box.y,
            "width": box.width,
            "height": box.height,
        }

    def _is_suspicious_overlap(
        self, lower: LayerMeasurement, upper: LayerMeasurement, overlap: _OverlapMeasurement
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
        self, lower: LayerMeasurement, upper: LayerMeasurement, overlap: _OverlapMeasurement
    ) -> bool:
        if lower.layer_type == "text" or upper.layer_type != "text":
            return False
        return overlap.upper_visible_pct >= BACKDROP_COVERAGE_RATIO

    def _measure_visible_overlap(
        self, lower: LayerMeasurement, upper: LayerMeasurement, overlap: BBox
    ) -> _OverlapMeasurement | None:
        lower_alpha = self._layer_alpha(lower)
        upper_alpha = self._layer_alpha(upper)
        visible_area = self._visible_intersection_area(
            lower, upper, overlap, lower_alpha, upper_alpha
        )
        if visible_area == 0:
            return None

        return _OverlapMeasurement(
            bbox_area=overlap.area,
            visible_area=visible_area,
            lower_bbox_pct=overlap.area / self._bbox(lower).area,
            upper_bbox_pct=overlap.area / self._bbox(upper).area,
            lower_visible_pct=visible_area / lower_alpha.visible_area,
            upper_visible_pct=visible_area / upper_alpha.visible_area,
        )

    def _visible_intersection_area(
        self,
        lower: LayerMeasurement,
        upper: LayerMeasurement,
        overlap: BBox,
        lower_alpha: _LayerAlpha,
        upper_alpha: _LayerAlpha,
    ) -> int:
        if lower_alpha.mask is None and upper_alpha.mask is None:
            return overlap.area

        lower_mask = self._alpha_region(lower, lower_alpha, overlap)
        upper_mask = self._alpha_region(upper, upper_alpha, overlap)
        combined = ImageChops.multiply(lower_mask, upper_mask)
        return int(ImageStat.Stat(combined).sum[0] / 255)

    def _alpha_region(
        self, measured: LayerMeasurement, alpha: _LayerAlpha, region: BBox
    ) -> Image.Image:
        if alpha.mask is None:
            return Image.new("L", (region.width, region.height), 255)
        box = self._bbox(measured)
        left, top = region.x - box.x, region.y - box.y
        mask = alpha.mask.crop((left, top, left + region.width, top + region.height))
        return mask.point(lambda value: 255 if value else 0)

    def _layer_alpha(self, measured: LayerMeasurement) -> _LayerAlpha:
        cached = self._alpha_cache.get(measured.layer_id)
        if cached is not None:
            return cached

        if self._has_opaque_rectangle_mask(measured):
            alpha = _LayerAlpha(visible_area=self._bbox(measured).area)
        else:
            mask = self._render_layer_alpha_mask(measured)
            alpha = _LayerAlpha(visible_area=self._mask_area(mask), mask=mask)
        self._alpha_cache[measured.layer_id] = alpha
        return alpha

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
        box = self._bbox(measured)
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

    @staticmethod
    def _mask_area(mask: Image.Image) -> int:
        return int(ImageStat.Stat(mask).sum[0] / 255)

    def _overlap_suggestion(self, upper: LayerMeasurement, lower: LayerMeasurement) -> str:
        upper_box = self._bbox(upper)
        lower_box = self._bbox(lower)

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

    @staticmethod
    def _bbox(measured: LayerMeasurement) -> BBox:
        box = measured.bbox
        assert box is not None and not box.is_empty
        return box

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
                suggestion=self._move_inside_canvas_suggestion(measured),
                **self._diagnostic_context(measured),
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
                suggestion=self._move_inside_canvas_suggestion(measured),
                **self._diagnostic_context(measured),
            )
        return None

    def _move_inside_canvas_suggestion(self, measured: LayerMeasurement) -> str:
        box = measured.bbox
        assert box is not None
        if box.width > self._ctx.width or box.height > self._ctx.height:
            return (
                f"resize layer to fit within the {self._ctx.width}x{self._ctx.height} canvas "
                "before moving it"
            )

        bbox_x = min(max(box.x, 0), self._ctx.width - box.width)
        bbox_y = min(max(box.y, 0), self._ctx.height - box.height)
        x, y = bbox_x, bbox_y
        align = measured.metadata.get("align")
        if not isinstance(align, Align):
            align = getattr(measured.raw_layer, "align", None)
        if isinstance(align, Align):
            if align.horizontal == "center":
                x += box.width // 2
            elif align.horizontal == "right":
                x += box.width

            if align.vertical == "middle":
                y += box.height // 2
            elif align.vertical == "bottom":
                y += box.height
        return f"move layer to x={x}, y={y} to fit within the canvas"

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
                    **self._diagnostic_context(measured),
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
                    **self._diagnostic_context(measured),
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
                    **self._diagnostic_context(measured),
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

    def _diagnostic_context(self, measured: LayerMeasurement) -> dict[str, Any]:
        return {
            "layer_id": measured.layer_id,
            "layer_name": measured.name,
            "bbox": self._bbox_payload(measured),
            "related_layers": [measured.layer_id],
        }

    @staticmethod
    def _bbox_payload(measured: LayerMeasurement) -> dict[str, int] | None:
        if measured.bbox is None:
            return None
        return DiagnosticsEngine._bbox_to_payload(measured.bbox)
