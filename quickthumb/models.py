import re
from enum import Enum

from pydantic import BaseModel, field_validator

from quickthumb.errors import ValidationError

HEX_COLOR_PATTERN = r"^#[0-9A-Fa-f]{6}([0-9A-Fa-f]{2})?$"


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
                raise ValidationError(f"invalid hex color: {v}")
        elif isinstance(v, tuple):
            if len(v) not in (3, 4):
                raise ValidationError(f"invalid color tuple: {v}")
        else:
            raise ValidationError(f"invalid color format: {v}")

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
                raise ValidationError(f"unsupported blend mode: {v}") from e

        raise ValidationError(f"unsupported blend mode: {v}")
