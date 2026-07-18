"""
YouTube Thumbnail Example

Creates an eye-catching YouTube-style thumbnail with:
- Background image (rainy/bokeh effect)
- Bold headline with rich text (brand name highlighted)
- Bright neon green border
"""

import os

from quickthumb import Canvas, Filter, LinearGradient, Shadow, TextPart
from quickthumb.models import Stroke

FILE_DIR = os.path.dirname(__file__)
ASSETS_DIR = os.path.join(FILE_DIR, "..", "assets")

os.environ["QUICKTHUMB_FONT_DIR"] = os.path.join(ASSETS_DIR, "fonts")
os.environ["QUICKTHUMB_DEFAULT_FONT"] = "Roboto"

# Create 16:9 YouTube thumbnail (1280x720) with method chaining
(
    Canvas.from_aspect_ratio("16:9", 1280)
    # Add background image (placeholder - you'll add your own image here)
    # For now, using a dark background as placeholder
    .background(
        image=os.path.join(ASSETS_DIR, "images", "c-g-JgDUVGAXsso-unsplash.jpg"),
        effects=[Filter(brightness=0.78, contrast=1.06, saturation=0.9)],
    )
    # Add a semi-transparent overlay to darken the background
    # This helps text stand out better
    .background(
        gradient=LinearGradient(
            angle=90,
            stops=[("#050805F2", 0.0), ("#050805C7", 0.48), ("#0508052E", 1.0)],
        )
    )
    .text(
        content="QUICKTHUMB  /  CREATOR SERIES",
        size=22,
        color="#D8E0D5",
        weight=700,
        letter_spacing=3,
        position=("8%", "16%"),
    )
    # Add headline and subtitle as rich text with different sizes and colors
    .text(
        content=[
            TextPart(
                text="MAKE BETTER\nTHUMBNAILS\n",
                color="#F7F9F5",
                effects=[Stroke(width=2, color="#081008")],
            ),
            TextPart(
                text="IN MINUTES\n",
                color="#B8FF00",
                effects=[Stroke(width=2, color="#081008")],
            ),
            TextPart(
                text="A practical workflow for faster creative output",
                color="#D8E0D5",
                size=32,
            ),
        ],
        size=100,
        line_height=1.02,
        position=("8%", "53%"),
        align=("left", "middle"),
        bold=True,
        effects=[Shadow(offset_x=0, offset_y=8, color="#00000099", blur_radius=16)],
    )
    # Add bright neon green border
    .outline(width=6, color="#B8FF00")
    # Render the thumbnail
    .render(os.path.join(FILE_DIR, "youtube_thumbnail_01.png"))
)

print(f"✓ YouTube thumbnail created: {os.path.join(FILE_DIR, 'youtube_thumbnail_01.png')}")
print("  Replace the background and text content with your own.")
