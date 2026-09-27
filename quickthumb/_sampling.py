"""Canonical still and timeline capture shared by Canvas and Deck."""

from __future__ import annotations

import base64
import functools
import hashlib
import math
from collections.abc import Sequence
from importlib import metadata
from numbers import Real
from typing import TYPE_CHECKING, Literal, cast

from quickthumb.errors import ValidationError
from quickthumb.models import (
    CanonicalFrame,
    FrameSequence,
    RenderEnvironment,
    TimelineSegment,
    VideoLayer,
)

if TYPE_CHECKING:
    from PIL import Image

    from quickthumb._document import Document

# Uniform captures stop before the timeline end; float noise in a duration
# such as 0.1 * 3 must not add a frame at the exclusive end instant.
_TIME_EPSILON = 1e-9
# Published timings are rounded so float-sum noise never reaches consumers.
_TIME_DIGITS = 9
# Matches the animated exporters' upper frame-rate bound.
_MAX_FPS = 120.0
# Distinct raw RGBA bytes one capture may hold; identical frames share storage.
_MAX_CAPTURE_BYTES = 768 * 1024 * 1024
# Frames one capture may observe, so request size alone cannot grow the time
# list and frame metadata without bound (about 14 minutes at 120 fps).
_MAX_OBSERVATIONS = 100_000


def sample_document(
    source: Document,
    time: float | Sequence[float] | None,
    *,
    fps: float | None,
    hold: float,
    matte: str,
) -> FrameSequence:
    """Capture settled pages, explicit timeline instants, or a uniform timeline grid."""
    from quickthumb._document import _contract_kind

    if time is not None and fps is not None:
        raise ValidationError("sample accepts either time or fps, not both")
    _require_non_negative_finite(hold, "hold")
    canonical_matte = _canonical_matte(matte)
    if fps is not None:
        _require_frame_rate(fps)
    times = None if time is None else _requested_times(time)
    kind = _contract_kind(source)
    still = times is None and fps is None
    _require_capture_fits(source, still=still)
    if still:
        return _still_capture(source, kind)
    return _timeline_capture(
        source,
        kind,
        times,
        fps=None if fps is None else float(fps),
        hold=float(hold),
        matte=canonical_matte,
    )


def _still_capture(source: Document, kind: Literal["canvas", "deck"]) -> FrameSequence:
    from quickthumb._document import _contract_canvases

    canvases = _contract_canvases(source)
    for canvas in canvases:
        canvas._validate_image_paths()
    environment = _render_environment(source)
    encoder = _FrameEncoder()
    return FrameSequence(
        kind=kind,
        capture="still",
        environment=environment,
        frames=[
            encoder.encode(canvas._render_to_image(), index=index, slide=index, time=None)
            for index, canvas in enumerate(canvases)
        ],
    )


def _timeline_capture(
    source: Document,
    kind: Literal["canvas", "deck"],
    times: list[float] | None,
    *,
    fps: float | None,
    hold: float,
    matte: str,
) -> FrameSequence:
    from quickthumb._document import _contract_timeline_inputs
    from quickthumb._export_video import TimelineSampler

    environment = _render_environment(source)
    canvases, transitions, slide_durations = _contract_timeline_inputs(source, hold)
    sampler = TimelineSampler(
        canvases,
        transitions,
        slide_duration=hold,
        slide_durations=slide_durations,
        matte=matte,
    )
    try:
        duration = round(sampler.duration, _TIME_DIGITS)
        if times is None:
            assert fps is not None
            count = max(1, math.ceil(duration * fps - _TIME_EPSILON))
            _require_observation_count(count)
            times = [index / fps for index in range(count)]
        encoder = _FrameEncoder()
        frames = []
        for index, instant in enumerate(times):
            slide, image = sampler.frame_at(instant)
            frames.append(encoder.encode(image, index=index, slide=slide, time=instant))
        segments = [
            TimelineSegment(
                slide=index,
                start=round(start, _TIME_DIGITS),
                transition_end=round(transition_end, _TIME_DIGITS),
                animation_end=round(animation_end, _TIME_DIGITS),
                end=round(end, _TIME_DIGITS),
            )
            for index, (start, transition_end, animation_end, end) in enumerate(sampler.segments())
        ]
    finally:
        sampler.close()
    return FrameSequence(
        kind=kind,
        capture="timeline",
        matte=matte,
        fps=fps,
        duration=duration,
        timeline=segments,
        environment=environment,
        frames=frames,
    )


def _render_environment(source: Document) -> RenderEnvironment:
    """Describe the renderer facts that determine this document's pixels.

    FFmpeg decodes video-layer pixels, so its version is part of the
    environment exactly when the document contains a video layer; resolving
    it up front fails before any frame renders when FFmpeg is unavailable.
    """
    from quickthumb._document import _contract_layers
    from quickthumb._video import ffmpeg_version

    has_video = any(isinstance(layer, VideoLayer) for layer in _contract_layers(source))
    return _static_environment().model_copy(
        update={"ffmpeg_version": ffmpeg_version() if has_video else None}
    )


@functools.cache
def _static_environment() -> RenderEnvironment:
    import PIL
    from PIL import features

    return RenderEnvironment(
        quickthumb_version=metadata.version("quickthumb"),
        pillow_version=PIL.__version__,
        freetype_version=features.version("freetype2"),
        text_layout="raqm" if features.check("raqm") else "basic",
    )


class _FrameEncoder:
    """Encode frames while bounding the distinct pixel data one capture holds."""

    def __init__(self) -> None:
        self._payloads: dict[str, str] = {}
        self._held_bytes = 0

    def encode(
        self, image: Image.Image, *, index: int, slide: int, time: float | None
    ) -> CanonicalFrame:
        raw = image.convert("RGBA").tobytes()
        digest = hashlib.sha256(raw).hexdigest()
        payload = self._payloads.get(digest)
        if payload is None:
            self._held_bytes += len(raw)
            if self._held_bytes > _MAX_CAPTURE_BYTES:
                raise _capture_budget_error()
            payload = base64.b64encode(raw).decode("ascii")
            self._payloads[digest] = payload
        # Identical frames share one payload string; the digest was computed
        # from these exact bytes, so re-validating it would only rehash them.
        return CanonicalFrame.model_construct(
            index=index,
            slide=slide,
            time=time,
            width=image.width,
            height=image.height,
            sha256=digest,
            data=payload,
        )


def _require_capture_fits(source: Document, *, still: bool) -> None:
    """Reject, before any frame renders, a capture that cannot fit the budget.

    A still capture holds every page, since distinct pages rarely repeat; a
    timeline capture holds at least one frame at the first page's size.
    """
    from quickthumb._document import _contract_canvases

    sizes = [canvas.width * canvas.height * 4 for canvas in _contract_canvases(source)]
    if (sum(sizes) if still else sizes[0]) > _MAX_CAPTURE_BYTES:
        raise _capture_budget_error()


def _capture_budget_error() -> ValidationError:
    return ValidationError(
        "sample exceeds the in-memory capture budget of "
        f"{_MAX_CAPTURE_BYTES // (1024 * 1024)} MiB of distinct frames; "
        "request fewer instants, a lower fps, or a shorter hold, or sample a smaller document"
    )


def _canonical_matte(matte: str) -> str:
    from quickthumb._export_video import matte_color

    return "#{:02X}{:02X}{:02X}".format(*matte_color(matte))


def _requested_times(time: float | Sequence[float]) -> list[float]:
    values: Sequence[object] = (
        time if isinstance(time, Sequence) and not isinstance(time, (str, bytes)) else (time,)
    )
    if not values:
        raise ValidationError("sample times must not be empty")
    # Checked on the caller's sequence, before any copy or per-instant work.
    _require_observation_count(len(values))
    for value in values:
        _require_non_negative_finite(value, "sample time")
    times = [float(cast(float, value)) for value in values]
    if any(later < earlier for earlier, later in zip(times, times[1:], strict=False)):
        raise ValidationError("sample times must be in ascending order")
    return times


def _require_observation_count(count: int) -> None:
    if count > _MAX_OBSERVATIONS:
        raise ValidationError(
            f"sample requests {count} observations but at most {_MAX_OBSERVATIONS} are "
            "allowed; request fewer instants, a lower fps, or a shorter hold"
        )


def _require_frame_rate(fps: object) -> None:
    if isinstance(fps, bool) or not isinstance(fps, Real) or not 0 < float(fps) <= _MAX_FPS:
        raise ValidationError(f"fps must be greater than zero and at most {_MAX_FPS:g}")


def _require_non_negative_finite(value: object, name: str) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, Real)
        or not math.isfinite(value)
        or value < 0
    ):
        raise ValidationError(f"{name} must be a finite non-negative number")
