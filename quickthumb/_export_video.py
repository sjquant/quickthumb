"""Animated GIF / WebM / MP4 exporter.

Renders the deck's slide transitions (``quickthumb.transitions``) and per-layer
entrance/exit animations (``quickthumb.Fade`` and friends) into an actual video
timeline, sampled at a fixed frame rate through the regular PIL pipeline -- so
every frame is pixel-identical to the raster renderer, unlike the HTML/PPTX
exporters which approximate effects in CSS/PowerPoint.

The timing model mirrors the HTML slideshow runtime (timeline.js /
deck_runtime.js), with the one difference a non-interactive medium forces:
there are no clicks, so ``on_click`` animations chain automatically exactly
like ``after_previous`` (the same thing PowerPoint's own video export does).
Concretely, per slide:

- The slide's transition animates the change into it, playing over the
  previous slide's final frame (slide 0 plays its transition from the matte;
  when slide 0 sets none it starts instantly, and later slides fall back to
  the HTML default 0.5s cross-fade).
- The slide's animation timeline starts when the transition starts, exactly
  like the HTML runtime: leading ``after_previous`` chains overlap the
  transition. ``with_previous`` effects run concurrently with the previous
  effect; everything else runs after it; ``delay`` holds the effect's hidden
  (entrance) or shown (exit) state before it plays.
- After the animations finish, the slide's final state holds for
  ``advance_after`` seconds when its transition sets one (counted from the
  end of the transition, like the HTML auto-advance timer), else for the
  exporter's ``slide_duration``.

Frames are eased with the CSS ``ease`` curve the HTML export uses, so both
animated formats move the same way. GIF is encoded by Pillow with per-frame
durations (holds cost one frame, not ``fps`` copies); MP4 (H.264) and WebM
(VP9) give each distinct shot and its duration to the ``ffmpeg`` binary, which
must be on PATH (or named via the ``QUICKTHUMB_FFMPEG`` environment variable).
H.264/VP9 4:2:0 output needs even dimensions, so odd-sized canvases lose their
last pixel row/column in MP4/WebM output.

Alpha does not survive into these formats: every frame is composited onto an
opaque ``matte`` color first. Slides that differ from the first slide's size
are scaled to fit and centered on the matte (PPTX-viewer letterboxing).

MP4/WebM output can carry a ``soundtrack`` audio file (any format ffmpeg
decodes: MP3, WAV, AAC, OGG, ...), encoded as AAC in MP4 and Opus in WebM.
The audio is trimmed to the video length; when ``loop_audio`` is set (the
default) a track shorter than the video repeats seamlessly. GIF cannot carry
audio.
"""

from __future__ import annotations

import contextlib
import itertools
import math
import os
import random
import shutil
import subprocess
import tempfile
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from PIL import Image, ImageChops, ImageColor, ImageDraw

from quickthumb._composition import has_layer_composition
from quickthumb._export_base import (
    flatten_layers,
    split_backdrop_prefix,
    validate_legacy_animation_export,
)
from quickthumb.errors import RenderingError, ValidationError
from quickthumb.models import (
    Animation,
    AnimationSpec,
    AudioTrack,
    ChartData,
    ChartLayer,
    GifOptions,
    GroupLayer,
    QRCodeLayer,
    TextLayer,
    VideoOptions,
    coerce_audio_track,
)
from quickthumb.motion import LayerState, Timeline, compile_timeline, resolve_staggered_timelines

if TYPE_CHECKING:
    from quickthumb.canvas import Canvas, RenderableLayer
    from quickthumb.transitions import Transition

AnimationFormat = Literal["gif", "mp4", "webm"]

# HTML deck parity: a slide with no transition set cross-fades in over 0.5s.
_DEFAULT_TRANSITION_DURATION = 0.5
_DEFAULT_FPS = {"gif": 20.0, "mp4": 30.0, "webm": 30.0}
# Tolerance for float noise in timeline arithmetic (seconds); boundaries
# closer than this are the same instant, far below any representable frame.
_TIME_EPSILON = 1e-9
# Fixed seeds keep dissolve speckle patterns deterministic across renders.
_TRANSITION_DISSOLVE_SEED = 97
_UNIT_DISSOLVE_SEED = 31
_DISSOLVE_BLOCK = 8
_BLINDS_STRIPS = 6
_COMB_STRIPS = 8
_MAX_GIF_FRAME_MEMORY_BYTES = 768 * 1024 * 1024
_MAX_SCHEDULED_AUDIO_TRACKS = 64
_MAX_SHOTS_PER_VIDEO_BATCH = 64
_VISUALIZATION_PRESETS = frozenset(
    {"bar_grow", "line_draw", "area_reveal", "point_pop", "value_count_up", "qr_reveal"}
)


def write_animation(
    canvases: list[Canvas],
    transitions: list[Transition | None],
    output_path: str,
    format: AnimationFormat,
    fps: float | None = None,
    slide_duration: float = 3.0,
    loop: int = 0,
    matte: str = "#000000",
    soundtrack: AudioTrack | str | dict | None = None,
    loop_audio: bool | None = None,
    slide_audio: list[AudioTrack | None] | None = None,
    slide_durations: list[float | None] | None = None,
    audio_offsets: list[float] | None = None,
    audio_durations: list[float] | None = None,
    audio_timeline_duration: float | None = None,
    animation: GifOptions | VideoOptions | None = None,
) -> None:
    """Render slides to an animated file, dispatching on ``format``."""
    if isinstance(animation, VideoOptions):
        if format == "gif":
            raise ValidationError("VideoOptions are only supported for MP4 or WebM output")
        if soundtrack is not None and animation.soundtrack is not None:
            raise ValidationError("specify the video soundtrack only once")
        soundtrack = animation.soundtrack if animation.soundtrack is not None else soundtrack
        loop_audio = animation.loop_audio if animation.loop_audio is not None else loop_audio
        fps = animation.fps
        matte = animation.matte
        loop = 0
        max_size = None
        colors = None
    elif animation is not None:
        if format != "gif":
            raise ValidationError("GifOptions are only supported for GIF output")
        fps = animation.fps
        loop = animation.loop
        matte = animation.matte
        max_size = animation.max_size
        colors = animation.colors
    else:
        max_size = None
        colors = None
    loop_audio = _resolve_loop_audio(soundtrack, loop_audio)
    soundtrack = coerce_audio_track(soundtrack)
    if format == "gif":
        data = export_animation_bytes(
            canvases,
            transitions,
            format="gif",
            fps=fps,
            slide_duration=slide_duration,
            loop=loop,
            matte=matte,
            soundtrack=soundtrack,
            max_size=max_size,
            colors=colors,
        )
        _write_bytes_atomically(output_path, data, suffix=".gif")
        return

    fps, matte_rgb = _validated_settings(
        canvases,
        format,
        fps,
        slide_duration,
        loop,
        matte,
        soundtrack,
        slide_audio,
        slide_durations,
        audio_offsets,
        audio_durations,
        audio_timeline_duration,
        max_size,
        colors,
    )
    plan = _deck_plan(canvases, transitions, fps, slide_duration, slide_durations)
    if slide_audio is not None and audio_offsets is None:
        audio_offsets = plan.offsets
        audio_timeline_duration = plan.duration
    shots = _deck_shots(canvases, transitions, fps, slide_duration, matte_rgb, plan=plan)
    descriptor, temp_path = _temporary_output_path(output_path, suffix=f".{format}")
    os.close(descriptor)
    try:
        _encode_video_file(
            shots,
            fps,
            format,
            temp_path,
            soundtrack,
            loop_audio,
            slide_audio,
            audio_offsets,
            audio_durations,
            audio_timeline_duration,
        )
        os.replace(temp_path, output_path)
    finally:
        _remove_quietly(temp_path)


def _write_bytes_atomically(output_path: str, data: bytes, suffix: str) -> None:
    """Replace an output only after all encoded bytes have been written."""
    descriptor, temp_path = _temporary_output_path(output_path, suffix=suffix)
    try:
        with os.fdopen(descriptor, "wb") as output_file:
            output_file.write(data)
        os.replace(temp_path, output_path)
    finally:
        _remove_quietly(temp_path)


def _temporary_output_path(output_path: str, suffix: str) -> tuple[int, str]:
    """Create a temporary output alongside its final destination for atomic replacement."""
    return tempfile.mkstemp(
        suffix=suffix,
        dir=os.path.dirname(os.path.abspath(output_path)),
    )


def export_animation_bytes(
    canvases: list[Canvas],
    transitions: list[Transition | None],
    format: AnimationFormat,
    fps: float | None = None,
    slide_duration: float = 3.0,
    loop: int = 0,
    matte: str = "#000000",
    soundtrack: AudioTrack | str | dict | None = None,
    loop_audio: bool | None = None,
    slide_audio: list[AudioTrack | None] | None = None,
    slide_durations: list[float | None] | None = None,
    audio_offsets: list[float] | None = None,
    audio_durations: list[float] | None = None,
    audio_timeline_duration: float | None = None,
    max_size: tuple[int, int] | None = None,
    colors: int | None = None,
) -> bytes:
    """Render slides to animated GIF/MP4/WebM bytes."""
    loop_audio = _resolve_loop_audio(soundtrack, loop_audio)
    soundtrack = coerce_audio_track(soundtrack)
    fps, matte_rgb = _validated_settings(
        canvases,
        format,
        fps,
        slide_duration,
        loop,
        matte,
        soundtrack,
        slide_audio,
        slide_durations,
        audio_offsets,
        audio_durations,
        audio_timeline_duration,
        max_size,
        colors,
    )
    plan = _deck_plan(canvases, transitions, fps, slide_duration, slide_durations)
    if slide_audio is not None and audio_offsets is None:
        audio_offsets = plan.offsets
        audio_timeline_duration = plan.duration
    shots = _deck_shots(canvases, transitions, fps, slide_duration, matte_rgb, plan=plan)

    if format == "gif":
        return _encode_gif(shots, loop, max_size=max_size, colors=colors)

    # ffmpeg needs a real, seekable output file (MP4 faststart rewrites the
    # header), so bytes go through a temporary file.
    descriptor, temp_path = tempfile.mkstemp(suffix=f".{format}")
    os.close(descriptor)
    try:
        _encode_video_file(
            shots,
            fps,
            format,
            temp_path,
            soundtrack,
            loop_audio,
            slide_audio,
            audio_offsets,
            audio_durations,
            audio_timeline_duration,
        )
        with open(temp_path, "rb") as video_file:
            return video_file.read()
    finally:
        # The encoder already removes the file when it fails.
        _remove_quietly(temp_path)


def _validated_settings(
    canvases: list[Canvas],
    format: AnimationFormat,
    fps: float | None,
    slide_duration: float,
    loop: int,
    matte: str,
    soundtrack: AudioTrack | None = None,
    slide_audio: list[AudioTrack | None] | None = None,
    slide_durations: list[float | None] | None = None,
    audio_offsets: list[float] | None = None,
    audio_durations: list[float] | None = None,
    audio_timeline_duration: float | None = None,
    max_size: tuple[int, int] | None = None,
    colors: int | None = None,
) -> tuple[float, tuple[int, int, int]]:
    """Validate the shared export knobs and resolve fps and matte defaults."""
    if format not in _DEFAULT_FPS:
        raise ValidationError(f"Unsupported animation format: {format!r}. Use gif, mp4, or webm.")
    if format != "gif" and max_size is not None:
        raise ValidationError("max_size is only supported for GIF output")
    if format != "gif" and colors is not None:
        raise ValidationError("colors is only supported for GIF output")
    if isinstance(loop, bool) or not isinstance(loop, int) or loop < 0:
        raise ValidationError("loop must be >= 0 (0 loops forever)")
    if format != "gif" and loop != 0:
        raise ValidationError("loop is only supported for GIF output")
    if max_size is not None and (
        not isinstance(max_size, (tuple, list))
        or len(max_size) != 2
        or any(
            isinstance(value, bool) or not isinstance(value, int) or value <= 0
            for value in max_size
        )
    ):
        raise ValidationError("max_size must contain two positive integers")
    if colors is not None and (
        isinstance(colors, bool) or not isinstance(colors, int) or not 2 <= colors <= 256
    ):
        raise ValidationError("colors must be between 2 and 256")
    if not canvases:
        raise RenderingError("No slides to animate.")
    if soundtrack is not None:
        if format == "gif":
            raise ValidationError("GIF cannot carry audio; use mp4 or webm for a soundtrack.")
        if not os.path.isfile(soundtrack.path):
            raise ValidationError(f"Soundtrack file not found: {soundtrack.path!r}")
    if slide_audio is not None:
        if sum(audio is not None for audio in slide_audio) > _MAX_SCHEDULED_AUDIO_TRACKS:
            raise ValidationError(
                f"Deck animation supports at most {_MAX_SCHEDULED_AUDIO_TRACKS} narrated slides."
            )
        if slide_durations is None or len(slide_durations) != len(slide_audio):
            raise RenderingError("Deck slide durations are out of sync.")
        if audio_durations is None:
            raise RenderingError("Deck audio schedule is incomplete.")
        if len(slide_audio) != len(audio_durations) or (
            audio_offsets is not None and len(slide_audio) != len(audio_offsets)
        ):
            raise RenderingError("Deck audio schedule is out of sync.")
        if audio_timeline_duration is not None and (
            isinstance(audio_timeline_duration, bool)
            or not isinstance(audio_timeline_duration, (int, float))
            or not math.isfinite(audio_timeline_duration)
            or audio_timeline_duration <= 0
        ):
            raise ValidationError("Deck audio timeline duration must be finite and > 0")
        for index, (audio, duration) in enumerate(zip(slide_audio, audio_durations, strict=True)):
            if audio is not None and not os.path.isfile(audio.path):
                raise ValidationError(f"Audio file not found: {audio.path!r}")
            if audio_offsets is not None and (
                isinstance(audio_offsets[index], bool)
                or not isinstance(audio_offsets[index], (int, float))
                or not math.isfinite(audio_offsets[index])
                or audio_offsets[index] < 0
            ):
                raise ValidationError("Deck audio offset must be finite and >= 0")
            if (
                isinstance(duration, bool)
                or not isinstance(duration, (int, float))
                or not math.isfinite(duration)
                or duration <= 0
            ):
                raise ValidationError("Deck audio duration must be finite and > 0")
        for duration in slide_durations:
            if duration is not None and (
                isinstance(duration, bool)
                or not isinstance(duration, (int, float))
                or not math.isfinite(duration)
                or duration <= 0
            ):
                raise ValidationError("Deck slide duration must be finite and > 0")
    if fps is None:
        fps = _DEFAULT_FPS[format]
    if (
        isinstance(fps, bool)
        or not isinstance(fps, (int, float))
        or not math.isfinite(fps)
        or fps <= 0
    ):
        raise ValidationError("fps must be > 0")
    max_fps = 100 if format == "gif" else 120
    if fps > max_fps:
        raise ValidationError(f"fps must be <= {max_fps} for {format} output")
    if isinstance(slide_duration, bool) or not isinstance(slide_duration, (int, float)):
        raise ValidationError("slide_duration must be finite")
    if not math.isfinite(slide_duration):
        raise ValidationError("slide_duration must be finite")
    if slide_duration < 0:
        raise ValidationError("slide_duration must be >= 0")
    if format in ("mp4", "webm") and (canvases[0].width < 2 or canvases[0].height < 2):
        raise ValidationError("MP4/WebM export requires canvas dimensions of at least 2x2 pixels")
    if format == "gif" and loop > 65535:
        raise ValidationError("loop must be <= 65535 for GIF output")
    try:
        matte_rgb = ImageColor.getrgb(matte)[:3]
    except (TypeError, ValueError):
        raise ValidationError(f"Invalid matte color: {matte!r}") from None
    # Validate every slide's assets up front so a missing image fails before
    # any frame is rendered or an encoder is started, leaving no partial
    # output behind (matching the all-or-nothing raster-sequence behaviour).
    for canvas in canvases:
        canvas._validate_image_paths()
    return fps, matte_rgb


def _resolve_loop_audio(
    soundtrack: AudioTrack | str | dict | None, loop_audio: bool | None
) -> bool:
    """Preserve legacy string looping while honoring AudioTrack loop settings."""
    if loop_audio is not None:
        return loop_audio
    if isinstance(soundtrack, (AudioTrack, dict)):
        track = coerce_audio_track(soundtrack)
        assert track is not None
        return track.loop
    return True


# ------------------------------------------------------------------- timeline


@dataclass
class _Shot:
    """One output frame held on screen for ``duration`` seconds."""

    frame: Image.Image  # RGB at the deck size
    duration: float


@dataclass
class _DeckPlan:
    """The rendered slide animators and their shared timeline metadata."""

    animators: list[_SlideAnimator]
    timings: list[tuple[Transition | None, float, float, float]]
    offsets: list[float]
    duration: float


def _deck_plan(
    canvases: list[Canvas],
    transitions: list[Transition | None],
    fps: float,
    slide_duration: float,
    slide_durations: list[float | None] | None,
) -> _DeckPlan:
    """Build animation state once for both visuals and scheduled narration."""
    animators = [_SlideAnimator(canvas) for canvas in canvases]
    timings = _deck_timing(
        canvases,
        transitions,
        slide_duration,
        animation_durations=[animator.duration for animator in animators],
        slide_durations=slide_durations,
        minimum_duration=1.0 / fps,
    )
    offsets: list[float] = []
    duration = 0.0
    for _, _, _, exit_time in timings:
        offsets.append(duration)
        duration += exit_time
    return _DeckPlan(animators, timings, offsets, duration)


def _deck_shots(
    canvases: list[Canvas],
    transitions: list[Transition | None],
    fps: float,
    slide_duration: float,
    matte_rgb: tuple[int, int, int],
    slide_durations: list[float | None] | None = None,
    plan: _DeckPlan | None = None,
) -> Iterator[_Shot]:
    """Yield the deck's full frame timeline as variable-duration shots."""
    size = (canvases[0].width, canvases[0].height)
    previous_final = Image.new("RGB", size, matte_rgb)
    plan = plan or _deck_plan(canvases, transitions, fps, slide_duration, slide_durations)

    for animator, timing in zip(
        plan.animators,
        plan.timings,
        strict=True,
    ):
        transition, duration_in, animation_end, exit_time = timing
        pending: _Shot | None = None
        for shot in _slide_motion_shots(
            animator,
            transition,
            duration_in,
            animation_end,
            previous_final,
            size,
            matte_rgb,
            fps,
        ):
            if pending is not None:
                yield pending
            pending = shot

        # Keep one motion shot pending so a sub-frame or zero hold can replace
        # it with the settled state without extending the shared timeline.
        final = _conform(animator.final_frame(), size, matte_rgb)
        hold = exit_time - max(animation_end, duration_in)
        if hold + _TIME_EPSILON >= 1.0 / fps:
            if pending is not None:
                yield pending
            yield _Shot(final, hold)
        elif pending is not None:
            yield _Shot(final, pending.duration + max(hold, 0.0))
        else:
            yield _Shot(final, max(exit_time, 1.0 / fps))
        previous_final = final


def _slide_motion_shots(
    animator: _SlideAnimator,
    transition: Transition | None,
    duration_in: float,
    animation_end: float,
    previous_final: Image.Image,
    size: tuple[int, int],
    matte_rgb: tuple[int, int, int],
    fps: float,
) -> Iterator[_Shot]:
    """Yield transition and layer-animation shots before the settled hold."""
    for time, duration in _sample_span(0.0, duration_in, fps):
        incoming = _conform(animator.frame_at(time), size, matte_rgb)
        progress = _ease(time / duration_in)
        yield _Shot(_transition_frame(transition, previous_final, incoming, progress), duration)
    # Between effect windows every unit's state is constant, so gaps (a
    # trailing `delay`, a pause between chained effects) collapse into one
    # held frame instead of resampling identical frames at fps.
    for seg_start, seg_end, animating in animator.segments(duration_in, animation_end):
        if animating:
            for time, duration in _sample_span(seg_start, seg_end, fps):
                yield _Shot(_conform(animator.frame_at(time), size, matte_rgb), duration)
        else:
            frame = _conform(animator.frame_at(seg_start), size, matte_rgb)
            yield _Shot(frame, seg_end - seg_start)


def animation_timeline(
    canvases: list[Canvas],
    transitions: list[Transition | None],
    slide_duration: float,
    slide_durations: list[float | None] | None = None,
    fps: float = _DEFAULT_FPS["mp4"],
) -> tuple[list[float], float]:
    """Return the shared visual start offsets and total duration for a Deck."""
    plan = _deck_plan(canvases, transitions, fps, slide_duration, slide_durations)
    return plan.offsets, plan.duration


def _deck_timing(
    canvases: list[Canvas],
    transitions: list[Transition | None],
    slide_duration: float,
    animation_durations: list[float] | None = None,
    slide_durations: list[float | None] | None = None,
    minimum_duration: float = 0.0,
) -> list[tuple[Transition | None, float, float, float]]:
    """Resolve each slide's transition, animation, and exit timing once."""
    if animation_durations is None:
        animation_durations = [_SlideAnimator(canvas).duration for canvas in canvases]
    if slide_durations is not None and len(slide_durations) != len(canvases):
        raise RenderingError("Deck slide durations are out of sync.")
    timings = []
    for index, animation_end in enumerate(animation_durations):
        transition = transitions[index] if index < len(transitions) else None
        if transition is None:
            duration_in = 0.0 if index == 0 else _DEFAULT_TRANSITION_DURATION
        elif transition.effect == "cut":
            duration_in = 0.0
        else:
            duration_in = transition.duration
        duration = slide_durations[index] if slide_durations is not None else None
        if transition is not None and transition.advance_after is not None:
            exit_time = max(
                duration_in + transition.advance_after,
                animation_end,
                duration_in,
                duration or 0.0,
            )
        elif duration is not None:
            exit_time = max(animation_end, duration_in, duration)
        else:
            exit_time = max(animation_end, duration_in) + slide_duration
        exit_time = max(exit_time, minimum_duration)
        timings.append((transition, duration_in, animation_end, exit_time))
    return timings


def _sample_span(start: float, end: float, fps: float) -> Iterator[tuple[float, float]]:
    """Sample the half-open span [start, end) as (time, frame duration) pairs."""
    length = end - start
    if length <= 0:
        return
    count = max(1, round(length * fps))
    step = length / count
    for frame_index in range(count):
        yield start + frame_index * step, step


def _conform(
    frame: Image.Image, size: tuple[int, int], matte_rgb: tuple[int, int, int]
) -> Image.Image:
    """Composite an RGBA slide frame onto the matte at the deck size.

    Slides that differ from the deck size are scaled to fit and centered,
    matching how PPTX viewers letterbox mixed-size decks.
    """
    base = Image.new("RGB", size, matte_rgb)
    if frame.size == size:
        base.paste(frame, (0, 0), frame)
        return base
    scale = min(size[0] / frame.width, size[1] / frame.height)
    fitted = (max(1, round(frame.width * scale)), max(1, round(frame.height * scale)))
    resized = frame.resize(fitted, Image.Resampling.LANCZOS)
    base.paste(resized, ((size[0] - fitted[0]) // 2, (size[1] - fitted[1]) // 2), resized)
    return base


def _ease(progress: float) -> float:
    """CSS ``ease`` -- cubic-bezier(0.25, 0.1, 0.25, 1.0) -- matching the HTML export."""
    if progress <= 0:
        return 0.0
    if progress >= 1:
        return 1.0
    x1, y1, x2, y2 = 0.25, 0.1, 0.25, 1.0
    low, high = 0.0, 1.0
    for _ in range(26):
        mid = (low + high) / 2
        x = 3 * (1 - mid) ** 2 * mid * x1 + 3 * (1 - mid) * mid**2 * x2 + mid**3
        if x < progress:
            low = mid
        else:
            high = mid
    t = (low + high) / 2
    return 3 * (1 - t) ** 2 * t * y1 + 3 * (1 - t) * t**2 * y2 + t**3


# ------------------------------------------------------- per-slide animation

# Sentinel states for a unit outside its animation windows.
_HIDDEN = object()
_SHOWN = object()


@dataclass
class _Node:
    """One scheduled animation effect: active over [start+delay, start+delay+duration]."""

    effect: Animation
    start: float


@dataclass
class _Unit:
    """A run of layers that shows/hides as one element on the animation timeline.

    Consecutive layers sharing one animation object (a flattened group) form a
    single unit, as do consecutive non-animated layers; each unit is rendered
    once through the PIL pipeline and cropped to its visible bounds, which is
    the box the reveal masks are relative to (the HTML element box).
    """

    image: Image.Image | None
    pos: tuple[int, int]
    effects: list[Animation]
    seed: int
    layers: list[RenderableLayer] = field(default_factory=list)
    component_duration: float = 0.0
    nodes: list[_Node] = field(default_factory=list)
    timeline: Timeline | None = None
    target_timelines: tuple[Timeline, ...] = ()


class _SlideAnimator:
    """Composites one slide's layer-animation state at any point in time."""

    def __init__(self, canvas: Canvas):
        self._canvas = canvas
        self._units = _build_units(canvas)
        self.duration = max(_schedule_units(self._units), _schedule_timelines(self._units))
        self._final: Image.Image | None = None

    def frame_at(self, time: float) -> Image.Image:
        """Render the slide's full RGBA frame at ``time`` seconds."""
        frame = Image.new("RGBA", (self._canvas.width, self._canvas.height), (0, 0, 0, 0))
        for unit in self._units:
            if unit.image is None:
                continue
            state = _unit_state(unit, time)
            if state is _HIDDEN:
                continue
            if unit.component_duration > 0:
                image, pos = _render_unit_image(self._canvas, unit.layers, time)
                if image is None:
                    continue
            else:
                pos = unit.pos
                image = unit.image
            if (
                unit.component_duration == 0
                and isinstance(state, tuple)
                and state
                and state[0] == "canonical"
            ):
                image = _canonical_render(unit.image, state[1], state[2])
                if image is None:
                    continue
            elif unit.component_duration == 0 and state is not _SHOWN:
                effect, reveal = state
                revealed = _animation_reveal(image, effect, reveal, unit.seed)
                if revealed is None:
                    continue
                image = revealed
            frame.alpha_composite(image, pos)
        return frame

    def final_frame(self) -> Image.Image:
        """The settled frame after every animation has played (cached)."""
        if self._final is None:
            self._final = self.frame_at(self.duration)
        return self._final

    def segments(self, start: float, end: float) -> list[tuple[float, float, bool]]:
        """Split [start, end) into (seg_start, seg_end, animating) runs.

        A segment is ``animating`` when some effect window overlaps it; outside
        every window each unit's state is constant, so a non-animating segment
        renders identically at any point within it and one frame can hold for
        the whole gap.
        """
        if end <= start:
            return []
        windows: list[tuple[float, float]] = []
        boundaries = {start, end}
        for unit in self._units:
            for node in unit.nodes:
                active_start = node.start + node.effect.delay
                window_start = max(active_start, start)
                window_end = min(active_start + node.effect.duration, end)
                if window_end > window_start:
                    windows.append((window_start, window_end))
                    boundaries.update((window_start, window_end))
            for timeline in unit.target_timelines or ((unit.timeline,) if unit.timeline else ()):
                for event in timeline.events:
                    window_start = max(event.active_start, start)
                    window_end = min(event.end, end)
                    if window_end > window_start:
                        windows.append((window_start, window_end))
                        boundaries.update((window_start, window_end))
        # Window boundaries derived from float sums can land one ulp apart
        # (e.g. 0.1 + 0.2 vs 0.3); merging cuts closer than the epsilon avoids
        # degenerate near-zero segments that would each emit a wasted frame.
        cuts = [start]
        for cut in sorted(boundaries):
            if cut - cuts[-1] > _TIME_EPSILON:
                cuts.append(cut)
        if len(cuts) == 1:
            return []
        cuts[-1] = end
        return [
            (
                seg_start,
                seg_end,
                # A segment's midpoint sits inside a window exactly when the
                # window covers the segment, staying robust to merged cuts.
                any(ws < (seg_start + seg_end) / 2 < we for ws, we in windows),
            )
            for seg_start, seg_end in itertools.pairwise(cuts)
        ]


def _build_units(canvas: Canvas) -> list[_Unit]:
    """Flatten the canvas into animation units rendered through the PIL pipeline."""
    validate_legacy_animation_export(canvas)
    canvas._validate_image_paths()
    canvas._ctx.begin_render_pass()
    group_target_counts = _canonical_group_target_counts(canvas)
    prefix, rest = split_backdrop_prefix(flatten_layers(canvas))
    if any(_has_animated_descendant_in_composed_group(layer) for layer in (*prefix, *rest)):
        raise RenderingError(
            "Animated export cannot animate descendants of a clipped or masked group. "
            "Move the animation to the group itself, or remove the group's clip or mask."
        )
    if any(getattr(layer, "animation", None) is not None for layer in prefix):
        raise RenderingError(
            "Animated export cannot animate layers that must be rasterized together for "
            "blend-mode or custom-layer backdrop compositing. Move animated layers "
            "after those backdrop-dependent layers, or remove the blend/custom layer."
        )

    # Group layers into units: the backdrop prefix is one static unit, layers
    # sharing one animation object (a flattened group) form one animated unit,
    # and runs of non-animated layers collapse into single static units.
    groups: list[tuple[object | None, list[RenderableLayer]]] = []
    if prefix:
        groups.append((None, list(prefix)))
    for layer in rest:
        animation = getattr(layer, "animation", None)
        key = id(animation) if animation is not None else None
        if groups and groups[-1][0] == key:
            groups[-1][1].append(layer)
        else:
            groups.append((key, [layer]))

    units: list[_Unit] = []
    for index, (_, layers) in enumerate(groups):
        animation = getattr(layers[0], "animation", None)
        raw_effects = animation if isinstance(animation, list) else [animation] if animation else []
        unsupported = [
            effect
            for effect in raw_effects
            if isinstance(effect, AnimationSpec)
            and effect.effect is not None
            and effect.effect.type not in _VISUALIZATION_PRESETS
        ]
        if unsupported and any(isinstance(layer, (ChartLayer, QRCodeLayer)) for layer in layers):
            raise RenderingError(
                "Chart and QR layers only support visualization AnimationSpec presets in "
                "animated export. Use a legacy effect for layer-level motion."
            )
        effects = [effect for effect in raw_effects if not isinstance(effect, AnimationSpec)]
        image, pos = _render_unit_image(canvas, layers)
        canonical = animation if isinstance(animation, AnimationSpec) else None
        target_timelines: tuple[Timeline, ...] = ()
        if canonical is not None:
            timeline = compile_timeline(canonical)
            target_count = 1
            stagger = canonical.stagger
            content = getattr(layers[0], "content", None)
            if stagger is not None:
                if stagger.target == "characters" and isinstance(content, str):
                    target_count = len(content)
                elif stagger.target in {"words", "lines"} and isinstance(layers[0], TextLayer):
                    target_count = len(
                        canvas._text.resolve_animation_targets(layers[0], stagger.target)
                    )
                elif stagger.target == "children":
                    target_count = group_target_counts.get(id(canonical), 1)
            target_timelines = resolve_staggered_timelines(timeline, target_count)
        component_duration = max(
            (_component_animation_duration(layer) for layer in layers), default=0.0
        )
        units.append(
            _Unit(
                image=image,
                pos=pos,
                effects=effects if canonical is None else [],
                seed=_UNIT_DISSOLVE_SEED + index,
                layers=layers,
                component_duration=component_duration,
                timeline=compile_timeline(canonical) if canonical is not None else None,
                target_timelines=target_timelines,
            )
        )
    return units


def _canonical_group_target_counts(canvas: Canvas) -> dict[int, int]:
    """Capture child cardinality before flattening removes group boundaries."""
    counts: dict[int, int] = {}

    def visit(layer) -> None:
        animation = getattr(layer, "animation", None)
        if (
            isinstance(animation, AnimationSpec)
            and animation.stagger
            and animation.stagger.target == "children"
            and hasattr(layer, "children")
        ):
            counts[id(animation)] = len(layer.children)
        for child in getattr(layer, "children", ()):
            visit(child)

    for layer in canvas.layers:
        visit(layer)
    return counts


def _schedule_timelines(units: list[_Unit]) -> float:
    """Return the settled duration of canonical normalized timeline units."""
    return (
        max(
            (
                max((timeline.duration for timeline in unit.target_timelines), default=0.0)
                if unit.target_timelines
                else unit.timeline.duration
            )
            for unit in units
            if unit.timeline
        )
        if any(unit.timeline for unit in units)
        else 0.0
    )


def _has_animated_descendant_in_composed_group(layer: RenderableLayer) -> bool:
    """Return whether a clipped or masked group contains an independently animated child."""
    if not isinstance(layer, GroupLayer):
        return False
    if (
        layer.animation is None
        and has_layer_composition(layer)
        and any(
            getattr(child, "animation", None) is not None
            or _has_animated_descendant_in_composed_group(child)
            for child in layer.children
        )
    ):
        return True
    return any(_has_animated_descendant_in_composed_group(child) for child in layer.children)


def _render_unit_image(
    canvas: Canvas, layers: list[RenderableLayer], time: float | None = None
) -> tuple[Image.Image | None, tuple[int, int]]:
    image = Image.new("RGBA", (canvas.width, canvas.height), (0, 0, 0, 0))
    for layer in layers:
        canvas._render_layer(image, layer, time)
    bbox = image.getbbox()
    if bbox is None:
        return None, (0, 0)
    return image.crop(bbox), (bbox[0], bbox[1])


def _schedule_units(units: list[_Unit]) -> float:
    """Assign start times to every effect, mirroring the HTML timeline runtime.

    ``with_previous`` effects start together with the previous effect; every
    other trigger (``on_click`` has no click to wait for in a video, so it
    behaves like ``after_previous``) starts a new group after the previous
    group's longest effect ends. Returns the time the last effect settles.
    """
    flat = [(unit, effect) for unit in units for effect in unit.effects]
    clock = 0.0
    index = 0
    while index < len(flat):
        group = [flat[index]]
        cursor = index + 1
        while cursor < len(flat) and flat[cursor][1].trigger == "with_previous":
            group.append(flat[cursor])
            cursor += 1
        group_end = clock
        for unit, effect in group:
            unit.nodes.append(_Node(effect=effect, start=clock))
            group_end = max(group_end, clock + effect.delay + effect.duration)
        clock = group_end
        index = cursor
    for unit in units:
        unit.nodes.sort(key=lambda node: node.start + node.effect.delay)
    return max([clock, *(unit.component_duration for unit in units)], default=0.0)


def _component_animation_duration(layer: RenderableLayer) -> float:
    """Return the settled duration of a canonical chart/QR motion preset."""
    if not isinstance(layer, (ChartLayer, QRCodeLayer)):
        return 0.0
    animations = getattr(layer, "animation", None)
    candidates = animations if isinstance(animations, list) else [animations]
    durations = []
    for animation in candidates:
        if not isinstance(animation, AnimationSpec):
            continue
        if animation.effect is None:
            durations.append(compile_timeline(animation).duration)
            continue
        if animation.effect.type not in _VISUALIZATION_PRESETS:
            continue
        timing = animation.timing
        duration = timing.duration if timing is not None else 0.5
        start = timing.start if timing is not None and timing.start is not None else 0.0
        delay = timing.delay if timing is not None else 0.0
        if animation.stagger is not None:
            if isinstance(layer, ChartLayer):
                data = layer.spec.data
                count = len(data.values) if isinstance(data, ChartData) else len(data)
            else:
                count = _qr_module_count(layer)
            duration += max(0, count - 1) * animation.stagger.delay
        durations.append(start + delay + duration)
    return max(durations, default=0.0)


def _qr_module_count(layer: QRCodeLayer) -> int:
    """Return the deterministic QR matrix cell count used by module stagger."""
    try:
        import qrcode  # ty: ignore[unresolved-import]
        from qrcode.constants import (  # ty: ignore[unresolved-import]
            ERROR_CORRECT_H,
            ERROR_CORRECT_L,
            ERROR_CORRECT_M,
            ERROR_CORRECT_Q,
        )

        code = qrcode.QRCode(
            version=None,
            error_correction={
                "L": ERROR_CORRECT_L,
                "M": ERROR_CORRECT_M,
                "Q": ERROR_CORRECT_Q,
                "H": ERROR_CORRECT_H,
            }[layer.error_correction],
            box_size=1,
            border=layer.quiet_zone,
        )
        code.add_data(layer.data, optimize=0)
        code.make(fit=True)
        matrix_size = len(code.get_matrix())
    except Exception as error:
        raise RenderingError(f"Could not prepare QR animation timing: {error}") from error
    return matrix_size * matrix_size


def _unit_state(unit: _Unit, time: float):
    """Resolve a unit's visibility at ``time``: hidden, shown, or (effect, reveal).

    The unit starts hidden when its first effect is an entrance (the HTML
    exporter's ``visibility:hidden`` priming); each node then leaves it shown
    (entrance) or hidden (exit) once its window has passed. During a window
    the reveal fraction runs 0..1 for entrances and 1..0 for exits; ``appear``
    snaps instead of interpolating.
    """
    if unit.timeline is not None:
        return _canonical_state(unit, time)
    if not unit.nodes:
        return _SHOWN
    state = _HIDDEN if unit.effects[0].animate == "entrance" else _SHOWN
    for node in unit.nodes:
        active_start = node.start + node.effect.delay
        active_end = active_start + node.effect.duration
        entrance = node.effect.animate == "entrance"
        if time < active_start:
            break
        if time < active_end:
            if node.effect.effect == "appear":
                state = _SHOWN if entrance else _HIDDEN
            else:
                progress = _ease((time - active_start) / node.effect.duration)
                state = (node.effect, progress if entrance else 1.0 - progress)
        else:
            state = _SHOWN if entrance else _HIDDEN
    return state


def _canonical_state(unit: _Unit, time: float):
    """Sample canonical motion, aggregating semantic target reveal progress."""
    timeline = unit.timeline
    if timeline is None:
        return _SHOWN
    timelines = unit.target_timelines or (timeline,)
    states = [timeline.sample(time, LayerState()) for timeline in timelines]
    event = timeline.events[0] if timeline.events else None
    if len(timelines) > 1 and event is not None:
        progresses = []
        for timeline in timelines:
            target_event = timeline.events[0] if timeline.events else event
            if time < target_event.active_start:
                progresses.append(0.0)
            elif target_event.duration == 0:
                progresses.append(1.0)
            else:
                progresses.append(
                    min(1.0, max(0.0, (time - target_event.active_start) / target_event.duration))
                )
        reveal = sum(progresses) / len(progresses)
        if event.effect == "typewriter":
            reveal = sum(state.clip_progress for state in states) / len(states)
    elif event is not None and time < event.active_start and event.effect in {"fade", "typewriter"}:
        reveal = 0.0
    elif event is not None and event.effect == "typewriter":
        reveal = sum(state.clip_progress for state in states) / len(states)
    else:
        reveal = sum(state.opacity for state in states) / len(states)
    return ("canonical", states[-1], min(1.0, max(0.0, reveal)))


def _canonical_render(image: Image.Image, state: LayerState, reveal: float) -> Image.Image | None:
    """Apply renderer-independent opacity and left-to-right reveal to a frame."""
    if reveal <= 0.0:
        return None
    output = image
    opacity = min(1.0, max(0.0, state.opacity)) * reveal
    if opacity < 1.0:
        output = _scaled_alpha(output, opacity)
    if reveal < 1.0 and state.clip_progress < 1.0:
        width = max(0, min(output.width, round(output.width * reveal)))
        mask = Image.new("L", output.size, 0)
        ImageDraw.Draw(mask).rectangle((0, 0, width, output.height), fill=255)
        output = _masked_alpha(output, mask)
    return output


def _animation_reveal(
    image: Image.Image, effect: Animation, reveal: float, seed: int
) -> Image.Image | None:
    """Apply a layer effect at reveal fraction ``reveal`` to a unit image."""
    if reveal <= 0:
        return None
    if reveal >= 1:
        return image
    name = effect.effect
    if name == "fade":
        return _scaled_alpha(image, reveal)
    mask = _animation_mask(effect, image.size, reveal, seed)
    if mask is None:
        return _scaled_alpha(image, reveal)
    return _masked_alpha(image, mask)


def _animation_mask(
    effect: Animation, size: tuple[int, int], reveal: float, seed: int
) -> Image.Image | None:
    """Build the reveal mask for one layer-animation effect, or None for fades."""
    name = effect.effect
    if name == "wipe":
        return _mask_wipe(size, reveal, getattr(effect, "direction", "up"))
    if name == "box":
        return _mask_box(size, reveal, getattr(effect, "direction", "in"))
    if name == "blinds":
        return _mask_blinds(size, reveal, getattr(effect, "orientation", "horizontal"))
    if name == "checkerboard":
        return _mask_checker(size, reveal, getattr(effect, "direction", "across"))
    if name == "circle":
        return _mask_circle(size, reveal)
    if name == "diamond":
        return _mask_diamond(size, reveal)
    if name == "dissolve":
        return _mask_dissolve(size, reveal, seed)
    if name == "wheel":
        return _mask_wheel(size, reveal, getattr(effect, "spokes", 1))
    return None


def _scaled_alpha(image: Image.Image, factor: float) -> Image.Image:
    lut = [min(255, int(value * factor)) for value in range(256)]
    faded = image.copy()
    faded.putalpha(image.getchannel("A").point(lut))
    return faded


def _masked_alpha(image: Image.Image, mask: Image.Image) -> Image.Image:
    masked = image.copy()
    masked.putalpha(ImageChops.multiply(image.getchannel("A"), mask))
    return masked


# ------------------------------------------------------------ slide transition


def _transition_frame(
    transition: Transition | None,
    previous: Image.Image,
    incoming: Image.Image,
    progress: float,
) -> Image.Image:
    """Composite one transition frame from the outgoing and incoming slides.

    ``random`` maps to a cross-fade like the HTML export (there is no viewer to
    randomize per playback), and unknown effects fall back to the same.
    """
    if progress >= 1:
        return incoming
    if progress <= 0:
        if transition is not None and transition.effect == "cut":
            return incoming
        return previous
    if transition is None:
        return Image.blend(previous, incoming, progress)
    effect = transition.effect
    if effect == "cut":
        return incoming
    if effect in ("fade", "random", "morph"):
        return Image.blend(previous, incoming, progress)
    if effect == "push":
        return _push_frame(previous, incoming, progress, getattr(transition, "direction", "left"))
    if effect == "cover":
        return _cover_frame(previous, incoming, progress, getattr(transition, "direction", "down"))
    if effect == "uncover":
        return _uncover_frame(
            previous, incoming, progress, getattr(transition, "direction", "down")
        )
    if effect == "zoom":
        return _zoom_frame(previous, incoming, progress, getattr(transition, "direction", "in"))
    if effect == "newsflash":
        return _newsflash_frame(previous, incoming, progress)
    mask = _transition_mask(transition, incoming.size, progress)
    if mask is None:
        return Image.blend(previous, incoming, progress)
    return Image.composite(incoming, previous, mask)


def _transition_mask(
    transition: Transition, size: tuple[int, int], progress: float
) -> Image.Image | None:
    """Build the incoming-slide reveal mask for one mask-style transition."""
    effect = transition.effect
    orientation = getattr(transition, "orientation", "horizontal")
    if effect == "wipe":
        return _mask_wipe(size, progress, getattr(transition, "direction", "up"))
    if effect == "split":
        return _mask_split(size, progress, orientation, getattr(transition, "direction", "out"))
    if effect == "blinds":
        return _mask_blinds(size, progress, orientation)
    if effect == "checker":
        return _mask_checker(size, progress, "across" if orientation == "horizontal" else "down")
    if effect == "comb":
        return _mask_comb(size, progress, orientation)
    if effect == "circle":
        return _mask_circle(size, progress)
    if effect == "diamond":
        return _mask_diamond(size, progress)
    if effect == "wheel":
        return _mask_wheel(size, progress, getattr(transition, "spokes", 1))
    if effect == "wedge":
        return _mask_wedge(size, progress)
    if effect == "dissolve":
        return _mask_dissolve(size, progress, _TRANSITION_DISSOLVE_SEED)
    return None


# PowerPoint names a push by where the content travels: "left" sends the old
# slide off the left edge while the new one arrives from the right. These maps
# mirror the HTML export's _DIR_IN/_DIR_OUT offsets as (dx, dy) unit factors.
_SLIDE_IN = {"left": (1, 0), "right": (-1, 0), "up": (0, 1), "down": (0, -1)}
_SLIDE_OUT = {"left": (-1, 0), "right": (1, 0), "up": (0, -1), "down": (0, 1)}


def _push_frame(
    previous: Image.Image, incoming: Image.Image, progress: float, direction: str
) -> Image.Image:
    width, height = incoming.size
    out_dx, out_dy = _SLIDE_OUT[direction]
    # Both offsets derive from one rounded shift so the slides stay exactly one
    # frame apart; rounding them independently could leave a 1px seam between.
    shift_x = round(out_dx * width * progress)
    shift_y = round(out_dy * height * progress)
    frame = Image.new("RGB", incoming.size)
    frame.paste(previous, (shift_x, shift_y))
    frame.paste(incoming, (shift_x - out_dx * width, shift_y - out_dy * height))
    return frame


def _cover_frame(
    previous: Image.Image, incoming: Image.Image, progress: float, direction: str
) -> Image.Image:
    width, height = incoming.size
    in_dx, in_dy = _SLIDE_IN[direction]
    frame = previous.copy()
    frame.paste(
        incoming,
        (round(in_dx * width * (1 - progress)), round(in_dy * height * (1 - progress))),
    )
    return frame


def _uncover_frame(
    previous: Image.Image, incoming: Image.Image, progress: float, direction: str
) -> Image.Image:
    width, height = incoming.size
    out_dx, out_dy = _SLIDE_OUT[direction]
    frame = incoming.copy()
    frame.paste(previous, (round(out_dx * width * progress), round(out_dy * height * progress)))
    return frame


def _zoom_frame(
    previous: Image.Image, incoming: Image.Image, progress: float, direction: str
) -> Image.Image:
    start_scale = 0.6 if direction == "in" else 1.4
    scale = start_scale + (1.0 - start_scale) * progress
    return _overlay_scaled(previous, incoming, scale, rotation=0.0, opacity=progress)


def _newsflash_frame(previous: Image.Image, incoming: Image.Image, progress: float) -> Image.Image:
    scale = 0.1 + 0.9 * progress
    rotation = 180.0 * (1.0 - progress)
    return _overlay_scaled(previous, incoming, scale, rotation=rotation, opacity=progress)


def _overlay_scaled(
    previous: Image.Image,
    incoming: Image.Image,
    scale: float,
    rotation: float,
    opacity: float,
) -> Image.Image:
    """Center the incoming slide over the previous one, scaled/rotated/faded."""
    width, height = incoming.size
    scaled_size = (max(1, round(width * scale)), max(1, round(height * scale)))
    overlay_content = incoming.convert("RGBA").resize(scaled_size, Image.Resampling.BILINEAR)
    if rotation:
        overlay_content = overlay_content.rotate(
            rotation, resample=Image.Resampling.BICUBIC, expand=True
        )
    overlay = Image.new("RGBA", incoming.size, (0, 0, 0, 0))
    overlay.paste(
        overlay_content,
        ((width - overlay_content.width) // 2, (height - overlay_content.height) // 2),
        overlay_content,
    )
    if opacity < 1:
        overlay = _scaled_alpha(overlay, opacity)
    frame = previous.convert("RGBA")
    frame.alpha_composite(overlay)
    return frame.convert("RGB")


# ------------------------------------------------------------------ masks
# Every mask maps a reveal fraction 0..1 to an "L" image: 255 where the
# revealed content shows, 0 where it stays hidden. For layer animations the
# box is the unit's cropped bounds (the HTML element box); for transitions it
# is the whole deck frame.


def _mask_wipe(size: tuple[int, int], reveal: float, direction: str) -> Image.Image:
    width, height = size
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    if direction == "up":
        draw.rectangle((0, height * (1 - reveal), width, height), fill=255)
    elif direction == "down":
        draw.rectangle((0, 0, width, height * reveal), fill=255)
    elif direction == "left":
        draw.rectangle((width * (1 - reveal), 0, width, height), fill=255)
    else:  # right
        draw.rectangle((0, 0, width * reveal, height), fill=255)
    return mask


def _mask_box(size: tuple[int, int], reveal: float, direction: str) -> Image.Image:
    width, height = size
    center_x, center_y = width / 2, height / 2
    if direction == "out":
        mask = Image.new("L", size, 0)
        half_w, half_h = center_x * reveal, center_y * reveal
        ImageDraw.Draw(mask).rectangle(
            (center_x - half_w, center_y - half_h, center_x + half_w, center_y + half_h),
            fill=255,
        )
        return mask
    # "in": the reveal closes from the edges toward the center.
    mask = Image.new("L", size, 255)
    half_w, half_h = center_x * (1 - reveal), center_y * (1 - reveal)
    if half_w > 0 and half_h > 0:
        ImageDraw.Draw(mask).rectangle(
            (center_x - half_w, center_y - half_h, center_x + half_w, center_y + half_h),
            fill=0,
        )
    return mask


def _mask_split(
    size: tuple[int, int], reveal: float, orientation: str, direction: str
) -> Image.Image:
    width, height = size
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    if orientation == "horizontal":
        if direction == "out":  # a vertical band opening from the center outward
            half = width / 2 * reveal
            draw.rectangle((width / 2 - half, 0, width / 2 + half, height), fill=255)
        else:  # closing in from both side edges
            edge = width / 2 * reveal
            draw.rectangle((0, 0, edge, height), fill=255)
            draw.rectangle((width - edge, 0, width, height), fill=255)
    elif direction == "out":
        half = height / 2 * reveal
        draw.rectangle((0, height / 2 - half, width, height / 2 + half), fill=255)
    else:
        edge = height / 2 * reveal
        draw.rectangle((0, 0, width, edge), fill=255)
        draw.rectangle((0, height - edge, width, height), fill=255)
    return mask


def _mask_blinds(size: tuple[int, int], reveal: float, orientation: str) -> Image.Image:
    width, height = size
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    if orientation == "horizontal":
        strip = height / _BLINDS_STRIPS
        for index in range(_BLINDS_STRIPS):
            draw.rectangle((0, index * strip, width, index * strip + strip * reveal), fill=255)
    else:
        strip = width / _BLINDS_STRIPS
        for index in range(_BLINDS_STRIPS):
            draw.rectangle((index * strip, 0, index * strip + strip * reveal, height), fill=255)
    return mask


def _mask_checker(size: tuple[int, int], reveal: float, direction: str) -> Image.Image:
    """Checkerboard sweep: alternating cells wipe in two half-phase waves."""
    width, height = size
    cell = max(8, round(min(width, height) / 8))
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    for row in range(math.ceil(height / cell)):
        for col in range(math.ceil(width / cell)):
            phase = (row + col) % 2
            local = min(1.0, max(0.0, reveal * 2 - phase))
            if local <= 0:
                continue
            x, y = col * cell, row * cell
            if direction == "across":
                draw.rectangle((x, y, x + cell * local, y + cell), fill=255)
            else:  # down
                draw.rectangle((x, y, x + cell, y + cell * local), fill=255)
    return mask


def _mask_comb(size: tuple[int, int], reveal: float, orientation: str) -> Image.Image:
    """Comb: interleaved strips sweep in from opposite edges."""
    width, height = size
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    if orientation == "horizontal":
        strip = height / _COMB_STRIPS
        for index in range(_COMB_STRIPS):
            y0, y1 = index * strip, (index + 1) * strip
            if index % 2 == 0:
                draw.rectangle((0, y0, width * reveal, y1), fill=255)
            else:
                draw.rectangle((width * (1 - reveal), y0, width, y1), fill=255)
    else:
        strip = width / _COMB_STRIPS
        for index in range(_COMB_STRIPS):
            x0, x1 = index * strip, (index + 1) * strip
            if index % 2 == 0:
                draw.rectangle((x0, 0, x1, height * reveal), fill=255)
            else:
                draw.rectangle((x0, height * (1 - reveal), x1, height), fill=255)
    return mask


def _mask_circle(size: tuple[int, int], reveal: float) -> Image.Image:
    width, height = size
    center_x, center_y = width / 2, height / 2
    radius = math.hypot(width, height) / 2 * reveal
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).ellipse(
        (center_x - radius, center_y - radius, center_x + radius, center_y + radius), fill=255
    )
    return mask


def _mask_diamond(size: tuple[int, int], reveal: float) -> Image.Image:
    width, height = size
    center_x, center_y = width / 2, height / 2
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).polygon(
        [
            (center_x, center_y - height * reveal),
            (center_x + width * reveal, center_y),
            (center_x, center_y + height * reveal),
            (center_x - width * reveal, center_y),
        ],
        fill=255,
    )
    return mask


def _mask_wheel(size: tuple[int, int], reveal: float, spokes: int) -> Image.Image:
    width, height = size
    center_x, center_y = width / 2, height / 2
    radius = math.hypot(width, height) / 2
    bounds = (center_x - radius, center_y - radius, center_x + radius, center_y + radius)
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    sector = 360.0 / spokes
    for spoke in range(spokes):
        start = -90.0 + spoke * sector
        draw.pieslice(bounds, start, start + sector * reveal, fill=255)
    return mask


def _mask_wedge(size: tuple[int, int], reveal: float) -> Image.Image:
    """Two clock hands sweeping from 12 o'clock in opposite directions."""
    width, height = size
    center_x, center_y = width / 2, height / 2
    radius = math.hypot(width, height) / 2
    bounds = (center_x - radius, center_y - radius, center_x + radius, center_y + radius)
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).pieslice(bounds, -90 - 180 * reveal, -90 + 180 * reveal, fill=255)
    return mask


def _mask_dissolve(size: tuple[int, int], reveal: float, seed: int) -> Image.Image:
    """Speckled dissolve: fixed-seed random blocks appear in a stable order."""
    width, height = size
    grid_w = math.ceil(width / _DISSOLVE_BLOCK)
    grid_h = math.ceil(height / _DISSOLVE_BLOCK)
    rng = random.Random(seed)
    threshold = reveal * 256
    data = bytes(255 if rng.randrange(256) < threshold else 0 for _ in range(grid_w * grid_h))
    tiny = Image.frombytes("L", (grid_w, grid_h), data)
    scaled = tiny.resize(
        (grid_w * _DISSOLVE_BLOCK, grid_h * _DISSOLVE_BLOCK), Image.Resampling.NEAREST
    )
    return scaled.crop((0, 0, width, height))


# --------------------------------------------------------------------- encode


def _encode_gif(
    shots: Iterable[_Shot],
    loop: int,
    *,
    max_size: tuple[int, int] | None = None,
    colors: int | None = None,
) -> bytes:
    """Encode shots as an animated GIF with per-frame durations via Pillow.

    GIF stores durations in centiseconds, so per-frame rounding would drift
    the playback clock (33.33ms frames at 30fps stored as 30ms play ~10%
    fast); instead each duration is the cumulative clock's centisecond delta,
    the same drift-free scheme the ffmpeg path uses. Frames are quantized to
    their GIF palette as they arrive, so the pending frame list holds one
    byte per pixel instead of full RGB.
    """
    frames: list[Image.Image] = []
    durations: list[int] = []
    clock = 0.0
    emitted_cs = 0
    target_size: tuple[int, int] | None = None
    for shot in shots:
        if target_size is None:
            target_size = _gif_target_size(shot.frame.size, max_size)
        frame = shot.frame
        if frame.size != target_size:
            frame = frame.resize(target_size, Image.Resampling.LANCZOS)
        estimated_memory = (len(frames) + 1) * frame.width * frame.height * 4
        if estimated_memory > _MAX_GIF_FRAME_MEMORY_BYTES:
            raise RenderingError(
                "GIF export exceeds the in-memory frame budget. Reduce fps or duration, "
                "or use MP4/WebM export."
            )
        clock += shot.duration
        duration_cs = max(1, round(clock * 100) - emitted_cs)
        emitted_cs += duration_cs
        frames.append(frame.quantize(colors=colors or 256))
        durations.append(duration_cs * 10)
    buffer = BytesIO()
    frames[0].save(
        buffer,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=durations if len(durations) > 1 else durations[0],
        loop=loop,
        optimize=True,
    )
    return buffer.getvalue()


def _gif_target_size(
    source_size: tuple[int, int], max_size: tuple[int, int] | None
) -> tuple[int, int]:
    """Return a proportional GIF size without upscaling the source frame."""
    if max_size is None:
        return source_size
    source_width, source_height = source_size
    max_width, max_height = max_size
    scale = min(1.0, max_width / source_width, max_height / source_height)
    return (
        max(1, round(source_width * scale)),
        max(1, round(source_height * scale)),
    )


_CODEC_ARGS = {
    "mp4": [
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-crf", "18", "-preset", "medium", "-movflags", "+faststart",
    ],
    "webm": [
        "-c:v", "libvpx-vp9", "-pix_fmt", "yuv420p",
        "-b:v", "0", "-crf", "32", "-row-mt", "1",
    ],
}  # fmt: skip
# WebM containers only allow Opus/Vorbis audio; MP4 uses the universal AAC.
_AUDIO_ARGS = {
    "mp4": ["-c:a", "aac", "-b:a", "192k"],
    "webm": ["-c:a", "libopus", "-b:a", "128k"],
}


def _encode_video_file(
    shots: Iterable[_Shot],
    fps: float,
    format: str,
    output_path: str,
    soundtrack: AudioTrack | None = None,
    loop_audio: bool = True,
    slide_audio: list[AudioTrack | None] | None = None,
    audio_offsets: list[float] | None = None,
    audio_durations: list[float] | None = None,
    audio_timeline_duration: float | None = None,
) -> None:
    """Encode timestamped shot images with ffmpeg at a constant output frame rate.

    Frame counts follow the cumulative clock (floor(clock*fps + 0.5) - emitted),
    so rounding never drifts the timing across long decks. Half-up rounding
    (rather than round()'s half-even) makes the count shift-invariant by one
    frame, guaranteeing every shot lasting >= 1/fps writes at least one frame —
    round-half-even can swallow a full-frame shot that lands on an exact .5
    boundary, dropping the deck's final settled frame.

    Each distinct shot is written once with its duration in an ffconcat manifest;
    ffmpeg performs constant-frame-rate duplication internally, avoiding repeated
    full-resolution RGB writes through Python for long static holds.
    """
    binary = _ffmpeg_binary()
    if slide_audio is not None:
        audio_input, audio_output = _scheduled_audio_args(
            format,
            soundtrack,
            loop_audio,
            slide_audio,
            audio_offsets or [],
            audio_durations or [],
            audio_timeline_duration or 0.0,
        )
    elif soundtrack is None:
        if format == "mp4":
            audio_input = ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
            audio_output = ["-map", "0:v", "-map", "1:a:0", *_AUDIO_ARGS[format]]
        else:
            audio_input, audio_output = [], ["-map", "0:v", "-an"]
    else:
        # The audio must never be the shortest stream or -shortest would cut
        # the video to the track length: looping repeats the track forever
        # (-stream_loop precedes its -i), otherwise silence pads it forever
        # (apad), and either way -shortest then trims audio to video length.
        audio_input = (["-stream_loop", "-1"] if loop_audio else []) + ["-i", soundtrack.path]
        filters = [f"volume={soundtrack.volume}"]
        if not loop_audio:
            filters.append("apad")
        audio_output = [
            "-map", "0:v", "-map", "1:a:0", "-af", ",".join(filters),
            *_AUDIO_ARGS[format],
        ]  # fmt: skip
    with tempfile.TemporaryDirectory() as video_dir:
        directory = Path(video_dir)
        segments, duration = _encode_shot_batches(
            binary,
            shots,
            fps,
            format,
            directory,
        )
        manifest_path = _write_video_segment_manifest(segments, directory)
        command = [
            binary,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(manifest_path),
            *audio_input,
            *audio_output,
            "-t",
            f"{duration:.9f}",
            "-c:v",
            "copy",
            *(["-movflags", "+faststart"] if format == "mp4" else []),
            output_path,
        ]
        _run_video_ffmpeg(command, format, output_path)


def _encode_shot_batches(
    binary: str,
    shots: Iterable[_Shot],
    fps: float,
    format: str,
    directory: Path,
) -> tuple[list[Path], float]:
    """Encode bounded groups of distinct shots and return their total duration."""
    segments: list[Path] = []
    entries: list[tuple[str, float]] = []
    batch_directory = directory / "frames-000"
    batch_directory.mkdir()
    clock = 0.0
    emitted = 0
    batch_duration = 0.0
    last_frame: Image.Image | None = None
    for shot in shots:
        clock += shot.duration
        last_frame = shot.frame
        count = math.floor(clock * fps + 0.5) - emitted
        if count <= 0:
            continue
        name = f"shot-{len(entries):03d}.png"
        shot.frame.save(batch_directory / name, format="PNG")
        duration = count / fps
        entries.append((name, duration))
        batch_duration += duration
        emitted += count
        if len(entries) == _MAX_SHOTS_PER_VIDEO_BATCH:
            segments.append(
                _encode_shot_batch(
                    binary,
                    batch_directory,
                    entries,
                    batch_duration,
                    fps,
                    format,
                    directory,
                    len(segments),
                )
            )
            shutil.rmtree(batch_directory)
            entries = []
            batch_duration = 0.0
            batch_directory = directory / f"frames-{len(segments):03d}"
            batch_directory.mkdir()
    if emitted == 0 and last_frame is not None:
        name = "shot-000.png"
        last_frame.save(batch_directory / name, format="PNG")
        entries.append((name, 1.0 / fps))
        batch_duration = 1.0 / fps
        emitted = 1
    if entries:
        segments.append(
            _encode_shot_batch(
                binary,
                batch_directory,
                entries,
                batch_duration,
                fps,
                format,
                directory,
                len(segments),
            )
        )
    shutil.rmtree(batch_directory)
    if not segments:
        raise RenderingError("Animation produced no frames.")
    return segments, emitted / fps


def _encode_shot_batch(
    binary: str,
    frame_directory: Path,
    entries: list[tuple[str, float]],
    duration: float,
    fps: float,
    format: str,
    output_directory: Path,
    index: int,
) -> Path:
    """Encode one bounded shot manifest into a normalized video segment."""
    manifest_path = frame_directory / "frames.ffconcat"
    manifest_path.write_text(
        "ffconcat version 1.0\n"
        + "".join(
            f"file '{name}'\nduration {shot_duration:.12f}\n" for name, shot_duration in entries
        )
        + f"file '{entries[-1][0]}'\n",
        encoding="utf-8",
    )
    output_path = output_directory / f"segment-{index:03d}.{format}"
    _run_video_ffmpeg(
        [
            binary,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(manifest_path),
            "-t",
            f"{max(duration - 0.5 / fps, 0.5 / fps):.9f}",
            "-vf",
            f"fps={fps:g},crop=trunc(iw/2)*2:trunc(ih/2)*2",
            *_CODEC_ARGS[format],
            str(output_path),
        ],
        format,
        str(output_path),
    )
    return output_path


def _write_video_segment_manifest(segments: list[Path], directory: Path) -> Path:
    """Write the bounded encoded segments as one concat-demuxer input."""
    manifest_path = directory / "segments.ffconcat"
    manifest_path.write_text(
        "ffconcat version 1.0\n" + "".join(f"file '{segment.name}'\n" for segment in segments),
        encoding="utf-8",
    )
    return manifest_path


def _run_video_ffmpeg(command: list[str], format: str, output_path: str) -> None:
    """Run one video encoder/muxer command with shared failure cleanup."""
    try:
        result = subprocess.run(command, check=False, capture_output=True, text=True)
    except OSError as error:
        _remove_quietly(output_path)
        raise RenderingError(
            "MP4/WebM export could not start ffmpeg. Install FFmpeg "
            "(e.g. 'brew install ffmpeg' or 'apt install ffmpeg'), or set "
            "QUICKTHUMB_FFMPEG to its executable path."
        ) from error
    if result.returncode != 0:
        _remove_quietly(output_path)
        detail = result.stderr.strip()[-2000:]
        raise RenderingError(
            f"ffmpeg failed while encoding {format} output" + (f":\n{detail}" if detail else ".")
        )


def _scheduled_audio_args(
    format: str,
    soundtrack: AudioTrack | None,
    loop_audio: bool,
    slide_audio: list[AudioTrack | None],
    offsets: list[float],
    durations: list[float],
    timeline_duration: float,
) -> tuple[list[str], list[str]]:
    """Build one ffmpeg filter graph for a music bed and scheduled narration."""
    inputs: list[str] = []
    input_index = 1
    filters: list[str]
    if soundtrack is None:
        filters = [f"anullsrc=r=48000:cl=stereo,atrim=duration={timeline_duration:.6f}[bed]"]
    else:
        if loop_audio:
            inputs.extend(["-stream_loop", "-1"])
        inputs.extend(["-i", soundtrack.path])
        filters = [
            f"[{input_index}:a]volume={soundtrack.volume},apad,atrim=duration={timeline_duration:.6f}[bed]"
        ]
        input_index += 1
    labels = ["[bed]"]
    for audio, offset, duration in zip(slide_audio, offsets, durations, strict=True):
        if audio is None:
            continue
        inputs.extend(["-i", audio.path])
        label = f"[voice{input_index}]"
        filters.append(
            f"[{input_index}:a]volume={audio.volume},apad,atrim=duration={duration:.6f},"
            f"adelay={round(offset * 1000)}:all=1{label}"
        )
        labels.append(label)
        input_index += 1
    filters.append(f"{''.join(labels)}amix=inputs={len(labels)}:duration=first:normalize=0[mix]")
    return inputs, [
        "-map",
        "0:v",
        "-filter_complex",
        ";".join(filters),
        "-map",
        "[mix]",
        *_AUDIO_ARGS[format],
    ]


def _remove_quietly(path: str) -> None:
    with contextlib.suppress(OSError):
        os.unlink(path)


def _ffmpeg_binary() -> str:
    override = os.environ.get("QUICKTHUMB_FFMPEG")
    if override:
        binary = shutil.which(override)
        if binary:
            return binary
        raise RenderingError(
            "MP4/WebM export requires a working ffmpeg binary. Install ffmpeg "
            "(e.g. 'brew install ffmpeg' or 'apt install ffmpeg'), or set "
            "QUICKTHUMB_FFMPEG to its executable path."
        )
    binary = shutil.which("ffmpeg")
    if binary is None:
        raise RenderingError(
            "MP4/WebM export requires the ffmpeg binary, which was not found on PATH. "
            "Install ffmpeg (e.g. 'brew install ffmpeg' or 'apt install ffmpeg'), or set "
            "the QUICKTHUMB_FFMPEG environment variable to its location. "
            "Animated GIF export works without ffmpeg."
        )
    return binary
