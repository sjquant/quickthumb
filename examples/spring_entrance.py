"""Bring the bundled Quickthumb logo and wordmark in with spring overshoot.

Run `python -m examples.spring_entrance` from the repository root.
"""

from pathlib import Path

from quickthumb import AnimationSpec, Canvas, KeyframeSpec, PositionTrack, SpringEasing, TimingSpec


def build_scene() -> Canvas:
    spring = SpringEasing(stiffness=100, damping=12, mass=1)
    return (
        Canvas(640, 240)
        .background(color="#F8F7F3")
        .image(
            "assets/brand/quickthumb-icon-152.png",
            (56, 72),
            width=96,
            height=96,
            id="logo",
            animation=AnimationSpec.timeline(
                PositionTrack(
                    keyframes=[
                        KeyframeSpec(time=0, value=(-160, 0)),
                        KeyframeSpec(time=1.2, value=(0, 0)),
                    ]
                ),
                easing=spring,
                timing=TimingSpec(duration=1.2),
            ),
        )
        .text(
            "Quickthumb",
            position=(184, 88),
            size=56,
            font="assets/fonts/NotoSans-Bold.ttf",
            color="#263344",
            id="wordmark",
            animation=AnimationSpec.timeline(
                PositionTrack(
                    keyframes=[
                        KeyframeSpec(time=0, value=(-600, 0)),
                        KeyframeSpec(time=1.5, value=(0, 0)),
                    ]
                ),
                easing=spring,
                timing=TimingSpec(duration=1.5),
            ),
        )
    )


if __name__ == "__main__":
    output = Path("examples/output")
    output.mkdir(exist_ok=True)
    scene = build_scene()
    (output / "spring_entrance.json").write_text(scene.to_json(), encoding="utf-8")
    (output / "spring_entrance.gif").write_bytes(scene.to_gif(fps=20, hold=0.5))
    scene.render_frame(0.6).save(output / "spring_entrance_overshoot.png")
    # The declared interval ends at its exact target; hold keeps that endpoint.
    scene.render_frame(1.5).save(output / "spring_entrance_settled.png")
