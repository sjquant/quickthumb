from typing import Literal, cast

from PIL import ImageFont

from quickthumb.models import Align

FileFormat = Literal["JPEG", "WEBP", "PNG"]

DEFAULT_TEXT_SIZE = 16
DEFAULT_TEXT_COLOR = (0, 0, 0)
DEFAULT_LINE_HEIGHT_MULTIPLIER = 1.2
FULL_OPACITY = 255
LINE_HEIGHT_REFERENCE = "Aby"

FontType = ImageFont.FreeTypeFont | ImageFont.ImageFont


class RenderContext:
    """Canvas-wide state shared by the render engines."""

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.svg_raster_cache: dict = {}


def parse_coordinate(value: int | str, dimension: int) -> int:
    """Resolve a pixel or percentage coordinate ("50%") against a canvas dimension."""
    if isinstance(value, int):
        return value

    percentage = float(value.rstrip("%"))
    return int(dimension * percentage / 100)


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
