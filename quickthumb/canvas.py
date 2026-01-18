import os

from typing_extensions import Self

from quickthumb.errors import ValidationError
from quickthumb.models import BackgroundLayer, BlendMode, LinearGradient, TextLayer

LayerType = BackgroundLayer | TextLayer


class Canvas:
    def __init__(self, width: int, height: int):
        if width <= 0:
            raise ValidationError("width must be > 0")
        if height <= 0:
            raise ValidationError("height must be > 0")

        self.width = width
        self.height = height
        self._layers: list[LayerType] = []

    @property
    def layers(self) -> list[LayerType]:
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

    def text(
        self,
        content: str,
        font: str | None = None,
        size: int | None = None,
        color: str | None = None,
        position: tuple[int, int] | tuple[str, str] | None = None,
        align: tuple[str, str] | None = None,
        stroke: tuple[int, str] | None = None,
        bold: bool = False,
        italic: bool = False,
    ) -> Self:
        layer = TextLayer(
            type="text",
            content=content,
            font=font,
            size=size,
            color=color,
            position=position,
            align=align,
            stroke=stroke,
            bold=bold,
            italic=italic,
        )
        self._layers.append(layer)
        return self

    def render(self, output_path: str):
        for layer in self._layers:
            if (
                isinstance(layer, BackgroundLayer)
                and layer.image
                and not os.path.exists(layer.image)
            ):
                raise FileNotFoundError(f"{layer.image}")
