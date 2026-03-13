"""
Podcast / interview promo example.

Demonstrates:
- Remote image URLs for the background and speaker portraits
- Webfont loading from a URL for the show title
- Background removal on image overlays for cutout-style portraits
"""

import os

from quickthumb import Canvas, Filter, FitMode, LinearGradient
from quickthumb.models import Background, Shadow, Stroke

FILE_DIR = os.path.dirname(__file__)
ASSETS_DIR = os.path.join(FILE_DIR, "..", "assets")
OUTPUT_PATH = os.path.join(FILE_DIR, "podcast_interview_promo.png")

os.environ["QUICKTHUMB_FONT_DIR"] = os.path.join(ASSETS_DIR, "fonts")
os.environ["QUICKTHUMB_DEFAULT_FONT"] = "Roboto"

BACKGROUND_URL = (
    "https://images.unsplash.com/photo-1478737270239-2f02b77fc618"
    "?auto=format&fit=crop&w=1600&q=80"
)
GUEST_URL = (
    "https://images.unsplash.com/photo-1494790108377-be9c29b29330"
    "?auto=format&fit=crop&w=900&q=80"
)
SHOW_FONT_URL = (
    "https://fonts.gstatic.com/s/pacifico/v22/FwZY7-Qmy14u9lezJ-6H6MmBp0u-.woff2"
)

(
    Canvas(1280, 720)
    .background(
        image=BACKGROUND_URL,
        fit=FitMode.COVER,
        effects=[Filter(brightness=0.42, saturation=0.75, blur=2)],
    )
    .background(
        gradient=LinearGradient(
            angle=0,
            stops=[("#07111F", 0.0), ("#07111FE8", 0.45), ("#07111F70", 1.0)],
        )
    )
    .shape(
        shape="rectangle",
        position=(56, 48),
        width=220,
        height=54,
        color="#F04D23",
        border_radius=18,
        effects=[Shadow(offset_x=0, offset_y=8, color="#00000066", blur_radius=14)],
    )
    .text(
        content="NEW EPISODE",
        size=24,
        color="#FFF7F2",
        weight=900,
        letter_spacing=2,
        position=(166, 75),
        align=("center", "middle"),
    )
    .text(
        content="Signal to Noise",
        font=SHOW_FONT_URL,
        size=62,
        color="#8CE1FF",
        position=(60, 130),
        effects=[Shadow(offset_x=0, offset_y=6, color="#021018CC", blur_radius=12)],
    )
    .text(
        content="HOW GREAT TEAMS\nBUILD BETTER\nFEEDBACK LOOPS",
        size=70,
        color="#FFFFFF",
        weight=900,
        line_height=1.0,
        position=(60, 220),
        effects=[
            Stroke(width=3, color="#04111A"),
            Shadow(offset_x=0, offset_y=10, color="#00000099", blur_radius=18),
        ],
    )
    .text(
        content="A practical interview on shipping faster without breaking trust.",
        size=34,
        color="#C7D5E0",
        position=(64, 415),
        max_width=600,
        line_height=1.2,
        effects=[Shadow(offset_x=0, offset_y=4, color="#00000080", blur_radius=8)],
    )
    .shape(
        shape="rectangle",
        position=(62, 530),
        width=430,
        height=120,
        color="#0E2436",
        border_radius=28,
        opacity=0.92,
        effects=[
            Stroke(width=2, color="#8CE1FF66"),
            Shadow(offset_x=0, offset_y=12, color="#00000066", blur_radius=16),
        ],
    )
    .text(
        content="Guest",
        size=22,
        color="#8CE1FF",
        weight=700,
        letter_spacing=2,
        position=(90, 556),
    )
    .text(
        content="Mina Park",
        size=42,
        color="#FFFFFF",
        weight=900,
        position=(88, 582),
    )
    .text(
        content="AI Product Lead",
        size=24,
        color="#C7D5E0",
        weight=500,
        position=(90, 622),
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
            Shadow(offset_x=16, offset_y=18, color="#000000AA", blur_radius=22),
        ],
    )
    .outline(width=10, color="#8CE1FF")
    .render(OUTPUT_PATH)
)

print(f"✓ Podcast / interview promo created: {OUTPUT_PATH}")
print("  This example requires network access and quickthumb[rembg] for portrait cutouts.")
