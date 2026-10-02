"""Prepared exports own rendering independently of consumers and publication."""

import gc
import weakref
from pathlib import Path
from types import GeneratorType

import pytest
from PIL import Image, ImageSequence
from quickthumb import Canvas, Fade, GifOptions
from quickthumb import _document as document
from quickthumb import _export_video as video
from quickthumb import _render_workers as workers
from quickthumb.errors import ValidationError


class Reader:
    def __init__(self, events, name, error=None):
        self.events, self.name, self.error = events, name, error

    def close(self):
        self.events.append(self.name)
        if self.error is not None:
            raise self.error


def install_render(monkeypatch, *, stage=None, primary=None, close_errors=()):
    """Acquire fake resources at their real lifetime boundaries."""
    events = []
    canvases = [Canvas(4, 3), Canvas(4, 3)]
    readers = [
        Reader(events, f"decoder-{index}", close_errors[index + 2] if close_errors else None)
        for index in range(2)
    ]

    def plan(*args, **kwargs):
        for index, canvas in enumerate(canvases):
            canvas._ctx.video_decoder_cache[str(index)] = readers[index]
        if stage == "plan":
            assert primary is not None
            raise primary
        return video._DeckPlan([], [], [0.0, 0.1], 0.2)

    class Pool:
        def __init__(self, *args, **kwargs):
            events.append("pool-create")
            if stage == "pool-create":
                assert primary is not None
                raise primary

        def __enter__(self):
            events.append("pool-enter")
            if stage == "pool-enter":
                assert primary is not None
                raise primary
            return self

        def __exit__(self, *args):
            events.append("pool-close")
            if close_errors and close_errors[1] is not None:
                raise close_errors[1]

    def shots(*args, **kwargs):
        try:
            yield video._Shot(Image.new("RGBA", (4, 3)), 0.15)
            if stage == "producer":
                assert primary is not None
                raise primary
            yield video._Shot(Image.new("RGBA", (4, 3)), 0.15)
        finally:
            events.append("shots-close")

    monkeypatch.setattr(video, "_deck_plan", plan)
    monkeypatch.setattr(video, "_ordered_deck_shots", shots)
    monkeypatch.setattr(workers, "ParallelFrames", Pool)
    prepared = video._PreparedAnimation(
        canvases, [None, None], fps=10, slide_duration=0.1, matte=None, workers=2
    )
    return prepared, events, canvases, readers


@pytest.mark.parametrize("stage", ["plan", "pool-create", "pool-enter", "producer", "consumer"])
@pytest.mark.parametrize("error_type", [RuntimeError, KeyboardInterrupt])
def test_original_failure_survives_exhaustive_cleanup(monkeypatch, stage, error_type):
    primary = error_type("primary")
    prepared, events, canvases, readers = install_render(
        monkeypatch,
        stage=stage,
        primary=primary,
        close_errors=(None, RuntimeError("pool close"), RuntimeError("decoder close"), None),
    )
    with pytest.raises(error_type) as caught, prepared:
        frames = prepared.frame_runs()
        next(frames)
        if stage == "consumer":
            assert primary is not None
            raise primary
        list(frames)
    assert caught.value is primary
    assert events[-2:] == ["decoder-0", "decoder-1"]
    assert (
        "pool-close" in events
        if stage not in {"plan", "pool-create"}
        else "pool-close" not in events
    )
    assert canvases[0]._ctx.video_decoder_cache == {"0": readers[0]}
    assert not canvases[1]._ctx.video_decoder_cache


def test_early_frame_consumer_closes_shots_pool_and_decoders(monkeypatch):
    prepared, events, _, _ = install_render(monkeypatch)
    with prepared:
        frames = prepared.frame_runs()
        frame, indices = next(frames)
        assert frame.mode == "RGBA" and list(indices) == [0, 1]
    assert events[-4:] == ["shots-close", "pool-close", "decoder-0", "decoder-1"]
    assert isinstance(frames, GeneratorType) and frames.gi_frame is None
    with pytest.raises(RuntimeError, match="have not completed"):
        _ = prepared.frame_facts


def test_cleanup_raises_first_error_and_failed_decoders_can_be_retried(monkeypatch):
    primary = RuntimeError("shot close")
    prepared, events, canvases, readers = install_render(
        monkeypatch,
        close_errors=(primary, RuntimeError("pool close"), RuntimeError("decoder close"), None),
    )

    class Shots:
        def close(self):
            events.append("shots-close")
            assert primary is not None
            raise primary

    monkeypatch.setattr(video, "_ordered_deck_shots", lambda *args: Shots())
    with pytest.raises(RuntimeError) as caught, prepared:
        pass
    assert caught.value is primary
    assert events[-4:] == ["shots-close", "pool-close", "decoder-0", "decoder-1"]
    readers[0].error = None
    video._close_video_decoders(canvases)
    assert events[-1] == "decoder-0"
    assert all(not canvas._ctx.video_decoder_cache for canvas in canvases)


def test_session_releases_source_and_iterators_without_cyclic_gc(monkeypatch):
    images = []
    original = video._deck_plan

    def observe(*args, **kwargs):
        plan = original(*args, **kwargs)
        plate = plan.animators[0]._static_plate
        assert plate is not None
        images.append(weakref.ref(plate))
        return plan

    monkeypatch.setattr(video, "_deck_plan", observe)
    enabled = gc.isenabled()
    gc.disable()
    try:

        def run():
            # Canvas has its own pre-existing DiagnosticsEngine cycle. Track the
            # caller's input sequence to isolate this render lifetime instead.
            class Sources(list):
                pass

            canvases = Sources([Canvas(3, 1).background(color="#123456")])
            prepared = video._PreparedAnimation(canvases, [None], fps=10, slide_duration=0.15)
            with prepared:
                frames = prepared.frame_runs()
                list(frames)
            facts = prepared.frame_facts
            assert (facts.width, facts.height, facts.frame_count, facts.duration) == (3, 1, 2, 0.2)
            return weakref.ref(canvases), weakref.ref(prepared), weakref.ref(frames)

        references = run()
        assert all(reference() is None for reference in [*references, *images])
    finally:
        if enabled:
            gc.enable()


@pytest.mark.parametrize("format", ["gif", "mp4"])
@pytest.mark.parametrize("entrypoint", ["file", "bytes"])
def test_cleanup_failure_prevents_publication_or_byte_return(
    monkeypatch, tmp_path, format, entrypoint
):
    primary = RuntimeError("decoder close")
    canvas = Canvas(4, 4)
    events = []
    reader = Reader(events, "decoder", primary)
    original = video._deck_plan

    def plan(*args, **kwargs):
        result = original(*args, **kwargs)
        canvas._ctx.video_decoder_cache["reader"] = reader
        return result

    def encode(frames, fps, format, path, *args, **kwargs):
        count = sum(repetitions for _, repetitions in frames)
        Path(path).write_bytes(b"encoded")
        return video._AnimationFacts(4, 4, count, count / fps, fps)

    monkeypatch.setattr(video, "_deck_plan", plan)
    monkeypatch.setattr(video, "_encode_video_file", encode)
    destination = tmp_path / f"existing.{format}"
    destination.write_bytes(b"original")
    with pytest.raises(RuntimeError) as caught:
        if entrypoint == "file":
            video.write_animation([canvas], [None], str(destination), format)
        else:
            video.export_animation_bytes([canvas], [None], format)
    assert caught.value is primary
    assert destination.read_bytes() == b"original"
    assert list(tmp_path.iterdir()) == [destination]
    assert events == ["decoder"]


def test_gif_receipt_uses_encoded_facts_and_preserves_canonical_dimensions(monkeypatch, tmp_path):
    canvas = Canvas(37, 23).shape(
        "rectangle", (2, 2), 20, 10, "#CC0011", animation=Fade(duration=0.17)
    )
    options = GifOptions(fps=7, max_size=(17, 17), colors=2)
    path = tmp_path / "resized.gif"
    monkeypatch.setattr(
        document, "_contract_motion_report", lambda *args: pytest.fail("receipt reopened rendering")
    )
    result = canvas.export(path, animation=options)
    with Image.open(path) as encoded:
        count = getattr(encoded, "n_frames", 1)
        duration = (
            sum(frame.info.get("duration", 0) for frame in ImageSequence.Iterator(encoded)) / 1000
        )
        assert encoded.size == (17, 11)
    assert (result.pixel_metrics.width, result.pixel_metrics.height) == (37, 23)
    assert result.pixel_metrics.frame_count == result.timing_metrics.frame_count == count
    assert result.timing_metrics.duration == duration
    assert result.timing_metrics.fps == 7
    private_path = tmp_path / "private.gif"
    facts = video.write_animation([canvas], [None], str(private_path), "gif", animation=options)
    assert (facts.width, facts.height, facts.frame_count, facts.duration, facts.fps) == (
        17,
        11,
        count,
        duration,
        7,
    )
    assert private_path.read_bytes() == path.read_bytes()


@pytest.mark.parametrize("fps", [True, "30", 0, float("nan")])
def test_renderer_preserves_scalar_frame_rate_validation(fps):
    with pytest.raises(ValidationError, match="fps must be > 0"):
        video._PreparedAnimation([Canvas(1, 1)], [None], fps=fps, slide_duration=0)


def test_full_size_rgba_preparation_has_no_codec_or_audio_requirements(monkeypatch):
    monkeypatch.setattr(video, "_ffmpeg_binary", lambda: pytest.fail("renderer looked up encoder"))
    monkeypatch.setattr(
        video, "_video_audio_schedule", lambda *args: pytest.fail("renderer scheduled audio")
    )
    with video._PreparedAnimation(
        [Canvas(1, 3)], [None], fps=10, slide_duration=0, matte=None
    ) as prepared:
        [(frame, indices)] = list(prepared.frame_runs())
    assert (frame.mode, frame.size, list(indices)) == ("RGBA", (1, 3), [0])


def test_early_consumer_closes_a_suspended_worker_stream(monkeypatch):
    from concurrent.futures import Future

    futures = []
    shutdown = []

    class Executor:
        def __init__(self, **kwargs):
            pass

        def submit(self, function, index, time):
            future = Future()
            # Ordered shot assembly keeps one frame pending, so two completed
            # worker results produce the first output while later work waits.
            if len(futures) < 2:
                frame = Image.new("RGB", (4, 4))
                future.set_result((frame.size, frame.tobytes()))
            futures.append(future)
            return future

        def shutdown(self, **kwargs):
            shutdown.append(kwargs)
            for future in futures:
                future.cancel()

    monkeypatch.setattr(workers, "ProcessPoolExecutor", Executor)
    canvas = Canvas(4, 4).shape("rectangle", (0, 0), 3, 3, "#FF0000", animation=Fade(duration=0.5))
    with video._PreparedAnimation(
        [canvas], [None], fps=10, slide_duration=0, workers=2
    ) as prepared:
        frames = prepared.frame_runs()
        next(frames)
        assert any(not future.done() for future in futures)
    assert len(futures) == 3
    assert futures[-1].cancelled()
    assert shutdown == [{"wait": True, "cancel_futures": True}]
    assert isinstance(frames, GeneratorType) and frames.gi_frame is None


@pytest.mark.parametrize("format", ["gif", "mp4"])
def test_successful_file_publication_follows_resource_closure(monkeypatch, tmp_path, format):
    events = []
    original_close = video._close_video_decoders
    original_replace = video.os.replace

    def close(canvases):
        original_close(canvases)
        events.append("closed")

    def replace(source, destination):
        assert events == ["closed"]
        original_replace(source, destination)
        events.append("published")

    def encode(frames, fps, format, path, *args, **kwargs):
        count = sum(repetitions for _, repetitions in frames)
        Path(path).write_bytes(b"encoded")
        return video._AnimationFacts(4, 4, count, count / fps, fps)

    monkeypatch.setattr(video, "_close_video_decoders", close)
    monkeypatch.setattr(video.os, "replace", replace)
    monkeypatch.setattr(video, "_encode_video_file", encode)
    facts = video.write_animation([Canvas(4, 4)], [None], str(tmp_path / f"file.{format}"), format)
    assert events == ["closed", "published"]
    assert facts.frame_count > 0


def test_encoder_facts_are_not_returned_when_final_audio_mux_fails(monkeypatch, tmp_path):
    primary = RuntimeError("audio mux failed")
    events = []
    facts = video._AnimationFacts(4, 2, 129, 129 / 29.97, 29.97)

    def batch(*args, **kwargs):
        events.append("video encoded")
        return [tmp_path / "segment.mp4"], facts

    def mux(*args):
        events.append("mux")
        raise primary

    monkeypatch.setattr(video, "_ffmpeg_binary", lambda: "ffmpeg")
    monkeypatch.setattr(video, "_encode_shot_batches", batch)
    monkeypatch.setattr(video, "_run_video_ffmpeg", mux)
    with pytest.raises(RuntimeError) as caught:
        video._encode_video_file([], 29.97, "mp4", str(tmp_path / "output.mp4"))
    assert caught.value is primary
    assert events == ["video encoded", "mux"]


def test_preparation_closes_partial_asset_acquisition(monkeypatch):
    canvas = Canvas(1, 1)
    primary = RuntimeError("asset validation")
    events = []

    def validate():
        canvas._ctx.video_decoder_cache["reader"] = Reader(events, "closed")
        raise primary

    monkeypatch.setattr(canvas, "_validate_image_paths", validate)
    with (
        pytest.raises(RuntimeError) as caught,
        video._PreparedAnimation([canvas], [None], fps=10, slide_duration=0),
    ):
        pytest.fail("preparation should fail")
    assert caught.value is primary
    assert events == ["closed"]


def test_frame_stream_is_single_use_and_session_cannot_be_reentered():
    prepared = video._PreparedAnimation([Canvas(1, 1)], [None], fps=10, slide_duration=0)
    with prepared:
        list(prepared.frame_runs())
        with pytest.raises(RuntimeError, match="consumed only once"):
            prepared.shots()
    with pytest.raises(RuntimeError, match="entered more than once"), prepared:
        pytest.fail("closed session was reentered")


@pytest.mark.parametrize("format", ["gif", "mp4", "webm"])
@pytest.mark.parametrize("matte", [None])
def test_opaque_scalar_none_matte_keeps_legacy_validation(format, matte):
    with pytest.raises(ValidationError, match="Invalid matte color: None"):
        getattr(Canvas(4, 4), f"to_{format}")(matte=matte)


@pytest.mark.parametrize("format", ["webm"])
@pytest.mark.parametrize("matte", [None, "not-a-color"])
def test_alpha_encoding_still_ignores_matte(format, matte):
    with video._prepare_animation(
        [Canvas(4, 4)], [None], format, 10, 0, 0, matte, transparent=True
    ) as prepared:
        [(frame, _)] = list(prepared.frame_runs())
    assert frame.mode == "RGBA"
