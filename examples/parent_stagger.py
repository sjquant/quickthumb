"""Separated text lines and group rows stagger through full ancestor transforms.

Run from the repository root:
    uv run python examples/parent_stagger.py
"""

from pathlib import Path

from quickthumb import (
    AnimationSpec,
    Canvas,
    ColorTrack,
    GifOptions,
    KeyframeSpec,
    OpacityTrack,
    PositionTrack,
    RotationTrack,
    ScaleXTrack,
    ScaleYTrack,
    StaggerSpec,
    TimingSpec,
)

ROOT = Path(__file__).resolve().parents[1]
FONT = str(ROOT / "assets/fonts/Roboto-Medium.ttf")


def track(kind, first, last, duration=1.4):
    return kind(
        keyframes=[KeyframeSpec(time=0, value=first), KeyframeSpec(time=duration, value=last)]
    )


def build_scene() -> Canvas:
    canvas = Canvas(600, 340).background(color="#101820")
    canvas.text("STAGGER IN PARENT SPACE", position=(24, 20), font=FONT, size=23, color="#FFFFFF")
    canvas.text(
        "Independent arrivals, shared affine motion",
        position=(24, 53),
        font=FONT,
        size=14,
        color="#A5BCC7",
    )
    canvas.null(
        (110, 98),
        id="rig",
        animation=AnimationSpec.timeline(
            track(RotationTrack, -12, 8),
            track(ScaleXTrack, 1.25, 0.95),
            timing=TimingSpec(duration=1.4),
            easing="linear",
        ),
    )
    canvas.null(
        (0, 0),
        id="arm",
        parent="rig",
        animation=AnimationSpec.timeline(
            track(RotationTrack, 20, -8),
            track(ScaleYTrack, 0.85, 1.1),
            timing=TimingSpec(duration=1.4),
            easing="linear",
        ),
    )
    canvas.text(
        "LOCAL\nLINES\nARRIVE",
        position=(0, 0),
        parent="arm",
        font=FONT,
        size=30,
        line_height=1.7,
        color="#42CEB7",
        anchor=(0, 0.5),
        animation=AnimationSpec.rise(
            distance=24, duration=0.6, stagger=0.3, target="lines", easing="linear"
        ),
    )
    canvas.null(
        (362, 99),
        id="rows",
        rotation=-8,
        animation=AnimationSpec.timeline(
            track(ScaleXTrack, 0.9, 1.2),
            track(RotationTrack, 0, 12),
            timing=TimingSpec(duration=1.4),
            easing="linear",
        ),
    )
    rows = AnimationSpec.timeline(
        track(PositionTrack, (20, 0), (0, 0), 0.8),
        track(OpacityTrack, 0, 1, 0.8),
        track(ColorTrack, "#FFCF56", "#42CEB7", 0.8),
        timing=TimingSpec(duration=0.8),
        easing="linear",
    )
    rows.stagger = StaggerSpec(delay=0.3, target="children")
    canvas.group(
        [
            {"type": "text", "content": label, "font": FONT, "size": 29, "color": "#FFFFFF"}
            for label in ("ONE", "TWO", "THREE")
        ],
        position=(0, 0),
        parent="rows",
        gap=25,
        animation=rows,
    )
    canvas.text("Text lines", position=(105, 300), font=FONT, size=14, color="#A5BCC7")
    canvas.text("Group rows + color", position=(350, 300), font=FONT, size=14, color="#A5BCC7")
    return canvas


if __name__ == "__main__":
    scene = build_scene()
    output = ROOT / "examples/output"
    output.mkdir(exist_ok=True)
    scene.render(str(output / "parent_stagger.gif"), animation=GifOptions(fps=24, quality="high"))
    scene.render_frame(0.95).save(output / "parent_stagger.png")
    # Document adapters keep the complete authored scene as a static fallback.
    scene.render(str(output / "parent_stagger.html"))
