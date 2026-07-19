"""
YouTube Thumbnail Example

Creates an eye-catching YouTube-style thumbnail with:
- Background image (rainy/bokeh effect)
- Bold headline with rich text (brand name highlighted)
- Bright neon green border
"""

import os

from quickthumb import Canvas, Filter, LinearGradient, TextPart

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
        effects=[Filter(brightness=0.76, contrast=1.08, saturation=0.5)],
    )
    # Add a semi-transparent overlay to darken the background
    # This helps text stand out better
    .background(
        gradient=LinearGradient(
            angle=90,
            stops=[("#000000FA", 0.0), ("#000000D6", 0.48), ("#00000014", 1.0)],
        )
    )
    .shape(
        shape="rectangle",
        position=("8%", "13%"),
        width=12,
        height=12,
        color="#0A84FF",
    )
    .text(
        content="QUICKTHUMB  /  FIELD GUIDE 01",
        size=18,
        color="#D2D2D7",
        weight=700,
        letter_spacing=3,
        position=("10.5%", "12.5%"),
    )
    # Add headline and subtitle as rich text with different sizes and colors
    .text(
        content=[
            TextPart(
                text="MAKE BETTER\nTHUMBNAILS\n",
                color="#F5F5F7",
            ),
            TextPart(
                text="IN MINUTES.",
                color="#0A84FF",
            ),
        ],
        size=108,
        line_height=0.98,
        position=("7%", "53%"),
        align=("left", "middle"),
        bold=True,
    )
    .shape(
        shape="rectangle",
        position=(1052, 88),
        width=1,
        height=512,
        color="#FFFFFF33",
    )
    .text(
        content="CODE  /  RENDER  /  SHIP",
        size=17,
        color="#A1A1A6",
        weight=600,
        line_height=1.8,
        letter_spacing=2,
        position=(1208, 68),
        align=("right", "top"),
    )
    .text(
        content="01",
        size=190,
        color="#0A84FF",
        opacity=0.9,
        weight=700,
        position=(1230, 690),
        align=("right", "bottom"),
    )
    # Add bright neon green border
    .outline(width=4, color="#0A84FF")
    # Render the thumbnail
    .render(os.path.join(FILE_DIR, "youtube_thumbnail_01.png"))
)

print(f"✓ YouTube thumbnail created: {os.path.join(FILE_DIR, 'youtube_thumbnail_01.png')}")
print("  Replace the background and text content with your own.")
