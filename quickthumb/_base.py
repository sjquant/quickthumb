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
    _layers: list

    def _render_layer(self, image, layer):  # pragma: no cover - implemented by Canvas
        raise NotImplementedError

    def _validate_image_paths(self):  # pragma: no cover - implemented by Canvas
        raise NotImplementedError

    def _create_canvas(self):  # pragma: no cover - implemented by Canvas
        raise NotImplementedError
