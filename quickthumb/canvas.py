import os
from contextlib import contextmanager

import pydantic_core
from typing_extensions import Self

from quickthumb.errors import ValidationError
from quickthumb.models import (
    BackgroundLayer,
    BlendMode,
    CanvasModel,
    LayerType,
    LinearGradient,
    TextLayer,
)


@contextmanager
def convert_pydantic_errors():
    try:
        yield
    except pydantic_core.ValidationError as e:
        errors = e.errors()
        if errors:
            error_locs = ",".join(errors[0].get("loc", []))
            error_msg = errors[0].get("msg", "validation error")
            final_msg = f"{error_locs}: {error_msg}" if error_locs else error_msg
            raise ValidationError(final_msg) from e
        raise ValidationError("validation error") from e


class Canvas:
    def __init__(self, width: int, height: int, layers: list[LayerType] | None = None):
        if width <= 0:
            raise ValidationError("width must be > 0")
        if height <= 0:
            raise ValidationError("height must be > 0")

        self.width = width
        self.height = height
        self._layers: list[LayerType] = layers or []

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
        with convert_pydantic_errors():
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
        with convert_pydantic_errors():
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

    def to_json(self) -> str:
        return CanvasModel(
            width=self.width, height=self.height, layers=self._layers
        ).model_dump_json()

    @classmethod
    def from_json(cls, data: str) -> Self:
        with convert_pydantic_errors():
            canvas_model = CanvasModel.model_validate_json(data)
        return cls(width=canvas_model.width, height=canvas_model.height, layers=canvas_model.layers)
