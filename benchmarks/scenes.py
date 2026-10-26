"""Fixed, offline scenes shared by timing and frame-identity commands."""

from quickthumb import (
    AnimationSpec,
    Canvas,
    Deck,
    KeyframeSpec,
    PositionKeyframeSpec,
    PositionTrack,
    RotationTrack,
    ScaleTrack,
    TimingSpec,
    TrimEndTrack,
)
from quickthumb.transitions import Cut

SCENES = ("translation", "rotation", "scale", "product_hype_reel")
DURATION = 2.0


def build_scene(name: str) -> Deck:
    """Use the complete example reel, or a high-contrast asymmetric marker."""
    if name == "path_trim":
        canvas = (
            Canvas(600, 400)
            .background(color="#101820")
            .path(
                "M4 30C4 4 40 4 40 20S76 36 76 10",
                (60, 170),
                120,
                60,
                None,
                view_box=(0, 0, 80, 40),
                stroke="#42CEB7",
                stroke_width=2,
                line_cap="round",
                line_join="round",
                anchor=(0, 0.5),
                id="benchmark.path",
                animation=AnimationSpec.timeline(
                    TrimEndTrack(
                        keyframes=[KeyframeSpec(time=0, value=0.05), KeyframeSpec(time=2, value=1)]
                    ),
                    ScaleTrack(
                        keyframes=[KeyframeSpec(time=0, value=1), KeyframeSpec(time=2, value=4)]
                    ),
                    timing=TimingSpec(duration=DURATION),
                    easing="linear",
                ),
            )
        )
        return Deck(600, 400).slide(
            canvas, transition=Cut(advance_after=DURATION), duration=DURATION
        )
    if name == "product_hype_reel":
        from examples.product_hype_reel import build_deck

        return build_deck()
    if name == "translation":
        track = PositionTrack(
            keyframes=[KeyframeSpec(time=0, value=(0, 0)), KeyframeSpec(time=2, value=(12, 0))]
        )
    elif name == "rotation":
        track = RotationTrack(
            keyframes=[KeyframeSpec(time=0, value=0), KeyframeSpec(time=2, value=12)]
        )
    elif name == "scale":
        track = ScaleTrack(
            keyframes=[KeyframeSpec(time=0, value=1), KeyframeSpec(time=2, value=1.15)]
        )
    elif name == "motion_path":
        track = PositionTrack(
            auto_orient=True,
            keyframes=[
                PositionKeyframeSpec(time=0, value=(0, 0), out_tangent=(0, 50)),
                PositionKeyframeSpec(time=2, value=(90, 0), in_tangent=(0, 50)),
            ],
        )
    else:
        raise ValueError(f"unknown benchmark scene: {name}")
    canvas = (
        Canvas(256, 192)
        .background(color="#000000")
        .shape(
            shape="polygon",
            position=(80, 60),
            width=64,
            height=64,
            # An asymmetric L has an off-centre centroid, so rotation and scale
            # actually move the measured point instead of reporting a false zero.
            points=[(0, 0), (0.25, 0), (0.25, 0.75), (1, 0.75), (1, 1), (0, 1)],
            color="#FFFFFF",
            animation=AnimationSpec.timeline(
                track, timing=TimingSpec(duration=DURATION), easing="linear"
            ),
        )
    )
    return Deck(256, 192).slide(canvas, transition=Cut(advance_after=DURATION), duration=DURATION)
