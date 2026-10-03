"""Exact frame allocation and decoded-output regressions for raw video streaming."""

import json
import math
import shutil
import subprocess
from pathlib import Path
from typing import cast

import pytest
from PIL import Image, ImageDraw
from quickthumb import _export_video as video
from quickthumb.errors import RenderingError

HAS_VIDEO_TOOLS = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def _numbered_frame(number: int) -> Image.Image:
    image = Image.new("RGB", (129, 19), (230, 30, 60))
    draw = ImageDraw.Draw(image)
    for bit in range(8):
        level = 255 if number & (1 << bit) else 0
        draw.rectangle((16 * bit, 0, 16 * bit + 15, 17), fill=(level, level, level))
    return image


def _decode(path: Path) -> bytes:
    return subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:v", "-vsync", "0",
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        check=True, capture_output=True, timeout=30,
    ).stdout  # fmt: skip


def _probe(path: Path) -> dict:
    return json.loads(subprocess.run(
        ["ffprobe", "-v", "error", "-count_frames", "-show_entries",
         "stream=width,height,nb_read_frames:format=duration", "-of", "json", str(path)],
        check=True, capture_output=True, timeout=30,
    ).stdout)  # fmt: skip


def _legacy_batch(entries, fps: float, container: str, directory: Path) -> Path:
    """Frozen pre-#150 PNG/concat reference, used only for decoded comparisons."""
    directory.mkdir()
    lines = ["ffconcat version 1.0"]
    count = 0
    for index, (frame, repeats) in enumerate(entries):
        name = f"shot-{index:03d}.png"
        frame.save(directory / name, format="PNG")
        lines.extend((f"file '{name}'", f"duration {repeats / fps:.12f}"))
        count += repeats
    lines.append(f"file 'shot-{len(entries) - 1:03d}.png'")
    manifest = directory / "frames.ffconcat"
    manifest.write_text("\n".join(lines) + "\n")
    output = directory / f"legacy.{container}"
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat",
         "-safe", "0", "-i", str(manifest), "-t", f"{max((count - 0.5) / fps, 0.5 / fps):.9f}",
         "-vf", f"fps={fps:g},crop=trunc(iw/2)*2:trunc(ih/2)*2",
         *video._CODEC_ARGS[container], str(output)],
        check=True, capture_output=True, timeout=30,
    )  # fmt: skip
    return output


@pytest.mark.parametrize("fps", [10.0, 12.0, 29.97, 120.0])
def test_cumulative_counts_do_not_drift(fps):
    durations = [0.5 / fps, 1 / fps, 0.2 / fps, 0.3 / fps, 0.037] * 30
    frames = [_numbered_frame(index % 256) for index in range(len(durations))]
    actual = list(
        video._counted_video_shots(
            (
                video._Shot(frame, duration)
                for frame, duration in zip(frames, durations, strict=True)
            ),
            fps,
        )
    )
    clock = 0.0
    allocated = 0
    expected = []
    for frame, duration in zip(frames, durations, strict=True):
        clock += duration
        endpoint = math.floor(clock * fps + 0.5)
        if endpoint > allocated:
            expected.append((frame, endpoint - allocated))
        allocated = endpoint
    assert actual == expected
    assert sum(count for _, count in actual) == math.floor(sum(durations) * fps + 0.5)


def test_sub_frame_fallback_uses_last_frame():
    first, last = _numbered_frame(0), _numbered_frame(1)
    assert list(
        video._counted_video_shots([video._Shot(first, 0.01), video._Shot(last, 0.01)], 10)
    ) == [(last, 1)]
    assert list(video._counted_video_shots([], 10)) == []


def test_batches_are_lazy_and_bounded(monkeypatch, tmp_path):
    events = []
    sizes = []

    def shots():
        for index in range(129):
            events.append(("produce", index))
            yield video._Shot(Image.new("RGB", (2, 2), (index, 0, 0)), 0.1)

    def encode(binary, entries, fps, container, directory, index):
        count = 0
        for image, repeats in entries:
            events.append(("write", image.getpixel((0, 0))[0]))
            count += repeats
        sizes.append(count)
        return directory / f"segment-{index}.mp4", count

    monkeypatch.setattr(video, "_encode_shot_batch", encode)
    segments, facts = video._encode_shot_batches(
        "ffmpeg", video._counted_video_shots(shots(), 10), 10, "mp4", tmp_path
    )
    assert sizes == [64, 64, 1]
    assert len(segments) == 3
    assert facts.duration == 12.9
    assert facts.frame_count == 129
    assert events == [event for i in range(129) for event in (("produce", i), ("write", i))]
    with pytest.raises(RenderingError, match="no frames"):
        video._encode_shot_batches("ffmpeg", [], 10, "mp4", tmp_path)


def test_static_hold_reuses_one_bytes_buffer(monkeypatch, tmp_path):
    image = _numbered_frame(3)
    calls = 0
    original = image.tobytes

    def tobytes():
        nonlocal calls
        calls += 1
        return original()

    monkeypatch.setattr(image, "tobytes", tobytes)
    buffers = []
    monkeypatch.setattr(
        video, "_stream_video_ffmpeg", lambda command, frames, *args: buffers.extend(frames)
    )
    _, count = video._encode_shot_batch("ffmpeg", [(image, 50)], 10, "mp4", tmp_path, 0)
    assert count == 50
    assert calls == 1
    assert len(buffers) == 50
    assert all(buffer is buffers[0] for buffer in buffers)


@pytest.mark.skipif(not HAS_VIDEO_TOOLS, reason="ffmpeg/ffprobe not installed")
@pytest.mark.parametrize("container", ["mp4", "webm"])
@pytest.mark.parametrize("fps", [10.0, 25.0])
def test_decoded_pixels_match_legacy_png_path(tmp_path, fps, container):
    entries = [(_numbered_frame(index), (index % 3) + 1) for index in range(12)]
    expected = _legacy_batch(entries, fps, container, tmp_path / "legacy")
    actual, count = video._encode_shot_batch("ffmpeg", entries, fps, container, tmp_path, 0)
    assert count == 24
    assert _decode(actual) == _decode(expected)
    assert _probe(actual) == _probe(expected)


@pytest.mark.skipif(not HAS_VIDEO_TOOLS, reason="ffmpeg/ffprobe not installed")
@pytest.mark.parametrize("container", ["mp4", "webm"])
@pytest.mark.parametrize("fps", [29.97, 30.0, 60.0, 120.0])
def test_high_fps_keeps_every_counted_frame_across_batches(tmp_path, fps, container):
    output = tmp_path / f"counted.{container}"
    facts = video._encode_video_file(
        video._counted_video_shots(
            (video._Shot(_numbered_frame(index), 1 / fps) for index in range(129)), fps
        ),
        fps,
        container,
        str(output),
    )
    probe = _probe(output)
    stream = probe["streams"][0]
    assert (stream["width"], stream["height"]) == (128, 18)
    assert int(stream["nb_read_frames"]) == facts.frame_count == 129
    assert (facts.width, facts.height) == (128, 18)
    assert facts.duration == 129 / fps
    assert facts.fps == fps
    assert float(probe["format"]["duration"]) == pytest.approx(129 / fps, abs=0.04)
    raw = _decode(output)
    frame_size = 128 * 18 * 3
    assert len(raw) == 129 * frame_size
    decoded = []
    for offset in range(0, len(raw), frame_size):
        image = Image.frombytes("RGB", (128, 18), raw[offset : offset + frame_size])
        decoded.append(
            sum(
                1 << bit
                for bit in range(8)
                if cast(tuple[int, int, int], image.getpixel((16 * bit + 8, 8)))[0] > 128
            )
        )
    assert decoded == list(range(129))


@pytest.mark.skipif(not HAS_VIDEO_TOOLS, reason="ffmpeg/ffprobe not installed")
@pytest.mark.parametrize("container", ["mp4", "webm"])
@pytest.mark.parametrize("fps", [12.0, 24.0])
def test_fractional_frame_period_does_not_trim_the_last_frame(tmp_path, fps, container):
    # The old PNG/concat -t half-frame workaround could trim a counted frame
    # at these rates. EOF on raw input must encode the entire allocation.
    entries = [(_numbered_frame(index), (index % 3) + 1) for index in range(12)]
    actual, count = video._encode_shot_batch("ffmpeg", entries, fps, container, tmp_path, 0)
    probe = _probe(actual)
    assert count == int(probe["streams"][0]["nb_read_frames"]) == 24
    assert float(probe["format"]["duration"]) == pytest.approx(24 / fps, abs=0.002)


def test_rejects_mismatched_raw_frame_dimensions(monkeypatch, tmp_path):
    monkeypatch.setattr(video, "_stream_video_ffmpeg", lambda command, frames, *args: list(frames))
    with pytest.raises(RenderingError, match="matching dimensions"):
        video._encode_shot_batch(
            "ffmpeg",
            [(Image.new("RGB", (2, 2)), 1), (Image.new("RGB", (4, 2)), 1)],
            10,
            "mp4",
            tmp_path,
            0,
        )


def test_normalizes_non_rgb_frames(monkeypatch, tmp_path):
    buffers = []
    monkeypatch.setattr(
        video, "_stream_video_ffmpeg", lambda command, frames, *args: buffers.extend(frames)
    )
    image = Image.new("RGBA", (2, 2), (10, 20, 30, 255))
    video._encode_shot_batch("ffmpeg", [(image, 1)], 10, "mp4", tmp_path, 0)
    assert buffers == [bytes([10, 20, 30]) * 4]
