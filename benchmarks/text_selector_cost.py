"""Record word/line/character cost using the existing instrumented export worker."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from benchmarks.animated_export import ROOT, RUNS, environment, run_worker, summarize
from benchmarks.scenes import (
    DURATION,
    TEXT_FONT,
    TEXT_SELECTOR_SCENES,
    TEXT_SELECTOR_TARGETS,
    build_scene,
    build_text_selector_scene,
)

FPS = 12


def canonical_check(name: str) -> dict:
    """Untimed correctness probe, never run in a measured export process."""
    times = [index / FPS for index in range(round(DURATION * FPS))] + [DURATION]
    source = build_scene(name)
    source_json = source.to_json()
    sequence = source.sample(time=times)
    frames = sequence.frames
    rest = build_text_selector_scene(name, rest=True).sample(time=DURATION).frames[0]
    if len(frames) != len(times) or sequence.duration != DURATION:
        raise RuntimeError(f"{name}: incomplete canonical timeline")
    if any(
        (frame.width, frame.height, frame.time) != (480, 240, time)
        for frame, time in zip(frames, times, strict=True)
    ):
        raise RuntimeError(f"{name}: changed canonical extent or sample clock")
    if frames[-1].sha256 != rest.sha256 or frames[FPS].sha256 == rest.sha256:
        raise RuntimeError(f"{name}: missing motion or shifted settled layout")
    layer = source.inspect_motion(target="video", fps=FPS).slides[0].layers[1]
    return {
        "scene": name,
        "source": json.loads(source_json),
        "source_sha256": hashlib.sha256(source_json.encode()).hexdigest(),
        "target_count": len(layer.targets),
        "motion_duration": layer.duration,
        "duration": sequence.duration,
        "frames": [{"time": frame.time, "sha256": frame.sha256} for frame in frames],
        "rest_sha256": rest.sha256,
        "environment": sequence.environment.model_dump(mode="json"),
    }


def run_check(name: str) -> dict:
    process = subprocess.run(
        [sys.executable, "-m", "benchmarks.text_selector_cost", "--check", name],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if process.returncode:
        raise RuntimeError(process.stderr or process.stdout)
    return json.loads(process.stdout)


def measure(report: dict, save) -> None:
    """Keep every attempted run; fail rather than retrying or dropping a failure."""
    checks = {}
    for name in TEXT_SELECTOR_SCENES:
        observed = []
        report["canonical_checks"].append(observed)
        for _ in range(2):
            observed.append(run_check(name))
            save()
        if observed[0] != observed[1]:
            raise RuntimeError(
                f"{name}: canonical frames/environment differ across fresh processes"
            )
        checks[name] = observed[0]
    # These cases intentionally produce different motion. Never call this a speedup.
    for target in TEXT_SELECTOR_TARGETS:
        digests = {
            tuple(frame["sha256"] for frame in checks[f"text_{target}_{mode}"]["frames"])
            for mode in ("baseline", "static", "animated")
        }
        if len(digests) != 3:
            raise RuntimeError(f"{target}: selector workloads did not produce distinct motion")
    for repetition in range(RUNS + 1):
        order = TEXT_SELECTOR_SCENES[repetition:] + TEXT_SELECTOR_SCENES[:repetition]
        for name in order:
            attempt = {
                "scene": name,
                "phase": "warmup" if repetition == 0 else "measured",
                "repetition": repetition,
            }
            report["attempts"].append(attempt)
            try:
                attempt["result"] = run_worker(name, "gif", FPS)
            except (OSError, RuntimeError, ValueError) as error:
                attempt["error"] = str(error)
                save()
                raise
            save()
    for name in TEXT_SELECTOR_SCENES:
        runs = [
            attempt["result"]
            for attempt in report["attempts"]
            if attempt["scene"] == name and attempt["phase"] == "measured"
        ]
        if len({run["output_sha256"] for run in runs}) != 1:
            raise RuntimeError(f"{name}: repeated GIF bytes differ")
        row = summarize(runs)
        row["render_ms_per_shot_min"] = min(run["render_ms_per_shot"] for run in runs)
        row["render_ms_per_shot_max"] = max(run["render_ms_per_shot"] for run in runs)
        report["results"].append(row)
    report["status"] = "complete"
    save()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path)
    parser.add_argument("--check", choices=TEXT_SELECTOR_SCENES, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.check:
        print(json.dumps(canonical_check(args.check)))
        return 0
    if args.json is None:
        parser.error("--json is required to preserve raw attempts")
    report: dict[str, Any] = {
        "version": 1,
        "measurement": "instrumented export cost; different motion, no optimization claim",
        "environment": environment(),
        "font": {
            "path": str(TEXT_FONT.relative_to(ROOT)),
            "sha256": hashlib.sha256(TEXT_FONT.read_bytes()).hexdigest(),
        },
        "source_sha256": {
            name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in (
                "benchmarks/scenes.py",
                "benchmarks/animated_export.py",
                "benchmarks/text_selector_cost.py",
                "quickthumb/motion.py",
                "quickthumb/models/motion.py",
                "quickthumb/_text_targets.py",
                "quickthumb/_text.py",
                "quickthumb/_fonts.py",
                "quickthumb/_export_base.py",
                "quickthumb/_export_video.py",
            )
        },
        "workload": {
            "width": 480,
            "height": 240,
            "duration": DURATION,
            "fps": FPS,
            "workers": 1,
            "quality": "standard",
            "format": "gif",
            "max_size": [432, 768],
            "colors": 64,
        },
        "cache_policy": (
            "fresh process per run; one discarded fresh-process warmup per condition; "
            "filesystem caches not flushed"
        ),
        "order": "warmup in scene order, then left rotation by repetition (1, 2, 3)",
        "status": "incomplete",
        "canonical_checks": [],
        "attempts": [],
        "results": [],
    }

    def save():
        args.json.write_text(json.dumps(report, indent=2) + "\n")

    save()
    try:
        measure(report, save)
    except (OSError, RuntimeError, ValueError) as error:
        report["error"] = str(error)
        save()
        print(f"selector benchmark failed: {error}", file=sys.stderr)
        return 1
    print("Environment: " + json.dumps(report["environment"], sort_keys=True))
    print(
        "Instrumented selector export cost (3 fresh runs, median [min..max]); no speed comparison"
    )
    print("Scene | Render ms/input [range] | Encode s | Total s [range] | Python RSS MiB | Inputs")
    for row in report["results"]:
        print(
            f"{row['scene']} | {row['render_ms_per_shot']:.3f} "
            f"[{row['render_ms_per_shot_min']:.3f}..{row['render_ms_per_shot_max']:.3f}] | "
            f"{row['encode_seconds']:.4f} | "
            f"{row['total_seconds']:.4f} "
            f"[{row['total_seconds_min']:.4f}..{row['total_seconds_max']:.4f}] | "
            f"{row['python_peak_rss_mib']:.1f} | {row['shots']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
