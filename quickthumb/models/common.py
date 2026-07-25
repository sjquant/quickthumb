"""Shared model primitives, validators, enums, and base classes."""

import math
import re
from enum import Enum
from typing import Annotated, Any, Literal, TypeAlias, TypeVar

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    NonNegativeInt,
    PositiveInt,
    WithJsonSchema,
    field_serializer,
    field_validator,
    model_validator,
)
from pydantic import ValidationError as PydanticValidationError

from quickthumb.errors import ValidationError

HEX_COLOR_PATTERN = r"^#[0-9A-Fa-f]{6}([0-9A-Fa-f]{2})?$"
PERCENT_COORDINATE_PATTERN = r"^-?(\d+(\.\d+)?)%$"
POSITIVE_PERCENT_PATTERN = r"^(\d+(\.\d+)?)%$"

PercentCoordinate = Annotated[
    str,
    WithJsonSchema({"type": "string", "pattern": PERCENT_COORDINATE_PATTERN}),
]
PositivePercent = Annotated[
    str,
    WithJsonSchema({"type": "string", "pattern": POSITIVE_PERCENT_PATTERN}),
]
Position = tuple[int | PercentCoordinate, int | PercentCoordinate]
FontSource: TypeAlias = Literal["auto", "system", "google"]
EmojiStyle: TypeAlias = Literal["monochrome", "color"]
FontVariations: TypeAlias = dict[str, float]


def validate_hex_color(color: str) -> str:
    """Validate hex color format and return the color string."""
    if not isinstance(color, str) or not re.match(HEX_COLOR_PATTERN, color):
        raise ValueError(f"invalid hex color: {color}")
    return color


# Reusable color type with validation
HexColor = Annotated[
    str,
    AfterValidator(validate_hex_color),
    WithJsonSchema({"type": "string", "pattern": HEX_COLOR_PATTERN}),
]


def _validate_opacity(v: float) -> float:
    if not math.isfinite(v) or v < 0.0 or v > 1.0:
        raise ValueError("opacity must be between 0.0 and 1.0")
    return v


OpacityField = Annotated[
    float,
    AfterValidator(_validate_opacity),
    WithJsonSchema({"type": "number", "minimum": 0.0, "maximum": 1.0}),
]


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


NormalizedUnitFloat = Annotated[float, Field(ge=0.0, le=1.0)]
PositiveNormalizedUnitFloat = Annotated[float, Field(gt=0.0, le=1.0)]
FocalPoint = tuple[NormalizedUnitFloat, NormalizedUnitFloat]
FiniteNonNegativeFloat = Annotated[float, Field(ge=0.0, allow_inf_nan=False)]
FinitePositiveFloat = Annotated[float, Field(gt=0.0, allow_inf_nan=False)]


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


AlignWithHVTuple = Annotated[
    Align | None,
    BeforeValidator(
        _validate_align_with_hv_tuple,
        json_schema_input_type=Align
        | tuple[Literal["left", "center", "right"], Literal["top", "middle", "bottom"]]
        | None,
    ),
]


class quickthumbModel(BaseModel):  # noqa: N801
    @model_validator(mode="wrap")
    @classmethod
    def handle_pydantic_error(cls, data: Any, handler):
        try:
            return handler(data)
        except PydanticValidationError as e:
            # Let union validation try its remaining branches for values that
            # cannot possibly be instances of this mapping model. Converting a
            # list or scalar here would abort legacy animation unions before
            # their list/string-compatible branch gets a chance to validate.
            if not isinstance(data, (dict, cls)):
                raise
            error_messages = []
            for err in e.errors():
                field = " -> ".join(map(str, err["loc"]))
                msg = err["msg"]
                error_messages.append(f"Field '{field}': {msg}")

            formatted_msg = " | ".join(error_messages)
            raise ValidationError(formatted_msg, original_error=e) from e


QuickThumbModel = quickthumbModel


class _MotionModel(quickthumbModel):
    """Strict base for canonical motion and export policy models."""

    model_config = ConfigDict(extra="forbid")


class FaceRegion(quickthumbModel):
    """Normalized source-image face box used to guide cover crops."""

    x: NormalizedUnitFloat
    y: NormalizedUnitFloat
    width: PositiveNormalizedUnitFloat
    height: PositiveNormalizedUnitFloat

    @model_validator(mode="after")
    def validate_bounds(self) -> "FaceRegion":
        if self.x + self.width > 1.0 or self.y + self.height > 1.0:
            raise ValueError("face region must fit within normalized image bounds")
        return self


def _validate_required_position(v: tuple | list | None) -> Position:
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


class LayerClip(quickthumbModel):
    """Canvas-space rectangle that clips a layer after it is rendered."""

    type: Literal["rect"] = "rect"
    position: Position
    width: PositiveInt
    height: PositiveInt
    border_radius: NonNegativeInt = 0
    align: AlignWithHVTuple = Align.TOP_LEFT

    @field_validator("position", mode="before")
    @classmethod
    def validate_position(cls, v: tuple | list | None) -> Position:
        return _validate_required_position(v)

    @field_serializer("align")
    def serialize_align(self, align: Align | None) -> str | None:
        if align is None:
            return None
        return align.value


class LayerMask(quickthumbModel):
    """Canvas-space alpha mask applied to a layer after it is rendered."""

    type: Literal["shape"] = "shape"
    shape: Literal["rectangle", "ellipse", "pill", "polygon"] = "rectangle"
    position: Position
    width: PositiveInt
    height: PositiveInt
    align: AlignWithHVTuple = Align.TOP_LEFT
    points: list[tuple[float, float]] | None = None
    invert: bool = False
    opacity: OpacityField = 1.0

    @field_validator("position", mode="before")
    @classmethod
    def validate_position(cls, v: tuple | list | None) -> Position:
        return _validate_required_position(v)

    @field_validator("points")
    @classmethod
    def validate_points(
        cls, v: list[tuple[float, float]] | None
    ) -> list[tuple[float, float]] | None:
        if v is None:
            return v
        if len(v) < 3:
            raise ValueError("points must contain at least 3 entries")
        for x, y in v:
            if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0):
                raise ValueError("points coordinates must be normalized between 0.0 and 1.0")
        return v

    @model_validator(mode="after")
    def validate_points_match_shape(self) -> "LayerMask":
        if self.shape == "polygon" and self.points is None:
            raise ValidationError("polygon masks require points")
        if self.shape != "polygon" and self.points is not None:
            raise ValidationError("points is only valid for polygon masks")
        return self

    @field_serializer("align")
    def serialize_align(self, align: Align | None) -> str | None:
        if align is None:
            return None
        return align.value
