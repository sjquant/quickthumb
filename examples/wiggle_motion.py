"""Compare three deterministic seeds on position and rotation tracks.

Run `uv run python examples/wiggle_motion.py` from the repository root.
"""

from pathlib import Path

from quickthumb import (
    AnimationSpec,
    Canvas,
    KeyframeSpec,
    PositionTrack,
    RotationTrack,
    TimingSpec,
    Wiggle,
)


def build_scene() -> Canvas:
    canvas = Canvas(320, 144).background(color="#102030")
    for row, color in enumerate(("#42CEB7", "#F1B95B", "#85A9EF")):
        seed = 156 + row
        canvas.shape(
            "rectangle",
            (146, 16 + row * 44),
            28,
            28,
            color,
            animation=AnimationSpec.timeline(
                PositionTrack(
                    keyframes=[KeyframeSpec(time=0, value=(0, 0))],
                    wiggle=Wiggle(frequency=2, amplitude=16, seed=seed),
                ),
                RotationTrack(
                    keyframes=[KeyframeSpec(time=0, value=0)],
                    wiggle=Wiggle(frequency=1, amplitude=12, seed=seed),
                ),
                timing=TimingSpec(duration=2, start=0),
            ),
        )
    return canvas


if __name__ == "__main__":
    output = Path("examples/output")
    output.mkdir(exist_ok=True)
    scene = build_scene()
    (output / "wiggle_motion.gif").write_bytes(scene.to_gif(fps=24, hold=0.5))
    (output / "wiggle_motion.json").write_text(scene.to_json(), encoding="utf-8")
    scene.render_frame(0.5).save(output / "wiggle_motion.png")
