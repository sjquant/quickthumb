import os
from typing import Self

from quickthumb.errors import ValidationError
from quickthumb.models import BackgroundLayer, BlendMode, LinearGradient


class Canvas:
    def __init__(self, width: int, height: int):
        if width <= 0:
            raise ValidationError("width must be > 0")
        if height <= 0:
            raise ValidationError("height must be > 0")

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
