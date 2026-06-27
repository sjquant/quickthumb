import math
from typing import Literal, TypeAlias, cast

from PIL import ImageFont

from quickthumb.errors import ValidationError
from quickthumb.models import Align

FileFormat = Literal["JPEG", "WEBP", "PNG"]

DEFAULT_TEXT_SIZE = 16
DEFAULT_TEXT_COLOR = (0, 0, 0)
DEFAULT_LINE_HEIGHT_MULTIPLIER = 1.2
FULL_OPACITY = 255
LINE_HEIGHT_REFERENCE = "Aby"

FontType: TypeAlias = ImageFont.FreeTypeFont | ImageFont.ImageFont


class RenderContext:
    """Canvas-wide state shared by the render engines."""

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.svg_raster_cache: dict = {}
        # measure_cache holds (layer, size) so the keyed id() stays valid for the pass
        self.measure_cache: dict[int, tuple[object, tuple[int, int]]] = {}
        self.image_size_cache: dict[str, tuple[int, int]] = {}

    def begin_render_pass(self):
        """Drop per-pass caches so a new render or diagnose picks up asset changes."""
        self.svg_raster_cache.clear()
        self.measure_cache.clear()
        self.image_size_cache.clear()


def parse_coordinate(value: int | str, dimension: int) -> int:
    """Resolve a pixel or percentage coordinate ("50%") against a canvas dimension."""
    if isinstance(value, int):
        return value

    percentage = float(value.rstrip("%"))
    return int(dimension * percentage / 100)


def aspect_ratio_dimensions(ratio: str, base_width: int) -> tuple[int, int]:
    """Resolve an aspect ratio like "16:9" and a base width into (width, height).

    Raises ValidationError for malformed ratios so callers get the library's
    error type instead of a raw ValueError/ZeroDivisionError.
    """
    parts = ratio.split(":")
    if len(parts) != 2:
        raise ValidationError(
            f"Aspect ratio must look like 'W:H' (for example '16:9'), got {ratio!r}."
        )
    try:
        width_ratio, height_ratio = int(parts[0]), int(parts[1])
    except ValueError:
        raise ValidationError(f"Aspect ratio parts must be integers, got {ratio!r}.") from None
    if width_ratio <= 0 or height_ratio <= 0:
        raise ValidationError(f"Aspect ratio parts must be positive, got {ratio!r}.")
    if base_width <= 0:
        raise ValidationError("base_width must be > 0")
    return base_width, int(base_width * height_ratio / width_ratio)


def is_url(path: str) -> bool:
    return path.startswith("http://") or path.startswith("https://")


def apply_alignment(x: int, y: int, size: tuple[int, int], align: Align) -> tuple[int, int]:
    """Shift an (x, y) anchor so a box of the given size is aligned around it."""
    width, height = size

    if align.horizontal == "center":
        x = x - width // 2
    elif align.horizontal == "right":
        x = x - width

    if align.vertical == "middle":
        y = y - height // 2
    elif align.vertical == "bottom":
        y = y - height

    return x, y


def parse_padding(
    padding: int | tuple[int, int] | tuple[int, int, int, int],
) -> tuple[int, int, int, int]:
    """Expand int / (vertical, horizontal) / (top, right, bottom, left) padding forms."""
    if isinstance(padding, int):
        return (padding, padding, padding, padding)
    if isinstance(padding, tuple) and len(padding) == 2:
        vertical, horizontal = cast(tuple[int, int], padding)
        return (vertical, horizontal, vertical, horizontal)
    return cast(tuple[int, int, int, int], padding)


def expanded_rotation_size(
    size: tuple[int, int], rotation: float, scale: int = 4
) -> tuple[int, int]:
    """Predict the rendered size of a layer rotated with expand=True.

    Mirrors the overlay render path exactly: rotate at `scale`x supersampling about
    the center (PIL corner/ceil-floor arithmetic, right angles transposed), then
    downscale by `scale` with rounding. Use scale=1 for render paths that rotate
    without supersampling (e.g. text layers).
    """
    angle = rotation % 360
    if angle in (0, 180):
        return size
    if angle in (90, 270):
        return size[1], size[0]

    w, h = size[0] * scale, size[1] * scale
    rad = -math.radians(-rotation % 360)
    cos, sin = math.cos(rad), math.sin(rad)
    matrix = [cos, sin, 0.0, -sin, cos, 0.0]
    cx, cy = w / 2.0, h / 2.0
    matrix[2] = cx - (matrix[0] * cx + matrix[1] * cy)
    matrix[5] = cy - (matrix[3] * cx + matrix[4] * cy)
    xs, ys = [], []
    for x, y in ((0, 0), (w, 0), (w, h), (0, h)):
        xs.append(matrix[0] * x + matrix[1] * y + matrix[2])
        ys.append(matrix[3] * x + matrix[4] * y + matrix[5])
    new_w = math.ceil(max(xs)) - math.floor(min(xs))
    new_h = math.ceil(max(ys)) - math.floor(min(ys))
    return round(new_w / scale), round(new_h / scale)
