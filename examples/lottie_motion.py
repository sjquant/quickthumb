"""Held canonical vector poses; no raster frames or hidden playback clock."""

from quickthumb import (
    AnimationSpec,
    Canvas,
    KeyframeSpec,
    LottieOptions,
    OpacityTrack,
    PositionTrack,
    RotationTrack,
    ScaleTrack,
    ScaleXTrack,
    ScaleYTrack,
    TimingSpec,
)


def build_canvas() -> Canvas:
    return (
        Canvas(300, 200)
        .path(
            "M8 8H48L40 34H8Z",
            (25, 45),
            90,
            60,
            "#159A8C80",
            view_box=(0, 0, 60, 40),
            rotation=15,
            opacity=0.6,
            anchor=(0, 1),
            id="path",
            animation=[
                AnimationSpec.timeline(
                    PositionTrack(
                        keyframes=[
                            KeyframeSpec(time=0, value=(0, 0)),
                            KeyframeSpec(time=1, value=(20, 0)),
                        ]
                    ),
                    RotationTrack(
                        keyframes=[KeyframeSpec(time=0, value=0), KeyframeSpec(time=1, value=20)]
                    ),
                    ScaleTrack(
                        keyframes=[KeyframeSpec(time=0, value=1), KeyframeSpec(time=1, value=1.2)]
                    ),
                    ScaleXTrack(
                        keyframes=[KeyframeSpec(time=0, value=1), KeyframeSpec(time=1, value=0.8)]
                    ),
                    ScaleYTrack(
                        keyframes=[KeyframeSpec(time=0, value=1), KeyframeSpec(time=1, value=1.1)]
                    ),
                    OpacityTrack(
                        keyframes=[
                            KeyframeSpec(time=0, value=0.5, hold=True),
                            KeyframeSpec(time=0.5, value=1),
                            KeyframeSpec(time=1, value=0.75),
                        ]
                    ),
                    timing=TimingSpec(duration=1, start=0.125),
                    easing="ease_in_out_sine",
                ),
                AnimationSpec.timeline(
                    PositionTrack(
                        keyframes=[
                            KeyframeSpec(time=0, value=(10, 0)),
                            KeyframeSpec(time=0.5, value=(20, 10)),
                        ]
                    ),
                    RotationTrack(
                        keyframes=[
                            KeyframeSpec(time=0, value=10),
                            KeyframeSpec(time=0.5, value=-10),
                        ]
                    ),
                    timing=TimingSpec(duration=0.5, trigger="with_previous", delay=0.5),
                ),
            ],
        )
        .shape(
            "star",
            (180, 45),
            60,
            60,
            "#E75A4080",
            rotation=12,
            opacity=0.75,
            anchor=(1, 0),
            id="shape",
            animation=AnimationSpec.timeline(
                PositionTrack(
                    keyframes=[
                        KeyframeSpec(time=0, value=(0, 0)),
                        KeyframeSpec(time=1, value=(-10, 25)),
                    ]
                ),
                RotationTrack(
                    keyframes=[KeyframeSpec(time=0, value=0), KeyframeSpec(time=1, value=-25)]
                ),
                ScaleTrack(
                    keyframes=[KeyframeSpec(time=0, value=1), KeyframeSpec(time=1, value=1.2)]
                ),
                ScaleXTrack(
                    keyframes=[KeyframeSpec(time=0, value=1), KeyframeSpec(time=1, value=0.8)]
                ),
                ScaleYTrack(
                    keyframes=[KeyframeSpec(time=0, value=1), KeyframeSpec(time=1, value=1.1)]
                ),
                OpacityTrack(
                    keyframes=[KeyframeSpec(time=0, value=0.5), KeyframeSpec(time=1, value=1)]
                ),
                timing=TimingSpec(duration=1),
                easing="ease_out_cubic",
            ),
        )
    )


if __name__ == "__main__":
    build_canvas().export("motion.lot", animation=LottieOptions(fps=20, hold=0.5))
