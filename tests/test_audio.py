"""Source-audio anchors become ordinary, portable motion authoring data."""

import hashlib
import json
import math
import shutil
import struct
import wave
from bisect import bisect_right
from itertools import accumulate
from typing import cast

import pytest
from PIL import Image
from pydantic import ValidationError as ModelValidationError
from quickthumb import (
    AnimationSpec,
    Canvas,
    ColorTrack,
    GifOptions,
    KeyframeSpec,
    RenderingError,
    TimingSpec,
    ValidationError,
)
from quickthumb.audio import AudioAnalysis, analyze_audio

HAS_FFMPEG = shutil.which("ffmpeg") is not None


def _write_pulses(path, *, times=(0.2, 0.6, 1.0), duration=1.2):
    with wave.open(str(path), "wb") as stream:
        stream.setparams((1, 2, 8000, 0, "NONE", "not compressed"))
        stream.writeframes(
            b"".join(
                struct.pack(
                    "<h",
                    round(24000 * math.sin(2 * math.pi * 440 * index / 8000))
                    if any(start <= index / 8000 < start + 0.04 for start in times)
                    else 0,
                )
                for index in range(round(duration * 8000))
            )
        )


@pytest.mark.skipif(not HAS_FFMPEG, reason="FFmpeg is required for source analysis")
def test_onsets_bake_into_portable_motion(tmp_path, monkeypatch):
    """Reference transients anchor decoded GIF motion after audio analysis is unavailable."""
    # Given: three independently authored pulses on a known source clock
    source = tmp_path / "pulses.wav"
    _write_pulses(source)
    analysis = analyze_audio(source, cache_dir=tmp_path / "cache")
    assert analysis.onsets == pytest.approx((0.2, 0.6, 1.0), abs=0.02)
    assert analysis.duration == 1.2
    assert analysis.source_sha256 == hashlib.sha256(source.read_bytes()).hexdigest()
    assert len(analysis.rms) == 60
    assert analysis.rms[0] == 0 and analysis.rms[10] > 0.1
    sidecar = tmp_path / "analysis.json"
    sidecar.write_text(analysis.model_dump_json())

    # When: only stored data is available to author, restore and export the scene
    monkeypatch.setenv("QUICKTHUMB_FFMPEG", "missing-audio-analyzer")
    source.unlink()
    restored = AudioAnalysis.model_validate_json(sidecar.read_text())
    canvas = (
        Canvas(32, 24)
        .background(color="#000000")
        .shape(
            "rectangle",
            (8, 6),
            16,
            12,
            "#000000",
            animation=AnimationSpec.timeline(
                ColorTrack(
                    keyframes=[
                        KeyframeSpec(time=0, value="#000000"),
                        KeyframeSpec(time=0.1, value="#FF0000"),
                    ]
                ),
                timing=TimingSpec(start=restored.onsets[0], duration=0.1),
                easing="linear",
            ),
        )
    )
    baked = Canvas.from_json(canvas.to_json())
    output = tmp_path / "anchored.gif"
    baked.export(output, animation=GifOptions(fps=50, hold=0.1))

    # Then: ordinary numeric JSON and decoded playback share the onset clock
    event = baked.inspect_motion(target="video").slides[0].layers[1].events[0]
    assert event.active_start == restored.onsets[0]
    assert event.tracks[0].type == "color"
    with Image.open(output) as image:
        frames = []
        durations = []
        for index in range(int(getattr(image, "n_frames", 1))):
            image.seek(index)
            frames.append(image.convert("RGB"))
            durations.append(image.info["duration"])
    ends = list(accumulate(durations))
    times = [0.18, 0.2, 0.24, 0.3]
    observed = [
        cast(
            tuple[int, int, int], frames[bisect_right(ends, round(time * 1000))].getpixel((16, 12))
        )[0]
        for time in times
    ]
    expected = [
        frame.to_image().convert("RGB").getpixel((16, 12))[0]
        for frame in baked.sample(times).frames
    ]
    assert observed == pytest.approx(expected, abs=2)
    assert observed[:2] == [0, 0]
    assert 70 < observed[2] < 150
    assert observed[3] == 255


@pytest.mark.skipif(not HAS_FFMPEG, reason="FFmpeg is required for source analysis")
def test_content_cache_and_silence(tmp_path, monkeypatch):
    """Cached analysis avoids decoding, follows changed bytes, and represents silence honestly."""
    # Given: cached transient analysis and a cache shared by different source paths
    source = tmp_path / "source.wav"
    _write_pulses(source)
    cache = tmp_path / "cache"
    first = analyze_audio(source, cache_dir=cache)
    copied = tmp_path / "copy.wav"
    copied.write_bytes(source.read_bytes())

    # When: the same bytes are analyzed again, decoding is unnecessary
    import quickthumb.audio as audio

    original_run = audio.subprocess.run

    def version_only(command, **kwargs):
        assert command[1:] == ["-version"], "cached source was decoded again"
        return original_run(command, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(audio.subprocess, "run", version_only)
        assert analyze_audio(copied, cache_dir=cache) == first

    # Then: editing that path invalidates its result; silence has no invented anchors
    _write_pulses(source, times=())
    silent = analyze_audio(source, cache_dir=cache)
    assert silent.source_sha256 != first.source_sha256
    assert silent.onsets == () and not any(silent.rms)
    silent_scene = (
        Canvas(32, 24)
        .background(color="#000000")
        .shape(
            "rectangle",
            (8, 6),
            16,
            12,
            "#FF0000",
            animation=AnimationSpec.timeline(silent.scale_track(min_scale=1, max_scale=2)),
        )
    )
    assert [
        frame.to_image().convert("RGB").getbbox()
        for frame in silent_scene.sample([0, 0.5, 1.2]).frames
    ] == [(8, 6, 24, 18)] * 3
    assert len(list(cache.glob("*.json"))) == 2
    for entry in cache.iterdir():
        assert AudioAnalysis.model_validate_json(entry.read_bytes()) in (first, silent)


def test_stored_envelope_drives_scale_without_audio(tmp_path, monkeypatch):
    """Stored RMS controls decoded scale windows and returns to baseline at the source end."""
    # Given: an independently authored envelope with quiet, soft and peak windows
    stored = AudioAnalysis(
        source_sha256="a" * 64,
        ffmpeg_version="stored decoder",
        duration=1.2,
        rms=(0, 0.25, 0.5, 0, 1) + (1, 0) * 27 + (1,),
        onsets=(),
    )
    monkeypatch.setenv("QUICKTHUMB_FFMPEG", "missing-audio-analyzer")
    canvas = (
        Canvas(64, 48)
        .background(color="#000000")
        .shape(
            "rectangle",
            (24, 16),
            16,
            16,
            "#FF0000",
            animation=AnimationSpec.timeline(stored.scale_track(min_scale=1, max_scale=2)),
        )
    )

    # When: ordinary canonical JSON is restored and exported as silent playback
    baked = Canvas.from_json(canvas.to_json())
    output = tmp_path / "envelope.gif"
    baked.export(output, animation=GifOptions(fps=50, hold=0.04))
    with Image.open(output) as image:
        frames = []
        durations = []
        for index in range(int(getattr(image, "n_frames", 1))):
            image.seek(index)
            frames.append(image.convert("RGB"))
            durations.append(image.info["duration"])
    ends = list(accumulate(durations))
    # The .9s boundary must not round backward through normalized progress / 1.2.
    times = [0, 0.02, 0.04, 0.06, 0.079, 0.08, 0.099, 0.1, 0.12, 0.899, 0.9, 1.199, 1.2, 1.22]
    widths = []
    for time in times:
        frame = frames[bisect_right(ends, round(time * 1000))]
        bounds = frame.getbbox()
        assert bounds is not None
        widths.append(bounds[2] - bounds[0])

    # Then: normalization, half-open windows and the settled hold are observable
    assert widths == [16, 20, 24, 16, 16, 32, 32, 32, 16, 16, 32, 32, 16, 16]
    exact = baked.render_frame(0.9).convert("RGB").getbbox()
    assert exact is not None and exact[2] - exact[0] == 32
    canonical = [frame.to_image().convert("RGB").getbbox() for frame in baked.sample(times).frames]
    assert [bounds[2] - bounds[0] for bounds in canonical] == widths
    event = baked.inspect_motion(target="video").slides[0].layers[1].events[0]
    assert event.duration == stored.duration
    assert event.tracks[0].type == "scale"


@pytest.mark.parametrize("bounds", [(0, 2), (2, 1), (1, float("inf")), (True, 2)])
def test_scale_bounds_reject_invalid_response(bounds):
    """Invalid scale bounds fail before motion tracks are returned."""
    # Given: a valid stored clock and invalid caller-specified scale bounds
    stored = AudioAnalysis(
        source_sha256="a" * 64,
        ffmpeg_version="stored decoder",
        duration=0.01,
        rms=(0.5,),
        onsets=(),
    )
    # When/Then: no malformed track is returned to the animation compiler
    with pytest.raises(ValidationError, match="scale"):
        stored.scale_track(min_scale=bounds[0], max_scale=bounds[1])


@pytest.mark.skipif(not HAS_FFMPEG, reason="FFmpeg is required for source analysis")
def test_invalid_audio_and_cache_report_recovery(tmp_path):
    """Invalid sources and corrupt cached records fail with actionable analysis errors."""
    # Given: a source without audio and a valid cached reference track
    source = tmp_path / "invalid.wav"
    source.write_text("not audio")
    with pytest.raises(RenderingError, match="readable audio file"):
        analyze_audio(source, cache_dir=tmp_path / "invalid-cache")
    _write_pulses(source)
    cache = tmp_path / "cache"
    analysis = analyze_audio(source, cache_dir=cache)
    cached = next(cache.glob("*.json"))
    cached.write_text(analysis.model_dump_json().replace('"version":"1"', '"version":"99"'))

    # When/Then: a corrupt cache cannot silently change persisted timing
    with pytest.raises(RenderingError, match="Remove it and analyze again"):
        analyze_audio(source, cache_dir=cache)


@pytest.mark.parametrize(
    "change",
    [
        {"onsets": [0.2, 0.2]},
        {"onsets": [1.2]},
        {"rms": [0.0]},
    ],
)
def test_stored_analysis_rejects_invalid_clocks(change):
    """Stored anchors must be ordered and bounded by their complete RMS source clock."""
    # Given: a complete source clock with invalid externally supplied fields
    data = {
        "source_sha256": "a" * 64,
        "ffmpeg_version": "ffmpeg reference",
        "duration": 1.2,
        "rms": [0.0] * 60,
        "onsets": [0.2],
        **change,
    }
    # When/Then: sidecar loading rejects the record before it can author motion
    with pytest.raises(ModelValidationError):
        AudioAnalysis.model_validate_json(json.dumps(data))


@pytest.mark.skipif(not HAS_FFMPEG, reason="FFmpeg is required for source analysis")
def test_analysis_limits_do_not_truncate(tmp_path):
    """Oversized sources fail instead of producing truncated onset anchors."""
    # Given: a cheap silent PCM source one sample beyond the supported duration
    source = tmp_path / "long.wav"
    with wave.open(str(source), "wb") as stream:
        stream.setparams((1, 2, 8000, 0, "NONE", "not compressed"))
        stream.writeframes(b"\0\0" * (600 * 8000 + 1))
    cache = tmp_path / "cache"
    # When/Then: no partial analysis is stored for either exceeded limit
    with pytest.raises(RenderingError, match="ten-minute limit"):
        analyze_audio(source, cache_dir=cache)
    assert not cache.exists()
    with source.open("wb") as stream:
        stream.truncate(64 * 1024 * 1024 + 1)
    with pytest.raises(RenderingError, match="64 MiB limit"):
        analyze_audio(source, cache_dir=cache)
