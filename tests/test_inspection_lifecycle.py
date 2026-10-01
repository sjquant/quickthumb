"""Timing inspection must release the temporary readers it prepares."""

import shutil
import subprocess
from io import BytesIO
from types import SimpleNamespace

import pytest
from PIL import Image
from quickthumb import Canvas, Deck
from quickthumb import _export_video as video
from quickthumb._base import RenderContext
from quickthumb._export_video import _close_video_decoders, _deck_timing
from quickthumb._video import VideoDecoder
from quickthumb.errors import RenderingError

from tests._helpers import pixel_rgb


@pytest.fixture(scope="module")
def source_video(tmp_path_factory):
    if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
        pytest.skip("ffmpeg/ffprobe not installed")
    source = tmp_path_factory.mktemp("inspection-video") / "clip.mp4"
    raw = b"".join(
        Image.new("RGB", (96, 64), color).tobytes()
        for color in ("red", "red", "red", "blue", "blue", "blue")
    )
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "rawvideo",
            "-pixel_format",
            "rgb24",
            "-video_size",
            "96x64",
            "-framerate",
            "10",
            "-i",
            "pipe:0",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(source),
        ],
        input=raw,
        capture_output=True,
        check=True,
        timeout=30,
    )
    return source


@pytest.fixture
def decoder_processes(monkeypatch):
    processes = []
    original = VideoDecoder._start

    def record_start(self, *args, **kwargs):
        process = original(self, *args, **kwargs)
        processes.append(process)
        return process

    monkeypatch.setattr(VideoDecoder, "_start", record_start)
    yield processes
    # Keep failing regressions from leaving their reproduced leak running.
    for process in processes:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        if process.stdout is not None:
            process.stdout.close()


@pytest.mark.parametrize("route", ["inspect", "timing"])
def test_timing_inspection_reaps_decoder_processes(source_video, decoder_processes, route):
    canvas = Canvas(96, 64).video(str(source_video), (0, 0), 96, 64)

    if route == "inspect":
        report = Deck(96, 64).slide(canvas).inspect_motion(target="video")
        assert report.duration == pytest.approx(3.6)
    else:
        timings = _deck_timing([canvas], [None], 3.0)
        assert timings[0][3] == pytest.approx(3.6)

    assert decoder_processes, "timing preparation should have decoded the video"
    assert all(process.poll() is not None for process in decoder_processes)
    assert all(process.stdout.closed for process in decoder_processes)
    assert not canvas._ctx.video_decoder_cache


def test_repeated_inspection_then_export_releases_each_reader(source_video, decoder_processes):
    canvas = Canvas(96, 64).video(str(source_video), (0, 0), 96, 64)
    deck = Deck(96, 64).slide(canvas)

    for _ in range(3):
        previous_count = len(decoder_processes)
        assert deck.inspect_motion(target="video").duration == pytest.approx(3.6)
        assert len(decoder_processes) > previous_count
        assert all(process.poll() is not None for process in decoder_processes)
        assert all(process.stdout.closed for process in decoder_processes)
        assert not canvas._ctx.video_decoder_cache

    previous_count = len(decoder_processes)
    with Image.open(BytesIO(deck.to_gif(fps=10, slide_duration=0))) as image:
        image.seek(0)
        red = pixel_rgb(image.convert("RGB"), (48, 32))
        image.seek(getattr(image, "n_frames", 1) - 1)
        blue = pixel_rgb(image.convert("RGB"), (48, 32))
    assert red[0] > 200 and red[2] < 30
    assert blue[2] > 200 and blue[0] < 30
    assert len(decoder_processes) > previous_count
    assert all(process.poll() is not None for process in decoder_processes)
    assert all(process.stdout.closed for process in decoder_processes)
    assert not canvas._ctx.video_decoder_cache


def _inspect(canvases, route, **kwargs):
    if route == "inspect":
        return video.animation_timeline(canvases, [None] * len(canvases), 3.0, **kwargs)
    return _deck_timing(canvases, [None] * len(canvases), 3.0, **kwargs)


@pytest.mark.parametrize("route", ["inspect", "timing"])
def test_later_slide_failure_reaps_earlier_process(
    source_video, decoder_processes, monkeypatch, route
):
    first = Canvas(96, 64).video(str(source_video), (0, 0), 96, 64)
    second = Canvas(96, 64)
    original = RenderingError("later slide preparation failed")

    def fail():
        raise original

    monkeypatch.setattr(second, "_validate_image_paths", fail)
    with pytest.raises(RenderingError) as raised:
        _inspect([first, second], route)

    assert raised.value is original
    assert decoder_processes
    assert all(process.poll() is not None for process in decoder_processes)
    assert all(process.stdout.closed for process in decoder_processes)
    assert not first._ctx.video_decoder_cache


class _Reader:
    def __init__(self, error=None):
        self.error = error
        self.calls = 0

    def close(self):
        self.calls += 1
        if self.error is not None:
            raise self.error


class _Cancelled(BaseException):
    pass


@pytest.mark.parametrize("error_type", [RuntimeError, _Cancelled])
def test_context_cleanup_attempts_all_readers_and_retains_only_failures_for_retry(error_type):
    context = RenderContext(16, 16)
    original = error_type("first close failed")
    first = _Reader(original)
    second = _Reader()
    third = _Reader(RuntimeError("later close failed"))
    context.video_decoder_cache.update(first=first, second=second, third=third)

    with pytest.raises(error_type) as raised:
        context.close_video_decoders()

    assert raised.value is original
    assert [reader.calls for reader in (first, second, third)] == [1, 1, 1]
    assert context.video_decoder_cache == {"first": first, "third": third}

    first.error = third.error = None
    context.close_video_decoders()
    assert [reader.calls for reader in (first, second, third)] == [2, 1, 2]
    assert not context.video_decoder_cache


@pytest.mark.parametrize("error_type", [RuntimeError, _Cancelled])
def test_aggregate_cleanup_attempts_all_canvases_and_preserves_first_error(error_type):
    canvases = [Canvas(16, 16) for _ in range(3)]
    original = error_type("first canvas close failed")
    readers = [_Reader(original), _Reader(), _Reader(RuntimeError("last canvas close failed"))]
    for canvas, reader in zip(canvases, readers, strict=True):
        canvas._ctx.video_decoder_cache["clip"] = reader

    with pytest.raises(error_type) as raised:
        _close_video_decoders(canvases)

    assert raised.value is original
    assert [reader.calls for reader in readers] == [1, 1, 1]
    assert not canvases[1]._ctx.video_decoder_cache
    assert canvases[0]._ctx.video_decoder_cache == {"clip": readers[0]}
    assert canvases[2]._ctx.video_decoder_cache == {"clip": readers[2]}

    readers[0].error = readers[2].error = None
    _close_video_decoders(canvases)
    assert [reader.calls for reader in readers] == [2, 1, 2]
    assert all(not canvas._ctx.video_decoder_cache for canvas in canvases)


@pytest.mark.parametrize("error_type", [RenderingError, _Cancelled])
@pytest.mark.parametrize("cleanup_error_type", [RuntimeError, _Cancelled])
def test_timeline_sample_preserves_preparation_error_when_cleanup_fails(
    monkeypatch, error_type, cleanup_error_type
):
    canvases = [Canvas(16, 16), Canvas(16, 16)]
    deck = Deck(slides=canvases)
    original = error_type("second animator failed after opening a reader")
    readers = [_Reader(cleanup_error_type("cleanup failed")), _Reader()]

    def prepare(canvas, *args, **kwargs):
        index = canvases.index(canvas)
        canvas._ctx.video_decoder_cache["clip"] = readers[index]
        if index == 1:
            raise original
        return SimpleNamespace(duration=1.0)

    monkeypatch.setattr(video, "_SlideAnimator", prepare)
    with pytest.raises(BaseException) as raised:
        deck.sample(0.0)

    assert raised.value is original
    assert [reader.calls for reader in readers] == [1, 1]
    assert canvases[0]._ctx.video_decoder_cache == {"clip": readers[0]}
    assert not canvases[1]._ctx.video_decoder_cache


@pytest.mark.parametrize("route", ["inspect", "timing"])
@pytest.mark.parametrize("error_type", [RenderingError, _Cancelled])
@pytest.mark.parametrize("cleanup_fails", [False, True])
def test_partial_preparation_preserves_exception_and_attempts_all_cleanup(
    monkeypatch, route, error_type, cleanup_fails
):
    canvases = [Canvas(16, 16), Canvas(16, 16)]
    original = error_type("second animator failed after opening a reader")
    readers = [_Reader(RuntimeError("cleanup failed") if cleanup_fails else None), _Reader()]

    def prepare(canvas, *args, **kwargs):
        index = canvases.index(canvas)
        canvas._ctx.video_decoder_cache["clip"] = readers[index]
        if index == 1:
            raise original
        return SimpleNamespace(duration=1.0)

    monkeypatch.setattr(video, "_SlideAnimator", prepare)
    with pytest.raises(error_type) as raised:
        _inspect(canvases, route)

    assert raised.value is original
    assert [reader.calls for reader in readers] == [1, 1]
    assert not canvases[1]._ctx.video_decoder_cache
    assert bool(canvases[0]._ctx.video_decoder_cache) is cleanup_fails


@pytest.mark.parametrize("route", ["inspect", "timing"])
@pytest.mark.parametrize("invalid_timing", [False, True])
def test_completed_preparation_cleans_all_readers_and_reports_the_relevant_error(
    monkeypatch, route, invalid_timing
):
    canvases = [Canvas(16, 16), Canvas(16, 16)]
    cleanup_error = RuntimeError("reader close failed")
    readers = [_Reader(cleanup_error), _Reader()]

    def prepare(canvas, *args, **kwargs):
        index = canvases.index(canvas)
        canvas._ctx.video_decoder_cache["clip"] = readers[index]
        return SimpleNamespace(duration=1.0)

    monkeypatch.setattr(video, "_SlideAnimator", prepare)
    with pytest.raises(RenderingError if invalid_timing else RuntimeError) as raised:
        _inspect(canvases, route, slide_durations=[] if invalid_timing else None)

    if invalid_timing:
        assert "out of sync" in str(raised.value)
    else:
        assert raised.value is cleanup_error
    assert [reader.calls for reader in readers] == [1, 1]
    assert canvases[0]._ctx.video_decoder_cache == {"clip": readers[0]}
    assert not canvases[1]._ctx.video_decoder_cache


@pytest.mark.parametrize("invalid_timing", [False, True])
def test_supplied_durations_do_not_acquire_or_close_readers(monkeypatch, invalid_timing):
    canvas = Canvas(16, 16)
    reader = _Reader()
    canvas._ctx.video_decoder_cache["clip"] = reader

    def forbidden(*args, **kwargs):
        pytest.fail("supplied timing must not acquire or close caller-owned readers")

    monkeypatch.setattr(video, "_SlideAnimator", forbidden)
    monkeypatch.setattr(canvas._ctx, "close_video_decoders", forbidden)
    if invalid_timing:
        with pytest.raises(RenderingError, match="out of sync"):
            _deck_timing([canvas], [None], 3.0, [1.0], slide_durations=[])
    else:
        assert _deck_timing([canvas], [None], 3.0, [1.0]) == [(None, 0.0, 1.0, 4.0)]
    assert canvas._ctx.video_decoder_cache == {"clip": reader}
    assert reader.calls == 0
