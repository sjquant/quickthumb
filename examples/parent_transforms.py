"""A three-controller parent chain: rotation, non-uniform scale and local motion.

Run from the repository root:
    uv run python examples/parent_transforms.py
"""

from pathlib import Path

from quickthumb import (
    AnimationSpec,
    Canvas,
    GifOptions,
    KeyframeSpec,
    PositionTrack,
    RotationTrack,
    ScaleXTrack,
    ScaleYTrack,
    TimingSpec,
)

ROOT = Path(__file__).resolve().parents[1]
FONT = str(ROOT / "assets/fonts/Roboto-Medium.ttf")


def track(kind, values):
    return kind(
        keyframes=[KeyframeSpec(time=index, value=value) for index, value in enumerate(values)]
    )


def motion(*tracks):
    return AnimationSpec.timeline(*tracks, timing=TimingSpec(duration=2), easing="ease_in_out")


def build_scene() -> Canvas:
    canvas = Canvas(480, 300).background(color="#101820")
    canvas.text("PARENT-LOCAL MOTION", position=(24, 20), font=FONT, size=21, color="#FFFFFF")
    canvas.text(
        "Three invisible controllers, one full affine chain",
        position=(24, 51),
        font=FONT,
        size=13,
        color="#A5BCC7",
    )
    canvas.null(
        (240, 140),
        id="rig",
        animation=motion(
            track(RotationTrack, [-12, 12, -12]),
            track(ScaleXTrack, [1.35, 0.85, 1.35]),
        ),
    )
    canvas.null(
        (-75, 0),
        id="arm",
        parent="rig",
        animation=motion(
            track(RotationTrack, [-20, 40, -20]),
            track(ScaleYTrack, [1, 0.65, 1]),
        ),
    )
    canvas.shape("rectangle", (-45, -14), 160, 28, "#42CEB7", parent="arm", border_radius=9)
    canvas.null(
        (95, 0),
        id="tip",
        parent="arm",
        animation=motion(
            track(PositionTrack, [(0, 0), (12, -15), (0, 0)]),
            track(RotationTrack, [15, -25, 15]),
        ),
    )
    canvas.group(
        [
            {"type": "shape", "shape": "ellipse", "width": 36, "height": 36, "color": "#FFCF56"},
            {"type": "text", "content": "LOCAL", "font": FONT, "size": 15, "color": "#FFFFFF"},
        ],
        position=(-20, -24),
        direction="column",
        item_align="center",
        gap=6,
        parent="tip",
    )
    canvas.shape("ellipse", (236, 136), 8, 8, "#FFFFFF")
    canvas.text(
        "Unlinked labels and marker keep their original render path",
        position=(24, 268),
        font=FONT,
        size=12,
        color="#A5BCC7",
    )
    return canvas


if __name__ == "__main__":
    scene = build_scene()
    output = ROOT / "examples/output"
    output.mkdir(exist_ok=True)
    scene.render(
        str(output / "parent_transforms.gif"), animation=GifOptions(fps=24, quality="high")
    )
    scene.render_frame(1).save(output / "parent_transforms.png")

    scene.render(str(output / "parent_transforms.html"))
    (output / "parent_transforms.inspection.json").write_text(
        scene.inspect().model_dump_json(indent=2), encoding="utf-8"
    )
    scene.render(str(output / "parent_transforms.debug.png"), debug=True)
