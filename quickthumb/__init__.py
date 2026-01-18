import os
import re
from enum import Enum
from typing import Any, Self

from pydantic import BaseModel, field_validator

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


class BackgroundLayer(BaseModel):
    type: str
    color: str | tuple | None = None
    gradient: LinearGradient | None = None
    image: str | None = None
    opacity: float = 1.0
    blend_mode: BlendMode | str | None = None

    model_config = {"arbitrary_types_allowed": True}

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: str | tuple | None) -> str | tuple | None:
        if v is None:
            return v

        if isinstance(v, str):
            if not re.match(HEX_COLOR_PATTERN, v):
                raise BackgroundValidationError(f"invalid hex color: {v}")
        elif isinstance(v, tuple):
            if len(v) not in (3, 4):
                raise BackgroundValidationError(f"invalid color tuple: {v}")
        else:
            raise BackgroundValidationError(f"invalid color format: {v}")

        return v

    @field_validator("blend_mode", mode="before")
    @classmethod
    def validate_blend_mode(cls, v: BlendMode | str | None) -> BlendMode | None:
        print(f"validate_blend_mode: {v}")
        if v is None:
            return v

        if isinstance(v, BlendMode):
            return v

        if isinstance(v, str):
            try:
                return BlendMode(v)
            except ValueError as e:
                raise BackgroundValidationError(f"unsupported blend mode: {v}") from e

        raise BackgroundValidationError(f"unsupported blend mode: {v}")


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
    ) -> Self:
        layer = BackgroundLayer(
            type="background",
            color=color,
            gradient=gradient,
            image=image,
            opacity=opacity,
            blend_mode=blend_mode,
        )
        self._layers.append(layer)
        return self

    def render(self, output_path: str):
        for layer in self._layers:
            if layer.image and not os.path.exists(layer.image):
                raise FileNotFoundError(f"{layer.image}")


__all__ = [
    "Canvas",
    "CanvasValidationError",
    "BackgroundValidationError",
    "BackgroundLayer",
    "BlendMode",
    "LinearGradient",
]
