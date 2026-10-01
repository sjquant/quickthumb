"""Compare worker counts with fresh exports and sampled Linux process-tree RSS.

Run ``uv run --locked python -m benchmarks.parallel_export --json /tmp/parallel.json``.
The defaults measure the complete product reel at 12 fps with workers 1/2/4 and
three fresh subprocesses per case. GIF uses 432x768 / 64 colors; video keeps the
original 1080x1920 canvas and narration. No additional dependencies are needed.

Run on a quiet machine. Process-local caches start cold; filesystem caches are
not flushed. Worker order rotates between repetitions to reduce order effects.
Export wall time includes scene construction and public Deck.render(), but not
interpreter startup or output hashing. Subprocess wall time includes both.

RSS is sampled from /proc throughout each subprocess's lifetime, nominally every
50 ms. Each observation sums concurrent RSS, including native Pillow memory.
Shared pages are counted once per process, so this is neither unique physical
memory nor PSS. Sampling can miss short-lived processes and between-sample peaks.
Python includes the export parent, render workers, and multiprocessing helpers;
FFmpeg is reported separately, and ffprobe/other children have their own bucket.
Category peaks need not coincide and must not be added to obtain the total peak.
The maximum observed Python process count is recorded alongside sampled RSS.
The separate parent_lifetime_peak_rss_mib diagnostic excludes descendants and may
retain an inherited pre-exec high-water mark; do not compare it with sampled RSS.

SHA-256 and output size are retained for every run. Byte equality is reported
within and across worker counts. WebM metadata can vary, so its container hash
is diagnostic only; no hash mismatch changes the command's exit status. Export
failures do. Pixel/codec identity still needs the dedicated regression gates.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import signal
import statistics
import subprocess
import sys
import tempfile
import time
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from unittest.mock import patch

from quickthumb import GifOptions, VideoOptions

from benchmarks.animated_export import (
    FORMATS,
    ROOT,
    RUNS,
    EncoderTimer,
    environment,
    peak_rss_mib,
    positive_fps,
)
from benchmarks.scenes import SCENES, build_scene

MIB = 1024 * 1024
DEFAULT_SAMPLE_INTERVAL = 0.05
MEMORY_FIELDS = (
    "python_tree_peak_rss_mib",
    "ffmpeg_peak_rss_mib",
    "other_children_peak_rss_mib",
    "process_tree_peak_rss_mib",
)


def positive_integer(value: str) -> int:
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("repetitions must be positive")
    return number


def positive_interval(value: str) -> float:
    interval = float(value)
    if not math.isfinite(interval) or interval <= 0:
        raise argparse.ArgumentTypeError("sample interval must be finite and positive")
    return interval


def export_options(format: str, fps: float, workers: int) -> GifOptions | VideoOptions:
    if format == "gif":
        return GifOptions(fps=fps, max_size=(432, 768), colors=64, workers=workers)
    if format in ("mp4", "webm"):
        return VideoOptions(fps=fps, workers=workers)
    raise ValueError(f"unknown export format: {format}")


@dataclass(frozen=True)
class ProcessRSS:
    pid: int
    ppid: int
    name: str
    rss_bytes: int


def read_processes(proc: Path = Path("/proc")) -> dict[int, ProcessRSS]:
    """Read each process once; tolerate processes exiting during the observation."""
    pagesize = os.sysconf("SC_PAGE_SIZE")
    result = {}
    for directory in proc.iterdir():
        if not directory.name.isdigit():
            continue
        try:
            stat = (directory / "stat").read_text()
            # Linux comm is parenthesized and may itself contain spaces or ')'.
            start, end = stat.index("("), stat.rindex(")")
            fields = stat[end + 1 :].split()
            pid = int(directory.name)
            result[pid] = ProcessRSS(
                pid=pid,
                ppid=int(fields[1]),  # /proc/PID/stat field 4
                name=stat[start + 1 : end],
                rss_bytes=max(0, int(fields[21])) * pagesize,  # field 24
            )
        except (OSError, ValueError, IndexError):
            continue
    return result


def process_tree(root: int, processes: Mapping[int, ProcessRSS]) -> list[ProcessRSS]:
    """Return only the export subprocess and its currently observed descendants."""
    children: dict[int, list[int]] = defaultdict(list)
    for process in processes.values():
        children[process.ppid].append(process.pid)
    pending = [root]
    seen = set()
    result = []
    while pending:
        pid = pending.pop()
        if pid in seen:
            continue
        seen.add(pid)
        if pid in processes:
            result.append(processes[pid])
        pending.extend(children.get(pid, ()))
    return result


def sample_tree(root: int, processes: Mapping[int, ProcessRSS]) -> dict[str, float]:
    """Sum simultaneously observed RSS, rather than adding per-process peaks."""
    totals = dict.fromkeys(MEMORY_FIELDS, 0.0)
    totals["python_processes_max"] = 0
    python_names = {"python", "python3", Path(sys.executable).name[:15]}
    ffmpeg_names = {"ffmpeg", Path(os.environ.get("QUICKTHUMB_FFMPEG", "ffmpeg")).name[:15]}
    for process in process_tree(root, processes):
        if process.pid == root or process.name.startswith("python") or process.name in python_names:
            bucket = "python_tree_peak_rss_mib"
            totals["python_processes_max"] += 1
        elif process.name in ffmpeg_names:
            bucket = "ffmpeg_peak_rss_mib"
        else:
            bucket = "other_children_peak_rss_mib"
        value = process.rss_bytes / MIB
        totals[bucket] += value
        totals["process_tree_peak_rss_mib"] += value
    return totals


def measure_export(scene: str, format: str, fps: float, workers: int) -> dict[str, Any]:
    """Same public export/options/corpus as animated_export, with a worker count."""
    from quickthumb import _export_video

    options = export_options(format, fps, workers)
    timer = EncoderTimer()
    with tempfile.TemporaryDirectory(prefix="quickthumb-parallel-") as directory:
        output = Path(directory) / f"result.{format}"
        with (
            patch.object(_export_video, "_encode_gif", timer.wrap(_export_video._encode_gif)),
            patch.object(
                _export_video, "_encode_video_file", timer.wrap(_export_video._encode_video_file)
            ),
        ):
            start = time.perf_counter()
            deck = build_scene(scene)
            deck.render(str(output), animation=options)
            elapsed = time.perf_counter() - start
        if timer.shots == 0 or not output.is_file() or output.stat().st_size == 0:
            raise RuntimeError("export produced no measured shots or output")
        digest = hashlib.sha256()
        with output.open("rb") as stream:
            for chunk in iter(lambda: stream.read(MIB), b""):
                digest.update(chunk)
        return {
            "scene": scene,
            "format": format,
            "fps": fps,
            "workers": workers,
            "shots": timer.shots,
            "total_seconds": elapsed,
            "parent_lifetime_peak_rss_mib": peak_rss_mib(),
            "output_bytes": output.stat().st_size,
            "output_sha256": digest.hexdigest(),
        }


def run_worker(
    scene: str, format: str, fps: float, workers: int, sample_interval: float
) -> dict[str, Any]:
    """Spawn a guarded module; the supervisor stays outside the measured tree."""
    if not sys.platform.startswith("linux") or not Path("/proc/self/stat").is_file():
        raise RuntimeError("process-tree RSS benchmarking requires Linux /proc")
    command = [
        sys.executable,
        "-m",
        "benchmarks.parallel_export",
        "--worker",
        scene,
        format,
        str(workers),
        "--fps",
        str(fps),
    ]
    peaks = dict.fromkeys((*MEMORY_FIELDS, "python_processes_max"), 0.0)
    sample_count = 0
    max_gap = 0.0
    previous_sample = None
    start = time.perf_counter()
    # Files cannot fill up like pipes while the supervisor samples memory.
    with tempfile.TemporaryFile(mode="w+t") as stdout, tempfile.TemporaryFile(mode="w+t") as stderr:
        process = subprocess.Popen(
            command, cwd=ROOT, stdout=stdout, stderr=stderr, text=True, start_new_session=True
        )
        try:
            while True:
                sampled_at = time.perf_counter()
                if previous_sample is not None:
                    max_gap = max(max_gap, sampled_at - previous_sample)
                previous_sample = sampled_at
                sample = sample_tree(process.pid, read_processes())
                for field, value in sample.items():
                    peaks[field] = max(peaks[field], value)
                sample_count += 1
                if process.poll() is not None:
                    break
                time.sleep(max(0, sample_interval - (time.perf_counter() - sampled_at)))
        except BaseException:
            # Own session only: don't leave rendering/FFmpeg children on Ctrl-C.
            try:
                os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=10)
            except ProcessLookupError:
                process.wait()
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            raise
        elapsed = time.perf_counter() - start
        stdout.seek(0)
        stderr.seek(0)
        output, diagnostic = stdout.read(), stderr.read()
    if process.returncode:
        raise RuntimeError(f"{scene}/{format}/workers={workers} failed:\n{diagnostic or output}")
    result = json.loads(output)
    if not peaks["python_tree_peak_rss_mib"]:
        raise RuntimeError("no Python RSS observed; check /proc access and sampling interval")
    result.update(peaks)
    result.update(
        subprocess_seconds=elapsed,
        rss_sample_count=sample_count,
        rss_sample_interval_seconds=sample_interval,
        rss_max_sample_gap_seconds=max_gap,
    )
    return result


def summarize(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Report independent medians; output hashes are never numerically summarized."""
    identity = ("scene", "format", "fps", "workers", "shots", "rss_sample_interval_seconds")
    if not runs:
        raise ValueError("a summary requires at least one run")
    if len({tuple(run[key] for key in identity) for run in runs}) != 1:
        raise ValueError("repeated runs disagree on scene, format, options, or shot count")
    result = {key: runs[0][key] for key in identity}
    for key, value in runs[0].items():
        if key not in (*identity, "repetition") and type(value) in (int, float):
            result[key] = statistics.median(run[key] for run in runs)
    hashes = sorted({run["output_sha256"] for run in runs})
    result.update(
        repetitions=len(runs),
        output_sha256_values=hashes,
        output_byte_identical=len(hashes) == 1,
        byte_identity_expected=runs[0]["format"] != "webm",
    )
    return result


def output_identity(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Compare all repetitions and worker settings, without asserting WebM equality."""
    groups: dict[tuple[str, str, float], list[dict[str, Any]]] = defaultdict(list)
    for run in runs:
        groups[(run["scene"], run["format"], run["fps"])].append(run)
    return [
        {
            "scene": scene,
            "format": format,
            "fps": fps,
            "workers": sorted({run["workers"] for run in group}),
            "byte_identity_expected": format != "webm",
            "output_byte_identical": len({run["output_sha256"] for run in group}) == 1,
            "output_sha256_values": sorted({run["output_sha256"] for run in group}),
        }
        for (scene, format, fps), group in groups.items()
    ]


def print_table(report: dict[str, Any]) -> None:
    print("Environment: " + json.dumps(report["environment"], sort_keys=True))
    print(
        f"Median of {report['runs_per_measurement']} fresh processes; fps={report['fps']}; "
        f"RSS sampled every {report['rss_sample_interval_seconds']:g}s (sum of RSS, "
        "shared pages counted per process)"
    )
    print("Scene             Format Workers Total s Python MiB FFmpeg MiB Other MiB Tree MiB")
    for row in report["results"]:
        print(
            f"{row['scene']:17} {row['format']:6} {row['workers']:7d} "
            f"{row['total_seconds']:7.3f} {row['python_tree_peak_rss_mib']:10.1f} "
            f"{row['ffmpeg_peak_rss_mib']:10.1f} {row['other_children_peak_rss_mib']:9.1f} "
            f"{row['process_tree_peak_rss_mib']:8.1f}"
        )
    for item in report["output_identity"]:
        match = "identical" if item["output_byte_identical"] else "different"
        qualifier = " (WebM metadata may vary)" if item["format"] == "webm" else ""
        print(f"{item['scene']}/{item['format']}: output hashes {match}{qualifier}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fps", type=positive_fps, default=12.0)
    parser.add_argument("--scenes", nargs="+", choices=SCENES, default=["product_hype_reel"])
    parser.add_argument("--formats", nargs="+", choices=FORMATS, default=list(FORMATS))
    parser.add_argument("--workers", nargs="+", type=int, choices=range(1, 9), default=[1, 2, 4])
    parser.add_argument("--repetitions", type=positive_integer, default=RUNS)
    parser.add_argument(
        "--sample-interval", type=positive_interval, default=DEFAULT_SAMPLE_INTERVAL
    )
    parser.add_argument("--json", type=Path, help="also save raw runs and medians")
    parser.add_argument(
        "--worker", nargs=3, metavar=("SCENE", "FORMAT", "WORKERS"), help=argparse.SUPPRESS
    )
    args = parser.parse_args(argv)
    try:
        if args.worker:
            scene, format, workers = args.worker
            if scene not in SCENES or format not in FORMATS:
                raise ValueError("unknown worker scene or format")
            print(json.dumps(measure_export(scene, format, args.fps, int(workers))))
            return 0
        selected_workers = list(dict.fromkeys(args.workers))
        report: dict[str, Any] = {
            "version": 1,
            "environment": environment(),
            "fps": args.fps,
            "workers": selected_workers,
            "runs_per_measurement": args.repetitions,
            "rss_sample_interval_seconds": args.sample_interval,
            "protocol": {
                "corpus": "benchmarks.scenes.build_scene, unchanged full scenes",
                "gif_max_size": [432, 768],
                "gif_colors": 64,
                "video_size": "original scene dimensions (product reel: 1080x1920)",
                "audio": "original scene narration; no added soundtrack",
                "total_seconds": "scene construction plus public export; excludes imports/hash",
                "subprocess_seconds": "lifetime including imports/hash and exit-poll delay",
                "rss_scope": "subprocess lifetime; supervisor excluded",
                "rss_method": "sampled concurrent sum of RSS; shared pages counted per process",
                "rss_limitations": (
                    "not PSS; short processes and between-sample peaks may be missed"
                ),
                "rss_categories": "Linux comm: Python tree, FFmpeg, other children",
                "python_processes_max": "maximum observed Python parent/workers/helpers count",
                "parent_lifetime_peak_rss_mib": (
                    "diagnostic only; excludes descendants; "
                    "may inherit a pre-exec high-water mark; not comparable to sampled RSS"
                ),
                "rss_peak_warning": "category peaks may not coincide; do not add them",
                "cache_state": "fresh process caches; filesystem caches not flushed",
                "run_order": "sequential; worker order rotates each repetition",
                "hash_policy": "observational; WebM metadata may vary; no byte-identity exit gate",
            },
            "raw_runs": [],
            "results": [],
        }
        for scene in dict.fromkeys(args.scenes):
            for format in dict.fromkeys(args.formats):
                groups = {workers: [] for workers in selected_workers}
                for repetition in range(args.repetitions):
                    offset = repetition % len(selected_workers)
                    order = selected_workers[offset:] + selected_workers[:offset]
                    for workers in order:
                        print(
                            f"Measuring {scene}/{format}, workers={workers}, "
                            f"run {repetition + 1}/{args.repetitions}...",
                            file=sys.stderr,
                        )
                        run = run_worker(scene, format, args.fps, workers, args.sample_interval)
                        run["repetition"] = repetition + 1
                        groups[workers].append(run)
                        report["raw_runs"].append(run)
                report["results"].extend(summarize(runs) for runs in groups.values())
        report["output_identity"] = output_identity(report["raw_runs"])
        print_table(report)
        if args.json:
            args.json.write_text(json.dumps(report, indent=2) + "\n")
        return 0
    except (OSError, RuntimeError, ValueError) as error:
        print(f"benchmark failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
