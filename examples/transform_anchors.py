"""Compare corner and centre pivots with independent horizontal/vertical scale.

Run from the repository root with:
    uv run python examples/transform_anchors.py
"""

from pathlib import Path

from quickthumb import (
    AnimationSpec,
    Canvas,
    GifOptions,
    KeyframeSpec,
    RotationTrack,
    ScaleXTrack,
    ScaleYTrack,
    TimingSpec,
)


def build_scene() -> Canvas:
    canvas = Canvas(480, 240).background(color="#101820")
    for index, (anchor, title) in enumerate(
        [((0.0, 0.0), "TOP LEFT"), ((0.5, 0.5), "CENTRE"), ((1.0, 1.0), "BOTTOM RIGHT")]
    ):
        x, y = 48 + index * 160, 110
        canvas.text(
            title,
            position=(index * 160 + 18, 25),
            font="assets/fonts/Roboto-Medium.ttf",
            size=16,
            color="#C6D4DF",
        )
        motion = AnimationSpec.timeline(
            ScaleXTrack(keyframes=[KeyframeSpec(time=0, value=1), KeyframeSpec(time=2, value=1.5)]),
            ScaleYTrack(keyframes=[KeyframeSpec(time=0, value=1), KeyframeSpec(time=2, value=0.6)]),
            RotationTrack(
                keyframes=[KeyframeSpec(time=0, value=0), KeyframeSpec(time=2, value=55)]
            ),
            timing=TimingSpec(
                duration=2, trigger="after_previous" if index == 0 else "with_previous"
            ),
            easing="linear",
        )
        canvas.shape("rectangle", (x, y), 64, 40, "#42CEB7", anchor=anchor, animation=motion)
        px, py = round(x + anchor[0] * 64), round(y + anchor[1] * 40)
        canvas.shape("rectangle", (px - 5, py - 1), 10, 2, "#FFFFFF")
        canvas.shape("rectangle", (px - 1, py - 5), 2, 10, "#FFFFFF")
    return canvas


if __name__ == "__main__":
    scene = build_scene()
    output = Path("examples/output")
    output.mkdir(exist_ok=True)
    scene.render(
        str(output / "transform_anchors.gif"), animation=GifOptions(fps=24, quality="high")
    )
    (output / "transform_anchors.html").write_text(scene.to_html(), encoding="utf-8")
    scene.render_frame(1).save(output / "transform_anchors.png")
