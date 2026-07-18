"""A cinematic city-journal thumbnail with fashion-editorial typography."""

import os

from quickthumb import Canvas, Filter, FitMode, LinearGradient

FILE_DIR = os.path.dirname(__file__)
ASSETS_DIR = os.path.join(FILE_DIR, "..", "assets")
OUTPUT_PATH = os.path.join(FILE_DIR, "youtube_thumbnail_01.png")
DISPLAY = os.path.join(ASSETS_DIR, "fonts", "NotoSerif-ExtraBoldItalic.ttf")
SANS = os.path.join(ASSETS_DIR, "fonts", "Roboto-Medium.ttf")

(
    Canvas.from_aspect_ratio("16:9", 1280)
    .background(
        image=os.path.join(ASSETS_DIR, "images", "c-g-JgDUVGAXsso-unsplash.jpg"),
        fit=FitMode.COVER,
        effects=[Filter(brightness=0.82, contrast=1.08, saturation=0.62)],
    )
    .background(
        gradient=LinearGradient(
            angle=90,
            stops=[("#08162BF5", 0.0), ("#08162BC4", 0.5), ("#08162B10", 1.0)],
        )
    )
    .text(
        content="NIGHT STUDIES  /  SEOUL 07",
        font=SANS,
        size=20,
        color="#FFB547",
        weight=700,
        letter_spacing=3,
        position=(64, 58),
    )
    .text(
        content="THE CITY\nAFTER RAIN",
        font=DISPLAY,
        size=108,
        color="#F7F1E8",
        weight=700,
        line_height=1.02,
        letter_spacing=-4,
        position=(64, 162),
    )
    .shape(
        shape="rectangle",
        position=(64, 538),
        width=470,
        height=1,
        color="#F5F1E866",
    )
    .text(
        content="Light, sound, and the quiet choreography of a late commute",
        font=SANS,
        size=25,
        color="#D9D4C9",
        weight=400,
        position=(64, 570),
    )
    .text(
        content="06:42 PM  /  EULJIRO",
        font=SANS,
        size=17,
        color="#F5F1E899",
        weight=500,
        letter_spacing=2,
        position=(1216, 662),
        align=("right", "bottom"),
    )
    .render(OUTPUT_PATH)
)

print(f"✓ Editorial city thumbnail created: {OUTPUT_PATH}")
