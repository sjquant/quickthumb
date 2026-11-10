"""Global trim across unequal contours, shared translucent strokes and morphs."""

from quickthumb import (
    AnimationSpec,
    Canvas,
    KeyframeSpec,
    PathMorphTrack,
    TimingSpec,
    TrimEndTrack,
    TrimOffsetTrack,
)


def build_canvas() -> Canvas:
    return (
        Canvas(960, 640)
        .path(
            "M20 20H220 M20 60H120",
            (40, 40),
            640,
            200,
            None,
            stroke="#3757A0",
            stroke_width=8,
            view_box=(0, 0, 320, 100),
            line_cap="round",
            trim_start=0.3,
            id="unequal",
            animation=AnimationSpec.timeline(
                TrimEndTrack(
                    keyframes=[
                        KeyframeSpec(time=0, value=0.2),
                        KeyframeSpec(time=0.25, value=0.3),
                        KeyframeSpec(time=0.5, value=0.7),
                        KeyframeSpec(time=1, value=0.2),
                    ]
                ),
                TrimOffsetTrack(
                    keyframes=[
                        KeyframeSpec(time=0, value=-0.25),
                        KeyframeSpec(time=0.5, value=0.25),
                        KeyframeSpec(time=1, value=1.25),
                    ]
                ),
                timing=TimingSpec(duration=1),
            ),
        )
        .path(
            "M20 20H120V90H20Z M70 20H170V90H70Z",
            (40, 320),
            400,
            240,
            None,
            stroke="#159A8C80",
            stroke_width=8,
            view_box=(0, 0, 200, 120),
            id="overlap",
            animation=AnimationSpec.timeline(
                TrimEndTrack(
                    keyframes=[
                        KeyframeSpec(time=0, value=1),
                        KeyframeSpec(time=0.5, value=0.8),
                        KeyframeSpec(time=1, value=0.3),
                    ]
                ),
                timing=TimingSpec(duration=1),
            ),
        )
        .path(
            "M5 5H55V35H5Z M20 15V25H40V15Z",
            (500, 320),
            360,
            240,
            "#159A8C",
            stroke="#3757A0",
            stroke_width=2,
            view_box=(0, 0, 60, 40),
            trim_start=0.8,
            trim_end=0.4,
            id="morph",
            animation=AnimationSpec.timeline(
                PathMorphTrack(
                    keyframes=[
                        KeyframeSpec(time=0, value="M5 5H55V35H5Z M20 15V25H40V15Z"),
                        KeyframeSpec(time=1, value="M10 5H55V35H10Z M25 15V25H42V15Z"),
                    ]
                ),
                timing=TimingSpec(duration=1),
            ),
        )
    )
