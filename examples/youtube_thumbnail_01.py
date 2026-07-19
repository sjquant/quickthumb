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
        effects=[Filter(brightness=0.68, contrast=1.04, saturation=0.52)],
    )
    # Add a semi-transparent overlay to darken the background
    # This helps text stand out better
    .background(
        gradient=LinearGradient(
            angle=90,
            stops=[("#0B1424F7", 0.0), ("#0B1424D9", 0.52), ("#0B142438", 1.0)],
        )
    )
    .shape(
        shape="rectangle",
        position=("8%", "13%"),
        width=12,
        height=12,
        color="#86A9E6",
    )
    .text(
        content="QUICKTHUMB  /  FIELD GUIDE 01",
        size=18,
        color="#D7DCE5",
        weight=700,
        letter_spacing=3,
        position=("10.5%", "12.5%"),
    )
    # Add headline and subtitle as rich text with different sizes and colors
    .text(
        content=[
            TextPart(
                text="MAKE BETTER\nTHUMBNAILS\n",
                color="#F2F3F5",
            ),
            TextPart(
                text="IN MINUTES\n",
                color="#86A9E6",
            ),
            TextPart(
                text="A practical workflow for faster creative output.",
                color="#B8C0CC",
                size=28,
            ),
        ],
        size=96,
        line_height=1.04,
        position=("8%", "51%"),
        align=("left", "middle"),
        bold=True,
    )
    .shape(
        shape="rectangle",
        position=(1040, 104),
        width=1,
        height=512,
        color="#D7DCE555",
    )
    .text(
        content="CODE\nRENDER\nSHIP",
        size=17,
        color="#D7DCE5",
        weight=600,
        line_height=1.8,
        letter_spacing=2,
        position=(1080, 112),
    )
    .text(
        content="01",
        size=72,
        color="#86A9E6",
        weight=500,
        position=(1192, 606),
        align=("right", "bottom"),
    )
    # Add bright neon green border
    .outline(width=2, color="#D7DCE5")
    # Render the thumbnail
    .render(os.path.join(FILE_DIR, "youtube_thumbnail_01.png"))
)

print(f"✓ YouTube thumbnail created: {os.path.join(FILE_DIR, 'youtube_thumbnail_01.png')}")
print("  Replace the background and text content with your own.")
