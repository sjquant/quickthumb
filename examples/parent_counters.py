"""Three counter styles share affine motion and keep their child markers stable.

Run from the repository root:
    uv run python examples/parent_counters.py
"""

from pathlib import Path

from quickthumb import (
    AnimationSpec,
    Canvas,
    GifOptions,
    KeyframeSpec,
    RotationTrack,
    ScaleXTrack,
    TimingSpec,
)

ROOT = Path(__file__).resolve().parents[1]
FONT = str(ROOT / "assets/fonts/Roboto-Medium.ttf")


def build_scene() -> Canvas:
    canvas = Canvas(600, 280).background(color="#101820")
    canvas.text("COUNTERS IN PARENT SPACE", position=(24, 20), font=FONT, size=23, color="#FFFFFF")
    canvas.text(
        "Digits change; each child marker keeps its settled frame",
        position=(24, 53),
        font=FONT,
        size=14,
        color="#A5BCC7",
    )
    for index, style in enumerate(("plain", "odometer", "flip")):
        root_id, counter_id = f"rig-{style}", f"counter-{style}"
        canvas.null(
            (100 + index * 200, 132),
            id=root_id,
            animation=AnimationSpec.timeline(
                RotationTrack(
                    keyframes=[KeyframeSpec(time=0, value=-12), KeyframeSpec(time=1.4, value=12)]
                ),
                ScaleXTrack(
                    keyframes=[KeyframeSpec(time=0, value=1), KeyframeSpec(time=1.4, value=1.25)]
                ),
                timing=TimingSpec(duration=1.4),
                easing="linear",
            ),
        )
        canvas.counter(
            99,
            100,
            1.4,
            position=(0, 0),
            align="center",
            font=FONT,
            size=43,
            color="#FFFFFF",
            style=style,
            easing="linear",
            parent=root_id,
            id=counter_id,
        )
        canvas.shape("rectangle", (0, 50), 24, 5, "#42CEB7", parent=counter_id, border_radius=2)
        canvas.text(
            style.upper(),
            position=(100 + index * 200, 227),
            align="top-center",
            font=FONT,
            size=15,
            color="#FFCF56",
        )
    return canvas


if __name__ == "__main__":
    scene = build_scene()
    output = ROOT / "examples/output"
    output.mkdir(exist_ok=True)
    scene.render(str(output / "parent_counters.gif"), animation=GifOptions(fps=24, quality="high"))
    scene.render_frame(0.49).save(output / "parent_counters.png")
    # Counter sources make HTML use the honest authored-static scene fallback.
    scene.render(str(output / "parent_counters.html"))
