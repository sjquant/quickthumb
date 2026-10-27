"""Fixed, offline scenes shared by timing and frame-identity commands."""

from pathlib import Path

from quickthumb import (
    AnimationSpec,
    Canvas,
    ColorTrack,
    Deck,
    KeyframeSpec,
    OpacityTrack,
    PositionKeyframeSpec,
    PositionTrack,
    RangeSelector,
    RotationTrack,
    ScaleTrack,
    StaggerSpec,
    TimingSpec,
)
from quickthumb.transitions import Cut

SCENES = ("translation", "rotation", "scale", "product_hype_reel")
TEXT_SELECTOR_SCENES = tuple(
    f"text_{target}_{mode}"
    for target in ("words", "lines")
    for mode in ("baseline", "static", "animated")
)
TEXT_FONT = Path(__file__).resolve().parents[1] / "assets/fonts/Roboto-Regular.ttf"
DURATION = 2.0


def build_text_selector_scene(name: str, *, rest: bool = False) -> Deck:
    """Same authored text and property tracks; only selector evaluation differs."""
    if name not in TEXT_SELECTOR_SCENES:
        raise ValueError(f"unknown text-selector scene: {name}")
    target = "words" if "_words_" in name else "lines"
    mode = name.rsplit("_", 1)[1]
    selector = None
    if mode != "baseline":
        selector = RangeSelector(target=target, shape="ramp", end=75)
        if mode == "animated":
            selector.offset = [
                KeyframeSpec(time=0, value=-25),
                KeyframeSpec(time=1, value=25),
                KeyframeSpec(time=2, value=0),
            ]
    motion = AnimationSpec(
        tracks=[
            PositionTrack(
                keyframes=[KeyframeSpec(time=0, value=(0, 16)), KeyframeSpec(time=2, value=(0, 0))]
            ),
            RotationTrack(keyframes=[KeyframeSpec(time=0, value=8), KeyframeSpec(time=2, value=0)]),
            ScaleTrack(keyframes=[KeyframeSpec(time=0, value=0.9), KeyframeSpec(time=2, value=1)]),
            OpacityTrack(
                keyframes=[KeyframeSpec(time=0, value=0.3), KeyframeSpec(time=2, value=1)]
            ),
            ColorTrack(
                keyframes=[
                    KeyframeSpec(time=0, value="#FFD18A"),
                    KeyframeSpec(time=2, value="#42CEB7"),
                ]
            ),
        ],
        timing=TimingSpec(duration=DURATION),
        stagger=StaggerSpec(target=target, delay=0),
        selector=selector,
        easing="linear",
    )
    canvas = (
        Canvas(480, 240)
        .background(color="#102030")
        .text(
            "ONE TWO\nONE TWO\nONE TWO",
            font=str(TEXT_FONT),
            size=40,
            line_height=1.3,
            color="#42CEB7",
            position=(24, 24),
            animation=None if rest else motion,
        )
    )
    return Deck(480, 240).slide(canvas, transition=Cut(advance_after=DURATION), duration=DURATION)


def build_scene(name: str) -> Deck:
    """Use the complete example reel, or a high-contrast asymmetric marker."""
    if name in TEXT_SELECTOR_SCENES:
        return build_text_selector_scene(name)
    if name == "motion_blur":
        from examples.motion_blur import build_deck

        return build_deck()
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
