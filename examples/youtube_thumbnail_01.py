"""
YouTube Thumbnail Example

Creates an eye-catching YouTube-style thumbnail with:
- Background image (rainy/bokeh effect)
- Bold headline with rich text (brand name highlighted)
- Bright neon green border
"""

import os

from quickthumb import Canvas, Filter, LinearGradient, Shadow, Stroke, TextPart

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
        content="BEFORE  /  AFTER",
        size=18,
        color="#D2D2D7",
        weight=700,
        letter_spacing=3,
        position=("10.5%", "12.5%"),
    )
    # Add headline and subtitle as rich text with different sizes and colors
    .text(
        content=[
            TextPart(text="BETTER\n", color="#F5F5F7", size=96),
            TextPart(text="THUMBNAILS.\n", color="#F5F5F7", size=78),
            TextPart(text="FASTER.", color="#0A84FF", size=96),
        ],
        size=96,
        line_height=0.98,
        position=("7%", "54%"),
        align=("left", "middle"),
        bold=True,
    )
    .shape(
        shape="rectangle",
        position=(832, 370),
        width=260,
        height=300,
        color="#242426",
        border_radius=16,
        rotation=-7,
        align=("center", "middle"),
        effects=[Stroke(width=2, color="#FFFFFF55")],
    )
    .text(
        content="BEFORE\nTOO MUCH\nNO FOCUS",
        size=22,
        color="#A1A1A6",
        weight=700,
        line_height=1.7,
        letter_spacing=1,
        position=(750, 270),
        rotation=-7,
    )
    .shape(
        shape="rectangle",
        position=(1054, 366),
        width=300,
        height=340,
        color="#0A84FF",
        border_radius=18,
        rotation=5,
        align=("center", "middle"),
        effects=[
            Stroke(width=2, color="#FFFFFFAA"),
            Shadow(offset_x=0, offset_y=18, color="#00000088", blur_radius=24),
        ],
    )
    .text(
        content="AFTER\nONE IDEA.\nONE FOCUS.",
        size=28,
        color="#FFFFFF",
        weight=800,
        line_height=1.55,
        position=(958, 248),
        rotation=5,
    )
    # Render the thumbnail
    .render(os.path.join(FILE_DIR, "youtube_thumbnail_01.png"))
)

print(f"✓ YouTube thumbnail created: {os.path.join(FILE_DIR, 'youtube_thumbnail_01.png')}")
print("  Replace the background and text content with your own.")
