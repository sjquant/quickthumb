"""
Podcast / interview promo example.

Demonstrates:
- Local editorial portrait assets used as full-bleed backgrounds
- Webfont loading from a URL for the show title
- Tonal gradients that preserve portrait detail behind high-contrast copy
"""

import os

from quickthumb import Canvas, FitMode, LinearGradient

FILE_DIR = os.path.dirname(__file__)
ASSETS_DIR = os.path.join(FILE_DIR, "..", "assets")
OUTPUT_PATH = os.path.join(FILE_DIR, "podcast_interview_promo.png")

os.environ["QUICKTHUMB_FONT_DIR"] = os.path.join(ASSETS_DIR, "fonts")
os.environ["QUICKTHUMB_DEFAULT_FONT"] = "Roboto"

GUEST_IMAGE_PATH = os.path.join(ASSETS_DIR, "images", "podcast-guest-editorial.png")
SHOW_FONT_URL = "https://fonts.gstatic.com/s/dmserifdisplay/v17/-nFnOHM81r4j6k0gjAW3mujVU2B2K_c.ttf"

(
    Canvas(1280, 720)
    .background(
        image=GUEST_IMAGE_PATH,
        fit=FitMode.COVER,
    )
    .background(
        gradient=LinearGradient(
            angle=0,
            stops=[
                ("#000000", 0.0),
                ("#000000F7", 0.48),
                ("#00000030", 0.72),
                ("#00000000", 1.0),
            ],
        )
    )
    .text(
        content="EPISODE 06",
        size=18,
        color="#A1A1A6",
        weight=800,
        letter_spacing=3,
        position=(64, 54),
    )
    .text(
        content="Signal to Noise",
        font=SHOW_FONT_URL,
        size=50,
        color="#F5F5F7",
        position=(62, 88),
    )
    .shape(
        shape="rectangle",
        position=(64, 158),
        width=96,
        height=6,
        color="#FF453A",
    )
    .text(
        content="HOW GREAT TEAMS\nBUILD BETTER\nFEEDBACK LOOPS",
        size=68,
        color="#F5F5F7",
        weight=700,
        line_height=0.98,
        position=(58, 188),
    )
    .text(
        content="Shipping faster — without breaking trust.",
        size=27,
        color="#A1A1A6",
        position=(64, 424),
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
    .render(OUTPUT_PATH)
)

print(f"✓ Podcast / interview promo created: {OUTPUT_PATH}")
print("  This example requires network access only for the display webfont.")
