"""Perceptual text and shape color animation, including alpha and movement.

Run from the repository root: uv run python examples/color_tracks.py
"""

from pathlib import Path

from quickthumb import (
    AnimationSpec,
    Canvas,
    ColorTrack,
    GifOptions,
    KeyframeSpec,
    PositionTrack,
    TimingSpec,
)


def build_scene() -> Canvas:
    canvas = Canvas(480, 240).background(color="#101820")
    color = ColorTrack(
        keyframes=[
            KeyframeSpec(time=0, value="#FF6258"),
            KeyframeSpec(time=1, value="#42CEB7"),
            KeyframeSpec(time=2, value="#6588FF"),
        ]
    )
    motion = AnimationSpec.timeline(color, timing=TimingSpec(start=0, duration=2), easing="linear")
    canvas.text(
        "COLOR IN MOTION",
        position=(40, 35),
        font="assets/fonts/Roboto-Medium.ttf",
        size=34,
        color="#FF6258",
        animation=motion,
    )
    canvas.shape(
        "pill",
        (40, 105),
        160,
        55,
        "#FF6258",
        animation=AnimationSpec.timeline(
            color,
            PositionTrack(
                keyframes=[KeyframeSpec(time=0, value=(0, 0)), KeyframeSpec(time=2, value=(200, 0))]
            ),
            timing=TimingSpec(start=0, duration=2),
            easing="linear",
        ),
    )
    canvas.text(
        "Perceptual color + alpha",
        position=(40, 185),
        font="assets/fonts/Roboto-Medium.ttf",
        size=22,
        color="#FFFFFF00",
        animation=AnimationSpec.timeline(
            ColorTrack(
                keyframes=[
                    KeyframeSpec(time=0, value="#FFFFFF00"),
                    KeyframeSpec(time=2, value="#FFFFFFFF"),
                ]
            ),
            timing=TimingSpec(start=0, duration=2),
            easing="linear",
        ),
    )
    return canvas


if __name__ == "__main__":
    scene = build_scene()
    output = Path("examples/output")
    output.mkdir(exist_ok=True)
    scene.render(str(output / "color_tracks.gif"), animation=GifOptions(fps=24))
    scene.render_frame(1).save(output / "color_tracks.png")
