"""Paint, filter, fill, and layer-effect models."""

# Effect fields use the shared model vocabulary re-exported by ``common``.
# ruff: noqa: F405

from typing import Annotated, Literal

from pydantic import (
    BeforeValidator,
    Discriminator,
    NonNegativeInt,
    PositiveFloat,
    PositiveInt,
    field_validator,
)

from .common import *  # noqa: F401,F403


class LinearGradient(quickthumbModel):
    type: Literal["linear"] = "linear"
    angle: float
    stops: list[tuple[str, float]]


class RadialGradient(quickthumbModel):
    type: Literal["radial"] = "radial"
    stops: list[tuple[str, float]]
    center: tuple[float, float] = (0.5, 0.5)


class TextFillImage(quickthumbModel):
    type: Literal["image"] = "image"
    path: str
    fit: Annotated[
        FitMode, BeforeValidator(lambda v: enum_converter(FitMode)(v) if v else FitMode.COVER)
    ] = FitMode.COVER
    focal_point: FocalPoint | None = None
    faces: list[FaceRegion] = []


TextFill = Annotated[LinearGradient | RadialGradient | TextFillImage, Discriminator("type")]


class Stroke(quickthumbModel):
    type: Literal["stroke"] = "stroke"
    width: PositiveInt
    color: HexColor


class Shadow(quickthumbModel):
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


class Glow(quickthumbModel):
    type: Literal["glow"] = "glow"
    color: HexColor
    radius: PositiveInt
    opacity: OpacityField = 1.0


class Duotone(quickthumbModel):
    type: Literal["duotone"] = "duotone"
    shadows: HexColor
    highlights: HexColor
    opacity: OpacityField = 1.0


class InnerShadow(quickthumbModel):
    type: Literal["inner_shadow"] = "inner_shadow"
    offset_x: int = 0
    offset_y: int = 0
    color: HexColor
    blur_radius: NonNegativeInt = 0
    opacity: OpacityField = 1.0


class BackdropBlur(quickthumbModel):
    type: Literal["backdrop_blur"] = "backdrop_blur"
    radius: PositiveInt
    opacity: OpacityField = 1.0


class Background(quickthumbModel):
    type: Literal["background"] = "background"
    color: HexColor
    padding: int | tuple[int, int] | tuple[int, int, int, int] = 0
    border_radius: int = 0
    opacity: OpacityField = 1.0

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


class Filter(quickthumbModel):
    type: Literal["filter"] = "filter"
    blur: NonNegativeInt = 0
    brightness: PositiveFloat = 1.0
    contrast: PositiveFloat = 1.0
    saturation: float = 1.0

    @field_validator("saturation")
    @classmethod
    def validate_saturation(cls, v: float) -> float:
        if v < 0.0:
            raise ValueError("saturation must be non-negative")
        return v


_GRAIN_BLEND_MODES = frozenset({"overlay", "screen", "multiply", "normal"})


class Grain(quickthumbModel):
    type: Literal["grain"] = "grain"
    intensity: float
    monochrome: bool = True
    blend_mode: str = "overlay"
    opacity: OpacityField = 1.0
    seed: int | None = None

    @field_validator("intensity")
    @classmethod
    def validate_intensity(cls, v: float) -> float:
        if v < 0.0 or v > 1.0:
            raise ValueError("intensity must be between 0.0 and 1.0")
        return v

    @field_validator("blend_mode")
    @classmethod
    def validate_blend_mode(cls, v: str) -> str:
        if v not in _GRAIN_BLEND_MODES:
            raise ValueError(f"blend_mode must be one of: {', '.join(sorted(_GRAIN_BLEND_MODES))}")
        return v


TextEffect = Annotated[Stroke | Shadow | Glow | Background, Discriminator("type")]

ImageEffect = Annotated[
    Stroke | Shadow | Glow | Filter | Grain | Duotone | InnerShadow | BackdropBlur,
    Discriminator("type"),
]

ShapeEffect = Annotated[Stroke | Shadow | Glow | InnerShadow | BackdropBlur, Discriminator("type")]

BackgroundEffect = Annotated[Filter | Grain, Discriminator("type")]
