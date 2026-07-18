"""An intimate audio-journal cover built around a bespoke editorial portrait."""

import os

from quickthumb import Canvas, Filter, FitMode, LinearGradient
from quickthumb.models import Shadow

FILE_DIR = os.path.dirname(__file__)
ASSETS_DIR = os.path.join(FILE_DIR, "..", "assets")
OUTPUT_PATH = os.path.join(FILE_DIR, "podcast_interview_promo.png")
DISPLAY = os.path.join(ASSETS_DIR, "fonts", "NotoSerif-ExtraBold.ttf")
SANS = os.path.join(ASSETS_DIR, "fonts", "Roboto-Medium.ttf")
BACKGROUND_URL = (
    "https://images.unsplash.com/photo-1478737270239-2f02b77fc618?auto=format&fit=crop&w=1600&q=80"
)
GUEST_IMAGE = os.path.join(ASSETS_DIR, "images", "podcast_guest_editorial.png")

(
    Canvas(1280, 720)
    .background(color="#351D2A")
    .background(
        image=BACKGROUND_URL,
        fit=FitMode.COVER,
        effects=[Filter(brightness=0.4, contrast=0.94, saturation=0.38, blur=2)],
    )
    .background(
        gradient=LinearGradient(
            angle=90,
            stops=[("#351D2AF7", 0.0), ("#351D2AE8", 0.52), ("#351D2A44", 1.0)],
        )
    )
    .text(
        content="WORK, QUIETLY",
        font=DISPLAY,
        size=24,
        color="#F2B8A2",
        weight=700,
        letter_spacing=1,
        position=(62, 54),
    )
    .text(
        content="AUDIO JOURNAL  /  EP. 42",
        font=SANS,
        size=17,
        color="#F4E8DE99",
        weight=700,
        letter_spacing=3,
        position=(62, 102),
    )
    .text(
        content="FEEDBACK\nWITHOUT FEAR",
        font=DISPLAY,
        size=70,
        color="#FFF9F1",
        weight=700,
        line_height=1.12,
        letter_spacing=-2,
        position=(62, 168),
        max_width=650,
    )
    .text(
        content="How thoughtful teams move fast without losing trust",
        font=SANS,
        size=26,
        color="#D6C2B7",
        weight=400,
        position=(66, 396),
    )
    .shape(
        shape="rectangle",
        position=(62, 500),
        width=430,
        height=142,
        color="#FFF8EE",
        border_radius=6,
        effects=[Shadow(offset_x=0, offset_y=18, color="#12070C66", blur_radius=24)],
    )
    .text(
        content="GUEST",
        font=SANS,
        size=15,
        color="#9A5748",
        weight=700,
        letter_spacing=2,
        position=(90, 528),
    )
    .text(
        content="MINA PARK\nAI PRODUCT LEAD",
        font=SANS,
        size=24,
        color="#2A1A20",
        weight=700,
        line_height=1.35,
        position=(90, 566),
    )
    .image(
        path=GUEST_IMAGE,
        position=(1055, 704),
        width=510,
        height=650,
        fit=FitMode.COVER,
        align=("center", "bottom"),
        effects=[Shadow(offset_x=-10, offset_y=12, color="#14080D88", blur_radius=26)],
    )
    .text(
        content="LISTEN WITH CARE",
        font=SANS,
        size=14,
        color="#F4E8DE99",
        weight=700,
        letter_spacing=3,
        position=(1218, 44),
        align=("right", "top"),
    )
    .render(OUTPUT_PATH)
)

print(f"✓ Audio journal promo created: {OUTPUT_PATH}")
print("  The guest portrait is bundled; network access is used only for the studio background.")
