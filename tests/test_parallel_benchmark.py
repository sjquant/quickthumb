"""Parallel benchmark protocol, concurrent RSS, and spawn-safe smoke coverage."""

import argparse
import json
import os
import sys

import pytest
from benchmarks import parallel_export as benchmark


def make_run(workers=1, seconds=1.0, format="gif", digest="a" * 64):
    return {
        "scene": "translation",
        "format": format,
        "fps": 12.0,
        "workers": workers,
        "shots": 24,
        "total_seconds": seconds,
        "output_bytes": 100,
        "output_sha256": digest,
        "rss_sample_interval_seconds": 0.05,
        **dict.fromkeys(benchmark.MEMORY_FIELDS, seconds),
    }


@pytest.mark.parametrize("workers", [1, 2, 4, 8])
def test_options_preserve_existing_full_workload(workers):
    gif = benchmark.export_options("gif", 12, workers)
    assert isinstance(gif, benchmark.GifOptions)
    assert gif.fps == 12
    assert gif.max_size == (432, 768)
    assert gif.colors == 64
    assert gif.workers == workers
    for format in ("mp4", "webm"):
        video = benchmark.export_options(format, 12, workers)
        assert video.fps == 12
        assert video.workers == workers
    with pytest.raises(ValueError, match="unknown export"):
        benchmark.export_options("png", 12, workers)


@pytest.mark.parametrize("value", ["0", "-1", "nan", "inf", "-inf"])
def test_invalid_sampling_intervals_rejected(value):
    with pytest.raises(argparse.ArgumentTypeError):
        benchmark.positive_interval(value)


@pytest.mark.parametrize("value", ["0", "-1"])
def test_invalid_repetition_counts_rejected(value):
    with pytest.raises(argparse.ArgumentTypeError):
        benchmark.positive_integer(value)


def test_read_proc_stat_handles_parentheses_disappearing_and_invalid_processes(tmp_path):
    directory = tmp_path / "123"
    directory.mkdir()
    # fields after the comm: state (3), ppid (4), ..., rss (24)
    fields = ["S", "12", *(["0"] * 19), "7"]
    (directory / "stat").write_text("123 (weird ) process) " + " ".join(fields))
    (tmp_path / "124").mkdir()  # Exited between directory listing and stat read.
    (tmp_path / "125").mkdir()
    (tmp_path / "125" / "stat").write_text("incomplete")
    (tmp_path / "self").mkdir()
    result = benchmark.read_processes(tmp_path)
    assert result == {
        123: benchmark.ProcessRSS(123, 12, "weird ) process", 7 * os.sysconf("SC_PAGE_SIZE"))
    }


def test_tree_follows_all_descendant_levels_without_siblings_or_cycles():
    process = benchmark.ProcessRSS
    processes = {
        5: process(5, 3, "ffmpeg", 40),
        4: process(4, 2, "python", 30),
        3: process(3, 2, "python", 20),
        2: process(2, 1, "python", 10),
        1: process(1, 0, "python", 500),
        6: process(6, 1, "unrelated", 1000),
    }
    assert {item.pid for item in benchmark.process_tree(2, processes)} == {2, 3, 4, 5}
    assert benchmark.process_tree(999, processes) == []
    processes[2] = process(2, 5, "python", 10)
    assert {item.pid for item in benchmark.process_tree(2, processes)} == {2, 3, 4, 5}


def test_concurrent_rss_buckets_include_helpers_and_separate_ffmpeg(monkeypatch):
    monkeypatch.setenv("QUICKTHUMB_FFMPEG", "/opt/custom-encoder")
    process = benchmark.ProcessRSS
    processes = {
        1: process(1, 0, "python3.12", 5 * benchmark.MIB),
        2: process(2, 1, "python3.12", 20 * benchmark.MIB),
        3: process(3, 2, "python3.12", 30 * benchmark.MIB),
        4: process(4, 2, "custom-encoder", 40 * benchmark.MIB),
        5: process(5, 2, "ffprobe", 10 * benchmark.MIB),
    }
    assert benchmark.sample_tree(1, processes) == {
        "python_tree_peak_rss_mib": 55,
        "ffmpeg_peak_rss_mib": 40,
        "other_children_peak_rss_mib": 10,
        "process_tree_peak_rss_mib": 105,
        "python_processes_max": 3,
    }


def test_summary_keeps_hashes_and_medians_without_requiring_three_runs():
    runs = [make_run(seconds=value) for value in (9.0, 1.0, 2.0)]
    summary = benchmark.summarize(runs)
    assert summary["total_seconds"] == 2
    assert summary["process_tree_peak_rss_mib"] == 2
    assert summary["output_sha256_values"] == ["a" * 64]
    assert summary["output_byte_identical"] is True
    assert summary["repetitions"] == 3
    assert benchmark.summarize(runs[:1])["repetitions"] == 1
    with pytest.raises(ValueError, match="at least one"):
        benchmark.summarize([])
    runs[2]["workers"] = 2
    with pytest.raises(ValueError, match="disagree"):
        benchmark.summarize(runs)


def test_output_identity_compares_worker_counts_and_does_not_require_webm_equality():
    runs = [make_run(workers=workers) for workers in (1, 2, 4)]
    identity = benchmark.output_identity(runs)
    assert identity[0]["workers"] == [1, 2, 4]
    assert identity[0]["output_byte_identical"] is True
    runs[2]["output_sha256"] = "b" * 64
    assert benchmark.output_identity(runs)[0]["output_byte_identical"] is False
    for run in runs:
        run["format"] = "webm"
    summary = benchmark.summarize([runs[0], {**runs[0], "output_sha256": "b" * 64}])
    assert summary["output_byte_identical"] is False
    assert summary["byte_identity_expected"] is False
    assert benchmark.output_identity(runs)[0]["byte_identity_expected"] is False


def test_default_protocol_and_rotating_run_order(monkeypatch, tmp_path):
    calls = []

    def worker(scene, format, fps, workers, sample_interval):
        calls.append((scene, format, fps, workers, sample_interval))
        return {**make_run(workers=workers, format=format), "scene": scene}

    monkeypatch.setattr(benchmark, "run_worker", worker)
    monkeypatch.setattr(benchmark, "environment", lambda: {"cpu": "test"})
    output = tmp_path / "report.json"
    assert benchmark.main(["--json", str(output)]) == 0
    assert len(calls) == 27
    assert all(call[0] == "product_hype_reel" and call[2] == 12 for call in calls)
    assert [call[3] for call in calls[:9]] == [1, 2, 4, 2, 4, 1, 4, 1, 2]
    report = json.loads(output.read_text())
    assert len(report["raw_runs"]) == 27
    assert len(report["results"]) == 9
    assert report["runs_per_measurement"] == 3
    assert report["rss_sample_interval_seconds"] == 0.05
    assert "shared pages" in report["protocol"]["rss_method"]


def test_export_error_fails_command_instead_of_skipping_row(monkeypatch, capsys):
    def fail(*args):
        raise RuntimeError("render worker failed")

    monkeypatch.setattr(benchmark, "environment", lambda: {})
    monkeypatch.setattr(benchmark, "run_worker", fail)
    assert benchmark.main(["--scenes", "translation", "--formats", "gif"]) == 1
    assert "render worker failed" in capsys.readouterr().err


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux /proc RSS sampling")
def test_fresh_spawn_exports_have_equal_hashes_and_report_worker_memory():
    serial = benchmark.run_worker("translation", "gif", 2, 1, 0.01)
    parallel = benchmark.run_worker("translation", "gif", 2, 2, 0.01)
    assert serial["output_sha256"] == parallel["output_sha256"]
    assert serial["output_bytes"] == parallel["output_bytes"] > 0
    for result in (serial, parallel):
        assert result["shots"] == 4
        assert result["total_seconds"] > 0
        assert result["subprocess_seconds"] > result["total_seconds"]
        assert result["python_tree_peak_rss_mib"] > 0
        assert result["process_tree_peak_rss_mib"] >= result["python_tree_peak_rss_mib"]
        assert result["rss_sample_count"] > 1
        assert result["rss_max_sample_gap_seconds"] > 0
    assert serial["python_processes_max"] == 1
    # Export parent + both actual render workers + the spawn resource tracker.
    # RUSAGE_SELF can retain a large pre-exec watermark from the pytest parent,
    # so it cannot establish whether child memory was included in these samples.
    assert parallel["python_processes_max"] >= parallel["workers"] + 2


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux /proc RSS sampling")
def test_failed_fresh_subprocess_reports_diagnostic():
    with pytest.raises(RuntimeError, match="unknown worker scene"):
        benchmark.run_worker("missing", "gif", 2, 2, 0.01)


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux /proc RSS sampling")
def test_high_inherited_parent_lifetime_rss_is_only_a_diagnostic(monkeypatch):
    class Process:
        pid = 123
        returncode = 0

        def __init__(self, command, *, stdout, **kwargs):
            record = make_run(workers=2)
            record["parent_lifetime_peak_rss_mib"] = 1000.0
            stdout.write(json.dumps(record))

        def poll(self):
            return self.returncode

    process = benchmark.ProcessRSS
    monkeypatch.setattr(benchmark.subprocess, "Popen", Process)
    monkeypatch.setattr(
        benchmark,
        "read_processes",
        lambda: {
            123: process(123, 0, "python", 10 * benchmark.MIB),
            124: process(124, 123, "python", 20 * benchmark.MIB),
            125: process(125, 123, "python", 30 * benchmark.MIB),
            126: process(126, 123, "python", 5 * benchmark.MIB),
        },
    )
    result = benchmark.run_worker("translation", "gif", 12, 2, 0.05)
    assert result["parent_lifetime_peak_rss_mib"] == 1000
    assert result["python_tree_peak_rss_mib"] == 65
    assert result["process_tree_peak_rss_mib"] == 65
    assert result["python_processes_max"] == 4


def test_non_linux_memory_benchmark_fails_explicitly(monkeypatch):
    monkeypatch.setattr(benchmark.sys, "platform", "darwin")
    with pytest.raises(RuntimeError, match="requires Linux"):
        benchmark.run_worker("translation", "gif", 2, 1, 0.01)
