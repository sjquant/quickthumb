"""Draw on a native vector stroke while its translucent fill stays complete."""

from quickthumb import (
    AnimationSpec,
    Canvas,
    KeyframeSpec,
    LottieOptions,
    TimingSpec,
    TrimEndTrack,
    TrimOffsetTrack,
)


def build_canvas() -> Canvas:
    return Canvas(240, 160).path(
        "M20 20H180V100H20Z",
        (20, 20),
        200,
        120,
        "#159A8C60",
        stroke="#3757A0C0",
        stroke_width=8,
        line_cap="round",
        line_join="round",
        trim_end=0,
        id="outline",
        animation=[
            AnimationSpec.timeline(
                TrimEndTrack(
                    keyframes=[
                        KeyframeSpec(time=0, value=0),
                        KeyframeSpec(time=0.5, value=0.5, hold=True),
                        KeyframeSpec(time=1, value=1),
                    ]
                ),
                timing=TimingSpec(duration=1, start=0.125),
                easing="ease_in_out_sine",
            ),
            AnimationSpec.timeline(
                TrimOffsetTrack(
                    keyframes=[KeyframeSpec(time=0, value=-0.25), KeyframeSpec(time=1, value=0.25)]
                ),
                timing=TimingSpec(duration=1, trigger="with_previous"),
            ),
        ],
    )


if __name__ == "__main__":
    build_canvas().export("trim.lot", animation=LottieOptions(fps=20, hold=0.5))
