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
(VP9) are piped as raw frames to the ``ffmpeg`` binary, which must be on PATH
(or named via the ``QUICKTHUMB_FFMPEG`` environment variable). H.264/VP9
4:2:0 output needs even dimensions, so odd-sized canvases lose their last
pixel row/column in MP4/WebM output.

Alpha does not survive into these formats: every frame is composited onto an
opaque ``matte`` color first. Slides that differ from the first slide's size
are scaled to fit and centered on the matte (PPTX-viewer letterboxing).
"""

from __future__ import annotations

import contextlib
import math
import os
import random
import shutil
import subprocess
import tempfile
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from io import BytesIO
from typing import TYPE_CHECKING, Literal

from PIL import Image, ImageChops, ImageColor, ImageDraw

from quickthumb._export_base import flatten_layers, split_backdrop_prefix
from quickthumb.errors import RenderingError, ValidationError
from quickthumb.models import Animation

if TYPE_CHECKING:
    from quickthumb.canvas import Canvas, RenderableLayer
    from quickthumb.transitions import Transition

AnimationFormat = Literal["gif", "mp4", "webm"]

# HTML deck parity: a slide with no transition set cross-fades in over 0.5s.
_DEFAULT_TRANSITION_DURATION = 0.5
_DEFAULT_FPS = {"gif": 20.0, "mp4": 30.0, "webm": 30.0}
# Fixed seeds keep dissolve speckle patterns deterministic across renders.
_TRANSITION_DISSOLVE_SEED = 97
_UNIT_DISSOLVE_SEED = 31
_DISSOLVE_BLOCK = 8
_BLINDS_STRIPS = 6
_COMB_STRIPS = 8


def write_animation(
    canvases: list[Canvas],
    transitions: list[Transition | None],
    output_path: str,
    format: AnimationFormat,
    fps: float | None = None,
    slide_duration: float = 3.0,
    loop: int = 0,
    matte: str = "#000000",
) -> None:
    """Render slides to an animated file, dispatching on ``format``."""
    if format == "gif":
        data = export_animation_bytes(
            canvases,
            transitions,
            format="gif",
            fps=fps,
            slide_duration=slide_duration,
            loop=loop,
            matte=matte,
        )
        with open(output_path, "wb") as output_file:
            output_file.write(data)
        return

    fps, matte_rgb = _validated_settings(canvases, format, fps, slide_duration, loop, matte)
    size = (canvases[0].width, canvases[0].height)
    shots = _deck_shots(canvases, transitions, fps, slide_duration, matte_rgb)
    _encode_video_file(shots, size, fps, format, output_path)


def export_animation_bytes(
    canvases: list[Canvas],
    transitions: list[Transition | None],
    format: AnimationFormat,
    fps: float | None = None,
    slide_duration: float = 3.0,
    loop: int = 0,
    matte: str = "#000000",
) -> bytes:
    """Render slides to animated GIF/MP4/WebM bytes."""
    fps, matte_rgb = _validated_settings(canvases, format, fps, slide_duration, loop, matte)
    shots = _deck_shots(canvases, transitions, fps, slide_duration, matte_rgb)

    if format == "gif":
        return _encode_gif(shots, loop)

    # ffmpeg needs a real, seekable output file (MP4 faststart rewrites the
    # header), so bytes go through a temporary file.
    size = (canvases[0].width, canvases[0].height)
    descriptor, temp_path = tempfile.mkstemp(suffix=f".{format}")
    os.close(descriptor)
    try:
        _encode_video_file(shots, size, fps, format, temp_path)
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
) -> tuple[float, tuple[int, int, int]]:
    """Validate the shared export knobs and resolve fps and matte defaults."""
    if format not in _DEFAULT_FPS:
        raise ValidationError(f"Unsupported animation format: {format!r}. Use gif, mp4, or webm.")
    if not canvases:
        raise RenderingError("No slides to animate.")
    if fps is None:
        fps = _DEFAULT_FPS[format]
    if not fps > 0:
        raise ValidationError("fps must be > 0")
    if fps > 120:
        raise ValidationError("fps must be <= 120")
    if slide_duration < 0:
        raise ValidationError("slide_duration must be >= 0")
    if loop < 0:
        raise ValidationError("loop must be >= 0 (0 loops forever)")
    try:
        matte_rgb = ImageColor.getrgb(matte)[:3]
    except ValueError:
        raise ValidationError(f"Invalid matte color: {matte!r}") from None
    # Validate every slide's assets up front so a missing image fails before
    # any frame is rendered or an encoder is started, leaving no partial
    # output behind (matching the all-or-nothing raster-sequence behaviour).
    for canvas in canvases:
        canvas._validate_image_paths()
    return fps, matte_rgb


# ------------------------------------------------------------------- timeline


@dataclass
class _Shot:
    """One output frame held on screen for ``duration`` seconds."""

    frame: Image.Image  # RGB at the deck size
    duration: float


def _deck_shots(
    canvases: list[Canvas],
    transitions: list[Transition | None],
    fps: float,
    slide_duration: float,
    matte_rgb: tuple[int, int, int],
) -> Iterator[_Shot]:
    """Yield the deck's full frame timeline as variable-duration shots."""
    size = (canvases[0].width, canvases[0].height)
    previous_final = Image.new("RGB", size, matte_rgb)

    for index, canvas in enumerate(canvases):
        animator = _SlideAnimator(canvas)
        transition = transitions[index] if index < len(transitions) else None

        if transition is None:
            # HTML parity for later slides; slide 0 with nothing set starts
            # clean rather than fading in from the matte.
            duration_in = 0.0 if index == 0 else _DEFAULT_TRANSITION_DURATION
        elif transition.effect == "cut":
            duration_in = 0.0
        else:
            duration_in = transition.duration

        animation_end = animator.duration
        if transition is not None and transition.advance_after is not None:
            exit_time = max(duration_in + transition.advance_after, animation_end, duration_in)
        else:
            exit_time = max(animation_end, duration_in) + slide_duration

        emitted = False
        for time, duration in _sample_span(0.0, duration_in, fps):
            incoming = _conform(animator.frame_at(time), size, matte_rgb)
            progress = _ease(time / duration_in)
            yield _Shot(_transition_frame(transition, previous_final, incoming, progress), duration)
            emitted = True
        for time, duration in _sample_span(duration_in, animation_end, fps):
            yield _Shot(_conform(animator.frame_at(time), size, matte_rgb), duration)
            emitted = True

        final = _conform(animator.final_frame(), size, matte_rgb)
        hold = exit_time - max(animation_end, duration_in)
        if hold > 0 or not emitted:
            yield _Shot(final, max(hold, 1.0 / fps))
        previous_final = final


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
    nodes: list[_Node] = field(default_factory=list)


class _SlideAnimator:
    """Composites one slide's layer-animation state at any point in time."""

    def __init__(self, canvas: Canvas):
        self._canvas = canvas
        self._units = _build_units(canvas)
        self.duration = _schedule_units(self._units)
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
            if state is _SHOWN:
                image = unit.image
            else:
                effect, reveal = state
                revealed = _animation_reveal(unit.image, effect, reveal, unit.seed)
                if revealed is None:
                    continue
                image = revealed
            frame.alpha_composite(image, unit.pos)
        return frame

    def final_frame(self) -> Image.Image:
        """The settled frame after every animation has played (cached)."""
        if self._final is None:
            self._final = self.frame_at(self.duration)
        return self._final


def _build_units(canvas: Canvas) -> list[_Unit]:
    """Flatten the canvas into animation units rendered through the PIL pipeline."""
    canvas._validate_image_paths()
    canvas._ctx.begin_render_pass()
    prefix, rest = split_backdrop_prefix(flatten_layers(canvas))
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
        effects = animation if isinstance(animation, list) else [animation] if animation else []
        image, pos = _render_unit_image(canvas, layers)
        units.append(_Unit(image=image, pos=pos, effects=effects, seed=_UNIT_DISSOLVE_SEED + index))
    return units


def _render_unit_image(
    canvas: Canvas, layers: list[RenderableLayer]
) -> tuple[Image.Image | None, tuple[int, int]]:
    image = Image.new("RGBA", (canvas.width, canvas.height), (0, 0, 0, 0))
    for layer in layers:
        canvas._render_layer(image, layer)
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
    return clock


def _unit_state(unit: _Unit, time: float):
    """Resolve a unit's visibility at ``time``: hidden, shown, or (effect, reveal).

    The unit starts hidden when its first effect is an entrance (the HTML
    exporter's ``visibility:hidden`` priming); each node then leaves it shown
    (entrance) or hidden (exit) once its window has passed. During a window
    the reveal fraction runs 0..1 for entrances and 1..0 for exits; ``appear``
    snaps instead of interpolating.
    """
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
    if transition is None:
        return Image.blend(previous, incoming, progress)
    effect = transition.effect
    if effect == "cut":
        return incoming
    if effect in ("fade", "random"):
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
    in_dx, in_dy = _SLIDE_IN[direction]
    frame = Image.new("RGB", incoming.size)
    frame.paste(previous, (round(out_dx * width * progress), round(out_dy * height * progress)))
    frame.paste(
        incoming,
        (round(in_dx * width * (1 - progress)), round(in_dy * height * (1 - progress))),
    )
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


def _encode_gif(shots: Iterable[_Shot], loop: int) -> bytes:
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
    for shot in shots:
        clock += shot.duration
        duration_cs = max(1, round(clock * 100) - emitted_cs)
        emitted_cs += duration_cs
        frames.append(shot.frame.quantize(colors=256))
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


def _encode_video_file(
    shots: Iterable[_Shot],
    size: tuple[int, int],
    fps: float,
    format: str,
    output_path: str,
) -> None:
    """Stream raw RGB frames into ffmpeg, expanding shots to a constant frame rate.

    Frame counts follow the cumulative clock (round(clock*fps) - emitted), so
    rounding never drifts the timing across long decks.
    """
    binary = _ffmpeg_binary()
    width, height = size
    command = [
        binary, "-hide_banner", "-loglevel", "error", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{width}x{height}",
        "-r", f"{fps:g}", "-i", "pipe:0", "-an",
        "-vf", "crop=trunc(iw/2)*2:trunc(ih/2)*2",
        *_CODEC_ARGS[format], output_path,
    ]  # fmt: skip

    with tempfile.TemporaryFile() as stderr_file:
        process = subprocess.Popen(
            command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=stderr_file
        )
        assert process.stdin is not None
        clock = 0.0
        emitted = 0
        last_frame: bytes | None = None
        try:
            try:
                for shot in shots:
                    clock += shot.duration
                    last_frame = shot.frame.tobytes()
                    count = round(clock * fps) - emitted
                    for _ in range(count):
                        process.stdin.write(last_frame)
                    emitted += count
                if emitted == 0 and last_frame is not None:
                    process.stdin.write(last_frame)
            except BrokenPipeError:
                # ffmpeg died mid-stream; fall through to surface its stderr.
                pass
            finally:
                # Closing flushes, which can hit the same broken pipe; the exit
                # code check below is what reports the failure.
                with contextlib.suppress(BrokenPipeError, OSError):
                    process.stdin.close()
        except BaseException:
            # Frame rendering failed mid-stream: reap ffmpeg and drop the
            # truncated output so a partial file is never mistaken for a
            # successful export.
            process.kill()
            process.wait()
            _remove_quietly(output_path)
            raise
        if process.wait() != 0:
            stderr_file.seek(0)
            detail = stderr_file.read().decode("utf-8", errors="replace").strip()[-2000:]
            _remove_quietly(output_path)
            raise RenderingError(
                f"ffmpeg failed while encoding {format} output"
                + (f":\n{detail}" if detail else ".")
            )


def _remove_quietly(path: str) -> None:
    with contextlib.suppress(OSError):
        os.unlink(path)


def _ffmpeg_binary() -> str:
    override = os.environ.get("QUICKTHUMB_FFMPEG")
    if override:
        return override
    binary = shutil.which("ffmpeg")
    if binary is None:
        raise RenderingError(
            "MP4/WebM export requires the ffmpeg binary, which was not found on PATH. "
            "Install ffmpeg (e.g. 'brew install ffmpeg' or 'apt install ffmpeg'), or set "
            "the QUICKTHUMB_FFMPEG environment variable to its location. "
            "Animated GIF export works without ffmpeg."
        )
    return binary
