from typing import Literal

from PIL import ImageFont

FileFormat = Literal["JPEG", "WEBP", "PNG"]

DEFAULT_TEXT_SIZE = 16
DEFAULT_TEXT_COLOR = (0, 0, 0)
DEFAULT_LINE_HEIGHT_MULTIPLIER = 1.2
FULL_OPACITY = 255
LINE_HEIGHT_REFERENCE = "Aby"

FontType = ImageFont.FreeTypeFont | ImageFont.ImageFont


class CanvasBase:
    """Shared attribute declarations for canvas render mixins."""

    width: int
    height: int
