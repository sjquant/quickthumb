"""
YouTube Thumbnail Example - Burnout Theme (Redesigned)

Professional thumbnail with:
- High contrast typography (Roboto Black)
- Manual drop shadows (workaround for library limitation)
- Gradient overlay for depth
- Strong visual hierarchy
"""

import os

from quickthumb import Canvas, FitMode, LinearGradient
from quickthumb.models import Background, Stroke

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
        brightness=0.7,  # Darken original image
    )
    # 2. Gradient Overlay (Dark bottom-left to transparent top-right)
    # This ensures text readability on the left side
    .background(
        gradient=LinearGradient(
            angle=120, stops=[("#0f0f23", 0.0), ("#0f0f23cc", 0.4), ("#0f0f2300", 1.0)]
        ),
        opacity=1.0,
    )
    # 3. Typography
    # Subtitle: "ARE YOU"
    # Manual Shadow
    .text(
        content="ARE YOU",
        size=40,
        color="#000000",
        position=(53, 83),
        weight=900,
        letter_spacing=2,
    )
    # Main Text
    .text(
        content="ARE YOU",
        size=40,
        color="#fbbf24",  # Amber accent
        position=(50, 80),
        weight=900,
        letter_spacing=2,
    )
    # Headline Line 1: "BURNING"
    # Manual Shadow
    .text(
        content="BURNING",
        size=150,
        color="#000000",
        position=(58, 138),
        weight=900,
    )
    # Main Text
    .text(
        content="BURNING",
        size=150,
        color="#FFFFFF",
        position=(50, 130),
        weight=900,
    )
    # Headline Line 2: "OUT?"
    # Manual Shadow
    .text(
        content="OUT?",
        size=150,
        color="#000000",
        position=(58, 268),
        weight=900,
    )
    # Main Text
    .text(
        content="OUT?",
        size=150,
        color="#ff5722",  # Deep Orange
        position=(50, 260),
        weight=900,
        effects=[Stroke(width=3, color="#FFFFFF")],
    )
    # 4. Footer / Hook
    # "5" in a box
    .text(
        content="5",
        size=70,
        color="#0f0f23",
        position=(50, 580),
        weight=900,
        effects=[Background(color="#fbbf24", padding=(15, 25), border_radius=8)],
    )
    # "WARNING SIGNS"
    # Manual Shadow
    .text(
        content="WARNING SIGNS",
        size=45,
        color="#000000",
        position=(153, 583),
        weight=700,
    )
    .text(
        content="WARNING SIGNS",
        size=45,
        color="#FFFFFF",
        position=(150, 580),
        weight=700,
    )
    # "YOU'RE IGNORING"
    # Manual Shadow
    .text(
        content="YOU'RE IGNORING",
        size=45,
        color="#000000",
        position=(153, 638),
        weight=700,
    )
    .text(
        content="YOU'RE IGNORING",
        size=45,
        color="#fbbf24",
        position=(150, 635),
        weight=700,
    )
    # Render
    .render(os.path.join(FILE_DIR, "youtube_thumbnail_02.png"))
)

print(f"✓ Thumbnail created: {os.path.join(FILE_DIR, 'youtube_thumbnail_02.png')}")
