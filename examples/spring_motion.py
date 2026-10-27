"""Compare under-, critically- and over-damped spring motion.

Run `uv run python examples/spring_motion.py` from the repository root.
"""

from pathlib import Path

from quickthumb import AnimationSpec, Canvas, KeyframeSpec, PositionTrack, SpringEasing, TimingSpec


def build_scene() -> Canvas:
    canvas = Canvas(320, 144).background(color="#102030")
    for row, (damping, color) in enumerate([(10, "#42CEB7"), (20, "#F1B95B"), (30, "#85A9EF")]):
        canvas.shape(
            "rectangle",
            (24, 16 + row * 44),
            28,
            28,
            color,
            animation=AnimationSpec.timeline(
                PositionTrack(
                    keyframes=[
                        KeyframeSpec(time=0, value=(0, 0)),
                        KeyframeSpec(time=1, value=(180, 0)),
                    ]
                ),
                easing=SpringEasing(stiffness=100, damping=damping, mass=1),
                timing=TimingSpec(duration=1, start=0),
            ),
        )
    return canvas


if __name__ == "__main__":
    output = Path("examples/output")
    output.mkdir(exist_ok=True)
    scene = build_scene()
    (output / "spring_motion.gif").write_bytes(scene.to_gif(fps=24, hold=0.5))
    (output / "spring_motion.json").write_text(scene.to_json(), encoding="utf-8")
    scene.render_frame(0.5).save(output / "spring_motion.png")
