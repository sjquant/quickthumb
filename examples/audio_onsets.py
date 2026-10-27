"""Bake a source-audio onset into ordinary motion, keeping a reusable analysis sidecar.

Run: uv run python examples/audio_onsets.py music.wav output-directory
Requires FFmpeg for analysis and video export; no analysis dependency is added.
"""

import argparse
from pathlib import Path

from quickthumb import (
    AnimationSpec,
    AudioTrack,
    Canvas,
    ColorTrack,
    KeyframeSpec,
    TimingSpec,
    VideoOptions,
)
from quickthumb.audio import analyze_audio


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    analysis = analyze_audio(args.source)
    if not analysis.onsets:
        parser.error("No transient onsets detected; choose audio with a clear attack.")
    scene = (
        Canvas(384, 216)
        .background(color="#102030")
        .shape(
            "rectangle",
            (96, 60),
            192,
            96,
            "#102030",
            animation=AnimationSpec.timeline(
                ColorTrack(
                    keyframes=[
                        KeyframeSpec(time=0, value="#102030"),
                        KeyframeSpec(time=0.2, value="#42CEB7"),
                    ]
                ),
                timing=TimingSpec(start=analysis.onsets[0], duration=0.2),
                easing="linear",
            ),
        )
    )
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "analysis.json").write_text(analysis.model_dump_json(), encoding="utf-8")
    (args.output / "scene.json").write_text(scene.to_json(), encoding="utf-8")
    scene.export(
        args.output / "onset.mp4",
        animation=VideoOptions(fps=30, hold=0.5, soundtrack=AudioTrack(path=str(args.source))),
    )


if __name__ == "__main__":
    main()
