import re
from enum import Enum
from typing import Annotated, Any, Literal, TypeVar

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    Discriminator,
    NonNegativeInt,
    PositiveFloat,
    PositiveInt,
    field_serializer,
    field_validator,
    model_validator,
)
from pydantic import ValidationError as PydanticValidationError

from quickthumb.errors import ValidationError

HEX_COLOR_PATTERN = r"^#[0-9A-Fa-f]{6}([0-9A-Fa-f]{2})?$"


def validate_hex_color(color: str) -> str:
    """Validate hex color format and return the color string."""
    if not re.match(HEX_COLOR_PATTERN, color):
        raise ValueError(f"invalid hex color: {color}")
    return color


# Reusable color type with validation
HexColor = Annotated[str, AfterValidator(validate_hex_color)]


# Generic enum converter
E = TypeVar("E", bound=Enum)


def enum_converter(enum_class: type[E]) -> Any:
    """Create a validator function that converts strings to enum values."""

    def convert(v: E | str) -> E:
        if isinstance(v, enum_class):
            return v
        try:
            return enum_class(v)
        except ValueError as e:
            raise ValueError(f"unsupported {enum_class.__name__.lower()}: {v}") from e

    return convert


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


class Align(Enum):
    """Text alignment enum supporting all 9 combinations of horizontal and vertical alignment."""

    CENTER = "center"
    TOP_LEFT = "top-left"
    TOP_CENTER = "top-center"
    TOP_RIGHT = "top-right"
    LEFT = "left"
    RIGHT = "right"
    BOTTOM_LEFT = "bottom-left"
    BOTTOM_CENTER = "bottom-center"
    BOTTOM_RIGHT = "bottom-right"

    def __init__(self, value: str) -> None:
        parts = value.split("-")
        if len(parts) == 2:
            self._vertical, self._horizontal = parts
        elif value in ("left", "right"):
            self._horizontal = value
            self._vertical = "middle"
        else:  # "center"
            self._horizontal = "center"
            self._vertical = "middle"

    @property
    def horizontal(self) -> str:
        return self._horizontal

    @property
    def vertical(self) -> str:
        return self._vertical


def _validate_align_with_hv_tuple(v: Any) -> Align | None:
    """Validate align value accepting (horizontal, vertical) tuple format.

    Used by TextLayer for backward compatibility.
    Accepts: Align enum, string shortcuts, or (horizontal, vertical) tuple.
    """
    if v is None or isinstance(v, Align):
        return v

    if isinstance(v, str):
        try:
            return Align(v)
        except ValueError:
            raise ValueError(f"unsupported align: {v}") from None

    if isinstance(v, (tuple, list)):
        if len(v) != 2:
            raise ValueError("align must be a tuple of two elements")

        horizontal, vertical = v

        if horizontal not in ("left", "center", "right"):
            raise ValueError(f"invalid align value: {horizontal}")
        if vertical not in ("top", "middle", "bottom"):
            raise ValueError(f"invalid align value: {vertical}")

        # Find the enum member matching this (horizontal, vertical) pair
        for member in Align:
            if member.horizontal == horizontal and member.vertical == vertical:
                return member

    raise ValueError(f"invalid align value: {v}")


def _validate_align_with_vh_tuple(v: Any) -> Align:
    """Validate align value accepting (vertical, horizontal) tuple format.

    Used by ImageLayer for backward compatibility.
    Accepts: Align enum, string shortcuts, or (vertical, horizontal) tuple.
    """
    if isinstance(v, Align):
        return v

    if isinstance(v, str):
        try:
            return Align(v)
        except ValueError:
            raise ValueError(f"unsupported align: {v}") from None

    if isinstance(v, (tuple, list)):
        if len(v) != 2:
            raise ValueError("align must be a tuple of two elements")

        vertical, horizontal = v

        if vertical not in ("top", "middle", "bottom"):
            raise ValueError(f"invalid align value: {vertical}")
        if horizontal not in ("left", "center", "right"):
            raise ValueError(f"invalid align value: {horizontal}")

        # Find the enum member matching this (vertical, horizontal) pair
        for member in Align:
            if member.vertical == vertical and member.horizontal == horizontal:
                return member

    raise ValueError(f"invalid align value: {v}")


AlignWithHVTuple = Annotated[Align | None, BeforeValidator(_validate_align_with_hv_tuple)]
AlignWithVHTuple = Annotated[Align, BeforeValidator(_validate_align_with_vh_tuple)]


class QuickThumbModel(BaseModel):
    @model_validator(mode="wrap")
    @classmethod
    def handle_pydantic_error(cls, data: Any, handler):
        try:
            return handler(data)
        except PydanticValidationError as e:
            error_messages = []
            for err in e.errors():
                field = " -> ".join(map(str, err["loc"]))
                msg = err["msg"]
                error_messages.append(f"Field '{field}': {msg}")

            formatted_msg = " | ".join(error_messages)
            raise ValidationError(formatted_msg, original_error=e) from e


class LinearGradient(QuickThumbModel):
    type: Literal["linear"] = "linear"
    angle: float
    stops: list[tuple[str, float]]


class RadialGradient(QuickThumbModel):
    type: Literal["radial"] = "radial"
    stops: list[tuple[str, float]]
    center: tuple[float, float] = (0.5, 0.5)


class Stroke(QuickThumbModel):
    type: Literal["stroke"] = "stroke"
    width: PositiveInt
    color: HexColor


class Shadow(QuickThumbModel):
    type: Literal["shadow"] = "shadow"
    offset_x: int
    offset_y: int
    color: HexColor
    blur_radius: int = 0

    @field_validator("blur_radius")
    @classmethod
    def validate_blur_radius(cls, v: int) -> int:
        if v < 0:
            raise ValueError("blur_radius cannot be negative")
        return v


class Glow(QuickThumbModel):
    type: Literal["glow"] = "glow"
    color: HexColor
    radius: PositiveInt
    opacity: float = 1.0

    @field_validator("opacity")
    @classmethod
    def validate_opacity(cls, v: float) -> float:
        if v < 0.0 or v > 1.0:
            raise ValueError("opacity must be between 0.0 and 1.0")
        return v


class Background(QuickThumbModel):
    type: Literal["background"] = "background"
    color: HexColor
    padding: int | tuple[int, int] | tuple[int, int, int, int] = 0
    border_radius: int = 0
    opacity: float = 1.0

    @field_validator("padding")
    @classmethod
    def validate_padding(
        cls, v: int | tuple[int, int] | tuple[int, int, int, int]
    ) -> int | tuple[int, int] | tuple[int, int, int, int]:
        if isinstance(v, int):
            if v < 0:
                raise ValueError("padding cannot be negative")
            return v

        if isinstance(v, tuple):
            if len(v) not in (2, 4):
                raise ValueError("padding tuple must have 2 or 4 elements")
            for val in v:
                if val < 0:
                    raise ValueError("padding values cannot be negative")

        return v

    @field_validator("border_radius")
    @classmethod
    def validate_border_radius(cls, v: int) -> int:
        if v < 0:
            raise ValueError("border_radius cannot be negative")
        return v

    @field_validator("opacity")
    @classmethod
    def validate_opacity(cls, v: float) -> float:
        if v < 0.0 or v > 1.0:
            raise ValueError("opacity must be between 0.0 and 1.0")
        return v


TextEffect = Annotated[Stroke | Shadow | Glow | Background, Discriminator("type")]

ImageEffect = Shadow


class TextPart(QuickThumbModel):
    text: str
    color: HexColor | None = None
    effects: list[TextEffect] = []
    size: PositiveInt | None = None
    bold: bool | None = None
    italic: bool | None = None
    weight: int | str | None = None
    line_height: PositiveFloat | None = None
    letter_spacing: int | None = None
    font: str | None = None

    @model_validator(mode="after")
    def validate_weight_bold_mutual_exclusivity(self) -> "TextPart":
        if self.weight is not None and self.bold is True:
            raise ValidationError("cannot specify both weight and bold parameters")
        return self

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        if not v:
            raise ValueError("text field cannot be empty")
        return v


class BackgroundLayer(QuickThumbModel):
    type: Literal["background"]
    color: HexColor | tuple | None = None
    gradient: Annotated[LinearGradient | RadialGradient, Discriminator("type")] | None = None
    image: str | None = None
    opacity: float = 1.0
    blend_mode: Annotated[
        BlendMode | None, AfterValidator(lambda v: enum_converter(BlendMode)(v) if v else None)
    ] = None
    fit: Annotated[
        FitMode | None, AfterValidator(lambda v: enum_converter(FitMode)(v) if v else None)
    ] = None
    brightness: PositiveFloat = 1.0
    blur: int = 0
    contrast: PositiveFloat = 1.0
    saturation: float = 1.0

    @field_validator("blur")
    @classmethod
    def validate_blur(cls, v: int) -> int:
        if v < 0:
            raise ValueError("blur must be non-negative")
        return v

    @field_validator("saturation")
    @classmethod
    def validate_saturation(cls, v: float) -> float:
        if v < 0.0:
            raise ValueError("saturation must be non-negative")
        return v

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: str | tuple | None) -> str | tuple | None:
        if v is None:
            return v

        # HexColor validation already applied to str, just validate tuple
        if isinstance(v, tuple) and len(v) not in (3, 4):
            raise ValueError(f"invalid color tuple: {v}")

        return v


class TextLayer(QuickThumbModel):
    type: Literal["text"]
    content: str | list[TextPart]
    font: str | None = None
    size: PositiveInt | None = None
    color: HexColor | None = None
    position: tuple | None = None
    align: AlignWithHVTuple = None
    bold: bool = False
    italic: bool = False
    weight: int | str | None = None
    max_width: int | str | None = None
    effects: list[TextEffect] = []
    line_height: PositiveFloat | None = None
    letter_spacing: int | None = None
    auto_scale: bool = False
    rotation: float = 0.0

    @field_validator("max_width")
    @classmethod
    def validate_max_width(cls, v: int | str | None) -> int | str | None:
        if v is None:
            return v

        if isinstance(v, str):
            match = re.fullmatch(r"(\d+(\.\d+)?)%", v)
            if not match:
                raise ValueError(f"invalid percentage format: {v}")
            percentage = float(match.group(1))
            if percentage <= 0:
                raise ValueError("max_width must be positive")
            return v

        if v <= 0:
            raise ValueError("max_width must be positive")

        return v

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str | list[TextPart]) -> str | list[TextPart]:
        if isinstance(v, list) and len(v) == 0:
            raise ValueError("content list cannot be empty")
        return v

    @model_validator(mode="after")
    def validate_weight_bold_mutual_exclusivity(self) -> "TextLayer":
        if self.weight is not None and self.bold is True:
            raise ValidationError("cannot specify both weight and bold parameters")
        return self

    @model_validator(mode="after")
    def validate_auto_scale_requires_max_width(self) -> "TextLayer":
        if self.auto_scale and not self.max_width:
            raise ValidationError("auto_scale requires max_width to be set")
        return self

    @field_validator("position", mode="before")
    @classmethod
    def validate_position(cls, v: tuple | list | None) -> tuple | None:
        if v is None:
            return v

        if not isinstance(v, (tuple, list)) or len(v) != 2:
            raise ValueError("position must be a tuple of two elements")

        if isinstance(v[0], str) or isinstance(v[1], str):
            for item in v:
                if isinstance(item, str):
                    match = re.fullmatch(r"-?(\d+(\.\d+)?)%", item)
                    if not match:
                        raise ValueError(f"invalid percentage format: {item}")

        return tuple(v)

    @field_serializer("align")
    def serialize_align(self, align: Align | None) -> str | None:
        """Serialize TextAlign to its string value for JSON."""
        if align is None:
            return None
        return align.value


class OutlineLayer(QuickThumbModel):
    type: Literal["outline"]
    width: PositiveInt
    color: HexColor
    offset: NonNegativeInt = 0


class ImageLayer(QuickThumbModel):
    type: Literal["image"]
    path: str
    position: tuple
    width: PositiveInt | None = None
    height: PositiveInt | None = None
    opacity: float = 1.0
    rotation: float = 0
    remove_background: bool = False
    align: AlignWithVHTuple = Align.TOP_LEFT
    border_radius: NonNegativeInt = 0
    effects: list[ImageEffect] = []

    @field_validator("position", mode="before")
    @classmethod
    def validate_position(cls, v: tuple | list | None) -> tuple | None:
        if v is None:
            raise ValueError("position is required")

        if not isinstance(v, (tuple, list)) or len(v) != 2:
            raise ValueError("position must be a tuple of two elements")

        if isinstance(v[0], str) or isinstance(v[1], str):
            for item in v:
                if isinstance(item, str):
                    match = re.fullmatch(r"-?(\d+(\.\d+)?)%", item)
                    if not match:
                        raise ValueError(f"invalid percentage format: {item}")

        return tuple(v)

    @field_validator("opacity")
    @classmethod
    def validate_opacity(cls, v: float) -> float:
        if v < 0.0 or v > 1.0:
            raise ValueError("opacity must be between 0.0 and 1.0")
        return v

    @field_serializer("align")
    def serialize_align(self, align: Align) -> str:
        """Serialize TextAlign to its string value for JSON."""
        return align.value


class ShapeLayer(QuickThumbModel):
    type: Literal["shape"]
    shape: Literal["rectangle", "ellipse"]
    position: tuple
    width: PositiveInt
    height: PositiveInt
    color: HexColor
    stroke_color: HexColor | None = None
    stroke_width: PositiveInt | None = None
    border_radius: NonNegativeInt = 0
    opacity: float = 1.0
    rotation: float = 0.0
    align: AlignWithHVTuple = None

    @field_validator("position", mode="before")
    @classmethod
    def validate_position(cls, v: tuple | list | None) -> tuple | None:
        if v is None:
            raise ValueError("position is required")

        if not isinstance(v, (tuple, list)) or len(v) != 2:
            raise ValueError("position must be a tuple of two elements")

        if isinstance(v[0], str) or isinstance(v[1], str):
            for item in v:
                if isinstance(item, str):
                    match = re.fullmatch(r"-?(\d+(\.\d+)?)%", item)
                    if not match:
                        raise ValueError(f"invalid percentage format: {item}")

        return tuple(v)

    @field_validator("opacity")
    @classmethod
    def validate_opacity(cls, v: float) -> float:
        if v < 0.0 or v > 1.0:
            raise ValueError("opacity must be between 0.0 and 1.0")
        return v

    @field_serializer("align")
    def serialize_align(self, align: Align | None) -> str | None:
        if align is None:
            return None
        return align.value


LayerType = Annotated[
    BackgroundLayer | TextLayer | OutlineLayer | ImageLayer | ShapeLayer,
    Discriminator("type"),
]


class CanvasModel(QuickThumbModel):
    width: int
    height: int
    layers: list[LayerType]
