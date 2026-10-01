"""Fixed, offline scenes shared by timing and frame-identity commands."""

from quickthumb import (
    AnimationSpec,
    Canvas,
    Deck,
    KeyframeSpec,
    PositionTrack,
    RotationTrack,
    ScaleTrack,
    TimingSpec,
)
from quickthumb.transitions import Cut

SCENES = ("translation", "rotation", "scale", "product_hype_reel")
DURATION = 2.0


def build_scene(name: str) -> Deck:
    """Use the complete example reel, or a high-contrast asymmetric marker."""
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
