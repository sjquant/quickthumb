from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from PIL import Image, ImageChops, ImageStat

from quickthumb._measurements import BBox, LayerMeasurement
from quickthumb.models import Align


@dataclass(frozen=True)
class LayerAlpha:
    """Binary alpha measurement for a rendered layer."""

    visible_area: int
    mask: Image.Image | None = None


@dataclass(frozen=True)
class OverlapMeasurement:
    """Measured bbox and visible-pixel intersection for two layers."""

    bbox_area: int
    visible_area: int
    lower_bbox_pct: float
    upper_bbox_pct: float
    lower_visible_pct: float
    upper_visible_pct: float


class DiagnosticPayloads:
    """Build structured diagnostic payload fragments from measurements."""

    @staticmethod
    def bbox(box: BBox) -> dict[str, int]:
        return {
            "x": box.x,
            "y": box.y,
            "width": box.width,
            "height": box.height,
        }

    @classmethod
    def context(cls, measured: LayerMeasurement) -> dict[str, Any]:
        box = measured.bbox
        return {
            "layer_id": measured.layer_id,
            "layer_name": measured.name,
            "bbox": cls.bbox(box) if box is not None else None,
            "related_layers": [measured.layer_id],
        }


class MeasurementGeometry:
    """Geometry helpers for measured diagnostic layers."""

    @staticmethod
    def require_bbox(measured: LayerMeasurement) -> BBox:
        box = measured.bbox
        assert box is not None and not box.is_empty
        return box

    @staticmethod
    def layer_label(measured: LayerMeasurement) -> str:
        return f"{measured.layer_type} layer {measured.layer_id}"

    @classmethod
    def visible_leaf_layers(
        cls, measurements: Iterable[LayerMeasurement]
    ) -> Iterable[LayerMeasurement]:
        for measured in measurements:
            if measured.children:
                yield from cls.visible_leaf_layers(measured.children)
            elif measured.visible and measured.bbox is not None and not measured.bbox.is_empty:
                yield measured

    @classmethod
    def overlap_pairs(
        cls, candidates: Iterable[LayerMeasurement]
    ) -> Iterable[tuple[LayerMeasurement, LayerMeasurement]]:
        active: list[tuple[int, LayerMeasurement]] = []
        pairs: list[tuple[int, int, LayerMeasurement, LayerMeasurement]] = []
        sorted_candidates = sorted(
            enumerate(candidates),
            key=lambda item: cls.require_bbox(item[1]).x,
        )

        for candidate_order, candidate in sorted_candidates:
            candidate_box = cls.require_bbox(candidate)
            active = [
                (other_order, other)
                for other_order, other in active
                if cls.require_bbox(other).right > candidate_box.x
            ]
            cls._append_candidate_pairs(active, candidate_order, candidate, pairs)
            active.append((candidate_order, candidate))

        for _, _, lower, upper in sorted(pairs, key=lambda item: (item[0], item[1])):
            yield lower, upper

    @staticmethod
    def _append_candidate_pairs(
        active: list[tuple[int, LayerMeasurement]],
        candidate_order: int,
        candidate: LayerMeasurement,
        pairs: list[tuple[int, int, LayerMeasurement, LayerMeasurement]],
    ) -> None:
        for other_order, other in active:
            if other_order < candidate_order:
                lower_order, upper_order = other_order, candidate_order
                lower, upper = other, candidate
            else:
                lower_order, upper_order = candidate_order, other_order
                lower, upper = candidate, other
            pairs.append((lower_order, upper_order, lower, upper))


class DiagnosticSuggestions:
    """Human-readable repair suggestions shared by diagnostic rules."""

    def move_inside_canvas(
        self, measured: LayerMeasurement, *, canvas_width: int, canvas_height: int
    ) -> str:
        box = measured.bbox
        assert box is not None
        if box.width > canvas_width or box.height > canvas_height:
            return (
                f"resize layer to fit within the {canvas_width}x{canvas_height} "
                "canvas before moving it"
            )

        bbox_x = min(max(box.x, 0), canvas_width - box.width)
        bbox_y = min(max(box.y, 0), canvas_height - box.height)
        x, y = self._aligned_position(measured, bbox_x, bbox_y)
        return f"move layer to x={x}, y={y} to fit within the canvas"

    def _aligned_position(
        self, measured: LayerMeasurement, bbox_x: int, bbox_y: int
    ) -> tuple[int, int]:
        x, y = bbox_x, bbox_y
        align = measured.metadata.get("align")
        if not isinstance(align, Align):
            align = getattr(measured.raw_layer, "align", None)
        if isinstance(align, Align):
            if align.horizontal == "center":
                x += MeasurementGeometry.require_bbox(measured).width // 2
            elif align.horizontal == "right":
                x += MeasurementGeometry.require_bbox(measured).width

            if align.vertical == "middle":
                y += MeasurementGeometry.require_bbox(measured).height // 2
            elif align.vertical == "bottom":
                y += MeasurementGeometry.require_bbox(measured).height
        return x, y

    def clear_overlap(
        self,
        upper: LayerMeasurement,
        lower: LayerMeasurement,
        *,
        canvas_width: int,
        canvas_height: int,
        clearance: int,
    ) -> str:
        upper_box = MeasurementGeometry.require_bbox(upper)
        lower_box = MeasurementGeometry.require_bbox(lower)

        below_y = lower_box.bottom + clearance
        if below_y + upper_box.height <= canvas_height:
            return f"move layer {upper.index} to y={below_y} to clear the overlap"

        above_y = lower_box.y - upper_box.height - clearance
        if above_y >= 0:
            return f"move layer {upper.index} to y={above_y} to clear the overlap"

        right_x = lower_box.right + clearance
        if right_x + upper_box.width <= canvas_width:
            return f"move layer {upper.index} to x={right_x} to clear the overlap"

        left_x = lower_box.x - upper_box.width - clearance
        if left_x >= 0:
            return f"move layer {upper.index} to x={left_x} to clear the overlap"

        return f"move or resize layer {upper.index} to clear the overlap"


class LayerAlphaCache:
    """Measure and cache visible alpha masks for overlap-style rules."""

    def __init__(
        self,
        opaque_rectangle: Callable[[LayerMeasurement], bool],
        render_mask: Callable[[LayerMeasurement], Image.Image],
    ):
        self._opaque_rectangle = opaque_rectangle
        self._render_mask = render_mask
        self._cache: dict[str, LayerAlpha] = {}

    def clear(self) -> None:
        self._cache.clear()

    def get(self, measured: LayerMeasurement) -> LayerAlpha:
        cached = self._cache.get(measured.layer_id)
        if cached is not None:
            return cached

        if self._opaque_rectangle(measured):
            alpha = LayerAlpha(visible_area=MeasurementGeometry.require_bbox(measured).area)
        else:
            mask = self._render_mask(measured)
            alpha = LayerAlpha(visible_area=mask_area(mask), mask=mask)
        self._cache[measured.layer_id] = alpha
        return alpha

    def measure(
        self, lower: LayerMeasurement, upper: LayerMeasurement, overlap: BBox
    ) -> OverlapMeasurement | None:
        lower_alpha = self.get(lower)
        upper_alpha = self.get(upper)
        visible_area = self._visible_intersection_area(
            lower, upper, overlap, lower_alpha, upper_alpha
        )
        if visible_area == 0:
            return None

        return OverlapMeasurement(
            bbox_area=overlap.area,
            visible_area=visible_area,
            lower_bbox_pct=overlap.area / MeasurementGeometry.require_bbox(lower).area,
            upper_bbox_pct=overlap.area / MeasurementGeometry.require_bbox(upper).area,
            lower_visible_pct=visible_area / lower_alpha.visible_area,
            upper_visible_pct=visible_area / upper_alpha.visible_area,
        )

    def _visible_intersection_area(
        self,
        lower: LayerMeasurement,
        upper: LayerMeasurement,
        overlap: BBox,
        lower_alpha: LayerAlpha,
        upper_alpha: LayerAlpha,
    ) -> int:
        if lower_alpha.mask is None and upper_alpha.mask is None:
            return overlap.area

        lower_mask = self._alpha_region(lower, lower_alpha, overlap)
        upper_mask = self._alpha_region(upper, upper_alpha, overlap)
        combined = ImageChops.multiply(lower_mask, upper_mask)
        return mask_area(combined)

    def _alpha_region(
        self, measured: LayerMeasurement, alpha: LayerAlpha, region: BBox
    ) -> Image.Image:
        if alpha.mask is None:
            return Image.new("L", (region.width, region.height), 255)
        box = MeasurementGeometry.require_bbox(measured)
        left, top = region.x - box.x, region.y - box.y
        mask = alpha.mask.crop((left, top, left + region.width, top + region.height))
        return mask.point(lambda value: 255 if value else 0)


class RegionSampler:
    """Pixel sampling helpers for diagnostic contrast-style rules."""

    @staticmethod
    def average_visible_background(image: Image.Image, region: BBox) -> tuple[float, float, float]:
        crop = image.crop((region.x, region.y, region.right, region.bottom))
        mean_r, mean_g, mean_b, mean_a = ImageStat.Stat(crop).mean

        # Transparent areas read as white, matching JPEG export and typical viewers.
        alpha = mean_a / 255
        return tuple(channel * alpha + 255 * (1 - alpha) for channel in (mean_r, mean_g, mean_b))

    @staticmethod
    def contrast_ratio(rgb_a: tuple[float, ...], rgb_b: tuple[float, ...]) -> float:
        lum_a = RegionSampler._relative_luminance(rgb_a)
        lum_b = RegionSampler._relative_luminance(rgb_b)
        lighter, darker = max(lum_a, lum_b), min(lum_a, lum_b)
        return (lighter + 0.05) / (darker + 0.05)

    @staticmethod
    def _relative_luminance(rgb: tuple[float, ...]) -> float:
        channels = []
        for value in rgb:
            c = value / 255
            channels.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
        r, g, b = channels[:3]
        return 0.2126 * r + 0.7152 * g + 0.0722 * b


def mask_area(mask: Image.Image) -> int:
    return int(ImageStat.Stat(mask).sum[0] / 255)
