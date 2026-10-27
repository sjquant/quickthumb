"""Character entrances over a transparent lower third, using only bundled assets."""

import argparse
from pathlib import Path

from quickthumb import (
    AnimationSpec,
    Canvas,
    KeyframeSpec,
    OpacityTrack,
    PositionTrack,
    StaggerSpec,
    TimingSpec,
    VideoOptions,
)

ROOT = Path(__file__).resolve().parents[1]
FONT = str(ROOT / "assets/fonts/Roboto-Medium.ttf")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "examples/output/kinetic_lower_third.webm"
    )
    args = parser.parse_args()
    if args.output.suffix.lower() not in {".webm", ".mov"}:
        parser.error("--output must end in .webm (VP9 alpha) or .mov (ProRes 4444)")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result = build_scene().export(
        args.output,
        animation=VideoOptions(transparent=True, fps=20, hold=0.5),
    )
    print(result.written_paths)


def build_scene() -> Canvas:
    panel = AnimationSpec.timeline(
        OpacityTrack(keyframes=[KeyframeSpec(time=0, value=0), KeyframeSpec(time=0.25, value=1)])
    )
    entrance = AnimationSpec(
        tracks=[
            PositionTrack(
                keyframes=[
                    KeyframeSpec(time=0, value=(0, 16)),
                    KeyframeSpec(time=0.4, value=(0, 0)),
                ]
            ),
            OpacityTrack(
                keyframes=[KeyframeSpec(time=0, value=0), KeyframeSpec(time=0.4, value=1)]
            ),
        ],
        stagger=StaggerSpec(target="characters", delay=0.05),
        timing=TimingSpec(start=0.2, duration=0.4),
        easing="ease_out_cubic",
    )
    return (
        Canvas(480, 180)
        .shape(
            "rectangle",
            (24, 86),
            400,
            72,
            "#142839D0",
            border_radius=8,
            animation=panel,
        )
        .shape("rectangle", (24, 86), 6, 72, "#45E4C1", animation=panel)
        .text(
            "ALEX MORGAN",
            position=(46, 99),
            size=23,
            font=FONT,
            color="#FFFFFF",
            id="name",
            animation=entrance,
        )
        .text(
            "DESIGN DIRECTOR",
            position=(46, 131),
            size=12,
            font=FONT,
            color="#B5D8E5",
            animation=panel,
        )
    )


if __name__ == "__main__":
    main()
