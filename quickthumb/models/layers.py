"""Layer and layer-composition models."""

# Layer fields use the shared model vocabulary re-exported by ``common``.
# ruff: noqa: F405

import re
from typing import Annotated, Any, Literal

from pydantic import (
    AfterValidator,
    Discriminator,
    Field,
    NonNegativeInt,
    PositiveFloat,
    PositiveInt,
    field_serializer,
    field_validator,
    model_validator,
)

from quickthumb.errors import ValidationError

from .common import *  # noqa: F401,F403
from .common import _validate_required_position
from .effects import *  # noqa: F401,F403
from .motion import AnimationInput
from .visualizations import ChartLayer, QRCodeLayer


class TextPart(quickthumbModel):
    text: str
    color: HexColor | None = None
    fill: TextFill | None = None
    effects: list[TextEffect] = []
    size: PositiveInt | None = None
    bold: bool | None = None
    italic: bool | None = None
    weight: int | str | None = None
    line_height: PositiveFloat | None = None
    letter_spacing: int | None = None
    font: str | None = None
    font_source: FontSource | None = None
    font_variations: FontVariations | None = None
    emoji_style: EmojiStyle | None = None

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

    @field_validator("font_variations")
    @classmethod
    def validate_font_variations(cls, v: FontVariations | None) -> FontVariations | None:
        if v is None:
            return None
        return _validate_font_variations(v)


class BackgroundLayer(LayerIdentityModel):
    type: Literal["background"]
    color: HexColor | tuple | None = None
    gradient: Annotated[LinearGradient | RadialGradient, Discriminator("type")] | None = None
    image: str | None = None
    opacity: OpacityField = 1.0
    blend_mode: Annotated[
        BlendMode | None, AfterValidator(lambda v: enum_converter(BlendMode)(v) if v else None)
    ] = None
    fit: Annotated[
        FitMode | None, AfterValidator(lambda v: enum_converter(FitMode)(v) if v else None)
    ] = None
    focal_point: FocalPoint | None = None
    faces: list[FaceRegion] = []
    effects: list[BackgroundEffect] = []

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: str | tuple | None) -> str | tuple | None:
        if v is None:
            return v

        # HexColor validation already applied to str, just validate tuple
        if isinstance(v, tuple) and (
            len(v) not in (3, 4) or not all(isinstance(c, int) and 0 <= c <= 255 for c in v)
        ):
            raise ValueError(f"invalid color tuple: {v}")

        return v

    @field_serializer("color")
    def serialize_color(self, v: str | tuple | None) -> str | None:
        if v is None or isinstance(v, str):
            return v
        return "#" + "".join(f"{c:02X}" for c in v)


class TextLayer(LayerIdentityModel):
    type: Literal["text"]
    content: str | list[TextPart]
    font: str | None = None
    font_source: FontSource = "auto"
    font_variations: FontVariations = Field(default_factory=dict)
    emoji_style: EmojiStyle = "monochrome"
    size: PositiveInt | None = None
    color: HexColor | None = None
    fill: TextFill | None = None
    position: Position | None = None
    align: AlignWithHVTuple = None
    bold: bool = False
    italic: bool = False
    weight: int | str | None = None
    max_width: int | PositivePercent | None = None
    max_height: int | PositivePercent | None = None
    min_size: PositiveInt = 1
    balance_lines: bool = False
    effects: list[TextEffect] = []
    line_height: PositiveFloat | None = None
    letter_spacing: int | None = None
    auto_scale: bool = False
    rotation: float = 0.0
    opacity: OpacityField = 1.0
    clip: LayerClip | None = None
    mask: LayerMask | None = None
    animation: AnimationInput | None = None

    @field_validator("max_width")
    @classmethod
    def validate_max_width(cls, v: int | str | None) -> int | str | None:
        return _validate_positive_dimension(v, "max_width")

    @field_validator("max_height")
    @classmethod
    def validate_max_height(cls, v: int | str | None) -> int | str | None:
        return _validate_positive_dimension(v, "max_height")

    @field_validator("font_variations")
    @classmethod
    def validate_font_variations(cls, v: FontVariations) -> FontVariations:
        return _validate_font_variations(v)

    @field_validator("weight")
    @classmethod
    def validate_weight(cls, v: int | str | None) -> int | str | None:
        if isinstance(v, int) and not 1 <= v <= 1000:
            raise ValueError("weight must be between 1 and 1000")
        return v

    @model_validator(mode="after")
    def validate_min_size_not_above_size(self) -> "TextLayer":
        if self.size is not None and self.min_size > self.size:
            raise ValidationError("min_size cannot exceed size")
        return self

    @model_validator(mode="after")
    def validate_balance_lines_requires_width(self) -> "TextLayer":
        if self.balance_lines and not self.max_width:
            raise ValidationError("balance_lines requires max_width to be set")
        return self

    @field_validator("position", mode="before")
    @classmethod
    def validate_position(cls, v: tuple | list | None) -> Position | None:
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
    def validate_auto_scale_requires_bounds(self) -> "TextLayer":
        if self.auto_scale and not (self.max_width or self.max_height):
            raise ValidationError("auto_scale requires max_width or max_height to be set")
        return self

    @field_serializer("align")
    def serialize_align(self, align: Align | None) -> str | None:
        """Serialize TextAlign to its string value for JSON."""
        if align is None:
            return None
        return align.value


def _validate_positive_dimension(v: int | str | None, field_name: str) -> int | str | None:
    if v is None:
        return v

    if isinstance(v, str):
        match = re.fullmatch(r"(\d+(\.\d+)?)%", v)
        if not match:
            raise ValueError(f"invalid percentage format: {v}")
        percentage = float(match.group(1))
        if percentage <= 0:
            raise ValueError(f"{field_name} must be positive")
        return v

    if v <= 0:
        raise ValueError(f"{field_name} must be positive")

    return v


def _validate_font_variations(v: FontVariations) -> FontVariations:
    for axis, value in v.items():
        if not re.fullmatch(r"[A-Za-z0-9]{4}", axis):
            raise ValueError("font_variations axes must be four alphanumeric characters")
        if not isinstance(value, int | float):
            raise ValueError("font_variations values must be numbers")
    return dict(v)


class OutlineLayer(LayerIdentityModel):
    type: Literal["outline"]
    width: PositiveInt
    color: HexColor
    offset: NonNegativeInt = 0
    opacity: OpacityField = 1.0


class ImageLayer(LayerIdentityModel):
    type: Literal["image"]
    path: str
    position: Position
    width: PositiveInt | None = None
    height: PositiveInt | None = None
    opacity: OpacityField = 1.0
    rotation: float = 0.0
    remove_background: bool = False
    align: AlignWithHVTuple = Align.TOP_LEFT
    border_radius: NonNegativeInt = 0
    fit: Annotated[
        FitMode | None, AfterValidator(lambda v: enum_converter(FitMode)(v) if v else None)
    ] = None
    focal_point: FocalPoint | None = None
    faces: list[FaceRegion] = []
    blend_mode: Annotated[
        BlendMode | None, AfterValidator(lambda v: enum_converter(BlendMode)(v) if v else None)
    ] = None
    clip: LayerClip | None = None
    mask: LayerMask | None = None
    effects: list[ImageEffect] = []
    animation: AnimationInput | None = None

    @field_validator("position", mode="before")
    @classmethod
    def validate_position(cls, v: tuple | list | None) -> Position | None:
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

    @field_serializer("align")
    def serialize_align(self, align: Align) -> str:
        """Serialize TextAlign to its string value for JSON."""
        return align.value


class ShapeLayer(LayerIdentityModel):
    type: Literal["shape"]
    shape: Literal["rectangle", "ellipse", "pill", "triangle", "star", "polygon"]
    position: Position
    width: PositiveInt
    height: PositiveInt
    color: HexColor
    border_radius: NonNegativeInt = 0
    opacity: OpacityField = 1.0
    rotation: float = 0.0
    align: AlignWithHVTuple = None
    points: list[tuple[float, float]] | None = None
    star_points: int = 5
    inner_radius: float = 0.5
    clip: LayerClip | None = None
    mask: LayerMask | None = None
    effects: list[ShapeEffect] = []
    animation: AnimationInput | None = None

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

    @field_validator("star_points")
    @classmethod
    def validate_star_points(cls, v: int) -> int:
        if v < 3:
            raise ValueError("star_points must be at least 3")
        return v

    @field_validator("inner_radius")
    @classmethod
    def validate_inner_radius(cls, v: float) -> float:
        if not (0.0 < v < 1.0):
            raise ValueError("inner_radius must be strictly between 0.0 and 1.0")
        return v

    @model_validator(mode="after")
    def validate_points_match_shape(self) -> "ShapeLayer":
        if self.shape == "polygon" and self.points is None:
            raise ValidationError("polygon shapes require points")
        if self.shape != "polygon" and self.points is not None:
            raise ValidationError("points is only valid for polygon shapes")
        return self

    @field_validator("position", mode="before")
    @classmethod
    def validate_position(cls, v: tuple | list | None) -> Position | None:
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

    @field_serializer("align")
    def serialize_align(self, align: Align | None) -> str | None:
        if align is None:
            return None
        return align.value


class SvgLayer(LayerIdentityModel):
    type: Literal["svg"]
    path: str
    position: Position
    width: PositiveInt | None = None
    height: PositiveInt | None = None
    opacity: OpacityField = 1.0
    rotation: float = 0.0
    align: AlignWithHVTuple = Align.TOP_LEFT
    blend_mode: Annotated[
        BlendMode | None, AfterValidator(lambda v: enum_converter(BlendMode)(v) if v else None)
    ] = None
    clip: LayerClip | None = None
    mask: LayerMask | None = None
    effects: list[ImageEffect] = []
    animation: AnimationInput | None = None

    @field_validator("position", mode="before")
    @classmethod
    def validate_position(cls, v: tuple | list | None) -> Position | None:
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

    @field_serializer("align")
    def serialize_align(self, align: Align) -> str:
        return align.value


class VideoCaption(quickthumbModel):
    """A deterministic caption cue rendered into video frames."""

    text: str
    start: FiniteNonNegativeFloat
    end: FinitePositiveFloat
    position: Position = ("50%", "90%")
    size: PositiveInt = 24
    color: HexColor = "#FFFFFF"
    background: HexColor | None = None
    background_opacity: OpacityField = 0.65
    padding: int | tuple[int, int] | tuple[int, int, int, int] = 0
    border_radius: NonNegativeInt = 0

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("caption text cannot be empty")
        return value

    @field_validator("position", mode="before")
    @classmethod
    def validate_position(cls, v: tuple | list) -> Position:
        return _validate_required_position(v)

    @field_validator("padding")
    @classmethod
    def validate_padding(cls, value: int | tuple[int, ...]) -> int | tuple[int, ...]:
        if isinstance(value, bool):
            raise ValueError("caption padding must be an integer or tuple")
        if isinstance(value, int):
            if value < 0:
                raise ValueError("caption padding cannot be negative")
            return value
        if len(value) not in (2, 4):
            raise ValueError("caption padding tuple must have 2 or 4 elements")
        if any(item < 0 for item in value):
            raise ValueError("caption padding values cannot be negative")
        return value

    @model_validator(mode="after")
    def validate_range(self) -> "VideoCaption":
        if self.end <= self.start:
            raise ValidationError("caption end must be greater than start")
        return self


class VideoLayer(LayerIdentityModel):
    """A constrained single-clip video layer for animated export."""

    type: Literal["video"]
    source: str
    position: Position
    width: PositiveInt
    height: PositiveInt
    fit: Annotated[FitMode, AfterValidator(lambda v: enum_converter(FitMode)(v))] = FitMode.CONTAIN
    trim_start: FiniteNonNegativeFloat = 0.0
    trim_end: FinitePositiveFloat | None = None
    start: FiniteNonNegativeFloat = 0.0
    duration: FinitePositiveFloat | None = None
    speed: FinitePositiveFloat = 1.0
    volume: FiniteNonNegativeFloat = 1.0
    captions: list[VideoCaption] = []

    @field_validator("source")
    @classmethod
    def validate_source(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("video source cannot be empty")
        return value

    @field_validator("position", mode="before")
    @classmethod
    def validate_position(cls, v: tuple | list) -> Position:
        return _validate_required_position(v)

    @model_validator(mode="after")
    def validate_timing(self) -> "VideoLayer":
        if self.trim_end is not None and self.trim_end <= self.trim_start:
            raise ValidationError("trim_end must be greater than trim_start")
        for caption in self.captions:
            if self.duration is not None and caption.start >= self.duration:
                raise ValidationError("caption timing must fall within the video duration")
        return self


class GroupLayer(LayerIdentityModel):
    type: Literal["group"]
    direction: Literal["row", "column"] = "column"
    gap: NonNegativeInt = 0
    padding: int | tuple[int, int] | tuple[int, int, int, int] = 0
    position: Position | None = None
    align: AlignWithHVTuple = None
    item_align: Literal["start", "center", "end"] = "start"
    clip: LayerClip | None = None
    mask: LayerMask | None = None
    animation: AnimationInput | None = None
    children: list["GroupChild"]

    @field_validator("children", mode="before")
    @classmethod
    def validate_children(cls, v: Any) -> Any:
        if not isinstance(v, list) or len(v) == 0:
            raise ValueError("children must be a non-empty list of layers")

        prepared = []
        for child in v:
            if isinstance(child, dict):
                position = child.get("position")
                if position is not None and (
                    not isinstance(position, (list, tuple)) or tuple(position) != (0, 0)
                ):
                    raise ValueError(
                        "group children must not set position; the group assigns positions"
                    )
                if child.get("type") in (
                    "image",
                    "svg",
                    "shape",
                    "chart",
                    "qr_code",
                ):
                    child = {**child, "position": (0, 0)}
            elif getattr(child, "position", None) not in (None, (0, 0)):
                raise ValueError(
                    "group children must not set position; the group assigns positions"
                )
            prepared.append(child)
        return prepared

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

    @field_validator("position", mode="before")
    @classmethod
    def validate_position(cls, v: tuple | list | None) -> Position | None:
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
        if align is None:
            return None
        return align.value


GroupChild = Annotated[
    TextLayer | ImageLayer | ShapeLayer | SvgLayer | ChartLayer | QRCodeLayer | GroupLayer,
    Discriminator("type"),
]

GroupLayer.model_rebuild()
