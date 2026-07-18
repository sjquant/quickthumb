"""
YouTube Reaction / Commentary Thumbnail

High-energy reaction format built entirely from text and shape layers:
- Dark base with a subtle image texture overlay at low opacity
- Giant reaction word with glow and stroke effects
- Stacked text hierarchy: "REACTING TO" badge, big word, secondary line
- Oversized decorative punctuation as a right-side graphic element
"""

import os

from quickthumb import Canvas, Filter, FitMode, Glow, Shadow, Stroke, TextPart

FILE_DIR = os.path.dirname(__file__)
ASSETS_DIR = os.path.join(FILE_DIR, "..", "assets")
OUTPUT_PATH = os.path.join(FILE_DIR, "youtube_reaction.png")

os.environ["QUICKTHUMB_FONT_DIR"] = os.path.join(ASSETS_DIR, "fonts")
os.environ["QUICKTHUMB_DEFAULT_FONT"] = "Roboto"

(
    Canvas(1280, 720)
    # Deep dark base
    .background(color="#0D0D0D")
    # Subtle image texture blended at low opacity for visual depth
    .background(
        image=os.path.join(ASSETS_DIR, "images", "c-g-JgDUVGAXsso-unsplash.jpg"),
        fit=FitMode.COVER,
        blend_mode="overlay",
        opacity=0.12,
        effects=[Filter(blur=3)],
    )
    # "REACTING TO" badge
    .shape(
        shape="rectangle",
        position=(48, 48),
        width=272,
        height=56,
        color="#FF4500",
        border_radius=28,
        effects=[Shadow(offset_x=0, offset_y=6, color="#00000088", blur_radius=12)],
    )
    .text(
        content="REACTING TO",
        size=26,
        color="#FFFFFF",
        weight=900,
        letter_spacing=3,
        position=(184, 76),
        align=("center", "middle"),
    )
    # Framed signal panel gives the decorative punctuation a clear visual role
    .shape(
        shape="rectangle",
        position=(838, 126),
        width=368,
        height=420,
        color="#121212",
        border_radius=24,
        opacity=0.92,
        effects=[Stroke(width=1, color="#FFFFFF20")],
    )
    .text(
        content="48H SIGNAL",
        size=20,
        color="#A3A3A3",
        weight=700,
        letter_spacing=3,
        position=(882, 166),
    )
    .text(
        content="?!",
        size=280,
        color="#FF450033",
        weight=900,
        position=(1022, 330),
        align=("center", "middle"),
        rotation=-12,
    )
    .text(
        content="12.4M VIEWS",
        size=28,
        color="#F5F5F5",
        weight=900,
        letter_spacing=1,
        position=(882, 490),
    )
    # Giant reaction word
    .text(
        content="VIRAL",
        size=176,
        color="#FF4500",
        weight=900,
        position=(52, 130),
        effects=[
            Stroke(width=2, color="#000000"),
            Glow(color="#FF4500", radius=14, opacity=0.18),
            Shadow(offset_x=0, offset_y=8, color="#000000AA", blur_radius=12),
        ],
    )
    # Secondary text line with accent number
    .text(
        content=[
            TextPart(text="TREND ", color="#FFFFFF", weight=900),
            TextPart(text="#1", color="#FFD700", weight=900),
        ],
        size=88,
        position=(52, 365),
        effects=[
            Stroke(width=2, color="#000000"),
            Shadow(offset_x=0, offset_y=6, color="#00000099", blur_radius=10),
        ],
    )
    # Bottom commentary label
    .text(
        content="WHY IT WORKED — AND WHAT COMES NEXT",
        size=30,
        color="#A3A3A3",
        weight=700,
        letter_spacing=1,
        position=(52, 624),
        effects=[Shadow(offset_x=2, offset_y=2, color="#000000", blur_radius=4)],
    )
    .outline(width=4, color="#FF4500")
    .render(OUTPUT_PATH)
)

print(f"✓ Reaction / commentary thumbnail created: {OUTPUT_PATH}")
