"""
YouTube Reaction / Commentary Thumbnail

High-energy reaction format built entirely from text and shape layers:
- Dark base with a subtle image texture overlay at low opacity
- Giant reaction word with glow and stroke effects
- Stacked text hierarchy: "REACTING TO" badge, big word, secondary line
- Oversized decorative punctuation as a right-side graphic element
"""

import os

from quickthumb import Canvas, Grain, Stroke, TextPart

FILE_DIR = os.path.dirname(__file__)
ASSETS_DIR = os.path.join(FILE_DIR, "..", "assets")
OUTPUT_PATH = os.path.join(FILE_DIR, "youtube_reaction.png")

os.environ["QUICKTHUMB_FONT_DIR"] = os.path.join(ASSETS_DIR, "fonts")
os.environ["QUICKTHUMB_DEFAULT_FONT"] = "Roboto"

(
    Canvas(1280, 720)
    .background(color="#F0EEE8", effects=[Grain(intensity=0.018, monochrome=True, seed=11)])
    .text(
        content="COMMENTARY  /  SIGNAL 01",
        size=17,
        color="#1A1A18",
        weight=700,
        letter_spacing=3,
        position=(64, 54),
    )
    .shape(
        shape="rectangle",
        position=(64, 92),
        width=1152,
        height=2,
        color="#1A1A18",
    )
    .text(
        content="VIRAL",
        size=198,
        color="#171715",
        weight=900,
        letter_spacing=-5,
        position=(58, 124),
    )
    .text(
        content=[
            TextPart(text="TREND ", color="#171715", weight=700),
            TextPart(text="#1", color="#D84B32", weight=900),
        ],
        size=76,
        position=(64, 360),
    )
    .shape(
        shape="ellipse",
        position=(1000, 290),
        width=340,
        height=340,
        color="#F0EEE8",
        align=("center", "middle"),
        effects=[Stroke(width=3, color="#D84B32")],
    )
    .text(
        content="12.4M",
        size=104,
        color="#D84B32",
        weight=900,
        letter_spacing=-3,
        position=(1000, 245),
        align=("center", "middle"),
    )
    .text(
        content="VIEWS / 48H",
        size=19,
        color="#171715",
        weight=700,
        letter_spacing=3,
        position=(1000, 338),
        align=("center", "middle"),
    )
    .text(
        content="?!",
        size=66,
        color="#171715",
        weight=700,
        position=(1178, 536),
        align=("right", "top"),
    )
    .text(
        content="WHY IT WORKED — AND WHAT COMES NEXT",
        size=22,
        color="#5E5D58",
        weight=600,
        letter_spacing=2,
        position=(64, 642),
    )
    .shape(
        shape="rectangle",
        position=(64, 610),
        width=1152,
        height=1,
        color="#1A1A1844",
    )
    .outline(width=2, color="#171715")
    .render(OUTPUT_PATH)
)

print(f"✓ Reaction / commentary thumbnail created: {OUTPUT_PATH}")
