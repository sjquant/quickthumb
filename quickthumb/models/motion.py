"""Public motion contract models."""

# Motion fields use the shared model vocabulary re-exported by ``common``.
# ruff: noqa: F405

import math
from typing import Annotated, Any, Literal

from pydantic import (
    ConfigDict,
    Discriminator,
    Field,
    NonNegativeFloat,
    PositiveFloat,
    PositiveInt,
    field_validator,
    model_validator,
)

from quickthumb.errors import ValidationError

from .common import *  # noqa: F401,F403
from .common import _MotionModel

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


# A layer accepts legacy effects, the new canonical spec, or an ordered list.
AnimationItem = Annotated[Animation | AnimationSpec, Field(union_mode="left_to_right")]
AnimationInput = Annotated[
    Animation | AnimationSpec | list[AnimationItem],
    Field(union_mode="left_to_right"),
]
