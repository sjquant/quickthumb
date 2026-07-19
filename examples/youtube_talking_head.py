"""
YouTube Talking-Head Thumbnail

Classic split layout with subject on the right and headline on the left:
- Background image with darkened filter and left-to-right gradient
- Subject portrait positioned bottom-right (remote URL, swap for your own)
- Topic badge using shape and text layers
- Bold left-aligned headline with rich text accents
"""

import os

from quickthumb import Canvas, FitMode, LinearGradient, Shadow, Stroke, TextPart

FILE_DIR = os.path.dirname(__file__)
ASSETS_DIR = os.path.join(FILE_DIR, "..", "assets")
OUTPUT_PATH = os.path.join(FILE_DIR, "youtube_talking_head.png")

os.environ["QUICKTHUMB_FONT_DIR"] = os.path.join(ASSETS_DIR, "fonts")
os.environ["QUICKTHUMB_DEFAULT_FONT"] = "Roboto"

# Replace with your subject photo (local path or URL)
PORTRAIT_URL = (
    "https://images.unsplash.com/photo-1560250097-0b93528c311a?auto=format&fit=crop&w=900&q=80"
)

(
    Canvas(1280, 720)
    .background(color="#000000")
    .background(
        gradient=LinearGradient(
            angle=90,
            stops=[("#000000", 0.0), ("#000000E8", 0.48), ("#00000011", 1.0)],
        )
    )
    .shape(
        shape="rectangle",
        position=(840, 0),
        width=440,
        height=720,
        color="#0A84FF",
    )
    .shape(
        shape="rectangle",
        position=(52, 132),
        width=56,
        height=5,
        color="#0A84FF",
        border_radius=3,
    )
    .text(
        content="30-DAY REVIEW",
        size=18,
        color="#A1A1A6",
        weight=900,
        letter_spacing=1,
        position=(52, 64),
    )
    # Main headline: stacked rich text with accent highlight
    .text(
        content=[
            TextPart(text="AI TOOLS.\n", color="#FFFFFF", weight=800),
            TextPart(text="WHAT ACTUALLY\nWORKS.", color="#0A84FF", weight=900),
        ],
        size=92,
        line_height=0.92,
        position=(48, 142),
        max_width="55%",
        effects=[
            Stroke(width=1, color="#000000"),
            Shadow(offset_x=0, offset_y=8, color="#00000099", blur_radius=14),
        ],
    )
    # Sub-copy anchored near the bottom
    .text(
        content="24 TESTED.  3 KEPT.",
        size=32,
        color="#D4D4D4",
        weight=500,
        position=(52, 620),
        effects=[Shadow(offset_x=2, offset_y=2, color="#000000", blur_radius=6)],
    )
    # Subject portrait — bottom-anchored on the right side
    .image(
        path=PORTRAIT_URL,
        position=(1280, 720),
        width=570,
        height=710,
        fit=FitMode.COVER,
        align=("right", "bottom"),
        remove_background=True,
        effects=[Shadow(offset_x=-14, offset_y=0, color="#00000088", blur_radius=22)],
    )
    .render(OUTPUT_PATH)
)

print(f"✓ Talking-head thumbnail created: {OUTPUT_PATH}")
print("  Replace PORTRAIT_URL with your subject photo for a personalised layout.")
