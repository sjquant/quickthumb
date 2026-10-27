"""Static word/line range weights over ordinary kinetic-text tracks."""

import argparse
from pathlib import Path

from quickthumb import (
    AnimationSpec,
    Canvas,
    ColorTrack,
    KeyframeSpec,
    PositionTrack,
    RangeSelector,
    RotationTrack,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=("words", "lines"), default="words")
    parser.add_argument("--output", type=Path, default=Path("text-selector.gif"))
    args = parser.parse_args()
    motion = AnimationSpec.timeline(
        PositionTrack(
            keyframes=[KeyframeSpec(time=0, value=(0, 24)), KeyframeSpec(time=0.6, value=(0, 0))]
        ),
        RotationTrack(keyframes=[KeyframeSpec(time=0, value=15), KeyframeSpec(time=0.6, value=0)]),
        ColorTrack(
            keyframes=[
                KeyframeSpec(time=0, value="#FCE38A80"),
                KeyframeSpec(time=0.6, value="#42CEB7"),
            ]
        ),
        selector=RangeSelector(
            target=args.target,
            shape="ramp",
            offset=[
                KeyframeSpec(time=0, value=0),
                KeyframeSpec(time=0.3, value=20),
                KeyframeSpec(time=0.6, value=0),
            ],
        ),
        easing="linear",
    )
    scene = (
        Canvas(480, 240)
        .background(color="#102030")
        .text(
            "MOVE\nWORDS",
            position=(40, 32),
            size=64,
            color="#42CEB7",
            font=str(Path(__file__).resolve().parents[1] / "assets/fonts/Roboto-Regular.ttf"),
            animation=motion,
        )
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(scene.to_gif(fps=20, hold=0.5))
    args.output.with_suffix(".json").write_text(scene.to_json())


if __name__ == "__main__":
    main()
