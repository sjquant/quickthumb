"""
YouTube Thumbnail Example

Creates an eye-catching YouTube-style thumbnail with:
- Background image (rainy/bokeh effect)
- Bold headline with neon green color and black stroke
- Subtitle text
- Bright neon green border
"""

from quickthumb import Canvas
from quickthumb.models import Stroke

# Create 16:9 YouTube thumbnail (1280x720) with method chaining
(
    Canvas.from_aspect_ratio("16:9", 1280)
    # Add background image (placeholder - you'll add your own image here)
    # For now, using a dark background as placeholder
    .background(image="examples/assets/c-g-JgDUVGAXsso-unsplash.jpg", brightness=0.7)
    # Add a semi-transparent overlay to darken the background
    # This helps text stand out better
    .background(color="#000000", opacity=0.3)
    # Add main headline with bold neon green text and black stroke
    .text(
        content="HOW TO MAKE\nTHUMBNAILS\nIN NO SECONDS",
        size=120,
        color="#B8FF00",  # Bright neon green
        position=("8%", "35%"),
        align=("left", "middle"),
        effects=[Stroke(width=8, color="#000000")],  # Black stroke for contrast
        bold=True,
    )
    # Add subtitle text
    .text(
        content="Try QuickThumb Today",
        size=48,
        color="#E0E0E0",  # Light gray
        position=("8%", "70%"),
        align=("left", "middle"),
    )
    # Add bright neon green border
    .outline(width=15, color="#B8FF00")
    # Render the thumbnail
    .render("examples/youtube_thumbnail_01.png")
)

print("✓ YouTube thumbnail created: examples/youtube_thumbnail_01.png")
print("  Replace the background and text content with your own.")
