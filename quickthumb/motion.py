"""Renderer-independent motion timelines and deterministic layer sampling."""

from __future__ import annotations

import math
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic import ValidationError as PydanticValidationError

from quickthumb.errors import ValidationError
from quickthumb.models import (
    AnimationSpec,
    HexColor,
    KeyframeSpec,
    TrackSpec,
    validate_hex_color,
)
from quickthumb.transitions import Transition, coerce_transition

MotionValue = tuple[float, float] | float | str
MotionProperty = Literal[
    "position", "scale", "rotation", "opacity", "clip_progress", "blur", "color"
]


class NormalizedKeyframe(BaseModel):
    """A keyframe with a renderer-independent property value."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    time: float = Field(ge=0.0, allow_inf_nan=False)
    value: MotionValue


class NormalizedTrack(BaseModel):
    """One normalized property track with local keyframe times."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    property: MotionProperty
    keyframes: tuple[NormalizedKeyframe, ...]

    @model_validator(mode="after")
    def validate_keyframes(self) -> NormalizedTrack:
        if not self.keyframes:
            raise ValidationError("normalized tracks must contain at least one keyframe")
        times = [keyframe.time for keyframe in self.keyframes]
        if times != sorted(times) or len(times) != len(set(times)):
            raise ValidationError("normalized keyframe times must be strictly increasing")
        for keyframe in self.keyframes:
            _validate_property_value(self.property, keyframe.value)
        return self

    @property
    def duration(self) -> float:
        """Return the local time of the final keyframe."""
        return self.keyframes[-1].time


class TimelineEvent(BaseModel):
    """A scheduled effect or track collection on the shared timeline."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source: Literal["effect", "timeline", "legacy", "transition"]
    start: float = Field(ge=0.0, allow_inf_nan=False)
    delay: float = Field(ge=0.0, allow_inf_nan=False)
    duration: float = Field(ge=0.0, allow_inf_nan=False)
    trigger: str | None = None
    effect: str | None = None
    options: dict[str, Any] = Field(default_factory=dict)
    tracks: tuple[NormalizedTrack, ...] = ()
    stagger: dict[str, Any] | None = None

    @property
    def active_start(self) -> float:
        """Return the instant at which this event begins changing state."""
        return self.start + self.delay

    @property
    def end(self) -> float:
        """Return the inclusive settled end of this event."""
        return self.active_start + self.duration


class LayerState(BaseModel):
    """The animatable state of a layer at one point in time."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    position: tuple[float, float] | None = None
    scale: float = Field(default=1.0, allow_inf_nan=False)
    rotation: float = Field(default=0.0, allow_inf_nan=False)
    opacity: float = Field(default=1.0, ge=0.0, le=1.0, allow_inf_nan=False)
    clip_progress: float = Field(default=1.0, ge=0.0, le=1.0, allow_inf_nan=False)
    blur: float = Field(default=0.0, ge=0.0, allow_inf_nan=False)
    color: HexColor | None = None

    def with_values(self, **values: MotionValue | None) -> LayerState:
        """Return a state with selected properties replaced."""
        try:
            return type(self).model_validate({**self.model_dump(), **values})
        except PydanticValidationError as error:
            raise ValidationError(f"invalid layer state update: {error}") from error


class Timeline(BaseModel):
    """An immutable, normalized collection of scheduled motion events."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    events: tuple[TimelineEvent, ...] = ()

    @property
    def duration(self) -> float:
        """Return the time at which the last event settles."""
        return max((event.end for event in self.events), default=0.0)

    def sample(self, time: float, base: LayerState | None = None) -> LayerState:
        """Sample the timeline at ``time`` seconds into a deterministic state."""
        if not math.isfinite(time):
            raise ValidationError("sample time must be finite")
        state = base if base is not None else LayerState()
        for event in self.events:
            state = _sample_event(event, time, state)
        return state

    def frame_times(self, fps: float) -> tuple[float, ...]:
        """Return deterministic frame timestamps from zero through the duration."""
        if not math.isfinite(fps) or fps <= 0:
            raise ValidationError("fps must be a finite number greater than 0")
        if self.duration == 0:
            return (0.0,)
        count = max(1, math.ceil(self.duration * fps - 1e-12))
        return tuple(min(index / fps, self.duration) for index in range(count + 1))


def compile_timeline(
    spec: AnimationSpec | list[AnimationSpec] | tuple[AnimationSpec, ...],
) -> Timeline:
    """Compile one or more canonical animation specs into a normalized timeline."""
    specs = list(spec) if isinstance(spec, (list, tuple)) else [spec]
    if not specs:
        return Timeline()
    if not all(isinstance(item, AnimationSpec) for item in specs):
        raise ValidationError("timeline compilation requires AnimationSpec values")

    events: list[TimelineEvent] = []
    previous_start = 0.0
    previous_end = 0.0
    for item in specs:
        event = _compile_spec(item, previous_start, previous_end)
        events.append(event)
        previous_start = event.start
        previous_end = max(previous_end, event.end)
    return Timeline(events=tuple(events))


def compile_transition_timeline(
    transition: Transition | dict[str, Any] | str | None,
) -> Timeline:
    """Normalize a slide transition's timing without importing exporter behavior."""
    transition = coerce_transition(transition)
    if transition is None:
        return Timeline()
    duration = transition.duration
    effect = transition.effect
    if not isinstance(duration, (int, float)) or not math.isfinite(duration) or duration <= 0:
        raise ValidationError("transition duration must be a finite number greater than 0")
    if not isinstance(effect, str):
        raise ValidationError("transition must define an effect")
    options = transition.model_dump(mode="json", exclude_none=True)
    return Timeline(
        events=(
            TimelineEvent(
                source="transition",
                start=0.0,
                delay=0.0,
                duration=float(duration),
                effect=effect,
                options=options,
            ),
        )
    )


def _compile_spec(spec: AnimationSpec, previous_start: float, previous_end: float) -> TimelineEvent:
    """Compile one spec after resolving its timing anchor."""
    timing = spec.timing
    tracks = tuple(_normalize_track(track) for track in spec.tracks or ())
    track_duration = max((track.duration for track in tracks), default=0.0)
    if timing is None:
        duration = track_duration if spec.tracks is not None else 0.5
        trigger = None
        delay = 0.0
        start = 0.0 if previous_end == 0 else previous_end
    else:
        duration = timing.duration
        if track_duration > duration:
            raise ValidationError("timing duration cannot be shorter than the final keyframe time")
        trigger = timing.trigger
        delay = timing.delay
        if timing.start is not None:
            start = timing.start
        elif trigger == "with_previous":
            start = previous_start
        else:
            start = previous_end

    effect = spec.effect
    options = effect.model_dump(mode="json", by_alias=True, exclude_none=True) if effect else {}
    return TimelineEvent(
        source="effect" if effect else "timeline",
        start=start,
        delay=delay,
        duration=duration,
        trigger=trigger,
        effect=effect.type if effect else None,
        options=options,
        tracks=tracks,
        stagger=(
            spec.stagger.model_dump(mode="json", exclude_none=True)
            if spec.stagger is not None
            else None
        ),
    )


def _normalize_track(track: TrackSpec) -> NormalizedTrack:
    """Convert a validated public track into the common IR track shape."""
    return NormalizedTrack(
        property=track.type,
        keyframes=tuple(
            NormalizedKeyframe(time=keyframe.time, value=_normalize_value(keyframe))
            for keyframe in track.keyframes
        ),
    )


def _normalize_value(keyframe: KeyframeSpec) -> MotionValue:
    """Convert tuple-like public values into JSON-stable primitive values."""
    value = keyframe.value
    if isinstance(value, (tuple, list)):
        return (float(value[0]), float(value[1]))
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    if isinstance(value, str):
        return value
    raise ValidationError(f"unsupported keyframe value: {value!r}")


def _validate_property_value(property: MotionProperty, value: MotionValue) -> None:
    """Validate a normalized value against the state property it updates."""
    if property == "position":
        if (
            not isinstance(value, tuple)
            or len(value) != 2
            or not all(math.isfinite(item) for item in value)
        ):
            raise ValidationError("position keyframes must contain two finite numbers")
        return
    if property == "color":
        if not isinstance(value, str):
            raise ValidationError("color keyframes must contain hexadecimal colors")
        try:
            validate_hex_color(value)
        except ValueError as error:
            raise ValidationError(str(error)) from error
        return
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        raise ValidationError(f"{property} keyframes must contain finite numbers")
    if property in {"opacity", "clip_progress"} and not 0.0 <= value <= 1.0:
        raise ValidationError(f"{property} keyframes must be between 0.0 and 1.0")
    if property == "blur" and value < 0.0:
        raise ValidationError("blur keyframes must be non-negative")


def _sample_event(event: TimelineEvent, time: float, state: LayerState) -> LayerState:
    """Apply one event to a state, preserving stable event-order precedence."""
    if time < event.active_start:
        return state
    progress = (
        1.0 if event.duration == 0 else min(1.0, (time - event.active_start) / event.duration)
    )
    for track in event.tracks:
        value = _sample_track(track, progress, event.duration)
        state = state.with_values(**{track.property: value})
    if event.effect is not None and event.source in {"effect", "legacy"}:
        state = _sample_effect(event, progress, state)
    return state


def _sample_track(track: NormalizedTrack, progress: float, duration: float) -> MotionValue:
    """Sample a local track at normalized event progress."""
    local_time = progress * duration
    if local_time <= track.keyframes[0].time:
        return track.keyframes[0].value
    if local_time >= track.keyframes[-1].time:
        return track.keyframes[-1].value
    for left, right in zip(track.keyframes, track.keyframes[1:], strict=True):
        if local_time <= right.time:
            ratio = (local_time - left.time) / (right.time - left.time)
            return _interpolate(left.value, right.value, ratio)
    return track.keyframes[-1].value


def _interpolate(left: MotionValue, right: MotionValue, ratio: float) -> MotionValue:
    """Linearly interpolate supported scalar, vector, and hex color values."""
    if isinstance(left, tuple) and isinstance(right, tuple):
        return tuple(a + (b - a) * ratio for a, b in zip(left, right, strict=True))
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return left + (right - left) * ratio
    if isinstance(left, str) and isinstance(right, str):
        return _interpolate_color(left, right, ratio)
    return left if ratio < 1.0 else right


def _interpolate_color(left: str, right: str, ratio: float) -> str:
    """Interpolate RGB(A) hex colors while preserving the input channel count."""
    left_hex, right_hex = left[1:], right[1:]
    if len(left_hex) != len(right_hex) or len(left_hex) not in (6, 8):
        return left if ratio < 1.0 else right
    channels = [
        round(int(a, 16) + (int(b, 16) - int(a, 16)) * ratio)
        for a, b in zip(
            (left_hex[i : i + 2] for i in range(0, len(left_hex), 2)),
            (right_hex[i : i + 2] for i in range(0, len(right_hex), 2)),
            strict=True,
        )
    ]
    return "#" + "".join(f"{channel:02X}" for channel in channels)


def _sample_effect(event: TimelineEvent, progress: float, state: LayerState) -> LayerState:
    """Sample renderer-independent effects whose state mapping is unambiguous."""
    effect = event.effect
    if effect == "fade":
        return state.with_values(opacity=state.opacity * progress)
    if effect in {"zoom", "pop"}:
        return state.with_values(scale=state.scale * (0.8 + 0.2 * progress))
    if effect == "typewriter":
        return state.with_values(clip_progress=state.clip_progress * progress)
    if effect == "ken_burns":
        return state.with_values(scale=state.scale * (1.0 + 0.1 * progress))
    if effect in {"float", "pulse", "shake"}:
        distance = float(event.options.get("distance", 12.0) or 0.0)
        oscillation = math.sin(progress * math.tau)
        if effect == "pulse":
            return state.with_values(scale=state.scale * (1.0 + 0.1 * math.sin(math.pi * progress)))
        if state.position is None:
            return state
        x, y = state.position
        if effect == "float":
            return state.with_values(position=(x, y - distance * oscillation))
        return state.with_values(position=(x + distance * oscillation, y))
    if effect in {"rise", "fall", "slide"} and state.position is not None:
        distance = float(event.options.get("distance", 48.0) or 0.0)
        origin = event.options.get("from")
        if origin is None:
            origin = {"rise": "bottom", "fall": "top", "slide": "left"}[effect]
        x, y = state.position
        if origin == "bottom":
            return state.with_values(position=(x, y + distance * (1.0 - progress)))
        if origin == "top":
            return state.with_values(position=(x, y - distance * (1.0 - progress)))
        if origin == "left":
            return state.with_values(position=(x - distance * (1.0 - progress), y))
        if origin == "right":
            return state.with_values(position=(x + distance * (1.0 - progress), y))
    return state


def sample_frames(timeline: Timeline, fps: float) -> tuple[tuple[float, LayerState], ...]:
    """Return deterministic timestamp/state pairs for a normalized timeline."""
    return tuple((time, timeline.sample(time)) for time in timeline.frame_times(fps))
