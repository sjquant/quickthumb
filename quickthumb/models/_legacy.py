import math
import re
from collections.abc import Sequence
from enum import Enum
from typing import Annotated, Any, Literal, TypeAlias, TypeVar

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Discriminator,
    Field,
    NonNegativeFloat,
    NonNegativeInt,
    PositiveFloat,
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


class AudioTrack(quickthumbModel):
    """An audio source with room for export-time mix controls."""

    path: str
    volume: Annotated[float, Field(ge=0, allow_inf_nan=False)] = 1.0
    loop: bool = False


class GifOptions(quickthumbModel):
    """Options specific to animated GIF output."""

    model_config = ConfigDict(extra="forbid")

    fps: Annotated[float, Field(gt=0, allow_inf_nan=False)] | None = None
    loop: NonNegativeInt = 0
    matte: str = "#000000"
    max_size: tuple[PositiveInt, PositiveInt] | None = None
    colors: int | None = None

    @field_validator("loop")
    @classmethod
    def validate_loop(cls, value: int) -> int:
        if value > 65535:
            raise ValueError("loop must be <= 65535")
        return value

    @field_validator("colors")
    @classmethod
    def validate_colors(cls, value: int | None) -> int | None:
        if value is not None and not 2 <= value <= 256:
            raise ValueError("colors must be between 2 and 256")
        return value


class VideoOptions(quickthumbModel):
    """Options specific to animated MP4 and WebM output."""

    model_config = ConfigDict(extra="forbid")

    fps: Annotated[float, Field(gt=0, allow_inf_nan=False)] | None = None
    matte: str = "#000000"
    soundtrack: AudioTrack | None = None
    loop_audio: bool | None = None


def coerce_audio_track(value: AudioTrack | str | dict | None) -> AudioTrack | None:
    """Normalize legacy path strings and mapping specs into an audio track."""
    if value is None:
        return None
    if isinstance(value, AudioTrack):
        return value
    if isinstance(value, str):
        return AudioTrack(path=value)
    if isinstance(value, dict):
        return AudioTrack(**value)
    raise ValidationError("audio must be a path string or AudioTrack configuration")


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


# --------------------------------------------------------------- slide effects
# Per-layer entrance/exit animations (below) and slide-level transitions (in
# quickthumb.transitions) play in PowerPoint (PPTX), HTML, and animated
# GIF/MP4/WebM output; still-image renderers (raster, SVG, PDF) ignore them.

AnimationTrigger = Literal["on_click", "with_previous", "after_previous"]


class _AnimationBase(quickthumbModel):
    """Shared timing fields for every animation effect.

    Each concrete effect (``Fade``, ``Wipe``, ``Box``, …) is its own class so it
    only exposes the options that effect actually supports — directional effects
    add a ``direction``/``orientation``, ``Wheel`` adds ``spokes``, and the rest
    add nothing. Attach one (or a list) to a ``text``/``shape``/``image``/
    ``svg``/``chart``/``qr_code``/``group`` layer via ``animation=``. Honoured by
    the PPTX, HTML, and animated GIF/MP4/WebM exporters; the layer renders normally
    in every other
    format. ``trigger`` controls how the effect starts relative to the previous
    animation on the slide (in video output, where there is nothing to click,
    ``on_click`` plays automatically like ``after_previous``).
    """

    animate: Literal["entrance", "exit"] = "entrance"
    duration: PositiveFloat = 0.5
    delay: NonNegativeFloat = 0.0
    trigger: AnimationTrigger = "on_click"


class Appear(_AnimationBase):
    """Instantly show (entrance) or hide (exit) the layer with no motion."""

    effect: Literal["appear"] = "appear"


class Fade(_AnimationBase):
    """Fade the layer in or out."""

    effect: Literal["fade"] = "fade"


class Wipe(_AnimationBase):
    """Wipe the layer in or out from a given edge."""

    effect: Literal["wipe"] = "wipe"
    direction: Literal["up", "down", "left", "right"] = "up"


class Box(_AnimationBase):
    """Reveal or conceal the layer with a box growing in or shrinking out."""

    effect: Literal["box"] = "box"
    direction: Literal["in", "out"] = "in"


class Blinds(_AnimationBase):
    """Reveal the layer through horizontal or vertical blinds."""

    effect: Literal["blinds"] = "blinds"
    orientation: Literal["horizontal", "vertical"] = "horizontal"


class Checkerboard(_AnimationBase):
    """Reveal the layer through a checkerboard sweeping across or down."""

    effect: Literal["checkerboard"] = "checkerboard"
    direction: Literal["across", "down"] = "across"


class Circle(_AnimationBase):
    """Reveal or conceal the layer through an expanding/contracting circle."""

    effect: Literal["circle"] = "circle"


class Diamond(_AnimationBase):
    """Reveal or conceal the layer through an expanding/contracting diamond."""

    effect: Literal["diamond"] = "diamond"


class Dissolve(_AnimationBase):
    """Dissolve the layer in or out through a speckled mask."""

    effect: Literal["dissolve"] = "dissolve"


class Wheel(_AnimationBase):
    """Sweep the layer in or out like a clock hand, using ``spokes`` arms."""

    effect: Literal["wheel"] = "wheel"
    spokes: Annotated[PositiveInt, Field(le=64)] = 1


# Discriminated union of every effect: validates a dict (e.g. from JSON) into the
# right class by its ``effect`` tag, so layers accept one animation or a list.
Animation = Annotated[
    Appear | Fade | Wipe | Box | Blinds | Checkerboard | Circle | Diamond | Dissolve | Wheel,
    Discriminator("effect"),
]


# --------------------------------------------------------------- motion contract
class _MotionModel(quickthumbModel):
    """Strict base for the canonical motion contract models."""

    model_config = ConfigDict(extra="forbid")


MotionPresetName = Literal[
    "fade",
    "rise",
    "fall",
    "slide",
    "zoom",
    "pop",
    "float",
    "pulse",
    "shake",
    "ken_burns",
    "typewriter",
]
MotionTarget = Literal["layer", "children", "characters", "words", "lines", "bars", "points"]


class KeyframeSpec(_MotionModel):
    """A property value at a non-negative point on an animation timeline."""

    type: Literal["keyframe"] = "keyframe"
    time: FiniteNonNegativeFloat
    value: Any


class _TrackBase(_MotionModel):
    """Shared fields for a typed motion property track."""

    keyframes: list[KeyframeSpec]

    @model_validator(mode="after")
    def validate_keyframes(self):
        if not self.keyframes:
            raise ValidationError("tracks must contain at least one keyframe")
        times = [keyframe.time for keyframe in self.keyframes]
        if times != sorted(times) or len(times) != len(set(times)):
            raise ValidationError("keyframe times must be strictly increasing")
        return self


class PositionTrack(_TrackBase):
    """A two-dimensional position track."""

    type: Literal["position"] = "position"

    @field_validator("keyframes")
    @classmethod
    def validate_positions(cls, keyframes: list[KeyframeSpec]) -> list[KeyframeSpec]:
        for keyframe in keyframes:
            value = keyframe.value
            if not isinstance(value, (tuple, list)) or len(value) != 2:
                raise ValueError("position keyframe values must contain exactly two numbers")
            if not all(
                isinstance(item, (int, float))
                and not isinstance(item, bool)
                and math.isfinite(item)
                for item in value
            ):
                raise ValueError("position keyframe values must contain numbers")
        return keyframes


class ScalarTrack(_TrackBase):
    """Base for scalar motion tracks with a shared numeric validator."""

    @field_validator("keyframes")
    @classmethod
    def validate_scalars(cls, keyframes: list[KeyframeSpec]) -> list[KeyframeSpec]:
        for keyframe in keyframes:
            if (
                not isinstance(keyframe.value, (int, float))
                or isinstance(keyframe.value, bool)
                or not math.isfinite(keyframe.value)
            ):
                raise ValueError(
                    f"{cls.model_fields['type'].default} keyframe values must be numbers"
                )
        return keyframes


class ScaleTrack(ScalarTrack):
    """A uniform scale track."""

    type: Literal["scale"] = "scale"


class RotationTrack(ScalarTrack):
    """A rotation-in-degrees track."""

    type: Literal["rotation"] = "rotation"


class OpacityTrack(ScalarTrack):
    """An opacity track constrained to the inclusive unit interval."""

    type: Literal["opacity"] = "opacity"

    @field_validator("keyframes")
    @classmethod
    def validate_opacities(cls, keyframes: list[KeyframeSpec]) -> list[KeyframeSpec]:
        for keyframe in keyframes:
            if not 0.0 <= keyframe.value <= 1.0:
                raise ValueError("opacity keyframe values must be between 0.0 and 1.0")
        return keyframes


class ClipProgressTrack(ScalarTrack):
    """A clip/reveal progress track constrained to the unit interval."""

    type: Literal["clip_progress"] = "clip_progress"

    @field_validator("keyframes")
    @classmethod
    def validate_progress(cls, keyframes: list[KeyframeSpec]) -> list[KeyframeSpec]:
        for keyframe in keyframes:
            if not 0.0 <= keyframe.value <= 1.0:
                raise ValueError("clip_progress keyframe values must be between 0.0 and 1.0")
        return keyframes


class BlurTrack(ScalarTrack):
    """A non-negative blur-radius track."""

    type: Literal["blur"] = "blur"

    @field_validator("keyframes")
    @classmethod
    def validate_blur(cls, keyframes: list[KeyframeSpec]) -> list[KeyframeSpec]:
        for keyframe in keyframes:
            if keyframe.value < 0:
                raise ValueError("blur keyframe values must be non-negative")
        return keyframes


class ColorTrack(_TrackBase):
    """A hexadecimal color track."""

    type: Literal["color"] = "color"

    @field_validator("keyframes")
    @classmethod
    def validate_colors(cls, keyframes: list[KeyframeSpec]) -> list[KeyframeSpec]:
        for keyframe in keyframes:
            validate_hex_color(keyframe.value)
        return keyframes


TrackSpec = Annotated[
    PositionTrack
    | ScaleTrack
    | RotationTrack
    | OpacityTrack
    | ClipProgressTrack
    | BlurTrack
    | ColorTrack,
    Discriminator("type"),
]


class TimingSpec(_MotionModel):
    """Relative or absolute timing; the two forms cannot be mixed."""

    duration: FinitePositiveFloat = 0.5
    trigger: AnimationTrigger | None = None
    delay: FiniteNonNegativeFloat = 0.0
    start: FiniteNonNegativeFloat | None = None

    @model_validator(mode="after")
    def validate_mode(self):
        if self.start is not None and {"trigger", "delay"} & self.model_fields_set:
            raise ValidationError(
                "timing must use either relative trigger/delay or absolute start, not both"
            )
        return self


class StaggerSpec(_MotionModel):
    """A deterministic interval for sequencing a target collection."""

    delay: FiniteNonNegativeFloat
    target: MotionTarget = "children"
    order: Literal["document", "top_to_bottom", "left_to_right", "reverse"] = "document"


class AnimationEffect(_MotionModel):
    """Validated semantic preset options used by ``AnimationSpec``."""

    type: MotionPresetName
    from_: Literal["top", "bottom", "left", "right", "center"] | None = Field(
        default=None, alias="from"
    )
    distance: FiniteNonNegativeFloat | None = None
    feel: Literal["gentle", "soft", "snappy", "dramatic", "minimal"] | None = None
    easing: str | None = None

    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
        extra="forbid",
    )


class AnimationSpec(_MotionModel):
    """Canonical layer-motion contract for preset or advanced timeline animation."""

    type: Literal["animation"] = "animation"
    effect: AnimationEffect | None = None
    tracks: list[TrackSpec] | None = None
    timing: TimingSpec | None = None
    stagger: StaggerSpec | None = None

    @model_validator(mode="after")
    def validate_composition(self):
        if (self.effect is None) == (self.tracks is None):
            raise ValidationError("animation must define exactly one of effect or tracks")
        if self.tracks is not None and not self.tracks:
            raise ValidationError("timeline animation must contain at least one track")
        return self

    @classmethod
    def _preset(cls, name: MotionPresetName, **kwargs) -> "AnimationSpec":
        """Build a semantic effect-based animation preset."""
        timing_fields = {
            key: kwargs.pop(key) for key in ("duration", "trigger", "delay") if key in kwargs
        }
        stagger_delay = kwargs.pop("stagger", None)
        stagger_target = kwargs.pop("target", None)
        stagger_order = kwargs.pop("order", "document")
        stagger = (
            StaggerSpec(
                delay=stagger_delay or 0.0,
                target=stagger_target or "children",
                order=stagger_order,
            )
            if stagger_delay is not None or stagger_target is not None
            else None
        )
        return cls(
            effect=AnimationEffect(type=name, **kwargs),
            timing=TimingSpec(**timing_fields) if timing_fields else None,
            stagger=stagger,
        )

    @classmethod
    def timeline(cls, *tracks: TrackSpec, timing: TimingSpec | None = None) -> "AnimationSpec":
        """Build an advanced animation from typed property tracks."""
        return cls(tracks=list(tracks), timing=timing)

    @classmethod
    def fade(cls, **kwargs) -> "AnimationSpec":
        return cls._preset("fade", **kwargs)

    @classmethod
    def rise(cls, **kwargs) -> "AnimationSpec":
        return cls._preset("rise", **kwargs)

    @classmethod
    def fall(cls, **kwargs) -> "AnimationSpec":
        return cls._preset("fall", **kwargs)

    @classmethod
    def slide(cls, **kwargs) -> "AnimationSpec":
        return cls._preset("slide", **kwargs)

    @classmethod
    def zoom(cls, **kwargs) -> "AnimationSpec":
        return cls._preset("zoom", **kwargs)

    @classmethod
    def pop(cls, **kwargs) -> "AnimationSpec":
        return cls._preset("pop", **kwargs)

    @classmethod
    def float(cls, **kwargs) -> "AnimationSpec":
        return cls._preset("float", **kwargs)

    @classmethod
    def pulse(cls, **kwargs) -> "AnimationSpec":
        return cls._preset("pulse", **kwargs)

    @classmethod
    def shake(cls, **kwargs) -> "AnimationSpec":
        return cls._preset("shake", **kwargs)

    @classmethod
    def ken_burns(cls, **kwargs) -> "AnimationSpec":
        return cls._preset("ken_burns", **kwargs)

    @classmethod
    def typewriter(cls, **kwargs) -> "AnimationSpec":
        return cls._preset("typewriter", **kwargs)


class MotionProfile(_MotionModel):
    """Deck-wide defaults for motion speed and visual feel."""

    name: Literal["presentation", "social", "cinematic", "minimal"]
    speed: FinitePositiveFloat = 1.0
    feel: Literal["gentle", "soft", "snappy", "dramatic", "minimal"] = "soft"


class ExportPolicy(_MotionModel):
    """Policy controlling how an exporter handles unsupported motion."""

    unsupported_motion: Literal["error", "warn", "rasterize", "static"] = "warn"
    pptx: dict[str, Literal["native", "rasterize", "static"]] = {}
    reduced_motion: bool = False


class ExportDiagnostic(_MotionModel):
    """Structured explanation of exporter support or fallback behavior."""

    layer_id: str | None = None
    feature: str
    target: str
    support: Literal["full", "native", "partial", "fallback", "unsupported"]
    fallback: Literal["fade", "rasterize", "static"] | None = None
    message: str


# A layer accepts legacy effects, the new canonical spec, or an ordered list.
AnimationItem = Annotated[Animation | AnimationSpec, Field(union_mode="left_to_right")]
AnimationInput = Annotated[
    Animation | AnimationSpec | list[AnimationItem],
    Field(union_mode="left_to_right"),
]


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


class ChartData(quickthumbModel):
    """Validated numeric samples shared by the chart layer models."""

    values: list[float] = Field(default_factory=list)

    @field_validator("values", mode="before")
    @classmethod
    def validate_values(cls, value: Any) -> list[float]:
        if not isinstance(value, (list, tuple)):
            raise ValueError("chart values must be a list of numbers")

        normalized: list[float] = []
        for item in value:
            if isinstance(item, bool) or not isinstance(item, (int, float)):
                raise ValueError("chart values must contain only numbers")
            try:
                number = float(item)
            except (OverflowError, ValueError):
                raise ValueError("chart values must contain only finite numbers") from None
            if not math.isfinite(number):
                raise ValueError("chart values must be finite numbers")
            normalized.append(number)
        return normalized


class VisualizationLayerBase(quickthumbModel):
    """Common positioning and composition contract for visualization layers."""

    position: Position = (0, 0)
    align: AlignWithHVTuple = Align.TOP_LEFT
    opacity: OpacityField = 1.0
    clip: LayerClip | None = None
    mask: LayerMask | None = None
    animation: AnimationInput | None = None

    @field_serializer("align")
    def serialize_align(self, align: Align | None) -> str | None:
        if align is None:
            return None
        return align.value


class BarChartStyle(quickthumbModel):
    """Deterministic paint and geometry options for bar charts."""

    model_config = ConfigDict(extra="forbid")

    color: HexColor = "#2563EB"
    negative_color: HexColor | None = None
    bar_gap: Annotated[float, Field(ge=0.0, lt=1.0)] = 0.2
    padding: NonNegativeInt = 0
    opacity: OpacityField = 1.0


class LineChartStyle(quickthumbModel):
    """Deterministic paint and geometry options for line charts."""

    model_config = ConfigDict(extra="forbid")

    color: HexColor = "#2563EB"
    fill: HexColor | None = None
    fill_opacity: OpacityField = 0.16
    stroke_width: PositiveInt = 2
    point_radius: NonNegativeInt = 2
    show_points: bool = True
    padding: NonNegativeInt = 0
    opacity: OpacityField = 1.0


class _ChartSpecBase(quickthumbModel):
    """Shared data normalization and serialization for chart specifications."""

    data: ChartData | Sequence[int | float]

    @field_validator(
        "data",
        mode="before",
        json_schema_input_type=list[float] | ChartData,
    )
    @classmethod
    def validate_data(cls, value: Any) -> ChartData:
        return value if isinstance(value, ChartData) else ChartData(values=value)

    @field_serializer("data")
    def serialize_data(self, data: ChartData) -> list[float]:
        return data.values


class BarChartSpec(_ChartSpecBase):
    """Validated bar chart data and bar-specific options."""

    type: Literal["bar"] = "bar"
    style: BarChartStyle = Field(default_factory=BarChartStyle)


class LineChartSpec(_ChartSpecBase):
    """Validated line chart data and line-specific options."""

    type: Literal["line"] = "line"
    style: LineChartStyle = Field(default_factory=LineChartStyle)


ChartSpec = Annotated[BarChartSpec | LineChartSpec, Discriminator("type")]


class ChartLayer(VisualizationLayerBase):
    """A deterministic data visualization layer selected by its spec."""

    type: Literal["chart"] = "chart"
    width: PositiveInt
    height: PositiveInt
    spec: ChartSpec


class QRCodeLayer(VisualizationLayerBase):
    """A deterministic QR code rendered into a square canvas region."""

    type: Literal["qr_code"] = "qr_code"
    data: str = Field(min_length=1)
    size: PositiveInt
    foreground: HexColor = "#000000"
    background: HexColor | None = "#FFFFFF"
    error_correction: Literal["L", "M", "Q", "H"] = "M"
    quiet_zone: NonNegativeInt = 4


class BackgroundLayer(quickthumbModel):
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


class TextLayer(quickthumbModel):
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


class OutlineLayer(quickthumbModel):
    type: Literal["outline"]
    width: PositiveInt
    color: HexColor
    offset: NonNegativeInt = 0
    opacity: OpacityField = 1.0


class ImageLayer(quickthumbModel):
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


class ShapeLayer(quickthumbModel):
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


class SvgLayer(quickthumbModel):
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


class GroupLayer(quickthumbModel):
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


class InspectionBBox(quickthumbModel):
    x: int
    y: int
    width: NonNegativeInt
    height: NonNegativeInt


DiagnosticBBox = InspectionBBox


class Diagnostic(quickthumbModel):
    code: Literal[
        "off-canvas",
        "tiny-text",
        "text-overflow",
        "text-clipped",
        "missing-glyph",
        "low-contrast",
        "layer-overlap",
        "near-alignment",
        "layer-hidden",
        "edge-crowding",
    ]
    severity: Literal["warning", "error"]
    layer_index: int
    message: str
    layer_id: str | None = Field(default=None, repr=False)
    layer_name: str | None = Field(default=None, repr=False)
    bbox: DiagnosticBBox | None = Field(default=None, repr=False)
    related_layers: list[str] = Field(default_factory=list, repr=False)
    measured: dict[str, Any] = Field(default_factory=dict, repr=False)
    suggestion: str | None = Field(default=None, repr=False)


class TextInspection(quickthumbModel):
    wrapped_lines: list[str]
    effective_font_size: PositiveInt | None = None
    effective_font_sizes: list[PositiveInt] = []
    max_width: int | str | None = None
    max_height: int | str | None = None
    min_size: PositiveInt = 1
    balance_lines: bool = False
    font_source: FontSource = "auto"
    font_variations: FontVariations = Field(default_factory=dict)
    emoji_style: EmojiStyle = "monochrome"
    auto_scaled: bool = False


class LayerInspection(quickthumbModel):
    id: str
    index: NonNegativeInt
    order: NonNegativeInt
    z_order: NonNegativeInt
    type: str
    name: str | None = None
    visible: bool
    bbox: InspectionBBox | None = None
    text: TextInspection | None = None
    children: list["LayerInspection"] = []


class CanvasInspection(quickthumbModel):
    width: PositiveInt
    height: PositiveInt
    layers: list[LayerInspection]


LayerType = Annotated[
    BackgroundLayer
    | TextLayer
    | OutlineLayer
    | ImageLayer
    | ShapeLayer
    | SvgLayer
    | ChartLayer
    | QRCodeLayer
    | GroupLayer,
    Discriminator("type"),
]


class CanvasModel(quickthumbModel):
    kind: Literal["canvas"] = "canvas"
    width: PositiveInt | None = None
    height: PositiveInt | None = None
    platform: str | None = None
    layers: list[LayerType]


class CanvasSpecModel(quickthumbModel):
    kind: Literal["canvas"] = "canvas"
    width: PositiveInt | None = None
    height: PositiveInt | None = None
    platform: str | None = None
    theme: dict[str, Any] = Field(default_factory=dict)
    layers: list[LayerType]
