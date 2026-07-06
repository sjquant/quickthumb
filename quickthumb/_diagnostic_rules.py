from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import cast

from PIL import Image, ImageChops, ImageStat
from typing_extensions import TypedDict

from quickthumb._composition import has_layer_composition
from quickthumb._measurements import BBox, LayerMeasurement
from quickthumb.models import Align, DiagnosticBBox


class DiagnosticContext(TypedDict):
    """Keyword payload shared by diagnostics for a single measured layer."""

    layer_id: str
    layer_name: str | None
    bbox: DiagnosticBBox | None
    related_layers: list[str]


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


@dataclass(frozen=True)
class TiledContrastMeasurement:
    """Worst contrast found by sampling a region in tiles."""

    contrast: float
    foreground: tuple[float, float, float]
    background: tuple[float, float, float]
    tile: BBox
    tile_count: int


@dataclass(frozen=True)
class SafeMarginOverlay:
    """A platform UI region that should stay clear of important layer pixels."""

    name: str
    label: str
    bounds: tuple[float, float, float, float]


@dataclass(frozen=True)
class SafeMarginPreset:
    """Canvas preset dimensions and safe regions for a publishing platform."""

    name: str
    width: int
    height: int
    margins: tuple[float, float, float, float]
    overlays: tuple[SafeMarginOverlay, ...] = ()


YOUTUBE_THUMBNAIL_PRESET = SafeMarginPreset(
    name="youtube-thumbnail",
    width=1280,
    height=720,
    margins=(0.05, 0.05, 0.08, 0.05),
    overlays=(
        SafeMarginOverlay(
            name="duration-badge",
            label="duration badge",
            bounds=(0.84, 0.86, 0.14, 0.10),
        ),
    ),
)
YOUTUBE_SHORTS_PRESET = SafeMarginPreset(
    name="youtube-shorts",
    width=1080,
    height=1920,
    margins=(0.14, 0.08, 0.18, 0.08),
    overlays=(
        SafeMarginOverlay(
            name="right-rail",
            label="right action rail",
            bounds=(0.86, 0.42, 0.12, 0.40),
        ),
        SafeMarginOverlay(
            name="caption-area",
            label="caption area",
            bounds=(0.05, 0.80, 0.72, 0.12),
        ),
    ),
)
INSTAGRAM_REELS_PRESET = SafeMarginPreset(
    name="instagram-reels",
    width=1080,
    height=1920,
    margins=(0.12, 0.08, 0.16, 0.08),
    overlays=(
        SafeMarginOverlay(
            name="right-rail",
            label="right action rail",
            bounds=(0.86, 0.45, 0.12, 0.36),
        ),
    ),
)
INSTAGRAM_SQUARE_PRESET = SafeMarginPreset(
    name="instagram-square",
    width=1080,
    height=1080,
    margins=(0.07, 0.07, 0.07, 0.07),
)
TIKTOK_PRESET = SafeMarginPreset(
    name="tiktok",
    width=1080,
    height=1920,
    margins=(0.14, 0.08, 0.18, 0.08),
    overlays=(
        SafeMarginOverlay(
            name="right-rail",
            label="right action rail",
            bounds=(0.86, 0.42, 0.12, 0.40),
        ),
        SafeMarginOverlay(
            name="caption-area",
            label="caption area",
            bounds=(0.05, 0.80, 0.72, 0.12),
        ),
    ),
)


PLATFORM_SAFE_MARGIN_PRESETS: dict[str, SafeMarginPreset] = {
    "youtube": YOUTUBE_THUMBNAIL_PRESET,
    "youtube-thumbnail": YOUTUBE_THUMBNAIL_PRESET,
    "youtube-shorts": YOUTUBE_SHORTS_PRESET,
    "instagram-square": INSTAGRAM_SQUARE_PRESET,
    "instagram-reel": INSTAGRAM_REELS_PRESET,
    "instagram-reels": INSTAGRAM_REELS_PRESET,
    "tiktok": TIKTOK_PRESET,
}


def bbox_payload(box: BBox) -> dict[str, int]:
    return {
        "x": box.x,
        "y": box.y,
        "width": box.width,
        "height": box.height,
    }


def diagnostic_context(measured: LayerMeasurement) -> DiagnosticContext:
    box = measured.bbox
    return {
        "layer_id": measured.layer_id,
        "layer_name": measured.name,
        "bbox": DiagnosticBBox(**bbox_payload(box)) if box is not None else None,
        "related_layers": [measured.layer_id],
    }


def require_bbox(measured: LayerMeasurement) -> BBox:
    box = measured.bbox
    assert box is not None and not box.is_empty
    return box


def layer_label(measured: LayerMeasurement) -> str:
    return f"{measured.layer_type} layer {measured.layer_id}"


def visible_leaf_layers(measurements: Iterable[LayerMeasurement]) -> Iterable[LayerMeasurement]:
    for measured in measurements:
        if measured.children and not has_layer_composition(measured.raw_layer):
            yield from visible_leaf_layers(measured.children)
        elif measured.visible and measured.bbox is not None and not measured.bbox.is_empty:
            yield measured


def overlap_pairs(
    candidates: Iterable[LayerMeasurement],
) -> Iterable[tuple[LayerMeasurement, LayerMeasurement]]:
    active: list[tuple[int, LayerMeasurement]] = []
    pairs: list[tuple[int, int, LayerMeasurement, LayerMeasurement]] = []
    sorted_candidates = sorted(
        enumerate(candidates),
        key=lambda item: require_bbox(item[1]).x,
    )

    for candidate_order, candidate in sorted_candidates:
        candidate_box = require_bbox(candidate)
        active = [
            (other_order, other)
            for other_order, other in active
            if require_bbox(other).right > candidate_box.x
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


def move_inside_canvas_suggestion(
    measured: LayerMeasurement, *, canvas_width: int, canvas_height: int
) -> str:
    box = measured.bbox
    assert box is not None
    if box.width > canvas_width or box.height > canvas_height:
        return (
            f"resize layer to fit within the {canvas_width}x{canvas_height} canvas before moving it"
        )

    bbox_x = min(max(box.x, 0), canvas_width - box.width)
    bbox_y = min(max(box.y, 0), canvas_height - box.height)
    x, y = _aligned_position(measured, bbox_x, bbox_y)
    return f"move layer to x={x}, y={y} to fit within the canvas"


def _aligned_position(measured: LayerMeasurement, bbox_x: int, bbox_y: int) -> tuple[int, int]:
    x, y = bbox_x, bbox_y
    align = measured.metadata.get("align")
    if not isinstance(align, Align):
        align = getattr(measured.raw_layer, "align", None)
    if isinstance(align, Align):
        box = require_bbox(measured)
        if align.horizontal == "center":
            x += box.width // 2
        elif align.horizontal == "right":
            x += box.width

        if align.vertical == "middle":
            y += box.height // 2
        elif align.vertical == "bottom":
            y += box.height
    return x, y


def clear_overlap_suggestion(
    upper: LayerMeasurement,
    lower: LayerMeasurement,
    *,
    canvas_width: int,
    canvas_height: int,
    clearance: int,
) -> str:
    upper_box = require_bbox(upper)
    lower_box = require_bbox(lower)

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


def edge_distances(box: BBox, *, canvas_width: int, canvas_height: int) -> dict[str, int]:
    return {
        "left": box.x,
        "top": box.y,
        "right": canvas_width - box.right,
        "bottom": canvas_height - box.bottom,
    }


def resolve_safe_margins(
    preset: SafeMarginPreset | None, *, canvas_width: int, canvas_height: int
) -> tuple[int, int, int, int]:
    if preset is None:
        margin = max(4, round(min(canvas_width, canvas_height) * 0.01))
        return margin, margin, margin, margin

    top, right, bottom, left = preset.margins
    return (
        round(canvas_height * top),
        round(canvas_width * right),
        round(canvas_height * bottom),
        round(canvas_width * left),
    )


def safe_area_bbox(
    *, canvas_width: int, canvas_height: int, margins: tuple[int, int, int, int]
) -> BBox:
    top, right, bottom, left = margins
    return BBox.from_points(left, top, canvas_width - right, canvas_height - bottom)


def resolve_overlay_bbox(
    overlay: SafeMarginOverlay, *, canvas_width: int, canvas_height: int
) -> BBox:
    x, y, width, height = overlay.bounds
    left = round(canvas_width * x)
    top = round(canvas_height * y)
    return BBox(left, top, round(canvas_width * width), round(canvas_height * height))


def move_inside_safe_area_suggestion(
    measured: LayerMeasurement, safe_area: BBox, *, platform: str | None
) -> str:
    box = require_bbox(measured)
    if box.width > safe_area.width or box.height > safe_area.height:
        target = f"{platform} safe area" if platform else "safe area"
        return f"resize layer {measured.index} to fit within the {target}"

    bbox_x = min(max(box.x, safe_area.x), safe_area.right - box.width)
    bbox_y = min(max(box.y, safe_area.y), safe_area.bottom - box.height)
    x, y = _aligned_position(measured, bbox_x, bbox_y)
    target = f"{platform} safe area" if platform else "safe area"
    return f"move layer {measured.index} to x={x}, y={y} to stay inside the {target}"


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
            alpha = LayerAlpha(visible_area=require_bbox(measured).area)
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
            lower_bbox_pct=overlap.area / require_bbox(lower).area,
            upper_bbox_pct=overlap.area / require_bbox(upper).area,
            lower_visible_pct=visible_area / lower_alpha.visible_area,
            upper_visible_pct=visible_area / upper_alpha.visible_area,
        )

    def region_mask(self, measured: LayerMeasurement, region: BBox) -> Image.Image:
        """Return a binary alpha mask for a canvas-space region of one layer."""
        return self._alpha_region(measured, self.get(measured), region)

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
        box = require_bbox(measured)
        left, top = region.x - box.x, region.y - box.y
        mask = alpha.mask.crop((left, top, left + region.width, top + region.height))
        return mask.point(lambda value: 255 if value else 0)


def average_visible_background(
    image: Image.Image, region: BBox, mask: Image.Image | None = None
) -> tuple[float, float, float]:
    crop = image.crop((region.x, region.y, region.right, region.bottom))
    mask_crop = (
        None if mask is None else mask.crop((region.x, region.y, region.right, region.bottom))
    )
    mean_r, mean_g, mean_b, mean_a = ImageStat.Stat(crop, mask=mask_crop).mean

    # Transparent areas read as white, matching JPEG export and typical viewers.
    alpha = mean_a / 255
    return tuple(channel * alpha + 255 * (1 - alpha) for channel in (mean_r, mean_g, mean_b))


def worst_tile_contrast(
    background_image: Image.Image,
    foreground_image: Image.Image,
    region: BBox,
    *,
    tile_size: int,
) -> TiledContrastMeasurement | None:
    """Measure the lowest text-pixel contrast across tiled samples."""
    if tile_size <= 0:
        raise ValueError("tile_size must be positive")

    foreground_alpha = foreground_image.getchannel("A").point(lambda value: 255 if value else 0)
    tile_count = ((region.width + tile_size - 1) // tile_size) * (
        (region.height + tile_size - 1) // tile_size
    )
    background_region = background_image.crop(
        (region.x, region.y, region.right, region.bottom)
    ).convert("RGBA")
    foreground_region = foreground_image.crop(
        (region.x, region.y, region.right, region.bottom)
    ).convert("RGBA")
    foreground_alpha_region = foreground_alpha.crop(
        (region.x, region.y, region.right, region.bottom)
    )

    worst: TiledContrastMeasurement | None = None
    for tile in _tiled_regions(region, tile_size):
        local_tile = BBox(tile.x - region.x, tile.y - region.y, tile.width, tile.height)
        alpha_tile = foreground_alpha_region.crop(
            (local_tile.x, local_tile.y, local_tile.right, local_tile.bottom)
        )
        if alpha_tile.getbbox() is None:
            continue

        measurement = _tile_contrast(
            background_region,
            foreground_region,
            local_tile,
            tile=tile,
            tile_count=tile_count,
        )
        if measurement is not None and (worst is None or measurement.contrast < worst.contrast):
            worst = measurement
    return worst


def _tile_contrast(
    background_region: Image.Image,
    foreground_region: Image.Image,
    region: BBox,
    *,
    tile: BBox,
    tile_count: int,
) -> TiledContrastMeasurement | None:
    background_crop = background_region.crop((region.x, region.y, region.right, region.bottom))
    foreground_crop = foreground_region.crop((region.x, region.y, region.right, region.bottom))
    background_pixels = background_crop.load()
    foreground_pixels = foreground_crop.load()
    assert background_pixels is not None and foreground_pixels is not None
    groups: dict[tuple[int, int, int], list[float]] = {}

    for y in range(region.height):
        for x in range(region.width):
            background_pixel = cast(tuple[int, int, int, int], background_pixels[x, y])
            foreground_pixel = cast(tuple[int, int, int, int], foreground_pixels[x, y])
            foreground_r, foreground_g, foreground_b, foreground_a = foreground_pixel
            if foreground_a == 0:
                continue

            background_alpha = background_pixel[3] / 255
            visible_background = (
                background_pixel[0] * background_alpha + 255 * (1 - background_alpha),
                background_pixel[1] * background_alpha + 255 * (1 - background_alpha),
                background_pixel[2] * background_alpha + 255 * (1 - background_alpha),
            )
            key = (foreground_r, foreground_g, foreground_b)
            group = groups.setdefault(key, [0.0, 0.0, 0.0, 0.0, 0.0])
            group[0] += visible_background[0]
            group[1] += visible_background[1]
            group[2] += visible_background[2]
            group[3] += 1
            group[4] = max(group[4], foreground_a)

    worst: TiledContrastMeasurement | None = None
    for foreground_raw, group in groups.items():
        background = (group[0] / group[3], group[1] / group[3], group[2] / group[3])
        opacity = group[4] / 255
        foreground = (
            foreground_raw[0] * opacity + background[0] * (1 - opacity),
            foreground_raw[1] * opacity + background[1] * (1 - opacity),
            foreground_raw[2] * opacity + background[2] * (1 - opacity),
        )
        contrast = contrast_ratio(foreground, background)
        if worst is None or contrast < worst.contrast:
            worst = TiledContrastMeasurement(
                contrast=contrast,
                foreground=foreground,
                background=background,
                tile=tile,
                tile_count=tile_count,
            )
    return worst


def _tiled_regions(region: BBox, tile_size: int) -> Iterable[BBox]:
    for y in range(region.y, region.bottom, tile_size):
        for x in range(region.x, region.right, tile_size):
            yield BBox.from_points(
                x,
                y,
                min(x + tile_size, region.right),
                min(y + tile_size, region.bottom),
            )


def contrast_ratio(rgb_a: tuple[float, ...], rgb_b: tuple[float, ...]) -> float:
    lum_a = _relative_luminance(rgb_a)
    lum_b = _relative_luminance(rgb_b)
    lighter, darker = max(lum_a, lum_b), min(lum_a, lum_b)
    return (lighter + 0.05) / (darker + 0.05)


def _relative_luminance(rgb: tuple[float, ...]) -> float:
    channels = []
    for value in rgb:
        c = value / 255
        channels.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    r, g, b = channels[:3]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def mask_area(mask: Image.Image) -> int:
    return int(ImageStat.Stat(mask).sum[0] / 255)
