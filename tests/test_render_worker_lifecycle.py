"""Lifecycle, payload isolation, and bounded scheduling for spawned renderers."""

import os
import pickle
import shutil
import subprocess
import sys
import textwrap
from concurrent.futures import Future, ThreadPoolExecutor
from concurrent.futures.process import BrokenProcessPool
from io import BytesIO
from pathlib import Path
from threading import Event

import pytest
from PIL import Image
from quickthumb import Canvas, Fade, TextPart
from quickthumb import _export_video as video
from quickthumb import _render_workers as workers
from quickthumb.errors import RenderingError


def _canvas():
    return Canvas(16, 12).shape("rectangle", (1, 1), 8, 6, "#F03080", animation=Fade(duration=0.5))


def _renderer(count=2):
    return workers.ParallelFrames([_canvas()], [(None, 0.0, 0.5, 1.0)], (0, 0, 0), False, count)


def _raw(time):
    image = Image.new("RGB", (2, 2), (int(time), 0, 0))
    return image.size, image.tobytes()


def _worker_decoder_processes():
    """Importable spawn job observing the decoder owned by its worker renderer."""
    renderer = workers._worker_renderer
    assert renderer is not None and renderer.canvas is not None
    decoder = next(iter(renderer.canvas._ctx.video_decoder_cache.values()))
    process = decoder._process
    assert process is not None
    return os.getpid(), process.pid, process.poll()


class RecordingExecutor:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.jobs = []
        self.futures = []
        self.shutdown_calls = []

    def submit(self, fn, index, time):
        future = Future()
        self.jobs.append((fn, index, time))
        self.futures.append(future)
        return future

    def shutdown(self, **kwargs):
        self.shutdown_calls.append(kwargs)
        if kwargs.get("cancel_futures"):
            for future in self.futures:
                future.cancel()


def test_default_export_and_static_parallel_export_never_start_a_pool(monkeypatch):
    def forbidden(**kwargs):
        raise AssertionError("no frame worker should be started")

    monkeypatch.setattr(workers, "ProcessPoolExecutor", forbidden)
    assert _canvas().to_gif(fps=4, hold=0.1).startswith(b"GIF")
    still = Canvas(16, 12).background(color="#345678")
    assert video.export_animation_bytes([still], [None], "gif", workers=2).startswith(b"GIF")


def test_empty_sample_iterator_does_not_start_a_pool(monkeypatch):
    monkeypatch.setattr(
        workers, "ProcessPoolExecutor", lambda **kwargs: pytest.fail("unexpected pool")
    )
    with _renderer() as renderer:
        assert list(renderer.frames(0, [])) == []
        assert renderer.executor is None


def test_spawn_context_and_ordered_slow_first_window_are_bounded(monkeypatch):
    executor = RecordingExecutor()
    started = Event()
    produced = []
    original_submit = executor.submit

    def submit(fn, index, time):
        future = original_submit(fn, index, time)
        if time:
            future.set_result(_raw(time))
        if len(executor.jobs) == 3:
            started.set()
        return future

    monkeypatch.setattr(executor, "submit", submit)

    def create(**kwargs):
        executor.kwargs = kwargs
        return executor

    def samples():
        for index in range(1000):
            produced.append(index)
            yield float(index), 0.125

    monkeypatch.setattr(workers, "ProcessPoolExecutor", create)
    with _renderer(3) as renderer:
        frames = renderer.frames(0, samples())
        with ThreadPoolExecutor(max_workers=1) as consumer:
            first = consumer.submit(lambda: next(frames))
            try:
                assert started.wait(5), "the initial window was never submitted"
                assert not first.done()
                assert produced == [0, 1, 2]
                assert len(executor.futures) == 3
                assert executor.futures[1].done() and executor.futures[2].done()
            finally:
                executor.futures[0].set_result(_raw(0))
            time, duration, frame = first.result(timeout=5)
        assert (time, duration, frame.getpixel((0, 0))) == (0.0, 0.125, (0, 0, 0))
        assert produced == [0, 1, 2]
        for expected in range(1, 8):
            time, duration, frame = next(frames)
            assert (time, duration, frame.getpixel((0, 0))) == (
                float(expected),
                0.125,
                (expected, 0, 0),
            )
            assert len(produced) - (expected + 1) == 2
        frames.close()
    assert executor.kwargs["max_workers"] == 3
    assert executor.kwargs["mp_context"].get_start_method() == "spawn"
    assert executor.shutdown_calls == [{"wait": True, "cancel_futures": True}]
    assert renderer.executor is None


def test_closing_iterator_cancels_unconsumed_jobs(monkeypatch):
    executor = RecordingExecutor()
    original_submit = executor.submit

    def submit(fn, index, time):
        future = original_submit(fn, index, time)
        if time == 0:
            future.set_result(_raw(time))
        return future

    monkeypatch.setattr(executor, "submit", submit)
    monkeypatch.setattr(workers, "ProcessPoolExecutor", lambda **kwargs: executor)
    with _renderer(3) as renderer:
        frames = renderer.frames(0, ((float(index), 0.1) for index in range(1000)))
        next(frames)
        frames.close()
        assert [future.cancelled() for future in executor.futures] == [False, True, True]
        assert len(executor.jobs) == 3
    assert executor.shutdown_calls == [{"wait": True, "cancel_futures": True}]


@pytest.mark.parametrize("broken", [False, True])
def test_failed_frame_cancels_remaining_jobs_and_shuts_down(monkeypatch, broken):
    executor = RecordingExecutor()
    original_submit = executor.submit

    def submit(fn, index, time):
        future = original_submit(fn, index, time)
        if time == 0:
            error = BrokenProcessPool("worker died") if broken else RenderingError("bad frame")
            future.set_exception(error)
        return future

    monkeypatch.setattr(executor, "submit", submit)
    monkeypatch.setattr(workers, "ProcessPoolExecutor", lambda **kwargs: executor)
    expected = "worker exited unexpectedly" if broken else "bad frame"
    with pytest.raises(RenderingError, match=expected), _renderer(3) as renderer:
        list(renderer.frames(0, [(0.0, 0.1), (1.0, 0.1), (2.0, 0.1)]))
    assert [future.cancelled() for future in executor.futures] == [False, True, True]
    assert executor.shutdown_calls == [{"wait": True, "cancel_futures": True}]


def test_executor_startup_failure_does_not_leave_an_executor(monkeypatch):
    def fail(**kwargs):
        raise OSError("cannot start workers")

    monkeypatch.setattr(workers, "ProcessPoolExecutor", fail)
    with pytest.raises(OSError, match="cannot start workers"), _renderer() as renderer:
        next(renderer.frames(0, [(0.0, 0.1)]))
    assert renderer.executor is None


def test_submission_failure_shuts_down_started_executor(monkeypatch):
    executor = RecordingExecutor()

    def fail(*args):
        raise OSError("cannot submit frame")

    monkeypatch.setattr(executor, "submit", fail)
    monkeypatch.setattr(workers, "ProcessPoolExecutor", lambda **kwargs: executor)
    with pytest.raises(OSError, match="cannot submit frame"), _renderer() as renderer:
        next(renderer.frames(0, [(0.0, 0.1)]))
    assert executor.shutdown_calls == [{"wait": True, "cancel_futures": True}]
    assert renderer.executor is None


def test_payload_roundtrip_preserves_shared_animation_identity():
    fade = Fade(duration=0.5)
    original = (
        Canvas(16, 12)
        .shape("rectangle", (1, 1), 5, 5, "#FF0000", animation=fade)
        .shape("rectangle", (8, 2), 5, 5, "#0000FF", animation=fade)
    )
    spec = pickle.loads(pickle.dumps(workers._CanvasSpec.capture(original)))
    rebuilt = spec.build()
    assert rebuilt.layers[0].animation is rebuilt.layers[1].animation
    assert rebuilt.layers[0].animation is not fade
    first, second = video._SlideAnimator(original, {}), video._SlideAnimator(rebuilt, {})
    assert first.duration == second.duration == 0.5
    assert len(first._units) == len(second._units) == 1
    assert first.frame_at(0.25).tobytes() == second.frame_at(0.25).tobytes()


def test_remote_payload_pins_bytes_and_never_refetches(monkeypatch, tmp_path):
    url = "https://example.invalid/frame.png"
    buffer = BytesIO()
    Image.new("RGB", (4, 4), "#E04020").save(buffer, format="PNG")
    original_bytes = buffer.getvalue()
    calls = []
    original = Canvas(8, 8).image(url, width=8, height=8, position=(0, 0))
    original._ctx.asset_resolver.cache_dir = tmp_path
    original._ctx.asset_resolver.max_age = 0

    def download(self, source, asset_type, fetcher):
        calls.append((source, asset_type))
        return original_bytes

    monkeypatch.setattr(type(original._ctx.asset_resolver), "_download", download)
    video._SlideAnimator(original, {})
    spec = pickle.loads(pickle.dumps(workers._CanvasSpec.capture(original)))
    assert calls == [(url, "image")]
    assert spec.records
    # A later cache refresh/deletion must not replace the frozen image bytes.
    for record in spec.records.values():
        if record.cache_path:
            Path(record.cache_path).unlink()

    def forbidden(*args, **kwargs):
        raise AssertionError("a worker tried to fetch remote bytes")

    monkeypatch.setattr(type(original._ctx.asset_resolver), "_download", forbidden)
    rebuilt = spec.build()
    assert rebuilt._ctx.asset_resolver.offline is True
    assert rebuilt._ctx.asset_resolver._records is not spec.records
    assert rebuilt._images.load_image_from_url(url).getpixel((0, 0)) == (224, 64, 32)
    assert video._SlideAnimator(rebuilt, {}).frame_at(0).getpixel((0, 0)) == (224, 64, 32, 255)
    assert calls == [(url, "image")]


def test_unused_rich_text_default_font_does_not_break_snapshot(monkeypatch, tmp_path):
    font = Path(__file__).resolve().parents[1] / "assets/fonts/NotoSans-Regular.ttf"
    canvas = Canvas(40, 20).text(
        [TextPart(text="x", font=str(font))],
        font="https://example.invalid/unused-default.ttf",
        size=12,
        position=(0, 0),
        animation=Fade(duration=0.2),
    )
    canvas._ctx.asset_resolver.cache_dir = tmp_path

    def unavailable(*args, **kwargs):
        raise OSError("offline")

    monkeypatch.setattr("quickthumb._fonts.urlopen", unavailable)
    original = video._SlideAnimator(canvas, {}).frame_at(0.1)
    rebuilt = workers._CanvasSpec.capture(canvas).build()
    assert video._SlideAnimator(rebuilt, {}).frame_at(0.1).tobytes() == original.tobytes()


def test_google_axis_fallback_survives_offline_worker_snapshot(monkeypatch, tmp_path):
    font = Path(__file__).resolve().parents[1] / "assets/fonts/NotoSans-Regular.ttf"
    font_url = "https://example.invalid/fallback.ttf"
    canvas = Canvas(40, 20).text(
        "x",
        font="Example Family",
        font_source="google",
        font_variations={"wdth": 100.0},
        size=12,
        position=(0, 0),
        animation=Fade(duration=0.2),
    )
    resolver = canvas._ctx.asset_resolver
    resolver.cache_dir = tmp_path

    def download(self, source, asset_type, fetcher):
        if source == font_url:
            return font.read_bytes()
        if "wdth" in source:
            raise RenderingError("requested font axis is unavailable")
        return f"@font-face {{ font-weight: 400; src: url({font_url}); }}".encode()

    monkeypatch.setattr(type(resolver), "_download", download)
    with pytest.warns(UserWarning):
        original = video._SlideAnimator(canvas, {}).frame_at(0.1)
    spec = workers._CanvasSpec.capture(canvas)

    def forbidden(*args, **kwargs):
        raise AssertionError("worker fallback attempted a network fetch")

    monkeypatch.setattr(type(resolver), "_download", forbidden)
    with pytest.warns(UserWarning):
        rebuilt = video._SlideAnimator(spec.build(), {}).frame_at(0.1)
    assert rebuilt.tobytes() == original.tobytes()


def _late_caption_canvas(tmp_path):
    canvas = Canvas(32, 32).video(
        str(tmp_path / "unused-source.mp4"),
        position=(0, 0),
        width=32,
        height=32,
        captions=[
            {
                "text": "later",
                "font": "https://example.invalid/late-caption.ttf",
                "start": 0.2,
                "end": 0.4,
            }
        ],
    )
    canvas._ctx.asset_resolver.cache_dir = tmp_path
    return canvas


def test_late_caption_font_is_available_without_worker_fetch(monkeypatch, tmp_path):
    font = Path(__file__).resolve().parents[1] / "assets/fonts/NotoSans-Regular.ttf"
    canvas = _late_caption_canvas(tmp_path)
    url = "https://example.invalid/late-caption.ttf"
    calls = []

    def download(self, source, asset_type, fetcher):
        calls.append((source, asset_type))
        return font.read_bytes()

    monkeypatch.setattr(type(canvas._ctx.asset_resolver), "_download", download)
    spec = pickle.loads(pickle.dumps(workers._CanvasSpec.capture(canvas)))
    assert calls == [(url, "font")]

    def forbidden(*args, **kwargs):
        raise AssertionError("late caption font was not captured before spawning")

    monkeypatch.setattr(type(canvas._ctx.asset_resolver), "_download", forbidden)
    rebuilt = spec.build()
    face = rebuilt._fonts.load_font_variant(url, 14, False, False)
    assert face.getbbox("later")[2] > 0
    assert calls == [(url, "font")]


def test_unavailable_unused_caption_font_is_deferred_until_render(monkeypatch, tmp_path):
    canvas = _late_caption_canvas(tmp_path)

    def unavailable(*args, **kwargs):
        raise RenderingError("caption font unavailable")

    monkeypatch.setattr(type(canvas._ctx.asset_resolver), "_download", unavailable)
    rebuilt = workers._CanvasSpec.capture(canvas).build()
    with pytest.raises(RenderingError, match="offline mode"):
        rebuilt._fonts.load_font_variant(
            "https://example.invalid/late-caption.ttf", 14, False, False
        )


@pytest.mark.parametrize("failure", ["incoming", "outgoing", "final"])
def test_partial_slide_preparation_closes_every_opened_decoder(monkeypatch, failure):
    opened = []
    closed = []

    class Decoder:
        def __init__(self, index):
            self.index = index

        def close(self):
            closed.append(self.index)

    class Animator:
        def __init__(self, canvas, cache, **kwargs):
            index = len(opened)
            opened.append(canvas)
            canvas._ctx.video_decoder_cache["test"] = Decoder(index)
            if (failure == "incoming" and index == 0) or (failure == "outgoing" and index == 1):
                raise RenderingError("prepare failed")

        def final_export_frame(self):
            raise RenderingError("prepare failed")

    specs = [workers._CanvasSpec.capture(Canvas(8, 8)) for _ in range(2)]
    renderer = workers._FrameRenderer(
        specs, [(None, 0.0, 0.5, 1.0), (None, 0.5, 0.5, 1.0)], (8, 8), (0, 0, 0), False
    )
    monkeypatch.setattr(video, "_SlideAnimator", Animator)
    with pytest.raises(RenderingError, match="prepare failed"):
        renderer.render(1, 0.1)
    assert sorted(closed) == list(range(len(opened)))
    assert all(not canvas._ctx.video_decoder_cache for canvas in opened)
    assert renderer.canvas is renderer.previous is renderer.animator is None
    assert renderer.previous_final is None
    renderer.close()
    assert len(closed) == len(opened)


def test_worker_finalizer_closes_renderer(monkeypatch):
    registrations = []
    closed = []
    monkeypatch.setattr(workers, "_worker_renderer", None)
    monkeypatch.setattr(
        workers,
        "Finalize",
        lambda owner, callback, **kwargs: registrations.append((callback, kwargs)),
    )
    monkeypatch.setattr(workers._FrameRenderer, "close", lambda self: closed.append(self))
    workers._initialize_worker([], [], (8, 8), (0, 0, 0), False)
    assert len(registrations) == 1
    callback, kwargs = registrations[0]
    assert kwargs == {"exitpriority": 10}
    callback()
    assert closed == [workers._worker_renderer]


def test_switching_slides_retains_at_most_two_decoder_contexts(monkeypatch):
    opened = []
    active = set()
    counts = []

    class Decoder:
        def __init__(self, index):
            self.index = index
            active.add(index)
            counts.append(len(active))

        def close(self):
            active.remove(self.index)

    class Animator:
        def __init__(self, canvas, cache, **kwargs):
            index = len(opened)
            opened.append(canvas)
            canvas._ctx.video_decoder_cache["test"] = Decoder(index)

        def final_export_frame(self):
            return Image.new("RGBA", (8, 8), "#203040")

    monkeypatch.setattr(video, "_SlideAnimator", Animator)
    specs = [workers._CanvasSpec.capture(Canvas(8, 8)) for _ in range(4)]
    renderer = workers._FrameRenderer(specs, [(None, 0.5, 0.5, 1.0)] * 4, (8, 8), (0, 0, 0), False)
    for index in range(1, 4):
        renderer._prepare(index)
        assert len(active) == 1
        assert all(not canvas._ctx.video_decoder_cache for canvas in opened[:-2])
        assert renderer.previous is not None
        assert not renderer.previous._ctx.video_decoder_cache
    renderer.close()
    assert not active
    assert max(counts) == 2
    assert all(not canvas._ctx.video_decoder_cache for canvas in opened)


@pytest.mark.parametrize("entrypoint", ["file", "bytes"])
@pytest.mark.parametrize("failure", ["plan", "audio", "temp", "encoder"])
def test_export_failures_close_parent_decoders(monkeypatch, tmp_path, entrypoint, failure):
    canvas = Canvas(8, 8)
    closed = []
    shots_closed = []

    class Decoder:
        def close(self):
            closed.append("decoder")

    def plan(*args, **kwargs):
        canvas._ctx.video_decoder_cache["test"] = Decoder()
        if failure == "plan":
            raise RenderingError("expected failure")
        return video._DeckPlan([], [], [0.0], 1.0)

    def audio(*args, **kwargs):
        if failure == "audio":
            raise RenderingError("expected failure")
        return []

    def shots(*args, **kwargs):
        try:
            yield video._Shot(Image.new("RGB", (8, 8)), 0.1)
        finally:
            shots_closed.append(True)

    def encode(shots, *args, **kwargs):
        next(shots)
        raise RenderingError("expected failure")

    def temp(*args, **kwargs):
        raise OSError("expected failure")

    monkeypatch.setattr(video, "_deck_plan", plan)
    monkeypatch.setattr(video, "_video_audio_schedule", audio)
    monkeypatch.setattr(video, "_deck_shots", shots)
    monkeypatch.setattr(video, "_encode_video_file", encode)
    if failure == "temp":
        monkeypatch.setattr(video, "_temporary_output_path", temp)
        monkeypatch.setattr(video.tempfile, "mkstemp", temp)
    destination = tmp_path / "existing.mp4"
    destination.write_bytes(b"previous output")
    with pytest.raises((OSError, RenderingError), match="expected failure"):
        if entrypoint == "file":
            video.write_animation([canvas], [None], str(destination), "mp4")
        else:
            video.export_animation_bytes([canvas], [None], "mp4")
    assert closed == ["decoder"]
    assert not canvas._ctx.video_decoder_cache
    assert destination.read_bytes() == b"previous output"
    assert list(tmp_path.iterdir()) == [destination]
    assert shots_closed == ([True] if failure == "encoder" else [])


def test_shot_cleanup_failure_still_closes_parent_decoders(monkeypatch):
    canvas = Canvas(8, 8)
    closed = []

    class Decoder:
        def close(self):
            closed.append(True)

    class Shots:
        def close(self):
            raise RuntimeError("worker shutdown failed")

    def plan(*args, **kwargs):
        canvas._ctx.video_decoder_cache["test"] = Decoder()
        return video._DeckPlan([], [], [0.0], 1.0)

    monkeypatch.setattr(video, "_deck_plan", plan)
    monkeypatch.setattr(video, "_deck_shots", lambda *args, **kwargs: Shots())
    monkeypatch.setattr(video, "_video_audio_schedule", lambda *args: [])
    monkeypatch.setattr(video, "_encode_gif", lambda *args, **kwargs: b"gif")
    with pytest.raises(RuntimeError, match="worker shutdown failed"):
        video.export_animation_bytes([canvas], [None], "gif")
    assert closed == [True]
    assert not canvas._ctx.video_decoder_cache


def test_abrupt_spawn_worker_exit_fails_without_hanging_or_survivors(tmp_path):
    script = tmp_path / "crash_worker.py"
    script.write_text(
        textwrap.dedent(
            """
            import multiprocessing
            import os
            from quickthumb import Canvas
            from quickthumb import _render_workers as workers
            from quickthumb.errors import RenderingError

            def crash(index, time):
                os._exit(17)

            if __name__ == "__main__":
                workers._render_frame_job = crash
                try:
                    with workers.ParallelFrames(
                        [Canvas(8, 8)], [(None, 0, 1, 1)], (0, 0, 0), False, 2
                    ) as renderer:
                        next(renderer.frames(0, [(0.0, 0.1), (0.1, 0.1)]))
                except RenderingError as error:
                    assert "worker exited unexpectedly" in str(error), str(error)
                else:
                    raise AssertionError("worker death was not reported")
                assert not multiprocessing.active_children()
                print("worker failure cleaned up")
            """
        ),
        encoding="utf-8",
    )
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "worker failure cleaned up" in result.stdout


def test_spawn_shutdown_runs_worker_decoder_finalizer(tmp_path):
    script = tmp_path / "finalize_worker.py"
    script.write_text(
        textwrap.dedent(
            """
            import multiprocessing
            import os
            from concurrent.futures import ProcessPoolExecutor
            from pathlib import Path
            from quickthumb import Canvas
            from quickthumb import _render_workers as workers

            class Decoder:
                def close(self):
                    Path("closed.txt").write_text("decoder closed")

            def initialize():
                workers._initialize_worker([], [], (8, 8), (0, 0, 0), False)
                canvas = Canvas(8, 8)
                canvas._ctx.video_decoder_cache["test"] = Decoder()
                workers._worker_renderer.canvas = canvas

            if __name__ == "__main__":
                with ProcessPoolExecutor(
                    max_workers=1,
                    mp_context=multiprocessing.get_context("spawn"),
                    initializer=initialize,
                ) as executor:
                    assert executor.submit(os.getpid).result(timeout=10) != os.getpid()
                assert not multiprocessing.active_children()
                assert Path("closed.txt").read_text() == "decoder closed"
            """
        ),
        encoding="utf-8",
    )
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.skipif(
    sys.platform != "linux" or not shutil.which("ffmpeg") or not shutil.which("ffprobe"),
    reason="Linux /proc and FFmpeg are required to verify decoder reaping",
)
def test_spawn_shutdown_reaps_actual_ffmpeg_decoder(tmp_path):
    source = tmp_path / "source.mkv"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=red:s=32x32:r=10:d=10",
            "-c:v",
            "ffv1",
            str(source),
        ],
        check=True,
        capture_output=True,
        timeout=20,
    )
    canvas = Canvas(32, 32).video(str(source), position=(0, 0), width=32, height=32)
    with workers.ParallelFrames(
        [canvas], [(None, 0.0, 10.0, 10.0)], (0, 0, 0), False, 1
    ) as renderer:
        frames = renderer.frames(0, [(0.0, 0.1)])
        next(frames)
        frames.close()
        assert renderer.executor is not None
        worker_pid, decoder_pid, returncode = renderer.executor.submit(
            _worker_decoder_processes
        ).result(timeout=10)
        assert returncode is None
        assert Path(f"/proc/{worker_pid}").exists()
        assert Path(f"/proc/{decoder_pid}").exists()
    assert not Path(f"/proc/{worker_pid}").exists()
    assert not Path(f"/proc/{decoder_pid}").exists()
