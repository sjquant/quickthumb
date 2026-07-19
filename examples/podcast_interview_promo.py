"""
Podcast / interview promo example.

Demonstrates:
- Remote image URLs for the background and speaker portraits
- Webfont loading from a URL for the show title
- Background removal on image overlays for cutout-style portraits
"""

import os

from quickthumb import Canvas, Filter, FitMode, LinearGradient
from quickthumb.models import Shadow

FILE_DIR = os.path.dirname(__file__)
ASSETS_DIR = os.path.join(FILE_DIR, "..", "assets")
OUTPUT_PATH = os.path.join(FILE_DIR, "podcast_interview_promo.png")

os.environ["QUICKTHUMB_FONT_DIR"] = os.path.join(ASSETS_DIR, "fonts")
os.environ["QUICKTHUMB_DEFAULT_FONT"] = "Roboto"

BACKGROUND_URL = (
    "https://images.unsplash.com/photo-1478737270239-2f02b77fc618?auto=format&fit=crop&w=1600&q=80"
)
GUEST_URL = (
    "https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=900&q=80"
)
SHOW_FONT_URL = "https://fonts.gstatic.com/s/dmserifdisplay/v17/-nFnOHM81r4j6k0gjAW3mujVU2B2K_c.ttf"

(
    Canvas(1280, 720)
    .background(
        image=BACKGROUND_URL,
        fit=FitMode.COVER,
        effects=[Filter(brightness=0.36, saturation=0.48, blur=2)],
    )
    .background(
        gradient=LinearGradient(
            angle=0,
            stops=[("#000000", 0.0), ("#000000F2", 0.5), ("#00000080", 1.0)],
        )
    )
    .text(
        content="NEW EPISODE  /  06",
        size=18,
        color="#A1A1A6",
        weight=800,
        letter_spacing=3,
        position=(64, 54),
    )
    .text(
        content="Signal to Noise",
        font=SHOW_FONT_URL,
        size=46,
        color="#F5F5F7",
        position=(62, 88),
    )
    .shape(
        shape="rectangle",
        position=(64, 158),
        width=78,
        height=4,
        color="#A1A1A6",
    )
    .text(
        content="HOW GREAT TEAMS\nBUILD BETTER\nFEEDBACK LOOPS",
        size=60,
        color="#F5F5F7",
        weight=700,
        line_height=1.04,
        position=(60, 196),
    )
    .text(
        content="A practical interview on shipping faster without breaking trust.",
        size=27,
        color="#A1A1A6",
        position=(64, 412),
        max_width=570,
        line_height=1.25,
    )
    .shape(
        shape="rectangle",
        position=(64, 536),
        width=420,
        height=1,
        color="#FFFFFF33",
    )
    .text(
        content="GUEST",
        size=15,
        color="#A1A1A6",
        weight=700,
        letter_spacing=3,
        position=(64, 558),
    )
    .text(
        content="Mina Park",
        font=SHOW_FONT_URL,
        size=38,
        color="#F5F5F7",
        position=(62, 582),
    )
    .text(
        content="AI Product Lead",
        size=19,
        color="#86868B",
        weight=500,
        position=(66, 630),
    )
    .shape(
        shape="rectangle",
        position=(872, 54),
        width=3,
        height=612,
        color="#FFFFFF33",
    )
    .image(
        path=GUEST_URL,
        position=(1095, 698),
        width=500,
        height=660,
        fit=FitMode.COVER,
        align=("center", "bottom"),
        remove_background=True,
        effects=[
            Shadow(offset_x=10, offset_y=18, color="#00000099", blur_radius=24),
        ],
    )
    .render(OUTPUT_PATH)
)

print(f"✓ Podcast / interview promo created: {OUTPUT_PATH}")
print("  This example requires network access and quickthumb[rembg] for portrait cutouts.")
