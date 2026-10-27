"""Native parent frames retain independent drawing order and opacity."""

from quickthumb import (
    AnimationSpec,
    Canvas,
    KeyframeSpec,
    LottieOptions,
    OpacityTrack,
    PositionTrack,
    RotationTrack,
    ScaleXTrack,
    ScaleYTrack,
    TimingSpec,
)


def build_canvas() -> Canvas:
    return (
        Canvas(320, 240)
        .null(
            ("20%", "20%"),
            id="root",
            rotation=15,
            animation=AnimationSpec.timeline(
                RotationTrack(
                    keyframes=[KeyframeSpec(time=0, value=0), KeyframeSpec(time=1, value=20)]
                ),
                ScaleXTrack(
                    keyframes=[KeyframeSpec(time=0, value=1), KeyframeSpec(time=1, value=1.8)]
                ),
                OpacityTrack(
                    keyframes=[KeyframeSpec(time=0, value=0), KeyframeSpec(time=1, value=0)]
                ),
                timing=TimingSpec(duration=1),
            ),
        )
        .null(
            (12, 8),
            id="middle",
            parent="root",
            rotation=-10,
            animation=AnimationSpec.timeline(
                ScaleYTrack(
                    keyframes=[KeyframeSpec(time=0, value=1), KeyframeSpec(time=1, value=0.8)]
                ),
                timing=TimingSpec(duration=1),
            ),
        )
        .shape(
            "rectangle",
            (5, 5),
            36,
            24,
            "#159A8C80",
            id="panel",
            parent="middle",
            rotation=12,
            opacity=0,
            anchor=(1, 0),
            animation=AnimationSpec.timeline(
                RotationTrack(
                    keyframes=[KeyframeSpec(time=0, value=0), KeyframeSpec(time=1, value=-20)]
                ),
                OpacityTrack(
                    keyframes=[KeyframeSpec(time=0, value=0), KeyframeSpec(time=1, value=0)]
                ),
                timing=TimingSpec(duration=1),
            ),
        )
        .shape(
            "star",
            (10, 8),
            38,
            38,
            "#E75A4080",
            id="child",
            parent="panel",
            rotation=7,
            anchor=(0, 1),
            opacity=0.75,
            animation=AnimationSpec.timeline(
                PositionTrack(
                    keyframes=[
                        KeyframeSpec(time=0, value=(0, 0)),
                        KeyframeSpec(time=1, value=(12, 4)),
                    ]
                ),
                RotationTrack(
                    keyframes=[KeyframeSpec(time=0, value=0), KeyframeSpec(time=1, value=15)]
                ),
                ScaleXTrack(
                    keyframes=[KeyframeSpec(time=0, value=1), KeyframeSpec(time=1, value=0.9)]
                ),
                timing=TimingSpec(duration=1),
                easing="ease_in_out_sine",
            ),
        )
        .shape("rectangle", ("35%", "35%"), 22, 16, "#3757A0", id="percent", parent="root")
    )


if __name__ == "__main__":
    build_canvas().export("parenting.lot", animation=LottieOptions(fps=20, hold=0.5))
