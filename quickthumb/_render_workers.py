"""Bounded, spawn-safe animation frame rendering with process-local state."""

from __future__ import annotations

import contextlib
import multiprocessing
from collections import deque
from collections.abc import Generator, Iterable
from concurrent.futures import Future, ProcessPoolExecutor
from concurrent.futures.process import BrokenProcessPool
from dataclasses import dataclass
from multiprocessing.util import Finalize
from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image
from pydantic import BaseModel

from quickthumb._base import is_url
from quickthumb.asset_cache import ResolvedAsset
from quickthumb.errors import RenderingError, ValidationError
from quickthumb.models import Grain, PluginLayer, VideoLayer

if TYPE_CHECKING:
    from quickthumb._export_video import _SlideAnimator
    from quickthumb.canvas import Canvas, RenderableLayer
    from quickthumb.transitions import Transition


@dataclass(frozen=True)
class _CanvasSpec:
    """Only authored data and resolved assets cross the process boundary."""

    width: int
    height: int
    platform: str | None
    layers: list[RenderableLayer]
    cache_dir: Path
    timeout: float
    max_bytes: int
    records: dict[tuple[str, str], ResolvedAsset]

    @classmethod
    def capture(cls, canvas: Canvas) -> _CanvasSpec:
        # _deck_plan already rendered every unit, so snapshot its effective
        # assets. Eagerly resolving all declared fonts can break a rich-text
        # layer whose parts override an unavailable, unused default font.
        # Captions may first appear later; pin those fonts when available, but
        # leave unused/failed cues to the same render-time validation as before.
        for layer in canvas._iter_layers_deep():
            if isinstance(layer, VideoLayer):
                for caption in layer.captions:
                    if caption.font and is_url(caption.font):
                        with contextlib.suppress(RenderingError, OSError):
                            canvas._fonts.resolve_remote_font_reference(caption.font)
        resolver = canvas._ctx.asset_resolver
        return cls(
            canvas.width,
            canvas.height,
            canvas.platform,
            canvas.layers,
            resolver.cache_dir,
            resolver.timeout,
            resolver.max_bytes,
            dict(resolver._records),
        )

    def build(self) -> Canvas:
        from quickthumb.canvas import Canvas

        canvas = Canvas(self.width, self.height, layers=self.layers, platform=self.platform)
        resolver = canvas._ctx.asset_resolver
        resolver.cache_dir = self.cache_dir
        resolver.timeout = self.timeout
        resolver.max_bytes = self.max_bytes
        # Existing records are pinned to the parent export. Workers must never
        # refresh remote content halfway through a supposedly identical frame.
        resolver.offline = True
        resolver._records = dict(self.records)
        return canvas


def _unseeded_grain(value: object) -> bool:
    if isinstance(value, Grain):
        return value.seed is None and value.intensity > 0 and value.opacity > 0
    if isinstance(value, BaseModel):
        return any(_unseeded_grain(getattr(value, field)) for field in type(value).model_fields)
    if isinstance(value, dict):
        return any(_unseeded_grain(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_unseeded_grain(item) for item in value)
    return False


def validate_parallel_canvases(canvases: list[Canvas]) -> None:
    """Refuse process-local extensions and unpinned randomness without changing workers=1."""
    from quickthumb.canvas import Canvas, CustomLayer

    for canvas in canvases:
        if type(canvas) is not Canvas:
            raise ValidationError(
                "Parallel rendering requires built-in Canvas objects; use workers=1"
            )
        for layer in canvas._iter_layers_deep():
            if isinstance(layer, (CustomLayer, PluginLayer)):
                raise ValidationError(
                    "Parallel rendering does not support custom/plugin layers; use workers=1"
                )
            if isinstance(layer, VideoLayer) and is_url(layer.source):
                raise ValidationError("Parallel video layers require a local source; use workers=1")
            if _unseeded_grain(layer):
                raise ValidationError(
                    "Parallel rendering requires an explicit Grain seed; use workers=1"
                )


class _FrameRenderer:
    """Rebuild at most the current slide and its outgoing transition source."""

    def __init__(self, specs, timings, size, matte, reduced_motion):
        self.specs: list[_CanvasSpec] = specs
        self.timings: list[tuple[Transition | None, float, float, float]] = timings
        self.size: tuple[int, int] = size
        self.matte: tuple[int, int, int] = matte
        self.reduced_motion: bool = reduced_motion
        self.index = -1
        self.canvas: Canvas | None = None
        self.previous: Canvas | None = None
        self.animator: _SlideAnimator | None = None
        self.previous_final: Image.Image | None = None

    def close(self) -> None:
        for canvas in (self.canvas, self.previous):
            if canvas is not None:
                canvas._ctx.close_video_decoders()
        self.index = -1
        self.canvas = self.previous = None
        self.animator = None
        self.previous_final = None

    def _prepare(self, index: int) -> None:
        from quickthumb._export_video import _conform, _SlideAnimator

        duration_in = self.timings[index][1]
        reuse_previous = index == self.index + 1 and index > 0 and duration_in > 0
        previous = self.canvas if reuse_previous else None
        previous_animator = self.animator if reuse_previous else None
        # Adjacent slides normally share the outgoing source. Reusing its
        # already prepared units avoids rasterizing that slide a second time.
        if self.previous is not None:
            self.previous._ctx.close_video_decoders()
        if self.canvas is not None and previous is None:
            self.canvas._ctx.close_video_decoders()
        self.canvas = None
        self.previous = previous
        self.animator = None
        self.previous_final = None
        self.index = index
        try:
            if index > 0 and duration_in > 0:
                if self.previous is None:
                    self.previous = self.specs[index - 1].build()
                    previous_animator = _SlideAnimator(
                        self.previous, {}, reduced_motion=self.reduced_motion
                    )
                assert previous_animator is not None
                self.previous_final = _conform(
                    previous_animator.final_export_frame(), self.size, self.matte
                )
                self.previous._ctx.close_video_decoders()
                # Keep only the outgoing Canvas for possible Morph rendering,
                # not its unit images/plate, while building the incoming slide.
                previous_animator = None
            else:
                self.previous_final = Image.new("RGB", self.size, self.matte)
            self.canvas = self.specs[index].build()
            self.animator = _SlideAnimator(self.canvas, {}, reduced_motion=self.reduced_motion)
        except BaseException:
            self.close()
            raise

    def render(self, index: int, time: float) -> tuple[tuple[int, int], bytes]:
        from quickthumb._export_video import _morph_source, _slide_frame

        if index != self.index:
            self._prepare(index)
        assert (
            self.canvas is not None
            and self.animator is not None
            and self.previous_final is not None
        )
        transition, duration_in, _, _ = self.timings[index]
        frame = _slide_frame(
            self.animator,
            transition,
            duration_in,
            time,
            self.previous_final,
            _morph_source(transition, self.previous, self.canvas),
            self.canvas,
            self.size,
            self.matte,
        )
        return frame.size, frame.tobytes()


_worker_renderer: _FrameRenderer | None = None


def _close_worker() -> None:
    if _worker_renderer is not None:
        _worker_renderer.close()


def _initialize_worker(specs, timings, size, matte, reduced_motion) -> None:
    global _worker_renderer
    # No rendering in the initializer: failures belong to Futures, not a
    # respawning worker initializer. multiprocessing runs this finalizer on exit.
    _worker_renderer = _FrameRenderer(specs, timings, size, matte, reduced_motion)
    Finalize(None, _close_worker, exitpriority=10)


def _render_frame_job(index: int, time: float) -> tuple[tuple[int, int], bytes]:
    assert _worker_renderer is not None
    return _worker_renderer.render(index, time)


class ParallelFrames:
    """One export owns a lazily started executor and at most workers outstanding frames."""

    def __init__(self, canvases, timings, matte, reduced_motion, workers: int):
        validate_parallel_canvases(canvases)
        self.specs = [_CanvasSpec.capture(canvas) for canvas in canvases]
        self.timings = timings
        self.size = (canvases[0].width, canvases[0].height)
        self.matte = matte
        self.reduced_motion = reduced_motion
        self.workers = workers
        self.executor: ProcessPoolExecutor | None = None

    def __enter__(self) -> ParallelFrames:
        return self

    def __exit__(self, *args) -> None:
        if self.executor is not None:
            self.executor.shutdown(wait=True, cancel_futures=True)
            self.executor = None

    def frames(
        self, index: int, samples: Iterable[tuple[float, float]]
    ) -> Generator[tuple[float, float, Image.Image], None, None]:
        iterator = iter(samples)
        pending: deque[tuple[float, float, Future]] = deque()

        def submit_next() -> bool:
            try:
                time, duration = next(iterator)
            except StopIteration:
                return False
            if self.executor is None:
                self.executor = ProcessPoolExecutor(
                    max_workers=self.workers,
                    mp_context=multiprocessing.get_context("spawn"),
                    initializer=_initialize_worker,
                    initargs=(self.specs, self.timings, self.size, self.matte, self.reduced_motion),
                )
            future = self.executor.submit(_render_frame_job, index, time)
            pending.append((time, duration, future))
            return True

        try:
            for _ in range(self.workers):
                if not submit_next():
                    break
            while pending:
                time, duration, future = pending.popleft()
                size, raw = future.result()
                frame = Image.frombytes("RGB", size, raw)
                # A Future retains its result, so release it and the raw buffer
                # before yielding. Only the caller's PIL frame remains here.
                del future, raw
                yield time, duration, frame
                del frame
                submit_next()
        except BrokenProcessPool as error:
            raise RenderingError(
                "A parallel frame worker exited unexpectedly; try workers=1"
            ) from error
        finally:
            for _, _, future in pending:
                future.cancel()
