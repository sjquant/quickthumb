"""Export a filled and stroked logo morph as held native Lottie vectors."""

import argparse
from pathlib import Path

from examples.path_morph import CIRCLE, LOGO
from quickthumb import (
    AnimationSpec,
    Canvas,
    KeyframeSpec,
    LottieOptions,
    PathMorphTrack,
    TimingSpec,
)


def build_canvas() -> Canvas:
    morph = AnimationSpec.timeline(
        PathMorphTrack(
            keyframes=[
                KeyframeSpec(time=0, value=LOGO),
                KeyframeSpec(time=1.5, value=CIRCLE),
            ]
        ),
        timing=TimingSpec(start=0.25, duration=1.5),
        easing="ease_in_out",
    )
    return Canvas(280, 240).path(
        LOGO,
        (30, 10),
        220,
        220,
        "#159A8C80",
        view_box=(0, 0, 100, 100),
        stroke="#24433F",
        stroke_width=1.4,
        line_join="round",
        animation=morph,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    build_canvas().export(parser.parse_args().output, animation=LottieOptions(fps=24, hold=0.5))
