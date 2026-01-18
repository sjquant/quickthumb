import re
from enum import Enum
from typing import Literal

from pydantic import BaseModel, field_validator

from quickthumb.errors import ValidationError

HEX_COLOR_PATTERN = r"^#[0-9A-Fa-f]{6}([0-9A-Fa-f]{2})?$"


def validate_hex_color(color: str) -> None:
    if not re.match(HEX_COLOR_PATTERN, color):
        raise ValidationError(f"invalid hex color: {color}")


class BlendMode(Enum):
    MULTIPLY = "multiply"
    OVERLAY = "overlay"


class LinearGradient(BaseModel):
    type: Literal["linear"] = "linear"
    angle: float
    stops: list[tuple[str, float]]


class RadialGradient(BaseModel):
    type: Literal["radial"] = "radial"
    stops: list[tuple[str, float]]
    center: tuple[float, float] = (0.5, 0.5)


class BackgroundLayer(BaseModel):
    type: Literal["background"]
    color: str | tuple | None = None
    gradient: LinearGradient | RadialGradient | None = None
    image: str | None = None
    opacity: float = 1.0
    blend_mode: BlendMode | str | None = None

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: str | tuple | None) -> str | tuple | None:
        if v is None:
            return v

        if isinstance(v, str):
            validate_hex_color(v)
        elif isinstance(v, tuple):
            if len(v) not in (3, 4):
                raise ValidationError(f"invalid color tuple: {v}")
        else:
            raise ValidationError(f"invalid color format: {v}")

        return v

    @field_validator("blend_mode", mode="before")
    @classmethod
    def validate_blend_mode(cls, v: BlendMode | str | None) -> BlendMode | None:
        if v is None:
            return v

        if isinstance(v, BlendMode):
            return v

        if isinstance(v, str):
            try:
                return BlendMode(v)
            except ValueError as e:
                raise ValidationError(f"unsupported blend mode: {v}") from e

        raise ValidationError(f"unsupported blend mode: {v}")


class TextLayer(BaseModel):
    type: Literal["text"]
    content: str
    font: str | None = None
    size: int | None = None
    color: str | None = None
    position: tuple | None = None
    align: tuple | None = None
    stroke: tuple | None = None
    bold: bool = False
    italic: bool = False

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: str | None) -> str | None:
        if v is None:
            return v

        validate_hex_color(v)
        return v

    @field_validator("position", mode="before")
    @classmethod
    def validate_position(cls, v: tuple | list | None) -> tuple | None:
        if v is None:
            return v

        if not isinstance(v, (tuple, list)) or len(v) != 2:
            raise ValidationError("position must be a tuple of two elements")

        if isinstance(v[0], str) or isinstance(v[1], str):
            for item in v:
                if isinstance(item, str) and not item.endswith("%"):
                    raise ValidationError(f"invalid percentage format: {item}")

        return tuple(v)

    @field_validator("align", mode="before")
    @classmethod
    def validate_align(cls, v: tuple | list | None) -> tuple | None:
        if v is None:
            return v

        if not isinstance(v, (tuple, list)) or len(v) != 2:
            raise ValidationError("align must be a tuple of two elements")

        valid_horizontal = ("left", "center", "right")
        valid_vertical = ("top", "middle", "bottom")

        if v[0] not in valid_horizontal:
            raise ValidationError(f"invalid align value: {v[0]}")
        if v[1] not in valid_vertical:
            raise ValidationError(f"invalid align value: {v[1]}")

        return tuple(v)

    @field_validator("stroke", mode="before")
    @classmethod
    def validate_stroke(cls, v: tuple | list | None) -> tuple | None:
        if v is None:
            return v

        if not isinstance(v, (tuple, list)) or len(v) != 2:
            raise ValidationError("stroke must be a tuple of width and color")

        width, color = v

        if not isinstance(width, int) or width <= 0:
            raise ValidationError("stroke width must be positive")

        validate_hex_color(color)
        return tuple(v)

    @field_validator("size")
    @classmethod
    def validate_size(cls, v: int | None) -> int | None:
        if v is None:
            return v

        if v <= 0:
            raise ValidationError("size must be positive")

        return v


LayerType = BackgroundLayer | TextLayer


class CanvasModel(BaseModel):
    width: int
    height: int
    layers: list[LayerType]
