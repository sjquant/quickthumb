"""A gradient path with Bézier curves, arcs, an even-odd hole and crisp 4x enlargement.

Run from the repository root:
    uv run python examples/path_layer.py --output-dir /tmp/quickthumb-path-layer

PNG shows the authored still; GIF scales its fixed viewport from 1x to 4x in
two seconds, then holds for half a second. JSON retains the complete source.
No fonts, external assets or optional rendering dependencies are needed.
"""

import argparse
from pathlib import Path
from tempfile import gettempdir

from quickthumb import (
    AnimationSpec,
    Canvas,
    GifOptions,
    KeyframeSpec,
    LinearGradient,
    ScaleTrack,
    TimingSpec,
)


def build_canvas() -> Canvas:
    return (
        Canvas(480, 360)
        .background(color="#101820")
        .path(
            "M15 40C15 10 50 5 70 18A30 25 25 0 1 85 50Q70 78 35 65"
            "C20 62 15 52 15 40Z M38 40A12 10 0 1 0 62 40A12 10 0 1 0 38 40Z",
            (200, 150),
            80,
            60,
            None,
            view_box=(0, 0, 100, 80),
            fill=LinearGradient(angle=30, stops=[("#42CEB7", 0), ("#315D8E", 1)]),
            stroke="#E4FFF8",
            stroke_width=1.6,
            line_join="round",
            anchor=(0.5, 0.5),
            id="path.emblem",
            animation=AnimationSpec.timeline(
                ScaleTrack(
                    keyframes=[KeyframeSpec(time=0, value=1), KeyframeSpec(time=2, value=4)]
                ),
                timing=TimingSpec(duration=2),
                easing="linear",
            ),
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(gettempdir()) / "quickthumb-path-layer",
    )
    output = parser.parse_args().output_dir
    output.mkdir(parents=True, exist_ok=True)
    canvas = build_canvas()
    canvas.export(output / "path_layer.png")
    canvas.export(output / "path_layer.gif", animation=GifOptions(fps=12, hold=0.5))
    (output / "path_layer.json").write_text(canvas.to_json(), encoding="utf-8")
