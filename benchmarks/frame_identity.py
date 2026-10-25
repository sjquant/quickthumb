"""Capture/compare canonical public Deck.sample() frame digests, without PNGs."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

from benchmarks.animated_export import ROOT, environment, positive_fps
from benchmarks.scenes import SCENES, build_scene

# Keep full-resolution reel captures below the public capture-memory budget.
BATCH_SIZE = 8


def capture_scene(name: str, fps: float) -> dict[str, Any]:
    deck = build_scene(name)
    spec = deck.to_json().replace(str(ROOT), "<repo>")
    initial = deck.sample(time=0.0)
    count = max(1, math.ceil(initial.duration * fps - 1e-9))
    times = [i / fps for i in range(count)] + [initial.duration]
    frames = []
    for offset in range(0, len(times), BATCH_SIZE):
        sequence = deck.sample(time=times[offset : offset + BATCH_SIZE])
        frames.extend(
            {
                "time": frame.time,
                "slide": frame.slide,
                "width": frame.width,
                "height": frame.height,
                "sha256": frame.sha256,
            }
            for frame in sequence.frames
        )
    stills = deck.sample()
    return {
        "scene": name,
        "spec_sha256": hashlib.sha256(spec.encode()).hexdigest(),
        "duration": initial.duration,
        "timeline": [segment.model_dump() for segment in initial.timeline],
        "frames": frames,
        "stills": [
            {
                "slide": frame.slide,
                "width": frame.width,
                "height": frame.height,
                "sha256": frame.sha256,
            }
            for frame in stills.frames
        ],
    }


def capture(names: list[str], fps: float) -> dict[str, Any]:
    return {
        "version": 1,
        "fps": fps,
        "environment": environment(),
        "scenes": [capture_scene(name, fps) for name in dict.fromkeys(names)],
    }


def validate_manifest(manifest: dict[str, Any]) -> None:
    if manifest.get("version") != 1:
        raise ValueError("unsupported identity manifest version")
    fps = manifest.get("fps")
    if isinstance(fps, bool) or not isinstance(fps, (int, float)) or not 0 < fps <= 100:
        raise ValueError("invalid identity manifest fps")
    scenes = manifest.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise ValueError("identity manifest must contain scenes")
    if len({scene["scene"] for scene in scenes}) != len(scenes):
        raise ValueError("duplicate identity scenes")
    for scene in scenes:
        if scene["scene"] not in SCENES:
            raise ValueError("unknown identity scene")
        duration = scene["duration"]
        if not math.isfinite(duration) or duration < 0:
            raise ValueError("invalid identity duration")
        timeline = scene["timeline"]
        if not isinstance(timeline, list) or not timeline:
            raise ValueError("identity timeline must contain segments")
        previous_end = 0.0
        for index, segment in enumerate(timeline):
            if type(segment["slide"]) is not int or segment["slide"] != index:
                raise ValueError("identity timeline must contain ordered slide indices")
            values = [
                segment[field] for field in ("start", "transition_end", "animation_end", "end")
            ]
            if any(
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                for value in values
            ):
                raise ValueError("invalid timeline segment times")
            start, transition_end, animation_end, end = values
            if (
                start != previous_end
                or not start <= transition_end <= end
                or not start <= animation_end <= end
            ):
                raise ValueError("invalid timeline segment boundaries")
            previous_end = end
        if previous_end != duration:
            raise ValueError("identity timeline duration differs")
        stills = scene["stills"]
        if [frame["slide"] for frame in stills] != list(range(len(timeline))):
            raise ValueError("identity capture needs one settled frame per slide")
        frames = scene["frames"]
        count = max(1, math.ceil(duration * fps - 1e-9))
        if len(frames) != count + 1 or not scene["stills"]:
            raise ValueError(f"{scene['scene']}: incomplete timeline or still frames")
        expected_times = [round(i / fps, 9) for i in range(count)] + [duration]
        if [round(frame["time"], 9) for frame in frames] != expected_times:
            raise ValueError(f"{scene['scene']}: changed or missing sample instants")
        for frame in [*frames, *scene["stills"]]:
            digest = frame["sha256"]
            if (
                type(frame["width"]) is not int
                or type(frame["height"]) is not int
                or type(frame["slide"]) is not int
                or frame["width"] <= 0
                or frame["height"] <= 0
                or not 0 <= frame["slide"] < len(timeline)
                or len(digest) != 64
                or any(character not in "0123456789abcdef" for character in digest)
            ):
                raise ValueError(f"{scene['scene']}: invalid frame metadata")


def compare(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    """Fail closed for incompatible captures as well as any differing frame."""
    validate_manifest(before)
    validate_manifest(after)
    failures = []
    if before["fps"] != after["fps"]:
        failures.append("sampling fps differs")
    for field in ("python", "pillow", "freetype", "text_layout", "ffmpeg", "platform"):
        if before["environment"][field] != after["environment"][field]:
            failures.append(f"rendering environment differs: {field}")
    if [scene["scene"] for scene in before["scenes"]] != [
        scene["scene"] for scene in after["scenes"]
    ]:
        failures.append("scene selection/order differs")
        return failures
    for old, new in zip(before["scenes"], after["scenes"], strict=True):
        for field in ("spec_sha256", "duration", "timeline", "frames", "stills"):
            if old[field] != new[field]:
                failures.append(f"{old['scene']}: {field} differs")
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    record = commands.add_parser("capture")
    record.add_argument("output", type=Path)
    record.add_argument("--fps", type=positive_fps, default=12.0)
    record.add_argument("--scenes", nargs="+", choices=SCENES, default=list(SCENES))
    diff = commands.add_parser("compare")
    diff.add_argument("before", type=Path)
    diff.add_argument("after", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "capture":
            result = capture(args.scenes, args.fps)
            validate_manifest(result)
            args.output.write_text(json.dumps(result, indent=2) + "\n")
            print(f"Captured {len(result['scenes'])} scenes to {args.output}")
        else:
            failures = compare(
                json.loads(args.before.read_text()), json.loads(args.after.read_text())
            )
            if failures:
                print("Identity check FAILED:\n" + "\n".join(failures), file=sys.stderr)
                return 1
            print("All canonical RGBA timeline and settled frames are byte-identical")
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"identity check failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
