"""
Social preview card for the docs site (1200x630, the Open Graph size).

The image link previews show for quickthumb.solaqua.dev is rendered by
quickthumb itself:
- Brand icon and wordmark, two-tone headline built from TextParts
- Two real example renders as tilted "output" cards with shadows
- Only bundled fonts and images, so it renders the same offline
"""

import os

from quickthumb import Canvas, Shadow, Stroke, TextPart

FILE_DIR = os.path.dirname(__file__)
REPO_DIR = os.path.abspath(os.path.join(FILE_DIR, ".."))
ASSETS_DIR = os.path.join(REPO_DIR, "assets")
DOCS_ASSETS_DIR = os.path.join(REPO_DIR, "docs", "assets")
OUTPUT_PATH = os.path.join(DOCS_ASSETS_DIR, "brand", "social-preview.png")

os.environ["QUICKTHUMB_FONT_DIR"] = os.path.join(ASSETS_DIR, "fonts")
os.environ["QUICKTHUMB_DEFAULT_FONT"] = "Roboto"

# Name the family on each text layer: weight is only applied to a named font.
FONT = "Roboto"

NAVY = "#0A1730"
BLUE = "#7FADFF"
WHITE = "#F5F7FB"
MUTED = "#A9BBD4"
CARD_EFFECTS = [
    Stroke(width=1, color="#FFFFFF33"),
    Shadow(offset_x=0, offset_y=18, color="#000000AA", blur_radius=28),
]

canvas = (
    Canvas(1200, 630)
    .background(color=NAVY)
    .image(
        path=os.path.join(DOCS_ASSETS_DIR, "brand", "quickthumb-icon.png"),
        position=(72, 64),
        width=64,
        height=64,
    )
    .text(
        content="quickthumb",
        font=FONT,
        size=34,
        weight=700,
        color=WHITE,
        position=(150, 96),
        align=("left", "middle"),
    )
    .text(
        content=[
            TextPart(text="Thumbnails,\n", color=WHITE),
            TextPart(text="from code.", color=BLUE),
        ],
        font=FONT,
        size=86,
        weight=800,
        line_height=1.02,
        letter_spacing=-2,
        position=(70, 196),
    )
    .text(
        content="Layers in Python or JSON.\nPNG, SVG, PDF, PPTX, and video out.",
        font=FONT,
        size=28,
        weight=500,
        color=MUTED,
        line_height=1.4,
        position=(72, 440),
    )
    # Back card: a real example render
    .image(
        path=os.path.join(DOCS_ASSETS_DIR, "examples", "youtube_reaction.png"),
        position=(930, 250),
        width=440,
        height=248,
        fit="cover",
        border_radius=14,
        rotation=7,
        align=("center", "middle"),
        effects=CARD_EFFECTS,
    )
    # Front card: the home page demo
    .image(
        path=os.path.join(DOCS_ASSETS_DIR, "home", "demo-thumbnail.png"),
        position=(880, 420),
        width=440,
        height=248,
        fit="cover",
        border_radius=14,
        rotation=-4,
        align=("center", "middle"),
        effects=CARD_EFFECTS,
    )
)

canvas.render(OUTPUT_PATH)
print(f"✓ Social preview created: {OUTPUT_PATH}")
