"""Renderer-independent motion timelines and deterministic layer sampling."""

from __future__ import annotations

import math
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Literal, cast, get_args

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic import ValidationError as PydanticValidationError

from quickthumb._measurements import layer_id_for
from quickthumb.errors import RenderingError, ValidationError
from quickthumb.models import (
    AnimationSpec,
    ExportDiagnostic,
    ExportPolicy,
    HexColor,
    KeyframeSpec,
    MotionEasingName,
    TimingSpec,
    TrackSpec,
    validate_hex_color,
)
from quickthumb.transitions import Transition, coerce_transition

if TYPE_CHECKING:
    from quickthumb.canvas import Canvas
    from quickthumb.deck import Deck

MotionValue = tuple[float, float] | float | str
MotionTargetName = Literal["characters", "words", "lines", "children"]
TargetOrder = Literal["document", "top_to_bottom", "left_to_right", "reverse"]
MotionProperty = Literal[
    "position", "scale", "rotation", "opacity", "clip_progress", "blur", "color"
]
TrackBlend = Literal["replace", "add", "multiply"]

EASING_NAMES = frozenset(get_args(MotionEasingName))


@dataclass(frozen=True)
class ResolvedMotionTarget:
    """One deterministic member of a semantic animation target collection.

    ``value`` is deliberately opaque.  Text and group renderers can retain
    their public layout/placement objects without making the normalized motion
    model depend on renderer-specific types.
    """

    index: int
    value: Any
    source_range: tuple[int, int] | None = None
    position: tuple[float, float] | None = None
    size: tuple[float, float] | None = None


def resolve_target_order(
    count: int,
    order: TargetOrder = "document",
    positions: Sequence[tuple[float, float]] | None = None,
) -> tuple[int, ...]:
    """Return stable indices for a semantic target collection.

    Layout-aware orders require one position per item.  Equal coordinates keep
    document order, making ties and repeated renders deterministic.
    """
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        raise ValidationError("target count must be a non-negative integer")
    if order not in {"document", "top_to_bottom", "left_to_right", "reverse"}:
        raise ValidationError(
            "target order must be document, top_to_bottom, left_to_right, or reverse"
        )
    if positions is not None and len(positions) != count:
        raise ValidationError("target positions must match target count")
    indices = list(range(count))
    if order == "reverse":
        indices.reverse()
    elif order in {"top_to_bottom", "left_to_right"}:
        if positions is None:
            raise ValidationError(f"{order} target order requires positions")
        axis = 1 if order == "top_to_bottom" else 0
        indices.sort(key=lambda index: (positions[index][axis], index))
    return tuple(indices)


def resolve_targets(
    items: Sequence[Any],
    *,
    order: TargetOrder = "document",
    positions: Sequence[tuple[float, float]] | None = None,
    sizes: Sequence[tuple[float, float]] | None = None,
) -> tuple[ResolvedMotionTarget, ...]:
    """Resolve text/group members through an existing public layout sequence."""
    ordered = resolve_target_order(len(items), order, positions)
    if sizes is not None and len(sizes) != len(items):
        raise ValidationError("target sizes must match target count")
    return tuple(
        ResolvedMotionTarget(
            index=index,
            value=items[index],
            position=positions[index] if positions is not None else None,
            size=sizes[index] if sizes is not None else None,
        )
        for index in ordered
    )


def resolve_text_targets(
    text: str,
    target: Literal["characters", "words", "lines"],
    *,
    lines: Sequence[str] | None = None,
    order: Literal["document", "reverse"] = "document",
) -> tuple[ResolvedMotionTarget, ...]:
    """Resolve semantic text members without changing the text layout.

    ``lines`` should be supplied by the renderer when wrapping is enabled.  If
    omitted, explicit newline boundaries are used.  Word splitting preserves
    whitespace in each returned member so the original text can be reconstructed
    exactly and whitespace still advances layout.
    """
    if not isinstance(text, str):
        raise ValidationError("text target resolution requires a string")
    if target == "characters":
        items: Sequence[Any] = tuple(text)
        ranges = tuple((index, index + 1) for index in range(len(text)))
    elif target == "words":
        matches = tuple(match for match in re.finditer(r"\S+", text))
        items = tuple(match.group(0) for match in matches)
        ranges = tuple((match.start(), match.end()) for match in matches)
    elif target == "lines":
        if lines is None:
            items = tuple(text.split("\n"))
            ranges = []
            cursor = 0
            for item in items:
                ranges.append((cursor, cursor + len(item)))
                cursor += len(item) + 1
        else:
            items = tuple(lines)
            ranges = []
            cursor = 0
            for item in items:
                start = text.find(item, cursor) if item else cursor
                start = cursor if start < 0 else start
                ranges.append((start, start + len(item)))
                cursor = start + len(item)
                if cursor < len(text) and text[cursor] == "\n":
                    cursor += 1
    else:
        raise ValidationError("text target must be characters, words, or lines")
    ordered = resolve_target_order(len(items), order)
    return tuple(
        ResolvedMotionTarget(
            index=index,
            value=items[index],
            source_range=ranges[index] if ranges else None,
        )
        for index in ordered
    )


def resolve_staggered_timelines(
    timeline: Timeline,
    target_count: int,
) -> tuple[Timeline, ...]:
    """Expand a normalized timeline into one timeline per semantic target.

    Stagger metadata remains untouched in the serialized source timeline.  The
    returned timelines are runtime views with the target offset folded into the
    event start, so every renderer samples the shared ``Timeline``/``LayerState``
    pipeline consistently.
    """
    if not isinstance(timeline, Timeline):
        raise ValidationError("stagger expansion requires a Timeline")
    if isinstance(target_count, bool) or not isinstance(target_count, int) or target_count < 0:
        raise ValidationError("target count must be a non-negative integer")
    if target_count == 0:
        return ()
    expanded: list[Timeline] = []
    for target_index in range(target_count):
        events = tuple(
            event.model_copy(
                update={
                    "start": event.start
                    + (
                        float(event.stagger.get("delay", 0.0)) * target_index
                        if event.stagger
                        else 0.0
                    ),
                    "stagger": None if event.stagger else event.stagger,
                }
            )
            for event in timeline.events
        )
        expanded.append(Timeline(events=events))
    return tuple(expanded)


def validate_easing_name(name: str | None) -> str:
    """Validate and canonicalize a supported deterministic easing name."""
    if name is None:
        return "linear"
    if not isinstance(name, str) or name not in EASING_NAMES:
        supported = ", ".join(sorted(EASING_NAMES))
        raise ValidationError(f"unknown easing {name!r}; expected one of: {supported}")
    return name


def easing_value(name: str | None, progress: float) -> float:
    """Return an eased progress for a finite normalized input."""
    easing = validate_easing_name(name)
    if not math.isfinite(progress):
        raise ValidationError("easing progress must be finite")
    t = min(1.0, max(0.0, progress))
    if easing == "linear":
        return t
    if easing == "ease":
        return _cubic_bezier(t, 0.25, 0.1, 0.25, 1.0)
    if easing == "ease_in":
        return t * t
    if easing == "ease_out":
        return 1.0 - (1.0 - t) * (1.0 - t)
    if easing == "ease_in_out":
        return _ease_in_out(t, 2)
    if easing.endswith("_sine"):
        return _ease_sine(easing, t)
    if easing.endswith("_back"):
        return _ease_back(easing, t)
    power = {"quad": 2, "cubic": 3, "quart": 4, "quint": 5}[easing.split("_")[-1]]
    if easing.startswith("ease_in_out"):
        return _ease_in_out(t, power)
    if easing.startswith("ease_in"):
        return t**power
    return 1.0 - (1.0 - t) ** power


def _ease_in_out(t: float, power: int) -> float:
    """Apply a symmetric polynomial ease-in-out curve."""
    return (2 ** (power - 1)) * t**power if t < 0.5 else 1 - ((-2 * t + 2) ** power) / 2


def _ease_sine(name: str, t: float) -> float:
    """Apply a deterministic sine easing curve."""
    if name == "ease_in_sine":
        return 1.0 - math.cos(t * math.pi / 2)
    if name == "ease_out_sine":
        return math.sin(t * math.pi / 2)
    return -(math.cos(math.pi * t) - 1.0) / 2.0


def _ease_back(name: str, t: float) -> float:
    """Apply a fixed-overshoot back easing curve."""
    amount = 1.70158
    if name == "ease_in_back":
        return (amount + 1) * t**3 - amount * t**2
    if name == "ease_out_back":
        return 1 + (amount + 1) * (t - 1) ** 3 + amount * (t - 1) ** 2
    return (
        ((2 * t) ** 2 * ((amount * 1.525 + 1) * 2 * t - amount * 1.525)) / 2
        if t < 0.5
        else ((2 * t - 2) ** 2 * ((amount * 1.525 + 1) * (t * 2 - 2) + amount * 1.525) + 2) / 2
    )


def _cubic_bezier(t: float, x1: float, y1: float, x2: float, y2: float) -> float:
    """Solve a cubic-bezier y value for x using fixed Newton iterations."""
    parameter = t
    for _ in range(8):
        x = _bezier(parameter, x1, x2)
        derivative = (
            3 * (1 - parameter) ** 2 * x1
            + 6 * (1 - parameter) * parameter * (x2 - x1)
            + 3 * parameter**2 * (1 - x2)
        )
        if abs(derivative) < 1e-12:  # pragma: no cover - public curves are non-degenerate
            break
        parameter = min(1.0, max(0.0, parameter - (x - t) / derivative))
    return _bezier(parameter, y1, y2)


def _bezier(t: float, first: float, second: float) -> float:
    """Evaluate one cubic-bezier coordinate with endpoints 0 and 1."""
    return 3 * (1 - t) ** 2 * t * first + 3 * (1 - t) * t**2 * second + t**3


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
    blend: TrackBlend = "replace"

    @model_validator(mode="after")
    def validate_keyframes(self) -> NormalizedTrack:
        if not self.keyframes:
            raise ValidationError("normalized tracks must contain at least one keyframe")
        times = [keyframe.time for keyframe in self.keyframes]
        if times != sorted(times) or len(times) != len(set(times)):
            raise ValidationError("normalized keyframe times must be strictly increasing")
        for keyframe in self.keyframes:
            _validate_property_value(self.property, keyframe.value)
        if self.blend == "add" and self.property != "position":
            raise ValidationError("additive tracks are only supported for position")
        if self.blend == "multiply" and self.property not in {"scale", "opacity", "clip_progress"}:
            raise ValidationError(
                "multiplicative tracks are only supported for scale, opacity, and clip_progress"
            )
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

    @model_validator(mode="after")
    def validate_options(self) -> TimelineEvent:
        """Validate easing metadata when normalized timelines are restored."""
        validate_easing_name(self.options.get("easing"))
        return self

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

    @field_validator("position")
    @classmethod
    def validate_position(cls, position: tuple[float, float] | None) -> tuple[float, float] | None:
        """Reject non-finite coordinates before they reach a renderer."""
        if position is not None and not all(math.isfinite(value) for value in position):
            raise ValueError("position coordinates must be finite")
        return position

    def with_values(self, **values: MotionValue | None) -> LayerState:
        """Return a state with selected properties replaced."""
        try:
            return type(self).model_validate({**self.model_dump(), **values})
        except PydanticValidationError as error:
            raise ValidationError(f"invalid layer state update: {error}") from error


def transform_matrix(state: LayerState) -> tuple[tuple[float, float, float], ...]:
    """Return the affine matrix for scale, then rotation, then translation.

    The matrix follows the renderer-independent convention ``T · R · S``.
    Consequently a local point is scaled first, rotated around the origin, and
    translated by ``state.position``. A missing position is treated as zero.
    """
    x, y = state.position or (0.0, 0.0)
    angle = math.radians(state.rotation)
    cosine, sine = math.cos(angle), math.sin(angle)
    scale = state.scale
    return (
        (scale * cosine, -scale * sine, x),
        (scale * sine, scale * cosine, y),
        (0.0, 0.0, 1.0),
    )


def apply_transform(point: tuple[float, float], state: LayerState) -> tuple[float, float]:
    """Apply the documented ``T · R · S`` transform to a local point."""
    if (
        not isinstance(point, (tuple, list))
        or len(point) != 2
        or any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in point)
        or not all(math.isfinite(value) for value in point)
    ):
        raise ValidationError("transform points must contain two finite numbers")
    matrix = transform_matrix(state)
    return (
        matrix[0][0] * point[0] + matrix[0][1] * point[1] + matrix[0][2],
        matrix[1][0] * point[0] + matrix[1][1] * point[1] + matrix[1][2],
    )


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
        if base is not None and not isinstance(base, LayerState):
            raise ValidationError("sample base must be a LayerState")
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
    """Compile canonical animation specs into one deterministic composition.

    The input order is the composition order.  A spec starts a new sequence
    group by default (including ``on_click`` and ``after_previous``), while
    ``with_previous`` joins the current group.  Absolute ``start`` values are
    anchors, not cursor assignments: a later relative event still follows the
    latest settled event.  Stagger metadata is retained for layer-aware
    consumers because target cardinality is not part of an AnimationSpec.
    """
    specs = list(spec) if isinstance(spec, (list, tuple)) else [spec]
    if not specs:
        return Timeline()
    if not all(isinstance(item, AnimationSpec) for item in specs):
        raise ValidationError("timeline compilation requires AnimationSpec values")

    events: list[TimelineEvent] = []
    composition = _CompositionCursor()
    for item in specs:
        event = _compile_spec(item, composition)
        events.append(event)
        composition.advance(event)
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


@dataclass
class _CompositionCursor:
    """State used while lowering sequence and parallel composition groups."""

    group_start: float = 0.0
    settled_end: float = 0.0

    def start_for(self, timing: TimingSpec) -> float:
        """Resolve a relative or absolute start without losing overlap state."""
        if timing.start is not None:
            return float(timing.start)
        if timing.trigger == "with_previous":
            return self.group_start
        return self.settled_end

    def advance(self, event: TimelineEvent) -> None:
        """Advance the settled cursor and open the next composition group."""
        self.settled_end = max(self.settled_end, event.end)
        if event.trigger != "with_previous":
            self.group_start = event.start


def _compile_spec(spec: AnimationSpec, composition: _CompositionCursor) -> TimelineEvent:
    """Compile one spec after resolving its composition-group timing anchor."""
    timing = spec.timing
    effect = spec.effect
    tracks = tuple(_normalize_track(track) for track in spec.tracks or ())
    track_duration = max((track.duration for track in tracks), default=0.0)
    if timing is None:
        duration = track_duration if spec.tracks is not None else 0.5
        trigger = None
        delay = 0.0
        start = composition.settled_end
    else:
        duration = timing.duration
        if track_duration > duration:
            raise ValidationError("timing duration cannot be shorter than the final keyframe time")
        trigger = timing.trigger
        delay = timing.delay
        start = composition.start_for(timing)

    options = effect.model_dump(mode="json", by_alias=True, exclude_none=True) if effect else {}
    if effect is not None:
        tracks = _compile_preset_tracks(effect.type, options, duration)
    if spec.easing is not None:
        options["easing"] = spec.easing
    elif effect is not None:
        options["easing"] = _preset_easing(options)
    validate_easing_name(options.get("easing"))
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


_FEEL_EASINGS = {
    "gentle": "ease_in_out_sine",
    "soft": "ease_out_cubic",
    "snappy": "ease_out_back",
    "dramatic": "ease_in_out_quint",
    "minimal": "linear",
}


def _preset_easing(options: Mapping[str, Any]) -> str:
    """Resolve a preset's explicit easing, feel profile, or linear default."""
    return cast(str, options.get("easing") or _FEEL_EASINGS.get(options.get("feel"), "linear"))


def _compile_preset_tracks(
    effect: str, options: Mapping[str, Any], duration: float
) -> tuple[NormalizedTrack, ...]:
    """Lower a semantic preset into renderer-independent normalized tracks."""
    distance = float(
        options.get("distance", 48.0 if effect in {"rise", "fall", "slide"} else 12.0) or 0.0
    )

    def track(
        property: MotionProperty,
        values: tuple[MotionValue, ...],
        *,
        blend: TrackBlend = "replace",
    ) -> NormalizedTrack:
        if len(values) == 1:
            times = (0.0,)
        else:
            times = tuple(index * duration / (len(values) - 1) for index in range(len(values)))
        return NormalizedTrack(
            property=property,
            blend=blend,
            keyframes=tuple(
                NormalizedKeyframe(time=time, value=value)
                for time, value in zip(times, values, strict=True)
            ),
        )

    oscillation_progress = tuple(index / 16 for index in range(17))

    if effect == "fade":
        return (track("opacity", (0.0, 1.0), blend="multiply"),)
    if effect in {"zoom", "pop"}:
        return (track("scale", (0.8, 1.0), blend="multiply"),)
    if effect == "ken_burns":
        return (track("scale", (1.0, 1.1), blend="multiply"),)
    if effect == "typewriter":
        return (track("clip_progress", (0.0, 1.0), blend="multiply"),)
    if effect in {
        "bar_grow",
        "line_draw",
        "area_reveal",
        "point_pop",
        "value_count_up",
        "qr_reveal",
    }:
        return (track("clip_progress", (0.0, 1.0)),)
    if effect == "pulse":
        return (
            track(
                "scale",
                tuple(
                    1.0 + 0.1 * math.sin(math.pi * progress) for progress in oscillation_progress
                ),
                blend="multiply",
            ),
        )
    if effect == "float":
        return (
            track(
                "position",
                tuple(
                    (0.0, -distance * math.sin(progress * math.tau))
                    for progress in oscillation_progress
                ),
                blend="add",
            ),
        )
    if effect == "shake":
        return (
            track(
                "position",
                tuple(
                    (distance * math.sin(progress * math.tau), 0.0)
                    for progress in oscillation_progress
                ),
                blend="add",
            ),
        )
    if effect in {"rise", "fall", "slide"}:
        origin = options.get("from") or {"rise": "bottom", "fall": "top", "slide": "left"}[effect]
        offsets = {
            "bottom": (0.0, distance),
            "top": (0.0, -distance),
            "left": (-distance, 0.0),
            "right": (distance, 0.0),
            "center": (0.0, 0.0),
        }
        return (track("position", (offsets.get(origin, (0.0, 0.0)), (0.0, 0.0)), blend="add"),)
    raise ValidationError(f"unsupported motion preset {effect!r}")


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
    eased_progress = easing_value(event.options.get("easing"), progress)
    for track in event.tracks:
        value = _sample_track(track, progress, event.duration, event.options.get("easing"))
        state = _compose_track_value(state, track, value)
    if event.effect is not None and event.source == "legacy":
        state = _sample_effect(event, eased_progress, state)
    return state


def _compose_track_value(
    state: LayerState, track: NormalizedTrack, value: MotionValue
) -> LayerState:
    """Apply a normalized track using its explicit composition mode."""
    if track.blend == "replace":
        return state.with_values(**{track.property: value})
    if track.blend == "add":
        if not isinstance(value, tuple):
            return state
        x, y = state.position or (0.0, 0.0)
        return state.with_values(position=(x + value[0], y + value[1]))
    current = getattr(state, track.property)
    if not isinstance(current, (int, float)) or not isinstance(value, (int, float)):
        raise ValidationError(f"{track.blend} tracks require numeric values")
    return state.with_values(**{track.property: current * value})


def _sample_track(
    track: NormalizedTrack, progress: float, duration: float, easing: str | None = None
) -> MotionValue:
    """Sample a local track at normalized event progress."""
    local_time = progress * duration
    if local_time <= track.keyframes[0].time:
        return track.keyframes[0].value
    if local_time >= track.keyframes[-1].time:
        return track.keyframes[-1].value
    for left, right in zip(track.keyframes, track.keyframes[1:], strict=True):
        if local_time <= right.time:
            ratio = (local_time - left.time) / (right.time - left.time)
            eased_ratio = easing_value(easing, ratio)
            if track.property in {"opacity", "clip_progress", "color"}:
                eased_ratio = min(1.0, max(0.0, eased_ratio))
            return _interpolate(left.value, right.value, eased_ratio)
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
    """Interpolate RGB(A) colors, treating omitted alpha as fully opaque."""
    left_hex, right_hex = left[1:], right[1:]
    if len(left_hex) not in (6, 8) or len(right_hex) not in (6, 8):  # pragma: no cover
        raise ValidationError("color keyframes must use six- or eight-digit hexadecimal colors")
    output_alpha = len(left_hex) == 8 or len(right_hex) == 8
    if len(left_hex) == 6:
        left_hex += "FF"
    if len(right_hex) == 6:
        right_hex += "FF"
    channels = [
        round(int(a, 16) + (int(b, 16) - int(a, 16)) * ratio)
        for a, b in zip(
            (left_hex[i : i + 2] for i in range(0, len(left_hex), 2)),
            (right_hex[i : i + 2] for i in range(0, len(right_hex), 2)),
            strict=True,
        )
    ]
    return "#" + "".join(f"{channel:02X}" for channel in channels[: 4 if output_alpha else 3])


def _sample_effect(event: TimelineEvent, progress: float, state: LayerState) -> LayerState:
    """Sample renderer-independent effects whose state mapping is unambiguous."""
    effect = event.effect
    if effect == "fade":
        return state.with_values(opacity=state.opacity * min(1.0, max(0.0, progress)))
    if effect in {"zoom", "pop"}:
        return state.with_values(scale=state.scale * (0.8 + 0.2 * progress))
    if effect == "typewriter":
        progress = min(1.0, max(0.0, progress))
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


# Export capability contract -------------------------------------------------

ExportTarget = Literal["raster", "video", "html", "pptx"]
CapabilityFeature = Literal[
    "position",
    "scale",
    "rotation",
    "opacity",
    "clip_progress",
    "blur",
    "color",
    "easing",
    "stagger",
    "motion_path",
    "morph",
    "chart_animation",
    "audio_sync",
]
SupportLevel = Literal["full", "native", "partial", "fallback", "unsupported"]
Fallback = Literal["fade", "rasterize", "static"]


@dataclass(frozen=True)
class MotionCapability:
    """The declared support and deterministic fallback for one target feature."""

    feature: CapabilityFeature
    target: ExportTarget
    support: SupportLevel
    fallback: Fallback | None = None


_CAPABILITY_FEATURES: tuple[CapabilityFeature, ...] = (
    "position",
    "scale",
    "rotation",
    "opacity",
    "clip_progress",
    "blur",
    "color",
    "easing",
    "stagger",
    "motion_path",
    "morph",
    "chart_animation",
    "audio_sync",
)
_FULL_CAPABILITIES: dict[CapabilityFeature, tuple[SupportLevel, Fallback | None]] = dict.fromkeys(
    _CAPABILITY_FEATURES, ("full", None)
)
_CAPABILITIES: dict[ExportTarget, dict[CapabilityFeature, MotionCapability]] = {}
for _target in ("raster", "video"):
    _CAPABILITIES[_target] = {
        feature: MotionCapability(feature, _target, support, fallback)
        for feature, (support, fallback) in _FULL_CAPABILITIES.items()
    }
_CAPABILITIES["html"] = {
    feature: MotionCapability(feature, "html", "partial", "fade" if feature == "blur" else None)
    if feature == "blur"
    else MotionCapability(feature, "html", "full")
    for feature in _CAPABILITY_FEATURES
}
_PPTX_FALLBACKS: dict[CapabilityFeature, tuple[SupportLevel, Fallback | None]] = {
    "position": ("native", None),
    "scale": ("native", None),
    "rotation": ("native", None),
    "opacity": ("native", None),
    "clip_progress": ("fallback", "fade"),
    "blur": ("unsupported", "rasterize"),
    "color": ("partial", "static"),
    "easing": ("partial", "fade"),
    "stagger": ("native", None),
    "motion_path": ("partial", "rasterize"),
    "morph": ("partial", "fade"),
    "chart_animation": ("fallback", "fade"),
    "audio_sync": ("unsupported", "static"),
}
_CAPABILITIES["pptx"] = {
    feature: MotionCapability(feature, "pptx", *_PPTX_FALLBACKS[feature])
    for feature in _CAPABILITY_FEATURES
}

CAPABILITY_MATRIX = MappingProxyType(
    {target: MappingProxyType(row) for target, row in _CAPABILITIES.items()}
)


def _normalize_target(target: ExportTarget | str) -> ExportTarget:
    aliases = {"gif": "raster", "mp4": "video", "webm": "video", "png": "raster"}
    normalized = aliases.get(str(target).lower(), str(target).lower())
    if normalized not in _CAPABILITIES:
        raise ValidationError("target must be one of raster, video, html, or pptx")
    return normalized  # type: ignore[return-value]


def capabilities_for(target: ExportTarget | str) -> Mapping[CapabilityFeature, MotionCapability]:
    """Return the immutable capability row for an export target."""
    normalized = _normalize_target(target)
    return CAPABILITY_MATRIX[normalized]


def _capability_features_for(animation: object) -> tuple[CapabilityFeature, ...]:
    if isinstance(animation, AnimationSpec):
        features: list[CapabilityFeature] = []
        if animation.tracks:
            features.extend(track.type for track in animation.tracks)
        if animation.effect:
            preset_features: dict[str, tuple[CapabilityFeature, ...]] = {
                "fade": ("opacity",),
                "rise": ("position", "opacity"),
                "fall": ("position", "opacity"),
                "slide": ("position", "opacity"),
                "zoom": ("scale", "opacity"),
                "pop": ("scale", "opacity"),
                "float": ("position",),
                "pulse": ("scale",),
                "shake": ("rotation",),
                "ken_burns": ("position", "scale"),
                "typewriter": ("clip_progress",),
                "bar_grow": ("clip_progress",),
                "line_draw": ("clip_progress",),
                "area_reveal": ("clip_progress",),
                "point_pop": ("clip_progress",),
                "value_count_up": ("clip_progress",),
                "qr_reveal": ("clip_progress",),
            }
            features.extend(preset_features[animation.effect.type])
            if animation.effect.easing:
                features.append("easing")
        if animation.stagger:
            features.append("stagger")
        return tuple(dict.fromkeys(features))
    return ("opacity",)


def _iter_export_layers(source: Canvas | Deck) -> Iterable[tuple[str, object]]:
    def walk(layer: object, index: int, path: tuple[int, ...]):
        yield layer_id_for(layer, index, path), layer
        for child_index, child in enumerate(getattr(layer, "children", ())):
            yield from walk(child, child_index, (*path, child_index))

    canvases = cast(Iterable[Any], source.slides if hasattr(source, "slides") else [source])
    for canvas in canvases:
        for layer_index, layer in enumerate(canvas.layers):
            yield from walk(layer, layer_index, (layer_index,))


def validate_export(
    source: Canvas | Deck,
    target: ExportTarget | str,
    policy: ExportPolicy | None = None,
) -> list[ExportDiagnostic]:
    """Validate motion against a target without invoking any exporter."""
    normalized = _normalize_target(target)
    resolved_policy = policy or ExportPolicy()
    row = capabilities_for(normalized)
    diagnostics: list[ExportDiagnostic] = []
    for layer_id, layer in _iter_export_layers(source):
        animations = getattr(layer, "animation", None)
        if animations is None:
            continue
        items = animations if isinstance(animations, list) else [animations]
        for animation in items:
            for feature in _capability_features_for(animation):
                capability = row[feature]
                canonical_unimplemented = isinstance(animation, AnimationSpec)
                declared_support = "unsupported" if canonical_unimplemented else capability.support
                declared_fallback = "static" if canonical_unimplemented else capability.fallback
                action = resolved_policy.pptx.get(layer_id) if normalized == "pptx" else None
                if action is None:
                    action = resolved_policy.unsupported_motion
                fallback = declared_fallback
                if action == "native" and declared_support not in ("full", "native"):
                    raise RenderingError(
                        f"{feature} motion on layer {layer_id} cannot use native handling "
                        f"for {normalized}"
                    )
                if declared_support in ("full", "native"):
                    action = "native"
                    fallback = None
                elif action == "rasterize":
                    fallback = "rasterize"
                elif action == "static":
                    fallback = "static"
                elif action == "warn" and fallback is None:
                    fallback = "fade"
                message = (
                    f"{feature} motion on layer {layer_id} is {declared_support} for {normalized}"
                    if action == "native"
                    else (
                        f"{feature} motion on layer {layer_id} requires {action} handling "
                        f"for {normalized}"
                    )
                )
                if action == "error" and declared_support not in ("full", "native"):
                    raise RenderingError(message)
                diagnostic_support = declared_support
                if action != "native" and declared_support not in ("full", "native"):
                    diagnostic_support = "fallback"
                diagnostics.append(
                    ExportDiagnostic(
                        layer_id=layer_id,
                        feature=feature,
                        target=normalized,
                        support=diagnostic_support,
                        fallback=fallback,
                        message=message,
                    )
                )
    return diagnostics


def validate_motion_export(source: Canvas | Deck, target: ExportTarget | str, policy=None):
    """Backward-compatible descriptive alias for :func:`validate_export`."""
    return validate_export(source, target, policy)
