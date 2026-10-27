"""Public motion contract models."""

# Motion fields use the shared model vocabulary re-exported by `common`.
# ruff: noqa: F405

import math
from typing import Annotated, Any, Literal

from pydantic import (
    ConfigDict,
    Discriminator,
    Field,
    FiniteFloat,
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

    Each concrete effect (`Fade`, `Wipe`, `Box`, …) is its own class so it
    only exposes the options that effect actually supports — directional effects
    add a `direction`/`orientation`, `Wheel` adds `spokes`, and the rest
    add nothing. Attach one (or a list) to a `text`/`shape`/`image`/
    `svg`/`chart`/`qr_code`/`group` layer via `animation=`. Honoured by
    the PPTX, HTML, and animated GIF/MP4/WebM exporters; the layer renders normally
    in every other
    format. `trigger` controls how the effect starts relative to the previous
    animation on the slide (in video output, where there is nothing to click,
    `on_click` plays automatically like `after_previous`).
    """

    animate: Literal["entrance", "exit"] = "entrance"
    duration: PositiveFloat = 0.5
    delay: NonNegativeFloat = 0.0
    trigger: AnimationTrigger = "on_click"
    # `easing` shapes the reveal over `duration`; "linear" is what a bar
    # measuring elapsed time needs, since the default eased curve would make it
    # misreport its own progress. `start` pins the effect to an absolute time
    # on the slide instead of chaining it to whatever ran before.
    easing: "MotionEasingName" = "ease"
    start: FiniteNonNegativeFloat | None = None


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
    """Sweep the layer in or out like a clock hand, using `spokes` arms."""

    effect: Literal["wheel"] = "wheel"
    spokes: Annotated[PositiveInt, Field(le=64)] = 1


# Discriminated union of every effect: validates a dict (e.g. from JSON) into the
# right class by its `effect` tag, so layers accept one animation or a list.
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
    "pan",
    "typewriter",
    "bar_grow",
    "line_draw",
    "area_reveal",
    "point_pop",
    "value_count_up",
    "qr_reveal",
]
MotionTarget = Literal["layer", "children", "characters", "words", "lines", "bars", "points"]
MotionEasingName = Literal[
    "linear",
    "ease",
    "ease_in",
    "ease_out",
    "ease_in_out",
    "ease_in_quad",
    "ease_out_quad",
    "ease_in_out_quad",
    "ease_in_cubic",
    "ease_out_cubic",
    "ease_in_out_cubic",
    "ease_in_quart",
    "ease_out_quart",
    "ease_in_out_quart",
    "ease_in_quint",
    "ease_out_quint",
    "ease_in_out_quint",
    "ease_in_sine",
    "ease_out_sine",
    "ease_in_out_sine",
    "ease_in_back",
    "ease_out_back",
    "ease_in_out_back",
]


class CubicBezierEasing(_MotionModel):
    """A custom CSS-style cubic-bezier easing curve.

    `points` are the two control points `[x1, y1, x2, y2]`. The x coordinates
    must stay within `[0, 1]` so time remains monotonic; y may overshoot.
    """

    type: Literal["cubic_bezier"] = "cubic_bezier"
    points: tuple[
        Annotated[float, Field(allow_inf_nan=False)],
        Annotated[float, Field(allow_inf_nan=False)],
        Annotated[float, Field(allow_inf_nan=False)],
        Annotated[float, Field(allow_inf_nan=False)],
    ]

    @field_validator("points")
    @classmethod
    def validate_points(cls, points: tuple[float, float, float, float]):
        if not (0.0 <= points[0] <= 1.0 and 0.0 <= points[2] <= 1.0):
            raise ValueError("cubic_bezier x1 and x2 must be between 0.0 and 1.0")
        return points


MotionEasing = MotionEasingName | CubicBezierEasing


class KeyframeSpec(_MotionModel):
    """A property value at a non-negative point on an animation timeline.

    `easing` shapes the segment *leaving* this keyframe and falls back to the
    animation's easing when omitted. `hold` keeps this value until the next
    keyframe, then steps to it; a hold takes precedence over `easing`.
    """

    type: Literal["keyframe"] = "keyframe"
    time: FiniteNonNegativeFloat
    value: Any
    easing: MotionEasing | None = Field(default=None, exclude_if=lambda value: value is None)
    hold: bool = Field(default=False, exclude_if=lambda value: value is False)


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
        if getattr(self, "type", None) != "position" and any(
            getattr(key, "in_tangent", None) is not None
            or getattr(key, "out_tangent", None) is not None
            for key in self.keyframes
        ):
            raise ValidationError("tangents are only supported for position tracks")
        return self


class PositionKeyframeSpec(KeyframeSpec):
    """A position with optional relative incoming/outgoing cubic control handles."""

    in_tangent: tuple[FiniteFloat, FiniteFloat] | None = Field(
        default=None, exclude_if=lambda value: value is None
    )
    out_tangent: tuple[FiniteFloat, FiniteFloat] | None = Field(
        default=None, exclude_if=lambda value: value is None
    )

    @field_validator("in_tangent", "out_tangent", mode="before")
    @classmethod
    def validate_tangent(cls, value):
        if value is not None and (
            not isinstance(value, (tuple, list))
            or len(value) != 2
            or any(not isinstance(item, (int, float)) or isinstance(item, bool) for item in value)
        ):
            raise ValueError("position tangents must contain exactly two finite numbers")
        return value


class _VectorTrack(_TrackBase):
    """Shared validation for position and source-viewport vectors."""

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


class PositionTrack(_VectorTrack):
    """Pixel translations; optional handles use constant arc-length progress."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "type": "position",
                    "auto_orient": True,
                    "keyframes": [
                        {"type": "keyframe", "time": 0, "value": [0, 0], "out_tangent": [0, 80]},
                        {"type": "keyframe", "time": 1, "value": [100, 0], "in_tangent": [0, 80]},
                    ],
                }
            ],
        }
    )

    type: Literal["position"] = "position"
    keyframes: list[PositionKeyframeSpec | KeyframeSpec]
    auto_orient: bool = Field(default=False, exclude_if=lambda value: not value)

    @field_validator("keyframes", mode="before")
    @classmethod
    def coerce_position_keyframes(cls, keyframes):
        if isinstance(keyframes, (list, tuple)):
            return [key.model_dump() if isinstance(key, KeyframeSpec) else key for key in keyframes]
        return keyframes

    @model_validator(mode="after")
    def validate_control_points(self):
        for key in self.keyframes:
            for tangent in (getattr(key, "in_tangent", None), getattr(key, "out_tangent", None)):
                if tangent is not None and not all(
                    math.isfinite(position + offset)
                    for position, offset in zip(key.value, tangent, strict=True)
                ):
                    raise ValueError("position plus tangent must form finite control points")
        return self


class ImagePanTrack(_VectorTrack):
    """A normalized source-viewport pan track for image layers."""

    type: Literal["image_pan"] = "image_pan"

    @field_validator("keyframes")
    @classmethod
    def validate_pan(cls, keyframes: list[KeyframeSpec]) -> list[KeyframeSpec]:
        for keyframe in keyframes:
            if not all(-1.0 <= float(item) <= 1.0 for item in keyframe.value):
                raise ValueError("image_pan keyframe values must be between -1.0 and 1.0")
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
    """Uniform outer-object scale about the layer anchor, including image layers."""

    type: Literal["scale"] = "scale"


class ScaleXTrack(ScalarTrack):
    """Horizontal layer scale, multiplied by the uniform scale."""

    type: Literal["scale_x"] = "scale_x"


class ScaleYTrack(ScalarTrack):
    """Vertical layer scale, multiplied by the uniform scale."""

    type: Literal["scale_y"] = "scale_y"


class ImageZoomTrack(ScalarTrack):
    """A positive source-viewport zoom track for image layers."""

    type: Literal["image_zoom"] = "image_zoom"

    @field_validator("keyframes")
    @classmethod
    def validate_zoom(cls, keyframes: list[KeyframeSpec]) -> list[KeyframeSpec]:
        for keyframe in keyframes:
            if keyframe.value < 1.0:
                raise ValueError("image_zoom keyframe values must be at least 1.0")
        return keyframes


class RotationTrack(ScalarTrack):
    """Clockwise rotation in degrees, added to path heading with auto-orient."""

    type: Literal["rotation"] = "rotation"


class DashOffsetTrack(ScalarTrack):
    """Relative Path dash phase in local SVG/viewBox distance units."""

    type: Literal["dash_offset"] = "dash_offset"
    blend: Literal["replace", "add"] = "replace"


class _TrimBoundaryTrack(ScalarTrack):
    @field_validator("keyframes")
    @classmethod
    def validate_boundaries(cls, keyframes: list[KeyframeSpec]) -> list[KeyframeSpec]:
        for keyframe in keyframes:
            if not 0 <= keyframe.value <= 1:
                raise ValueError("trim boundary keyframes must be between 0 and 1")
        return keyframes


class TrimStartTrack(_TrimBoundaryTrack):
    """Absolute normalized stroke trim start along local SVG arc length."""

    type: Literal["trim_start"] = "trim_start"


class TrimEndTrack(_TrimBoundaryTrack):
    """Absolute normalized stroke trim end along local SVG arc length."""

    type: Literal["trim_end"] = "trim_end"


class TrimOffsetTrack(ScalarTrack):
    """Relative cyclic stroke trim offset, measured in normalized turns."""

    type: Literal["trim_offset"] = "trim_offset"
    blend: Literal["replace", "add"] = "replace"


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
    """A text/shape fill track interpolated in premultiplied Oklab and linear alpha."""

    type: Literal["color"] = "color"

    @field_validator("keyframes")
    @classmethod
    def validate_colors(cls, keyframes: list[KeyframeSpec]) -> list[KeyframeSpec]:
        for keyframe in keyframes:
            validate_hex_color(keyframe.value)
        return keyframes


TrackSpec = Annotated[
    PositionTrack
    | ImagePanTrack
    | ScaleTrack
    | ScaleXTrack
    | ScaleYTrack
    | ImageZoomTrack
    | RotationTrack
    | DashOffsetTrack
    | TrimStartTrack
    | TrimEndTrack
    | TrimOffsetTrack
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
        if self.start is not None and (self.trigger is not None or self.delay != 0):
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
    """Validated semantic preset options used by `AnimationSpec`."""

    type: MotionPresetName
    from_: Literal["top", "bottom", "left", "right", "center"] | None = Field(
        default=None, alias="from"
    )
    distance: FiniteNonNegativeFloat | None = None
    direction: Literal["in", "out"] | None = Field(
        default=None, exclude_if=lambda value: value is None
    )
    focal_point: FocalPoint | None = Field(default=None, exclude_if=lambda value: value is None)
    feel: Literal["gentle", "soft", "snappy", "dramatic", "minimal"] | None = None
    easing: MotionEasing | None = None

    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
        extra="forbid",
    )


class RangeSelector(_MotionModel):
    """Keyframeable percentage range over source codepoint, word or line centers."""

    target: Literal["characters", "words", "lines"] = "words"
    start: (
        Annotated[float, Field(ge=0, le=100, allow_inf_nan=False)]
        | Annotated[list[KeyframeSpec], Field(min_length=1)]
    ) = 0
    end: (
        Annotated[float, Field(ge=0, le=100, allow_inf_nan=False)]
        | Annotated[list[KeyframeSpec], Field(min_length=1)]
    ) = 100
    offset: FiniteFloat | Annotated[list[KeyframeSpec], Field(min_length=1)] = 0
    shape: Literal["square", "ramp", "triangle", "smooth"] = "square"

    @field_validator("start", "end", "offset")
    @classmethod
    def validate_percent_keys(cls, value, info):
        if isinstance(value, list):
            _TrackBase(keyframes=value)
            for key in value:
                if (
                    isinstance(key.value, bool)
                    or not isinstance(key.value, (int, float))
                    or not math.isfinite(key.value)
                    or info.field_name != "offset"
                    and not 0 <= key.value <= 100
                ):
                    raise ValueError(
                        "selector keyframes require finite numbers; start/end must be 0..100"
                    )
        return value

    @model_validator(mode="after")
    def validate_range(self):
        if (
            not isinstance(self.start, list)
            and not isinstance(self.end, list)
            and self.start > self.end
        ):
            raise ValidationError("selector start must not exceed end")
        return self


class AnimationSpec(_MotionModel):
    """Canonical layer-motion contract for preset or advanced timeline animation."""

    type: Literal["animation"] = "animation"
    effect: AnimationEffect | None = None
    tracks: list[TrackSpec] | None = None
    easing: MotionEasing | None = None
    timing: TimingSpec | None = None
    stagger: StaggerSpec | None = None
    selector: RangeSelector | None = None

    @model_validator(mode="after")
    def validate_composition(self):
        if (self.effect is None) == (self.tracks is None):
            raise ValidationError("animation must define exactly one of effect or tracks")
        if self.tracks is not None and not self.tracks:
            raise ValidationError("timeline animation must contain at least one track")
        if self.effect is not None and self.easing is not None:
            raise ValidationError("timeline easing is only valid with tracks")
        if self.selector is not None:
            if self.tracks is None or any(
                track.type not in {"position", "rotation", "scale", "opacity", "color"}
                for track in self.tracks
            ):
                raise ValidationError(
                    "selectors require position, rotation, scale, opacity or color tracks"
                )
            if any(
                getattr(track, "auto_orient", False)
                or any(
                    getattr(key, "in_tangent", None) or getattr(key, "out_tangent", None)
                    for key in track.keyframes
                )
                for track in self.tracks
            ):
                raise ValidationError(
                    "selector motion paths are not supported; use position keyframes"
                )
            if self.stagger is not None and (
                self.stagger.target != self.selector.target
                or self.stagger.order not in {"document", "reverse"}
            ):
                raise ValidationError(
                    "selector stagger must use the same target and document/reverse order"
                )
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
    def timeline(
        cls,
        *tracks: TrackSpec,
        timing: TimingSpec | None = None,
        easing: MotionEasing | None = None,
        selector: RangeSelector | None = None,
    ) -> "AnimationSpec":
        """Build an advanced animation from typed property tracks."""
        return cls(tracks=list(tracks), timing=timing, easing=easing, selector=selector)

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
    def pan(cls, **kwargs) -> "AnimationSpec":
        return cls._preset("pan", **kwargs)

    @classmethod
    def typewriter(cls, **kwargs) -> "AnimationSpec":
        return cls._preset("typewriter", **kwargs)

    @classmethod
    def bar_grow(cls, **kwargs) -> "AnimationSpec":
        return cls._preset("bar_grow", **kwargs)

    @classmethod
    def line_draw(cls, **kwargs) -> "AnimationSpec":
        return cls._preset("line_draw", **kwargs)

    @classmethod
    def area_reveal(cls, **kwargs) -> "AnimationSpec":
        return cls._preset("area_reveal", **kwargs)

    @classmethod
    def point_pop(cls, **kwargs) -> "AnimationSpec":
        return cls._preset("point_pop", **kwargs)

    @classmethod
    def value_count_up(cls, **kwargs) -> "AnimationSpec":
        return cls._preset("value_count_up", **kwargs)

    @classmethod
    def qr_reveal(cls, **kwargs) -> "AnimationSpec":
        return cls._preset("qr_reveal", **kwargs)


# A layer accepts legacy effects, the new canonical spec, or an ordered list.
AnimationItem = Annotated[Animation | AnimationSpec, Field(union_mode="left_to_right")]
AnimationInput = Annotated[
    Animation | AnimationSpec | list[AnimationItem],
    Field(union_mode="left_to_right"),
]
