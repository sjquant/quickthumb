"""Public transparent WebM options, destination safety, and audio integration."""

import inspect
import json
import math
import shutil
import struct
import subprocess
import wave
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import pytest
from PIL import Image
from quickthumb import AudioTrack, Canvas, Deck, VideoOptions
from quickthumb import _export_video as video
from quickthumb.errors import RenderingError, ValidationError

SIZE = (32, 24)
HAS_FFMPEG = shutil.which("ffmpeg") is not None
HAS_FFPROBE = shutil.which("ffprobe") is not None


def alpha_canvas() -> Canvas:
    """Keep transparent, half-opaque, and opaque interiors clear of codec edges."""
    return (
        Canvas(*SIZE)
        .shape("rectangle", (4, 4), 10, 16, "#E04060", opacity=0.5)
        .shape("rectangle", (18, 4), 10, 16, "#3060D0")
    )


def document(kind: str) -> Canvas | Deck:
    canvas = alpha_canvas()
    return canvas if kind == "canvas" else Deck(*SIZE).slide(canvas, duration=0.3)


def decode_rgba(path: Path) -> list[Image.Image]:
    """Force libvpx at input: ffmpeg's native VP9 decoder discards WebM alpha."""
    raw = subprocess.run(
        [
            "ffmpeg", "-v", "error", "-c:v", "libvpx-vp9", "-i", str(path),
            "-map", "0:v:0", "-f", "rawvideo", "-pix_fmt", "rgba", "-",
        ],
        check=True,
        capture_output=True,
        timeout=20,
    ).stdout  # fmt: skip
    frame_size = SIZE[0] * SIZE[1] * 4
    assert raw and len(raw) % frame_size == 0
    return [
        Image.frombytes("RGBA", SIZE, raw[offset : offset + frame_size])
        for offset in range(0, len(raw), frame_size)
    ]


def assert_alpha_interiors(frames: list[Image.Image]) -> None:
    for frame in (frames[0], frames[-1]):
        alpha = frame.getchannel("A")
        assert alpha.getpixel((1, 12)) == 0
        assert alpha.getpixel((8, 12)) == pytest.approx(128, abs=1)
        assert alpha.getpixel((23, 12)) == 255


def tone_wav(path: Path, seconds: float) -> str:
    rate = 8000
    samples = (
        int(16000 * math.sin(2 * math.pi * 440 * index / rate))
        for index in range(round(rate * seconds))
    )
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes(b"".join(struct.pack("<h", sample) for sample in samples))
    return str(path)


def decode_audio(path: Path) -> tuple[int, ...]:
    pcm = subprocess.run(
        [
            "ffmpeg", "-v", "error", "-i", str(path), "-map", "0:a:0",
            "-f", "s16le", "-ar", "8000", "-ac", "1", "-",
        ],
        check=True,
        capture_output=True,
        timeout=20,
    ).stdout  # fmt: skip
    return struct.unpack(f"<{len(pcm) // 2}h", pcm)


class TestTransparentWebmValidation:
    def test_options_default_and_schema_describe_an_opt_in_boolean(self):
        assert VideoOptions().transparent is False
        assert VideoOptions.model_validate_json("{}").transparent is False
        field = VideoOptions.model_json_schema()["properties"]["transparent"]
        assert field["type"] == "boolean"
        assert field["default"] is False

    @pytest.mark.parametrize("transparent", [False, True])
    def test_options_round_trip_json(self, transparent):
        options = VideoOptions(transparent=transparent)
        assert json.loads(options.model_dump_json())["transparent"] is transparent
        assert VideoOptions.model_validate_json(options.model_dump_json()) == options

    @pytest.mark.parametrize("value", [0, 1, "true", "false", "yes", None, [], {}])
    def test_options_reject_non_boolean_python_and_json_values(self, value):
        with pytest.raises(ValidationError, match="transparent"):
            VideoOptions.model_validate({"transparent": value})
        with pytest.raises(ValidationError, match="transparent"):
            VideoOptions.model_validate_json(json.dumps({"transparent": value}))

    @pytest.mark.parametrize("kind", ["canvas", "deck"])
    def test_public_keyword_is_keyword_only_and_defaults_to_false(self, kind):
        parameter = inspect.signature(document(kind).to_webm).parameters["transparent"]
        assert parameter.kind == inspect.Parameter.KEYWORD_ONLY
        assert parameter.default is False

    @pytest.mark.parametrize("kind", ["canvas", "deck"])
    @pytest.mark.parametrize("value", [0, 1, "true", None])
    def test_bytes_api_rejects_non_boolean_before_rendering(self, monkeypatch, kind, value):
        monkeypatch.setattr(video, "_deck_plan", lambda *a, **k: pytest.fail("built timeline"))
        monkeypatch.setattr(video.tempfile, "mkstemp", lambda *a, **k: pytest.fail("tempfile"))
        with pytest.raises(ValidationError, match="transparent.*boolean"):
            document(kind).to_webm(transparent=cast(Any, value))

    @pytest.mark.parametrize("kind", ["canvas", "deck"])
    @pytest.mark.parametrize(
        "extension", ["mp4", "gif", "pdf", "pptx", "svg", "html", "png", "jpg", "webp"]
    )
    def test_unsupported_targets_preserve_destination_before_work(
        self, monkeypatch, tmp_path, kind, extension
    ):
        destination = tmp_path / f"existing.{extension}"
        destination.write_bytes(b"previous export")
        monkeypatch.setattr(video, "_deck_plan", lambda *a, **k: pytest.fail("built timeline"))
        monkeypatch.setattr(video, "_ffmpeg_binary", lambda: pytest.fail("looked up ffmpeg"))
        monkeypatch.setattr(video.tempfile, "mkstemp", lambda *a, **k: pytest.fail("tempfile"))
        with pytest.raises(
            (ValidationError, RenderingError), match="transparent|animation|VideoOptions"
        ):
            document(kind).render(str(destination), animation=VideoOptions(transparent=True))
        assert destination.read_bytes() == b"previous export"
        assert list(tmp_path.iterdir()) == [destination]

    @pytest.mark.parametrize("kind", ["canvas", "deck"])
    @pytest.mark.parametrize("method", ["to_mp4", "to_gif"])
    def test_other_public_bytes_methods_do_not_accept_transparent(self, kind, method):
        export = cast(Callable[..., bytes], getattr(document(kind), method))
        with pytest.raises(TypeError, match="transparent"):
            export(transparent=True)

    @pytest.mark.parametrize("format", ["mp4", "gif"])
    def test_internal_bytes_reject_unsupported_transparency_before_work(self, monkeypatch, format):
        monkeypatch.setattr(video, "_deck_plan", lambda *a, **k: pytest.fail("built timeline"))
        monkeypatch.setattr(video.tempfile, "mkstemp", lambda *a, **k: pytest.fail("tempfile"))
        with pytest.raises(ValidationError, match="transparent.*WebM"):
            video.export_animation_bytes([alpha_canvas()], [None], format, transparent=True)


@pytest.mark.parametrize("kind", ["canvas", "deck"])
@pytest.mark.parametrize("entrypoint", ["bytes", "render"])
@pytest.mark.parametrize("failure", ["encoder", "producer"])
def test_transparent_failures_remove_temporary_files_and_preserve_destination(
    monkeypatch, tmp_path, kind, entrypoint, failure
):
    destination = tmp_path / "existing.webm"
    destination.write_bytes(b"previous export")
    closed = []
    segments = []
    monkeypatch.setattr(video.tempfile, "tempdir", str(tmp_path))
    monkeypatch.setattr(video, "_ffmpeg_binary", lambda: "unused-ffmpeg")

    def shots(*args, **kwargs):
        try:
            yield video._Shot(Image.new("RGBA", SIZE, (240, 80, 120, 128)), 0.1)
            if failure == "producer":
                raise RuntimeError("injected alpha producer failure")
        finally:
            closed.append(True)

    def stream(command, frames, format, output_path):
        assert command[command.index("-pixel_format") + 1] == "rgba"
        partial = Path(output_path)
        partial.write_bytes(b"partial encoded segment")
        segments.append(partial)
        if failure == "encoder":
            next(iter(frames))
            raise RenderingError("injected alpha encoder failure")
        for frame in frames:
            assert len(frame) == SIZE[0] * SIZE[1] * 4

    monkeypatch.setattr(video, "_deck_shots", shots)
    monkeypatch.setattr(video, "_stream_video_ffmpeg", stream)
    source = document(kind)
    with pytest.raises((RenderingError, RuntimeError), match=f"injected alpha {failure} failure"):
        if entrypoint == "bytes":
            source.to_webm(fps=10, transparent=True)
        else:
            source.render(str(destination), animation=VideoOptions(fps=10, transparent=True))
    assert closed == [True]
    assert segments and all(not path.exists() for path in segments)
    assert destination.read_bytes() == b"previous export"
    assert list(tmp_path.iterdir()) == [destination]


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg not installed")
class TestTransparentWebmPublicExports:
    @pytest.mark.parametrize("kind", ["canvas", "deck"])
    @pytest.mark.parametrize("entrypoint", ["bytes", "render"])
    def test_public_paths_preserve_decodable_alpha(self, tmp_path, kind, entrypoint):
        source = document(kind)
        destination = tmp_path / "alpha.webm"
        destination.write_bytes(b"previous export")
        if entrypoint == "render":
            written = source.render(
                str(destination), animation=VideoOptions(fps=10, transparent=True)
            )
            assert written == (None if kind == "canvas" else [str(destination)])
        elif isinstance(source, Canvas):
            destination.write_bytes(source.to_webm(fps=10, hold=0.3, transparent=True))
        else:
            destination.write_bytes(source.to_webm(fps=10, slide_duration=0.3, transparent=True))
        assert destination.read_bytes().startswith(b"\x1a\x45\xdf\xa3")
        assert_alpha_interiors(decode_rgba(destination))
        assert list(tmp_path.iterdir()) == [destination]

    @pytest.mark.parametrize("loop", [False, True])
    def test_soundtrack_keeps_full_duration_and_alpha(self, tmp_path, loop):
        soundtrack = AudioTrack(path=tone_wav(tmp_path / "music.wav", 0.15), loop=loop)
        destination = tmp_path / "music.webm"
        destination.write_bytes(
            alpha_canvas().to_webm(fps=10, hold=0.6, transparent=True, soundtrack=soundtrack)
        )
        frames = decode_rgba(destination)
        samples = decode_audio(destination)
        assert len(frames) == 6
        assert_alpha_interiors(frames)
        assert len(samples) / 8000 == pytest.approx(0.6, abs=0.06)
        assert max(abs(sample) for sample in samples[160:800]) > 5000
        tail = max(abs(sample) for sample in samples[3200:4000])
        assert tail > 5000 if loop else tail < 100

    @pytest.mark.parametrize("entrypoint", ["bytes", "render"])
    def test_scheduled_narration_stays_aligned_and_trimmed_with_alpha(self, tmp_path, entrypoint):
        voice = tone_wav(tmp_path / "voice.wav", 0.7)
        deck = (
            Deck(*SIZE, transition="cut")
            .slide(alpha_canvas(), duration=0.3)
            .slide(alpha_canvas(), audio=voice, duration=0.3)
        )
        destination = tmp_path / "narration.webm"
        if entrypoint == "bytes":
            destination.write_bytes(deck.to_webm(fps=10, transparent=True))
        else:
            deck.render(str(destination), animation=VideoOptions(fps=10, transparent=True))
        frames = decode_rgba(destination)
        samples = decode_audio(destination)
        assert len(frames) == 6
        assert_alpha_interiors(frames)
        assert len(samples) / 8000 == pytest.approx(0.6, abs=0.06)
        assert max(abs(sample) for sample in samples[400:1600]) < 100
        assert max(abs(sample) for sample in samples[3200:4000]) > 5000

    @pytest.mark.skipif(not HAS_FFPROBE, reason="ffprobe not installed")
    def test_narration_infers_duration_and_survives_soundtrack_mux_with_alpha(self, tmp_path):
        voice = tone_wav(tmp_path / "voice.wav", 0.6)
        music = AudioTrack(path=tone_wav(tmp_path / "music.wav", 0.1), volume=0.1, loop=True)
        deck = Deck(*SIZE).slide(alpha_canvas(), audio=voice)
        destination = tmp_path / "mixed.webm"
        destination.write_bytes(
            deck.to_webm(fps=10, slide_duration=0.1, transparent=True, soundtrack=music)
        )
        frames = decode_rgba(destination)
        samples = decode_audio(destination)
        assert len(frames) == 6
        assert_alpha_interiors(frames)
        assert len(samples) / 8000 == pytest.approx(0.6, abs=0.06)
        assert max(abs(sample) for sample in samples[3200:4000]) > 5000
