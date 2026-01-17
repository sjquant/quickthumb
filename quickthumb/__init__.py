import os
import re
from enum import Enum
from typing import TypedDict

HEX_COLOR_PATTERN = r"^#[0-9A-Fa-f]{6}([0-9A-Fa-f]{2})?$"


class QuickthumbError(Exception):
    pass


class CanvasValidationError(QuickthumbError):
    pass


class BackgroundValidationError(QuickthumbError):
    pass


class BlendMode(Enum):
    MULTIPLY = "multiply"
    OVERLAY = "overlay"


class LinearGradient:
    def __init__(self, angle: float, color_stops: list[tuple[str, float]]):
        self.angle = angle
        self.color_stops = color_stops


class BackgroundLayer(TypedDict, total=False):
    type: str
    color: str | tuple | None
    gradient: LinearGradient | None
    image: str | None
    opacity: float
    blend_mode: BlendMode | None


class Canvas:
    def __init__(self, width: int, height: int):
        if width <= 0:
            raise CanvasValidationError("width must be > 0")
        if height <= 0:
            raise CanvasValidationError("height must be > 0")

        self.width = width
        self.height = height
        self._layers: list[BackgroundLayer] = []

    @property
    def layers(self) -> list[BackgroundLayer]:
        return self._layers

    @classmethod
    def from_aspect_ratio(cls, ratio: str, base_width: int):
        width_ratio, height_ratio = ratio.split(":")
        calculated_height = int(base_width * int(height_ratio) / int(width_ratio))
        return cls(base_width, calculated_height)

    def background(
        self,
        color: str | tuple | None = None,
        gradient: LinearGradient | None = None,
        image: str | None = None,
        opacity: float = 1.0,
        blend_mode: BlendMode | str | None = None,
    ):
        if color is not None:
            self._validate_color(color)

        if blend_mode is not None:
            blend_mode = self._validate_blend_mode(blend_mode)

        layer: BackgroundLayer = {
            "type": "background",
            "color": color,
            "gradient": gradient,
            "image": image,
            "opacity": opacity,
            "blend_mode": blend_mode,
        }
        self._layers.append(layer)

    def render(self, output_path: str):
        for layer in self._layers:
            if layer.get("image") and not os.path.exists(layer["image"]):
                raise FileNotFoundError(f"{layer['image']}")

    def _validate_color(self, color: str | tuple):
        if isinstance(color, str):
            if not re.match(HEX_COLOR_PATTERN, color):
                raise BackgroundValidationError(f"invalid hex color: {color}")
        elif isinstance(color, tuple):
            if len(color) not in (3, 4):
                raise BackgroundValidationError(f"invalid color tuple: {color}")
        else:
            raise BackgroundValidationError(f"invalid color format: {color}")

    def _validate_blend_mode(self, blend_mode: BlendMode | str) -> BlendMode | None:
        if isinstance(blend_mode, BlendMode):
            return blend_mode
        if isinstance(blend_mode, str):
            try:
                return BlendMode(blend_mode)
            except ValueError as e:
                raise BackgroundValidationError(f"unsupported blend mode: {blend_mode}") from e
        raise BackgroundValidationError(f"unsupported blend mode: {blend_mode}")


__all__ = [
    "Canvas",
    "CanvasValidationError",
    "BackgroundValidationError",
    "BlendMode",
    "LinearGradient",
]
