"""Run with ``uv run python -m benchmarks.animated_export`` (three fresh runs)."""

from __future__ import annotations

import argparse
import json
import math
import os
import platform
import statistics
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable, Iterable, Iterator
from pathlib import Path
from typing import Any, Literal
from unittest.mock import patch

import PIL
from PIL import Image, ImageFont, features
from quickthumb import GifOptions, VideoOptions

from benchmarks.scenes import DURATION, SCENES, build_scene

ROOT = Path(__file__).resolve().parents[1]
FORMATS = ("gif", "mp4", "webm")
RUNS = 3


def positive_fps(value: str) -> float:
    fps = float(value)
    if not math.isfinite(fps) or not 0 < fps <= 100:
        raise argparse.ArgumentTypeError("fps must be finite and in (0, 100]")
    return fps


def environment() -> dict[str, Any]:
    """Record observable facts; CPU frequency and competing load still vary."""
    cpu = platform.processor() or platform.machine()
    if Path("/proc/cpuinfo").exists():
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                cpu = line.partition(":")[2].strip()
                break
    ffmpeg = os.environ.get("QUICKTHUMB_FFMPEG", "ffmpeg")
    try:
        version = subprocess.run(
            [ffmpeg, "-version"], capture_output=True, text=True, check=True
        ).stdout.splitlines()[0]
    except (OSError, subprocess.CalledProcessError, IndexError):
        version = "unavailable"
    git = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=False
    )
    return {
        "cpu": cpu,
        "logical_cpus": os.cpu_count(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "pillow": PIL.__version__,
        "freetype": features.version("freetype2"),
        "text_layout": "raqm" if features.check("raqm") else "basic",
        "ffmpeg": version,
        "commit": git.stdout.strip() if git.returncode == 0 else "unknown",
    }


def centroid(image: Image.Image) -> tuple[float, float]:
    """Intensity-weighted centroid of the white marker on an opaque black field."""
    gray = image.convert("L")
    weights = list(gray.get_flattened_data())
    mass = sum(weights)
    if mass == 0:
        raise ValueError("jitter scene has no visible marker")
    return (
        sum((i % gray.width) * value for i, value in enumerate(weights)) / mass,
        sum((i // gray.width) * value for i, value in enumerate(weights)) / mass,
    )


def displacement_jitter(points: list[tuple[float, float]]) -> float:
    """Population stddev of Euclidean displacement, in pixels per frame."""
    if len(points) < 3:
        raise ValueError("jitter requires at least three observations")
    steps = [math.dist(a, b) for a, b in zip(points, points[1:], strict=False)]
    return statistics.pstdev(steps)


def measure_jitter(scene: str) -> float | None:
    if scene == "product_hype_reel":
        return None
    # Independent fixed 30 fps probe; do not contaminate export timing/cache/RSS.
    frames = build_scene(scene).sample(time=[i / 30 for i in range(round(DURATION * 30))])
    return displacement_jitter([centroid(frame.to_image()) for frame in frames.frames])


class EncoderTimer:
    """Subtract lazy shot production from the existing encoder's wall time."""

    def __init__(self) -> None:
        self.shots = 0
        self.production_seconds = 0.0
        self.encode_seconds = 0.0

    def timed_shots(self, shots: Iterable[Any]) -> Iterator[Any]:
        iterator = iter(shots)
        while True:
            start = time.perf_counter()
            try:
                shot = next(iterator)
            except StopIteration:
                self.production_seconds += time.perf_counter() - start
                return
            self.production_seconds += time.perf_counter() - start
            self.shots += 1
            yield shot

    def wrap(self, encoder: Callable[..., Any]) -> Callable[..., Any]:
        def measured(shots: Iterable[Any], *args: Any, **kwargs: Any) -> Any:
            produced_before = self.production_seconds
            start = time.perf_counter()
            result = encoder(self.timed_shots(shots), *args, **kwargs)
            elapsed = time.perf_counter() - start
            self.encode_seconds += elapsed - (self.production_seconds - produced_before)
            return result

        return measured


def peak_rss_mib() -> float:
    """Peak resident memory of this isolated Python process, including native PIL."""
    try:
        import resource
    except ImportError as error:
        raise RuntimeError("RSS benchmarking requires Linux or macOS") from error
    usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return usage / (1024 * 1024 if sys.platform == "darwin" else 1024)


def measure_export(
    scene: str, format: str, fps: float, quality: Literal["standard", "high"] = "standard"
) -> dict[str, Any]:
    """Measure the real public export; no frames are pre-rendered or held here."""
    from quickthumb import _export_video

    timer = EncoderTimer()
    font_loads = 0
    font_seconds = 0.0
    getfont = ImageFont.core.getfont

    def load_font(*args: Any, **kwargs: Any) -> Any:
        nonlocal font_loads, font_seconds
        start = time.perf_counter()
        try:
            font = getfont(*args, **kwargs)
        finally:
            font_seconds += time.perf_counter() - start
        font_loads += 1  # Successful native loads, excluding failed family probes.
        return font

    with tempfile.TemporaryDirectory(prefix="quickthumb-benchmark-") as directory:
        output = Path(directory) / f"result.{format}"
        with (
            patch.object(_export_video, "_encode_gif", timer.wrap(_export_video._encode_gif)),
            patch.object(
                _export_video, "_encode_video_file", timer.wrap(_export_video._encode_video_file)
            ),
            patch.object(ImageFont.core, "getfont", load_font),
        ):
            start = time.perf_counter()
            deck = build_scene(scene)
            options = (
                GifOptions(fps=fps, max_size=(432, 768), colors=64, quality=quality)
                if format == "gif"
                else VideoOptions(fps=fps, quality=quality)
            )
            deck.render(str(output), animation=options)
            total = time.perf_counter() - start
        if timer.shots == 0 or not output.is_file() or output.stat().st_size == 0:
            raise RuntimeError("export produced no measured shots or output")
        return {
            "scene": scene,
            "format": format,
            "quality": quality,
            "shots": timer.shots,
            "render_ms_per_shot": (total - timer.encode_seconds) * 1000 / timer.shots,
            "render_seconds": total - timer.encode_seconds,
            "encode_seconds": timer.encode_seconds,
            "total_seconds": total,
            "python_peak_rss_mib": peak_rss_mib(),
            "font_loads": font_loads,
            "font_seconds": font_seconds,
            "output_bytes": output.stat().st_size,
        }


def summarize(runs: list[dict[str, Any]]) -> dict[str, Any]:
    if len(runs) != RUNS:
        raise ValueError("each measurement requires exactly three runs")
    if (
        len(
            {
                (run["scene"], run["format"], run["shots"], run.get("quality", "standard"))
                for run in runs
            }
        )
        != 1
    ):
        raise ValueError("repeated runs disagree on scene, format, quality, or shot count")
    result = {key: runs[0][key] for key in ("scene", "format")}
    result["quality"] = runs[0].get("quality", "standard")
    for key, value in runs[0].items():
        if isinstance(value, (int, float)):
            result[key] = statistics.median(run[key] for run in runs)
    return result


def run_worker(
    scene: str, format: str, fps: float, quality: Literal["standard", "high"] = "standard"
) -> dict[str, Any]:
    process = subprocess.run(
        [
            sys.executable,
            "-m",
            "benchmarks.animated_export",
            "--worker",
            scene,
            format,
            "--fps",
            str(fps),
            "--quality",
            quality,
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if process.returncode:
        raise RuntimeError(f"{scene}/{format} failed:\n{process.stderr or process.stdout}")
    return json.loads(process.stdout)


def print_table(report: dict[str, Any]) -> None:
    print("Environment: " + json.dumps(report["environment"], sort_keys=True))
    print(
        f"Median of 3 fresh processes; export fps={report['fps']}; "
        f"quality={report.get('quality', 'standard')}"
    )
    print("Jitter: 30 fps standard canonical sample; not measured for high quality")
    print(
        "Scene             Format  Shots  Render ms/shot  Encode s  Total s  Python RSS MiB  "
        "Font loads  Font s  Jitter px/frame"
    )
    for row in report["results"]:
        jitter = row["jitter_px_per_frame"]
        jitter_text = "n/a" if jitter is None else f"{jitter:.6f}"
        print(
            f"{row['scene']:17} {row['format']:6} {row['shots']:5g} "
            f"{row['render_ms_per_shot']:15.3f} {row['encode_seconds']:9.3f} "
            f"{row['total_seconds']:8.3f} {row['python_peak_rss_mib']:15.1f} "
            f"{row['font_loads']:11g} {row['font_seconds']:7.3f} {jitter_text:>15}"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fps", type=positive_fps, default=12.0)
    parser.add_argument("--quality", choices=("standard", "high"), default="standard")
    parser.add_argument("--scenes", nargs="+", choices=SCENES, default=list(SCENES))
    parser.add_argument("--formats", nargs="+", choices=FORMATS, default=list(FORMATS))
    parser.add_argument("--json", type=Path, help="also save raw runs and medians")
    parser.add_argument("--worker", nargs=2, metavar=("SCENE", "FORMAT"), help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        if args.worker:
            scene, format = args.worker
            if scene not in SCENES or format not in (*FORMATS, "jitter"):
                raise ValueError("unknown worker scene or format")
            result = (
                {"jitter": measure_jitter(scene)}
                if format == "jitter"
                else measure_export(scene, format, args.fps, args.quality)
            )
            print(json.dumps(result))
            return 0
        report: dict[str, Any] = {
            "version": 1,
            "environment": environment(),
            "fps": args.fps,
            "quality": args.quality,
            "runs_per_measurement": RUNS,
            "results": [],
            "raw_runs": [],
        }
        for scene in dict.fromkeys(args.scenes):
            jitters = (
                [run_worker(scene, "jitter", args.fps)["jitter"] for _ in range(RUNS)]
                if args.quality == "standard"
                else [None] * RUNS
            )
            for format in dict.fromkeys(args.formats):
                print(f"Measuring {scene}/{format} (3 fresh processes)...", file=sys.stderr)
                runs = [run_worker(scene, format, args.fps, args.quality) for _ in range(RUNS)]
                row = summarize(runs)
                row["jitter_px_per_frame"] = (
                    None if jitters[0] is None else statistics.median(jitters)
                )
                report["raw_runs"].append(
                    {"scene": scene, "format": format, "exports": runs, "jitter": jitters}
                )
                report["results"].append(row)
        print_table(report)
        if args.json:
            args.json.write_text(json.dumps(report, indent=2) + "\n")
        return 0
    except (OSError, RuntimeError, ValueError) as error:
        print(f"benchmark failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
