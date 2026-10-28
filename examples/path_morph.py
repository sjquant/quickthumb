"""Draw a logo outline, fade in its fill, then morph the same closed shape.

Run from the repository root:
    uv run python examples/path_morph.py --output-dir /tmp/quickthumb-path-morph

The PNG is the authored logo; the GIF reveals, fills, and morphs it into a circle.
No fonts, external assets, or optional render dependencies are needed.
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
    OpacityTrack,
    PathMorphTrack,
    TimingSpec,
    TrimEndTrack,
)

LOGO = "M20 10H80Q90 10 90 20V80Q90 90 80 90H20Q10 90 10 80V20Q10 10 20 10Z"
CIRCLE = "M50 10C72 10 90 28 90 50C90 72 72 90 50 90C28 90 10 72 10 50C10 28 28 10 50 10Z"


def build_canvas() -> Canvas:
    morph = AnimationSpec.timeline(
        PathMorphTrack(
            keyframes=[KeyframeSpec(time=0, value=LOGO), KeyframeSpec(time=1.5, value=CIRCLE)]
        ),
        timing=TimingSpec(start=2, duration=1.5),
        easing="ease_in_out",
    )
    fill_in = AnimationSpec.timeline(
        OpacityTrack(
            keyframes=[
                KeyframeSpec(time=0, value=0),
                KeyframeSpec(time=0.9, value=0),
                KeyframeSpec(time=1.8, value=1),
            ]
        ),
        timing=TimingSpec(duration=1.8),
        easing="ease_out",
    )
    outline = AnimationSpec.timeline(
        TrimEndTrack(keyframes=[KeyframeSpec(time=0, value=0), KeyframeSpec(time=1.25, value=1)]),
        timing=TimingSpec(duration=1.25),
        easing="ease_in_out",
    )
    canvas = Canvas(360, 320).background(color="#111A24")
    canvas.path(
        LOGO,
        (70, 50),
        220,
        220,
        None,
        view_box=(0, 0, 100, 100),
        fill=LinearGradient(angle=30, stops=[("#42CEB7", 0), ("#315D8E", 1)]),
        id="logo.fill",
        animation=[fill_in, morph],
    )
    canvas.path(
        LOGO,
        (70, 50),
        220,
        220,
        None,
        view_box=(0, 0, 100, 100),
        stroke="#C8FFF0",
        stroke_width=1.4,
        line_join="round",
        id="logo.outline",
        animation=[outline, morph],
    )
    return canvas


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir", type=Path, default=Path(gettempdir()) / "quickthumb-path-morph"
    )
    output = parser.parse_args().output_dir
    output.mkdir(parents=True, exist_ok=True)
    canvas = build_canvas()
    canvas.export(output / "path_morph.png")
    canvas.export(output / "path_morph.gif", animation=GifOptions(fps=12, hold=0.5))
    (output / "path_morph.json").write_text(canvas.to_json(), encoding="utf-8")
