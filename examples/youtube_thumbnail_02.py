"""
YouTube Thumbnail Example - Burnout Theme (Redesigned)

Professional thumbnail with:
- High contrast typography (Roboto Black)
- Drop shadows using the Shadow effect
- Gradient overlay for depth
- Strong visual hierarchy
"""

import os

from quickthumb import Canvas, Filter, FitMode, LinearGradient

FILE_DIR = os.path.dirname(__file__)
ASSETS_DIR = os.path.join(FILE_DIR, "..", "assets")

os.environ["QUICKTHUMB_FONT_DIR"] = os.path.join(ASSETS_DIR, "fonts")
os.environ["QUICKTHUMB_DEFAULT_FONT"] = "Roboto"

# Canvas dimensions
WIDTH = 1280
HEIGHT = 720

(
    Canvas(WIDTH, HEIGHT)
    # 1. Background Image with darkening
    .background(
        image=os.path.join(ASSETS_DIR, "images", "denise-jans-WIRvXd1PYlg-unsplash.jpg"),
        fit=FitMode.COVER,
        effects=[Filter(brightness=0.78, contrast=1.12, saturation=0.32)],
    )
    # 2. Gradient Overlay (Dark bottom-left to transparent top-right)
    # This ensures text readability on the left side
    .background(
        gradient=LinearGradient(
            angle=110,
            stops=[("#000000F7", 0.0), ("#000000B8", 0.44), ("#00000012", 1.0)],
        ),
    )
    # 3. Typography
    # Subtitle: "ARE YOU"
    .text(
        content="ARE YOU",
        size=20,
        color="#FF9F0A",
        position=(54, 74),
        weight=700,
        letter_spacing=3,
    )
    # Headline Line 1: "BURNING"
    .text(
        content="BURNING",
        size=148,
        color="#F5F5F7",
        position=(46, 108),
        weight=800,
    )
    # Headline Line 2: "OUT?"
    .text(
        content="OUT?",
        size=148,
        color="#FF9F0A",
        position=(46, 250),
        weight=800,
    )
    # 4. Footer / Hook
    .shape(
        shape="rectangle",
        position=(52, 554),
        width=620,
        height=1,
        color="#FFFFFF33",
    )
    .text(
        content="5 SIGNS YOU'RE IGNORING",
        size=32,
        color="#F5F5F7",
        position=(52, 592),
        weight=600,
    )
    # Render
    .render(os.path.join(FILE_DIR, "youtube_thumbnail_02.png"))
)

print(f"✓ Thumbnail created: {os.path.join(FILE_DIR, 'youtube_thumbnail_02.png')}")
