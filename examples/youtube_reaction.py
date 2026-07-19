"""
YouTube Reaction / Commentary Thumbnail

High-energy reaction format built entirely from text and shape layers:
- Dark base with a subtle image texture overlay at low opacity
- Giant reaction word with glow and stroke effects
- Stacked text hierarchy: "REACTING TO" badge, big word, secondary line
- Oversized decorative punctuation as a right-side graphic element
"""

import os

from quickthumb import Canvas, FitMode, LinearGradient, RadialGradient, Shadow, TextPart

FILE_DIR = os.path.dirname(__file__)
ASSETS_DIR = os.path.join(FILE_DIR, "..", "assets")
OUTPUT_PATH = os.path.join(FILE_DIR, "youtube_reaction.png")

os.environ["QUICKTHUMB_FONT_DIR"] = os.path.join(ASSETS_DIR, "fonts")
os.environ["QUICKTHUMB_DEFAULT_FONT"] = "Roboto"

PORTRAIT_URL = (
    "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=900&q=80"
)

(
    Canvas(1280, 720)
    .background(color="#000000")
    .background(
        gradient=RadialGradient(
            center=(0.82, 0.48),
            stops=[("#3D1110", 0.0), ("#000000", 0.68)],
        )
    )
    .background(
        gradient=LinearGradient(
            angle=90,
            stops=[("#000000", 0.0), ("#000000E8", 0.46), ("#00000011", 1.0)],
        )
    )
    .text(
        content="#1",
        size=470,
        color="#FF453A",
        opacity=0.13,
        weight=900,
        letter_spacing=-18,
        position=(1210, 28),
        align=("right", "top"),
    )
    .shape(
        shape="ellipse",
        position=(1034, 372),
        width=548,
        height=548,
        color="#1C1C1E",
        align=("center", "middle"),
    )
    .image(
        path=PORTRAIT_URL,
        position=(1280, 720),
        width=620,
        height=710,
        fit=FitMode.COVER,
        align=("right", "bottom"),
        remove_background=True,
        effects=[Shadow(offset_x=-12, offset_y=12, color="#00000099", blur_radius=26)],
    )
    .text(
        content="COMMENTARY  /  48H SIGNAL",
        size=17,
        color="#A1A1A6",
        weight=700,
        letter_spacing=3,
        position=(64, 54),
    )
    .shape(
        shape="rectangle",
        position=(64, 92),
        width=610,
        height=1,
        color="#FFFFFF33",
    )
    .text(
        content="VIRAL",
        size=212,
        color="#F5F5F7",
        weight=900,
        letter_spacing=-5,
        position=(52, 104),
    )
    .text(
        content=[
            TextPart(text="TREND ", color="#A1A1A6", weight=600),
            TextPart(text="#1", color="#FF453A", weight=800),
        ],
        size=80,
        position=(60, 344),
    )
    .text(
        content="12.4M",
        size=82,
        color="#F5F5F7",
        weight=700,
        letter_spacing=-2,
        position=(60, 474),
    )
    .text(
        content="VIEWS / 48H",
        size=16,
        color="#86868B",
        weight=700,
        letter_spacing=3,
        position=(64, 568),
    )
    .text(
        content="WHY IT WORKED — AND WHAT COMES NEXT",
        size=19,
        color="#A1A1A6",
        weight=600,
        letter_spacing=2,
        position=(64, 650),
    )
    .shape(
        shape="rectangle",
        position=(64, 620),
        width=610,
        height=1,
        color="#FFFFFF33",
    )
    .render(OUTPUT_PATH)
)

print(f"✓ Reaction / commentary thumbnail created: {OUTPUT_PATH}")
