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
        effects=[Filter(brightness=0.58, contrast=1.04, saturation=0.18)],
    )
    # 2. Gradient Overlay (Dark bottom-left to transparent top-right)
    # This ensures text readability on the left side
    .background(
        gradient=LinearGradient(
            angle=110,
            stops=[("#000000F5", 0.0), ("#000000D6", 0.48), ("#00000033", 1.0)],
        ),
    )
    .text(
        content="WORK / LIFE  —  FIELD GUIDE 05",
        size=17,
        color="#A1A1A6",
        weight=700,
        letter_spacing=3,
        position=(1216, 58),
        align=("right", "top"),
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
        size=118,
        color="#F5F5F7",
        position=(50, 122),
        weight=800,
    )
    # Headline Line 2: "OUT?"
    .text(
        content="OUT?",
        size=118,
        color="#D2D2D7",
        position=(50, 242),
        weight=800,
    )
    # 4. Footer / Hook
    .shape(
        shape="rectangle",
        position=(52, 546),
        width=540,
        height=1,
        color="#FFFFFF33",
    )
    .text(
        content="05",
        size=30,
        color="#FF9F0A",
        position=(52, 574),
        weight=800,
    )
    # "WARNING SIGNS"
    .text(
        content="WARNING SIGNS",
        size=28,
        color="#F5F5F7",
        position=(126, 576),
        weight=600,
    )
    # "YOU'RE IGNORING"
    .text(
        content="YOU'RE IGNORING",
        size=28,
        color="#A1A1A6",
        position=(126, 620),
        weight=500,
    )
    # Render
    .render(os.path.join(FILE_DIR, "youtube_thumbnail_02.png"))
)

print(f"✓ Thumbnail created: {os.path.join(FILE_DIR, 'youtube_thumbnail_02.png')}")
