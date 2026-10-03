"""A portrait motion storyboard for the live raster timeline scrubber.

Run: uv run quickthumb serve examples/timeline_preview.py --timeline
Switch to Full to inspect canonical pixels. This module does not export files.
"""

from pathlib import Path

from quickthumb import (
    AnimationSpec,
    Canvas,
    ColorTrack,
    Deck,
    KeyframeSpec,
    PositionKeyframeSpec,
    PositionTrack,
    TimingSpec,
)
from quickthumb.transitions import Push

FONT = str(Path(__file__).resolve().parents[1] / "assets/fonts/Roboto-Medium.ttf")


def scene(title: str, accent: str, *, reverse: bool = False) -> Canvas:
    canvas = Canvas(1080, 1920).background(color="#101820")
    canvas.text(
        "QUICKTHUMB / MOTION STUDY", position=(80, 100), font=FONT, size=30, color="#8FA6B6"
    )
    canvas.text(title, position=(80, 220), font=FONT, size=88, color="#F3F6F9")
    canvas.text(
        "Scrub the route. Inspect the change.",
        position=(80, 450),
        font=FONT,
        size=34,
        color="#B8C9D4",
    )
    canvas.shape("rectangle", (110, 540), 860, 900, "#1C2B39", border_radius=40)
    start, end = ((620, 550), (0, 0)) if reverse else ((0, 0), (620, 550))
    track = PositionTrack(
        keyframes=[
            PositionKeyframeSpec(time=0, value=start, out_tangent=(300, -180)),
            PositionKeyframeSpec(time=3, value=end, in_tangent=(-300, 180)),
        ]
    )
    color = ColorTrack(
        keyframes=[KeyframeSpec(time=0, value=accent), KeyframeSpec(time=3, value="#FFCC66")]
    )
    canvas.shape(
        "ellipse",
        (180, 720),
        100,
        100,
        accent,
        animation=AnimationSpec.timeline(
            track, color, easing="linear", timing=TimingSpec(duration=3, trigger="after_previous")
        ),
    )
    canvas.text(
        "02     FOLLOW THE TRANSITION" if reverse else "01     EXPLORE THE TIMELINE",
        position=(80, 1550),
        font=FONT,
        size=34,
        color="#F3F6F9",
    )
    canvas.text(
        "Proxy for motion. Full for pixels.",
        position=(80, 1640),
        font=FONT,
        size=32,
        color="#8FA6B6",
    )
    return canvas


deck = (
    Deck()
    .slide(scene("From idea\nto motion", "#44CFB2"), duration=4)
    .slide(
        scene("Another\nperspective", "#8AABFF", reverse=True),
        transition=Push(duration=0.75, direction="left"),
        duration=4,
    )
)
