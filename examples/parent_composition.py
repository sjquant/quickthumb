"""Own clips and masks travel with sources while explicit children stay free.

Run from the repository root:
    uv run python examples/parent_composition.py
"""

from pathlib import Path

from quickthumb import (
    Align,
    AnimationSpec,
    Background,
    Canvas,
    GifOptions,
    KeyframeSpec,
    LayerClip,
    LayerMask,
    RotationTrack,
    ScaleXTrack,
    TimingSpec,
)

ROOT = Path(__file__).resolve().parents[1]
FONT = str(ROOT / "assets/fonts/Roboto-Medium.ttf")


def build_scene() -> Canvas:
    canvas = Canvas(760, 310).background(color="#101820")
    canvas.text(
        "SOURCE BOUNDARIES, SHARED MOTION", position=(24, 20), font=FONT, size=23, color="#FFFFFF"
    )
    canvas.text(
        "Clipped paint travels; child markers keep the full body frame",
        position=(24, 54),
        font=FONT,
        size=15,
        color="#A5BCC7",
    )
    for index, name in enumerate(("shape", "counter", "stagger")):
        canvas.null(
            (135 + index * 245, 155),
            id=name,
            animation=AnimationSpec.timeline(
                RotationTrack(
                    keyframes=[KeyframeSpec(time=0, value=-10), KeyframeSpec(time=1.4, value=15)]
                ),
                ScaleXTrack(
                    keyframes=[KeyframeSpec(time=0, value=1), KeyframeSpec(time=1.4, value=1.2)]
                ),
                timing=TimingSpec(duration=1.4),
                easing="linear",
            ),
        )
        canvas.text(
            ("MASKED PARENT", "MASKED COUNTER", "CLIPPED STAGGER")[index],
            position=(135 + index * 245, 270),
            align="top-center",
            font=FONT,
            size=15,
            color="#FFCF56",
        )
    canvas.shape(
        "rectangle",
        (-65, -40),
        130,
        80,
        "#32BAA5",
        rotation=12,
        parent="shape",
        id="body",
        clip=LayerClip(position=(-45, -30), width=90, height=60, border_radius=14),
        mask=LayerMask(
            shape="polygon",
            position=(-60, -35),
            width=120,
            height=70,
            points=[(0, 0), (1, 0.2), (0.85, 1), (0.1, 0.85)],
        ),
    )
    canvas.shape("ellipse", (115, 65), 13, 13, "#FFCF56", parent="body")
    canvas.counter(
        99,
        105,
        1.4,
        position=(0, 0),
        align="center",
        font=FONT,
        size=53,
        style="odometer",
        color="#FFFFFF",
        easing="linear",
        parent="counter",
        id="digits",
        effects=[Background(color="#246C89", padding=8)],
        clip=LayerClip(position=(0, 0), width=145, height=80, align=Align.CENTER, border_radius=15),
        mask=LayerMask(shape="ellipse", position=(-73, -43), width=146, height=86, opacity=0.75),
    )
    canvas.shape("rectangle", (30, 75), 25, 5, "#FFCF56", parent="digits", border_radius=2)
    canvas.text(
        "SOURCE\nBOUNDARY\nTRAVELS",
        position=(-65, -55),
        size=24,
        font=FONT,
        color="#FFFFFF",
        line_height=1.5,
        parent="stagger",
        clip=LayerClip(position=(-65, -55), width=115, height=145, border_radius=10),
        animation=AnimationSpec.rise(distance=14, duration=0.45, stagger=0.25, target="lines"),
    )
    return canvas


if __name__ == "__main__":
    scene = build_scene()
    output = ROOT / "examples/output"
    output.mkdir(exist_ok=True)
    scene.render(
        str(output / "parent_composition.gif"), animation=GifOptions(fps=24, quality="high")
    )
    scene.render_frame(0.7).save(output / "parent_composition.png")
    scene.render(str(output / "parent_composition.html"))
