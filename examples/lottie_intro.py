"""A self-contained vector intro: title, drawing logo, and parented badge.

Run from the repository root: python -m examples.lottie_intro /tmp/intro.lot
"""

import argparse
from pathlib import Path

from examples.path_morph import CIRCLE, LOGO
from quickthumb import (
    AnimationSpec,
    Canvas,
    KeyframeSpec,
    LottieOptions,
    PathMorphTrack,
    RotationTrack,
    TimingSpec,
    TrimEndTrack,
)


def build_canvas() -> Canvas:
    return (
        Canvas(520, 300)
        .background(color="#111A24")
        .text(
            "QUICKTHUMB",
            size=40,
            letter_spacing=2,
            position=(30, 30),
            color="#FFFFFF",
            id="title",
        )
        .path(
            LOGO,
            (270, 95),
            180,
            180,
            "#159A8C80",
            view_box=(0, 0, 100, 100),
            stroke="#C8FFF0",
            stroke_width=1.4,
            line_join="round",
            id="logo",
            animation=[
                AnimationSpec.timeline(
                    TrimEndTrack(
                        keyframes=[KeyframeSpec(time=0, value=0), KeyframeSpec(time=1, value=1)]
                    ),
                    timing=TimingSpec(duration=1),
                    easing="ease_in_out",
                ),
                AnimationSpec.timeline(
                    PathMorphTrack(
                        keyframes=[
                            KeyframeSpec(time=0, value=LOGO),
                            KeyframeSpec(time=1, value=CIRCLE),
                        ]
                    ),
                    timing=TimingSpec(start=1, duration=1),
                    easing="ease_in_out",
                ),
            ],
        )
        .null(
            (100, 180),
            id="badge-pivot",
            animation=AnimationSpec.timeline(
                RotationTrack(
                    keyframes=[KeyframeSpec(time=0, value=0), KeyframeSpec(time=2, value=90)]
                ),
                timing=TimingSpec(duration=2),
                easing="ease_in_out",
            ),
        )
        .shape(
            "rectangle",
            (10, 0),
            65,
            35,
            "#E75A40",
            border_radius=8,
            parent="badge-pivot",
            id="badge",
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    build_canvas().export(parser.parse_args().output, animation=LottieOptions(fps=24, hold=0.5))
