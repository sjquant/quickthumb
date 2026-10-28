"""Move, resize and feather an owner-attached curved mask without a source layer."""

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
    mask = LayerMask(
        shape="path",
        d="M0 60 C0 -20 120 -20 120 60 C120 140 0 140 0 60 Z M40 40 H80 V80 H40 Z",
        position=(20, 20),
        width=120,
        height=120,
    )
    return Canvas(360, 160).shape(
        "rectangle",
        (20, 20),
        320,
        120,
        color="#42CEB7",
        mask=mask,
        animation=AnimationSpec.timeline(
            MaskPositionTrack(
                keyframes=[
                    KeyframeSpec(time=0, value=(0, 0)),
                    KeyframeSpec(time=1.5, value=(140, 0)),
                ]
            ),
            MaskSizeTrack(
                keyframes=[
                    KeyframeSpec(time=0, value=(120, 120)),
                    KeyframeSpec(time=1.5, value=(160, 120)),
                ]
            ),
            MaskFeatherTrack(
                keyframes=[KeyframeSpec(time=0, value=0), KeyframeSpec(time=1.5, value=4)]
            ),
            timing=TimingSpec(duration=1.5),
            easing="ease_in_out",
        ),
    )


if __name__ == "__main__":
    build_scene().export("path-mask.gif")
