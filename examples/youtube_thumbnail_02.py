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
from quickthumb.models import Background, Shadow, Stroke

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
        effects=[Filter(brightness=0.7)],  # Darken original image
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
    .text(
        content="ARE YOU",
        size=40,
        color="#fbbf24",  # Amber accent
        position=(50, 80),
        weight=900,
        letter_spacing=2,
        effects=[Shadow(offset_x=3, offset_y=3, color="#000000", blur_radius=0)],
    )
    # Headline Line 1: "BURNING"
    .text(
        content="BURNING",
        size=150,
        color="#FFFFFF",
        position=(50, 130),
        weight=900,
        effects=[Shadow(offset_x=8, offset_y=8, color="#000000", blur_radius=0)],
    )
    # Headline Line 2: "OUT?"
    .text(
        content="OUT?",
        size=150,
        color="#ff5722",  # Deep Orange
        position=(50, 260),
        weight=900,
        effects=[
            Stroke(width=3, color="#FFFFFF"),
            Shadow(offset_x=8, offset_y=8, color="#000000", blur_radius=0),
        ],
    )
    # 4. Footer / Hook
    # "5" in a box
    .text(
        content="5",
        size=70,
        color="#0f0f23",
        position=(50, 580),
        weight=900,
        effects=[
            Background(color="#fbbf24", padding=(15, 25), border_radius=8),
            Shadow(offset_x=4, offset_y=4, color="#000000", blur_radius=4),
        ],
    )
    # "WARNING SIGNS"
    .text(
        content="WARNING SIGNS",
        size=45,
        color="#FFFFFF",
        position=(150, 580),
        weight=700,
        effects=[Shadow(offset_x=3, offset_y=3, color="#000000", blur_radius=0)],
    )
    # "YOU'RE IGNORING"
    .text(
        content="YOU'RE IGNORING",
        size=45,
        color="#fbbf24",
        position=(150, 635),
        weight=700,
        effects=[Shadow(offset_x=3, offset_y=3, color="#000000", blur_radius=0)],
    )
    # Render
    .render(os.path.join(FILE_DIR, "youtube_thumbnail_02.png"))
)

print(f"✓ Thumbnail created: {os.path.join(FILE_DIR, 'youtube_thumbnail_02.png')}")
