"""Regression coverage for trustworthy benchmark and lossless-change gates."""

import argparse
import copy
import json
import math
import subprocess

import pytest
from benchmarks import animated_export as benchmark
from benchmarks import frame_identity as identity
from benchmarks.scenes import SCENES, build_scene
from PIL import Image


@pytest.mark.parametrize("scene", SCENES[:3])
def test_synthetic_scenes_have_visible_motion_and_jitter(scene):
    deck = build_scene(scene)
    samples = deck.sample(time=[0, 0.5, 1.0, 1.5, 2.0])
    assert len({frame.sha256 for frame in samples.frames}) > 1
    assert samples.duration == 2
    jitter = benchmark.measure_jitter(scene)
    assert jitter is not None and math.isfinite(jitter) and jitter >= 0


def test_centroid_uses_intensity_weights_and_jitter_detects_staircase():
    image = Image.new("RGB", (4, 1))
    image.putpixel((0, 0), (255, 255, 255))
    image.putpixel((3, 0), (85, 85, 85))
    assert benchmark.centroid(image) == (0.75, 0.0)
    assert benchmark.displacement_jitter([(0, 0), (1, 0), (2, 0)]) == 0
    assert benchmark.displacement_jitter([(0, 0), (0, 0), (1, 0)]) == 0.5
    with pytest.raises(ValueError, match="visible"):
        benchmark.centroid(Image.new("RGB", (1, 1)))
    with pytest.raises(ValueError, match="three"):
        benchmark.displacement_jitter([(0, 0)])


def test_encoder_timer_excludes_lazy_render_work(monkeypatch):
    clock = [0.0]
    monkeypatch.setattr(benchmark.time, "perf_counter", lambda: clock[0])
    timer = benchmark.EncoderTimer()

    def shots():
        for index in range(3):
            clock[0] += 2
            yield index

    def encode(frames):
        result = []
        for frame in frames:
            result.append(frame)
            clock[0] += 3
        clock[0] += 1
        return result

    assert timer.wrap(encode)(shots()) == [0, 1, 2]
    assert timer.shots == 3
    assert timer.production_seconds == 6
    assert timer.encode_seconds == 10


def test_summary_requires_three_compatible_runs_and_takes_medians():
    runs = [
        {"scene": "translation", "format": "gif", "shots": 24, "total_seconds": value}
        for value in [10, 1, 3]
    ]
    assert benchmark.summarize(runs)["total_seconds"] == 3
    with pytest.raises(ValueError, match="three"):
        benchmark.summarize(runs[:2])
    runs[2]["shots"] = 25
    with pytest.raises(ValueError, match="disagree"):
        benchmark.summarize(runs)


def test_worker_failures_are_not_silently_skipped(monkeypatch):
    monkeypatch.setattr(
        benchmark.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args, 1, "", "ffmpeg unavailable"),
    )
    with pytest.raises(
        RuntimeError,
        match="translation/mp4 failed.*",
    ):
        benchmark.run_worker("translation", "mp4", 12)


@pytest.mark.parametrize("value", ["0", "-1", "nan", "inf", "101"])
def test_invalid_frame_rates_are_rejected(value):
    with pytest.raises(argparse.ArgumentTypeError):
        benchmark.positive_fps(value)


def test_real_gif_measurement_and_three_process_command(tmp_path, capsys):
    measured = benchmark.measure_export("translation", "gif", 4)
    assert measured["shots"] == 8
    assert measured["output_bytes"] > 0
    assert measured["render_seconds"] > 0
    assert measured["encode_seconds"] > 0
    assert measured["total_seconds"] == pytest.approx(
        measured["render_seconds"] + measured["encode_seconds"]
    )
    assert measured["python_peak_rss_mib"] > 0
    output = tmp_path / "results.json"
    assert (
        benchmark.main(
            ["--scenes", "translation", "--formats", "gif", "--fps", "4", "--json", str(output)]
        )
        == 0
    )
    report = json.loads(output.read_text())
    assert report["runs_per_measurement"] == 3
    assert len(report["raw_runs"][0]["exports"]) == 3
    assert "Median of 3" in capsys.readouterr().out
    assert report["environment"]["cpu"]
    assert report["environment"]["pillow"]


@pytest.fixture
def manifest():
    return identity.capture(["translation"], 2)


def test_identity_gate_covers_entire_timeline_endpoint_and_still(manifest):
    scene = manifest["scenes"][0]
    assert [frame["time"] for frame in scene["frames"]] == [0, 0.5, 1, 1.5, 2]
    assert len(scene["stills"]) == 1
    assert identity.compare(manifest, copy.deepcopy(manifest)) == []


@pytest.mark.parametrize("field", ["frames", "stills"])
def test_identity_gate_fails_on_changed_pixel_digest(manifest, field):
    changed = copy.deepcopy(manifest)
    changed["scenes"][0][field][0]["sha256"] = "0" * 64
    assert identity.compare(manifest, changed) == [f"translation: {field} differs"]


def test_identity_gate_refuses_missing_frames_scenes_and_mismatched_environment(manifest):
    changed = copy.deepcopy(manifest)
    changed["scenes"][0]["frames"].pop()
    with pytest.raises(ValueError, match="incomplete"):
        identity.compare(manifest, changed)
    changed = copy.deepcopy(manifest)
    changed["scenes"] = []
    with pytest.raises(ValueError, match="must contain"):
        identity.compare(manifest, changed)
    changed = copy.deepcopy(manifest)
    changed["environment"]["pillow"] = "different"
    assert identity.compare(manifest, changed) == ["rendering environment differs: pillow"]


def test_identity_gate_refuses_changed_times_even_with_same_digests(manifest):
    changed = copy.deepcopy(manifest)
    changed["scenes"][0]["frames"][1]["time"] += 0.1
    with pytest.raises(ValueError, match="instants"):
        identity.compare(manifest, changed)


def test_identity_cli_round_trip_and_nonzero_failure(tmp_path, capsys):
    before, after = tmp_path / "before.json", tmp_path / "after.json"
    assert identity.main(["capture", str(before), "--scenes", "translation", "--fps", "2"]) == 0
    after.write_text(before.read_text())
    assert identity.main(["compare", str(before), str(after)]) == 0
    data = json.loads(after.read_text())
    data["scenes"][0]["frames"][0]["sha256"] = "0" * 64
    after.write_text(json.dumps(data))
    assert identity.main(["compare", str(before), str(after)]) == 1
    assert "translation: frames differs" in capsys.readouterr().err


@pytest.mark.parametrize(
    "corruption", ["timeline", "missing_slide", "duplicate_still", "fractional_dimension"]
)
def test_identity_gate_rejects_identically_malformed_manifests(manifest, corruption):
    scene = manifest["scenes"][0]
    if corruption == "timeline":
        scene["timeline"] = []
    elif corruption == "missing_slide":
        del scene["frames"][0]["slide"]
    elif corruption == "duplicate_still":
        scene["stills"].append(copy.deepcopy(scene["stills"][0]))
    else:
        scene["frames"][0]["width"] = 1.5
    with pytest.raises((ValueError, KeyError)):
        identity.compare(manifest, copy.deepcopy(manifest))
