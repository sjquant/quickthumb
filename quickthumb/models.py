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
    SCREEN = "screen"
    DARKEN = "darken"
    LIGHTEN = "lighten"
    NORMAL = "normal"


class FitMode(Enum):
    COVER = "cover"
    CONTAIN = "contain"
    FILL = "fill"


class LinearGradient(BaseModel):
    type: Literal["linear"] = "linear"
    angle: float
    stops: list[tuple[str, float]]


class RadialGradient(BaseModel):
    type: Literal["radial"] = "radial"
    stops: list[tuple[str, float]]
    center: tuple[float, float] = (0.5, 0.5)


class Stroke(BaseModel):
    type: Literal["stroke"] = "stroke"
    width: int
    color: str

    @field_validator("width")
    @classmethod
    def validate_width(cls, v: int) -> int:
        if v <= 0:
            raise ValidationError("stroke width must be positive")
        return v

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: str) -> str:
        validate_hex_color(v)
        return v


class Shadow(BaseModel):
    type: Literal["shadow"] = "shadow"
    offset_x: int
    offset_y: int
    color: str
    blur_radius: int = 0

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: str) -> str:
        validate_hex_color(v)
        return v

    @field_validator("blur_radius")
    @classmethod
    def validate_blur_radius(cls, v: int) -> int:
        if v < 0:
            raise ValidationError("blur_radius cannot be negative")
        return v


class Glow(BaseModel):
    type: Literal["glow"] = "glow"
    color: str
    radius: int
    opacity: float = 1.0

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: str) -> str:
        validate_hex_color(v)
        return v

    @field_validator("radius")
    @classmethod
    def validate_radius(cls, v: int) -> int:
        if v <= 0:
            raise ValidationError("radius must be positive")
        return v

    @field_validator("opacity")
    @classmethod
    def validate_opacity(cls, v: float) -> float:
        if v < 0.0 or v > 1.0:
            raise ValidationError("opacity must be between 0.0 and 1.0")
        return v


TextEffect = Stroke | Shadow | Glow


class TextPart(BaseModel):
    text: str
    color: str | None = None
    effects: list[TextEffect] = []

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: str | None) -> str | None:
        if v is None:
            return v

        validate_hex_color(v)
        return v

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        if not v:
            raise ValidationError("text field cannot be empty")
        return v


class BackgroundLayer(BaseModel):
    type: Literal["background"]
    color: str | tuple | None = None
    gradient: LinearGradient | RadialGradient | None = None
    image: str | None = None
    opacity: float = 1.0
    blend_mode: BlendMode | str | None = None
    fit: FitMode | str | None = None
    brightness: float = 1.0

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

    @field_validator("fit", mode="before")
    @classmethod
    def validate_fit(cls, v: FitMode | str | None) -> FitMode | None:
        if v is None:
            return v

        if isinstance(v, FitMode):
            return v

        if isinstance(v, str):
            try:
                return FitMode(v)
            except ValueError as e:
                raise ValidationError(f"unsupported fit mode: {v}") from e

        raise ValidationError(f"unsupported fit mode: {v}")

    @field_validator("brightness")
    @classmethod
    def validate_brightness(cls, v: float) -> float:
        if v < 0.0:
            raise ValidationError("brightness must be >= 0.0")
        return v


class TextLayer(BaseModel):
    type: Literal["text"]
    content: str | list[TextPart]
    font: str | None = None
    size: int | None = None
    color: str | None = None
    position: tuple | None = None
    align: tuple | None = None
    bold: bool = False
    italic: bool = False
    max_width: int | str | None = None
    effects: list[TextEffect] = []
    line_height: float | None = None
    letter_spacing: int | None = None

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str | list[TextPart]) -> str | list[TextPart]:
        if isinstance(v, list) and len(v) == 0:
            raise ValidationError("content list cannot be empty")
        return v

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
                if isinstance(item, str):
                    match = re.fullmatch(r"-?(\d+(\.\d+)?)%", item)
                    if not match:
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

    @field_validator("size")
    @classmethod
    def validate_size(cls, v: int | None) -> int | None:
        if v is None:
            return v

        if v <= 0:
            raise ValidationError("size must be positive")

        return v

    @field_validator("max_width")
    @classmethod
    def validate_max_width(cls, v: int | str | None) -> int | str | None:
        if v is None:
            return v

        if isinstance(v, str):
            match = re.fullmatch(r"(\d+(\.\d+)?)%", v)
            if not match:
                raise ValidationError(f"invalid percentage format: {v}")
            percentage = float(match.group(1))
            if percentage <= 0:
                raise ValidationError("max_width percentage must be positive")
            return v

        if v <= 0:
            raise ValidationError("max_width must be positive")

        return v

    @field_validator("line_height")
    @classmethod
    def validate_line_height(cls, v: float | None) -> float | None:
        if v is None:
            return v

        if v <= 0:
            raise ValidationError("line_height must be positive")

        return v


class OutlineLayer(BaseModel):
    type: Literal["outline"]
    width: int
    color: str
    offset: int = 0

    @field_validator("width")
    @classmethod
    def validate_width(cls, v: int) -> int:
        if v <= 0:
            raise ValidationError("width must be positive")
        return v

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: str) -> str:
        validate_hex_color(v)
        return v

    @field_validator("offset")
    @classmethod
    def validate_offset(cls, v: int) -> int:
        if v < 0:
            raise ValidationError("offset cannot be negative")
        return v


LayerType = BackgroundLayer | TextLayer | OutlineLayer


class CanvasModel(BaseModel):
    width: int
    height: int
    layers: list[LayerType]
