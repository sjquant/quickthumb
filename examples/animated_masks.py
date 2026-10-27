"""Resize, move and soften a shape mask on the owner's ordinary animation clock."""

from quickthumb import (
    AnimationSpec,
    Canvas,
    KeyframeSpec,
    LayerMask,
    MaskFeatherTrack,
    MaskPositionTrack,
    MaskSizeTrack,
    TimingSpec,
)


def build_scene():
    motion = AnimationSpec.timeline(
        MaskPositionTrack(
            keyframes=[KeyframeSpec(time=0, value=(0, 0)), KeyframeSpec(time=1.5, value=(160, 0))]
        ),
        MaskSizeTrack(
            keyframes=[
                KeyframeSpec(time=0, value=(40, 120)),
                KeyframeSpec(time=1.5, value=(120, 120)),
            ]
        ),
        MaskFeatherTrack(
            keyframes=[KeyframeSpec(time=0, value=0), KeyframeSpec(time=1.5, value=8)]
        ),
        timing=TimingSpec(duration=1.5),
        easing="ease_in_out",
    )
    return Canvas(360, 160).shape(
        "rectangle",
        (20, 20),
        320,
        120,
        color="#42CEB7",
        mask=LayerMask(shape="ellipse", position=(20, 20), width=40, height=120),
        animation=motion,
    )


if __name__ == "__main__":
    build_scene().export("animated-mask.gif")
