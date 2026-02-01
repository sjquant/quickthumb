"""
YouTube Thumbnail Example

Creates an eye-catching YouTube-style thumbnail with:
- Background image (rainy/bokeh effect)
- Bold headline with rich text (brand name highlighted)
- Bright neon green border
"""

import os

from quickthumb import Canvas, TextPart
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
        image=os.path.join(ASSETS_DIR, "images", "c-g-JgDUVGAXsso-unsplash.jpg"), brightness=0.7
    )
    # Add a semi-transparent overlay to darken the background
    # This helps text stand out better
    .background(color="#000000", opacity=0.6)
    # Add headline and subtitle as rich text with different sizes and colors
    .text(
        content=[
            TextPart(
                text="HOW TO MAKE\nTHUMBNAILS\nIN NO SECONDS\n",
                color="#B8FF00",
                effects=[Stroke(width=8, color="#000000")],
            ),
            TextPart(
                text="Try Quickthumb Today",
                color="#E0E0E0",
                size=48,
                effects=[Stroke(width=4, color="#000000")],
            ),
        ],
        size=120,
        position=("8%", "50%"),
        align=("left", "middle"),
        bold=True,
    )
    # Add bright neon green border
    .outline(width=15, color="#B8FF00")
    # Render the thumbnail
    .render(os.path.join(FILE_DIR, "youtube_thumbnail_01.png"))
)

print(f"✓ YouTube thumbnail created: {os.path.join(FILE_DIR, 'youtube_thumbnail_01.png')}")
print("  Replace the background and text content with your own.")
