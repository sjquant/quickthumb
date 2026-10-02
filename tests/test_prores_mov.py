"""Decoded ProRes contracts: alpha precision, uncropped frames, timing and audio."""

import json
import math
import shutil
import struct
import subprocess
import wave
from pathlib import Path
from typing import cast

import pytest
from PIL import Image, ImageChops, ImageDraw
from quickthumb import AudioTrack, Canvas, Deck, Fade, VideoOptions
from quickthumb import _export_video as video
from quickthumb import transitions as tr
from quickthumb.errors import RenderingError

HAS_TOOLS = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))
real_codec = pytest.mark.skipif(not HAS_TOOLS, reason="FFmpeg and ffprobe required")
TRANSITIONS = [
    tr.Cut(),
    tr.Fade(),
    tr.Random(),
    tr.Morph(),
    tr.Push(),
    tr.Cover(),
    tr.Uncover(),
    tr.Zoom(),
    tr.Newsflash(),
    tr.Wipe(),
    tr.Split(),
    tr.Blinds(),
    tr.Checker(),
    tr.Comb(),
    tr.Circle(),
    tr.Diamond(),
    tr.Wheel(),
    tr.Wedge(),
    tr.Dissolve(),
]


def decode(path: Path, size: tuple[int, int]) -> list[Image.Image]:
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:v:0", "-vsync", "0",
         "-f", "rawvideo", "-pix_fmt", "rgba", "-"],
        check=True, capture_output=True, timeout=30,
    ).stdout  # fmt: skip
    stride = size[0] * size[1] * 4
    assert raw and len(raw) % stride == 0
    return [Image.frombytes("RGBA", size, raw[i : i + stride]) for i in range(0, len(raw), stride)]


def probe(path: Path) -> dict:
    return json.loads(subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
        check=True, capture_output=True, timeout=30,
    ).stdout)  # fmt: skip


def assert_alpha(actual: Image.Image, expected: Image.Image) -> None:
    assert actual.size == expected.size
    difference = ImageChops.difference(actual.getchannel("A"), expected.getchannel("A"))
    assert cast(int, difference.getextrema()[1]) <= 1


def assert_composites(actual: Image.Image, expected: Image.Image, tolerance: int = 3) -> None:
    # FFmpeg 7.1.5 measured <=2 across these composites; allow one level
    # for conversion differences between supported FFmpeg builds.
    for matte in [(0, 0, 0, 255), (255, 255, 255, 255), (35, 110, 170, 255)]:
        background = Image.new("RGBA", expected.size, matte)
        a = Image.alpha_composite(background, actual).convert("RGB")
        e = Image.alpha_composite(background, expected).convert("RGB")
        assert (
            max(cast(int, band.getextrema()[1]) for band in ImageChops.difference(a, e).split())
            <= tolerance
        )


@real_codec
def test_all_256_rgba8_alpha_levels_survive_fixed_16_bit_coding(tmp_path):
    expected = Image.new("RGBA", (256, 3), (190, 80, 30, 255))
    expected.putalpha(Image.frombytes("L", expected.size, bytes(range(256)) * 3))
    path = tmp_path / "ramp.mov"
    video._encode_video_file([video._Shot(expected, 0.1)], 10, "mov", str(path), transparent=True)
    actual = decode(path, expected.size)[0]
    # Alpha itself must stay within one RGBA8 level across all 256 codes.
    assert_alpha(actual, expected)
    # This separate tolerance applies only to lossy RGB after compositing.
    assert_composites(actual, expected, 2)
    alpha = actual.getchannel("A")
    assert alpha.getpixel((0, 1)) == 0
    assert alpha.getpixel((255, 1)) == 255
    stream = probe(path)["streams"][0]
    assert stream["codec_name"] == "prores" and stream["profile"] == "4444"
    assert stream["codec_tag_string"] == "ap4h"


@real_codec
@pytest.mark.parametrize("size", [(1, 1), (1, 3), (3, 1), (3, 3), (17, 19)])
@pytest.mark.parametrize("transparent", [False, True])
def test_odd_and_tiny_dimensions_retain_last_row_and_column(tmp_path, size, transparent):
    expected = Image.new("RGBA", size, (40, 100, 170, 110 if transparent else 255))
    draw = ImageDraw.Draw(expected)
    draw.line((size[0] - 1, 0, size[0] - 1, size[1] - 1), fill=(180, 70, 25, 255))
    draw.line(
        (0, size[1] - 1, size[0] - 1, size[1] - 1), fill=(30, 180, 80, 64 if transparent else 255)
    )
    path = tmp_path / "edges.mov"
    video._encode_video_file(
        [video._Shot(expected, 0.1)], 10, "mov", str(path), transparent=transparent
    )
    stream = probe(path)["streams"][0]
    assert (stream["width"], stream["height"]) == size
    assert stream["pix_fmt"].startswith("yuva444" if transparent else "yuv444")
    actual = decode(path, size)[0]
    assert_alpha(actual, expected)
    assert_composites(actual, expected)


@real_codec
@pytest.mark.parametrize("kind", ["canvas", "deck"])
@pytest.mark.parametrize("entrypoint", ["render", "export", "bytes"])
def test_all_public_outputs_decode_alpha_and_settled_final_frame(tmp_path, kind, entrypoint):
    canvas = Canvas(33, 17).shape("rectangle", (1, 1), 12, 15, "#E0406080")
    canvas.shape("rectangle", (20, 0), 13, 17, "#3060D0")
    source = canvas if kind == "canvas" else Deck().slide(canvas, duration=0.3)
    path = tmp_path / "public.mov"
    path.write_bytes(b"previous")
    if entrypoint == "bytes":
        data = (
            canvas.to_mov(fps=10, hold=0.3, transparent=True)
            if kind == "canvas"
            else cast(Deck, source).to_mov(fps=10, slide_duration=0.3, transparent=True)
        )
        path.write_bytes(data)
    else:
        result = getattr(source, entrypoint)(
            str(path), animation=VideoOptions(fps=10, transparent=True)
        )
        if entrypoint == "export":
            assert result.target == "video" and result.output_format == "mov"
            assert result.pixel_metrics.frame_count == (30 if kind == "canvas" else 3)
    frames = decode(path, (33, 17))
    expected = video._SlideAnimator(canvas, {}).final_export_frame()
    assert_alpha(frames[-1], expected)
    assert_composites(frames[-1], expected)
    assert list(tmp_path.iterdir()) == [path]


@real_codec
@pytest.mark.parametrize("quality", ["standard", "high"])
@pytest.mark.parametrize("workers", [1, 2])
def test_public_quality_and_spawn_preserve_transparent_letterboxing(tmp_path, quality, workers):
    first = Canvas(33, 25).background(color="#30806040")
    second = Canvas(17, 25).shape(
        "rectangle", (1, 1), 15, 23, "#E0604080", animation=Fade(duration=0.2)
    )
    deck = Deck(33, 25, transition="cut").slide(first, duration=0.1).slide(second, duration=0.1)
    path = tmp_path / "workers.mov"
    deck.render(
        str(path),
        animation=VideoOptions(transparent=True, fps=10, quality=quality, workers=workers),
    )
    frames = decode(path, (33, 25))
    expected = video._conform(
        video._SlideAnimator(second, {}, quality=quality).final_export_frame(), (33, 25), None
    )
    assert_alpha(frames[-1], expected)
    assert_composites(frames[-1], expected)
    assert frames[0].getchannel("A").getextrema() == (64, 64)
    assert frames[-1].getchannel("A").getpixel((0, 12)) == 0


@real_codec
def test_transition_families_and_keyed_mixed_size_morph_decode_composites(tmp_path):
    previous = Image.new("RGBA", (33, 25), (230, 50, 70, 128))
    incoming = Image.new("RGBA", (33, 25), (30, 110, 210, 64))
    expected = [video._transition_frame(t, previous, incoming, 0.5) for t in TRANSITIONS]
    old = (
        Canvas(33, 25)
        .background(color="#30806040")
        .shape("rectangle", (3, 5), 10, 12, "#E0406080", motion_key="box")
    )
    new = (
        Canvas(17, 25)
        .background(color="#30806040")
        .shape("rectangle", (3, 5), 10, 12, "#E0406080", motion_key="box")
    )
    expected.append(video._morph_frame(old, new, 0.5, 1, output_size=(33, 25)))
    path = tmp_path / "transitions.mov"
    video._encode_video_file(
        (video._Shot(f, 0.1) for f in expected), 10, "mov", str(path), transparent=True
    )
    actual = decode(path, (33, 25))
    assert len(actual) == len(expected)
    for a, e in zip(actual, expected, strict=True):
        assert_alpha(a, e)
        assert_composites(a, e)


@real_codec
@pytest.mark.parametrize("fps", [10.0, 29.97])
def test_fractional_counting_real_segment_boundary_and_final_frame(tmp_path, fps):
    shots = []
    expected = []
    clock = 0.0
    emitted = 0
    for index in range(100):
        frame = Image.new("RGBA", (17, 3), (100, 120, 150, index * 2))
        duration = [0.5, 1, 0.3, 0.7, 1][index % 5] / fps
        clock += duration
        end = math.floor(clock * fps + 0.5)
        expected.extend([index * 2] * (end - emitted))
        emitted = end
        shots.append(video._Shot(frame, duration))
    assert len(list(video._counted_video_shots(shots, fps))) > 64
    path = tmp_path / "boundaries.mov"
    video._encode_video_file(iter(shots), fps, "mov", str(path), transparent=True)
    actual = [cast(int, frame.getchannel("A").getpixel((16, 2))) for frame in decode(path, (17, 3))]
    assert len(actual) == len(expected)
    assert all(abs(a - e) <= 1 for a, e in zip(actual, expected, strict=True))
    assert actual[-1] == pytest.approx(198, abs=1)
    assert float(probe(path)["format"]["duration"]) == pytest.approx(len(expected) / fps, abs=0.002)


def tone(path: Path, duration: float) -> str:
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(8000)
        output.writeframes(
            b"".join(
                struct.pack("<h", round(16000 * math.sin(2 * math.pi * 440 * i / 8000)))
                for i in range(round(8000 * duration))
            )
        )
    return str(path)


def audio(path: Path) -> tuple[int, ...]:
    pcm = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            str(path),
            "-map",
            "0:a:0",
            "-f",
            "s16le",
            "-ar",
            "8000",
            "-ac",
            "1",
            "-",
        ],
        check=True,
        capture_output=True,
        timeout=30,
    ).stdout
    return struct.unpack(f"<{len(pcm) // 2}h", pcm)


@real_codec
@pytest.mark.parametrize("loop", [False, True])
def test_soundtrack_aac_padding_loop_and_alpha(tmp_path, loop):
    track = AudioTrack(path=tone(tmp_path / "tone.wav", 0.15), loop=loop)
    path = tmp_path / "soundtrack.mov"
    path.write_bytes(
        Canvas(17, 3)
        .background(color="#C0502080")
        .to_mov(fps=10, hold=0.6, transparent=True, soundtrack=track)
    )
    streams = probe(path)["streams"]
    assert [s["codec_name"] for s in streams] == ["prores", "aac"]
    frames = decode(path, (17, 3))
    assert len(frames) == 6
    assert frames[-1].getchannel("A").getextrema() == pytest.approx((128, 128), abs=1)
    samples = audio(path)
    assert len(samples) / 8000 == pytest.approx(0.6, abs=0.06)
    assert max(abs(s) for s in samples[160:800]) > 5000
    tail = max(abs(s) for s in samples[3200:4000])
    assert tail > 5000 if loop else tail < 100


@real_codec
def test_narration_inferred_duration_offsets_and_music_bed(tmp_path):
    voice = tone(tmp_path / "voice.wav", 0.3)
    music = AudioTrack(path=voice, loop=True, volume=0.1)
    canvas = Canvas(17, 3).background(color="#C0502080")
    deck = Deck(transition="cut").slide(canvas, duration=0.3).slide(canvas, audio=voice)
    path = tmp_path / "narrated.mov"
    path.write_bytes(deck.to_mov(fps=10, slide_duration=0.1, transparent=True, soundtrack=music))
    assert len(decode(path, (17, 3))) == 6
    samples = audio(path)
    assert 500 < max(abs(s) for s in samples[400:1600]) < 3000
    assert max(abs(s) for s in samples[3200:4000]) > 5000


@pytest.mark.parametrize("transparent", [False, True])
@pytest.mark.parametrize("kind", ["canvas", "deck"])
@pytest.mark.parametrize("entrypoint", ["render", "export", "bytes"])
@pytest.mark.parametrize("failure", ["producer", "encoder", "mux"])
def test_failures_close_resources_remove_temps_and_preserve_destination(
    monkeypatch, tmp_path, transparent, kind, entrypoint, failure
):
    destination = tmp_path / "existing.mov"
    destination.write_bytes(b"original")
    monkeypatch.setattr(video.tempfile, "tempdir", str(tmp_path))
    monkeypatch.setattr(video, "_ffmpeg_binary", lambda: "unused")
    closed = []
    decoders_closed = []
    monkeypatch.setattr(
        video, "_close_video_decoders", lambda canvases: decoders_closed.append(True)
    )

    def shots(*args, **kwargs):
        try:
            yield video._Shot(Image.new("RGBA" if transparent else "RGB", (3, 3)), 0.1)
            if failure == "producer":
                raise RuntimeError("injected producer")
        finally:
            closed.append(True)

    def stream(command, frames, format, output_path):
        assert command[command.index("-c:v") + 1] == "prores_ks"
        assert "-vf" not in command
        assert command[command.index("-alpha_bits") + 1] == ("16" if transparent else "0")
        Path(output_path).write_bytes(b"partial segment")
        for _ in frames:
            if failure == "encoder":
                raise RenderingError("injected encoder")

    def mux(command, format, output_path):
        Path(output_path).write_bytes(b"partial mux")
        raise RenderingError("injected mux")

    monkeypatch.setattr(video, "_deck_shots", shots)
    monkeypatch.setattr(video, "_stream_video_ffmpeg", stream)
    monkeypatch.setattr(video, "_run_video_ffmpeg", mux)
    canvas = Canvas(3, 3)
    source = canvas if kind == "canvas" else Deck().slide(canvas)
    with pytest.raises((RenderingError, RuntimeError), match=f"injected {failure}"):
        if entrypoint == "bytes":
            source.to_mov(fps=10, transparent=transparent)
        else:
            getattr(source, entrypoint)(
                str(destination), animation=VideoOptions(fps=10, transparent=transparent)
            )
    assert closed == [True] and decoders_closed == [True]
    assert destination.read_bytes() == b"original"
    assert list(tmp_path.iterdir()) == [destination]


@real_codec
def test_missing_prores_encoder_reports_error_and_preserves_destination(monkeypatch, tmp_path):
    monkeypatch.setitem(video._ALPHA_CODEC_ARGS, "mov", ["-c:v", "missing_prores_encoder"])
    path = tmp_path / "existing.mov"
    path.write_bytes(b"original")
    monkeypatch.setattr(video.tempfile, "tempdir", str(tmp_path))
    with pytest.raises(RenderingError, match="Unknown encoder.*missing_prores_encoder"):
        Canvas(3, 3).render(str(path), animation=VideoOptions(transparent=True, fps=1))
    assert path.read_bytes() == b"original" and list(tmp_path.iterdir()) == [path]


@real_codec
def test_embedded_clip_audio_trim_speed_and_delay_with_alpha(tmp_path):
    clip = tmp_path / "clip.mp4"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=red:s=16x16:r=10:d=0.6",
         "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=0.6",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(clip)],
        check=True, capture_output=True, timeout=30,
    )  # fmt: skip
    canvas = Canvas(33, 25).video(
        str(clip),
        position=(8, 4),
        width=16,
        height=16,
        start=0.2,
        trim_start=0.1,
        trim_end=0.5,
        speed=2,
    )
    path = tmp_path / "embedded.mov"
    path.write_bytes(canvas.to_mov(fps=10, hold=0.2, transparent=True))
    frames = decode(path, (33, 25))
    assert len(frames) == 6
    assert all(frame.getchannel("A").getpixel((0, 0)) == 0 for frame in frames)
    assert frames[2].getchannel("A").getpixel((16, 12)) == 255
    samples = audio(path)
    assert max(abs(s) for s in samples[200:1000]) < 100
    assert max(abs(s) for s in samples[2000:2800]) > 1000
    assert max(abs(s) for s in samples[3800:4500]) < 100


def test_mov_pipe_failure_reaps_encoder_and_preserves_destination(monkeypatch, tmp_path):
    from tests.test_video_stream_process import _Process

    process = _Process(
        write_error=BrokenPipeError("injected pipe failure"), stderr=b"encoder closed"
    )
    monkeypatch.setattr(video.subprocess, "Popen", lambda *a, **k: process)
    monkeypatch.setattr(video, "_ffmpeg_binary", lambda: "unused")
    monkeypatch.setattr(video.tempfile, "tempdir", str(tmp_path))
    path = tmp_path / "existing.mov"
    path.write_bytes(b"original")
    with pytest.raises(RenderingError, match="(?s)encoding mov.*encoder closed"):
        Canvas(3, 3).render(str(path), animation=VideoOptions(transparent=True, fps=1))
    assert process.stdin.closed and process.stderr.closed and process.returncode == 0
    assert path.read_bytes() == b"original" and list(tmp_path.iterdir()) == [path]
