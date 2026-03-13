"""
YouTube Talking-Head Thumbnail

Classic split layout with subject on the right and headline on the left:
- Background image with darkened filter and left-to-right gradient
- Subject portrait positioned bottom-right (remote URL, swap for your own)
- Topic badge using shape and text layers
- Bold left-aligned headline with rich text accents
"""

import os

from quickthumb import Canvas, Filter, FitMode, LinearGradient, Shadow, Stroke, TextPart

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
    # Background image with darkening
    .background(
        image=os.path.join(ASSETS_DIR, "images", "tobias-rademacher-wnF27F85ZKw-unsplash.jpg"),
        fit=FitMode.COVER,
        effects=[Filter(brightness=0.5, saturation=0.75)],
    )
    # Left-to-right gradient: dark on left for text legibility, transparent on right
    .background(
        gradient=LinearGradient(
            angle=90,
            stops=[("#0A0A0A", 0.0), ("#0A0A0ACC", 0.48), ("#0A0A0A00", 1.0)],
        )
    )
    # Topic badge
    .shape(
        shape="rectangle",
        position=(52, 56),
        width=244,
        height=52,
        color="#E53E3E",
        border_radius=8,
        effects=[Shadow(offset_x=0, offset_y=6, color="#00000066", blur_radius=10)],
    )
    .text(
        content="MY HONEST REVIEW",
        size=22,
        color="#FFFFFF",
        weight=900,
        letter_spacing=1,
        position=(174, 82),
        align=("center", "middle"),
    )
    # Main headline: stacked rich text with accent highlight
    .text(
        content=[
            TextPart(text="THE TRUTH\nABOUT\n", color="#FFFFFF", weight=900),
            TextPart(text="AI TOOLS", color="#FFD700", weight=900),
        ],
        size=96,
        line_height=0.95,
        position=(52, 155),
        align=("left", "top"),
        max_width="52%",
        effects=[
            Stroke(width=4, color="#000000"),
            Shadow(offset_x=4, offset_y=4, color="#000000", blur_radius=8),
        ],
    )
    # Sub-copy anchored near the bottom
    .text(
        content="What nobody tells you",
        size=36,
        color="#D4D4D4",
        weight=500,
        position=(52, 620),
        effects=[Shadow(offset_x=2, offset_y=2, color="#000000", blur_radius=6)],
    )
    # Subject portrait — bottom-anchored on the right side
    .image(
        path=PORTRAIT_URL,
        position=(1280, 720),
        width=480,
        height=680,
        fit=FitMode.COVER,
        align=("right", "bottom"),
        remove_background=True,
        effects=[Shadow(offset_x=-14, offset_y=0, color="#00000088", blur_radius=22)],
    )
    .outline(width=12, color="#FFD700")
    .render(OUTPUT_PATH)
)

print(f"✓ Talking-head thumbnail created: {OUTPUT_PATH}")
print("  Replace PORTRAIT_URL with your subject photo for a personalised layout.")
