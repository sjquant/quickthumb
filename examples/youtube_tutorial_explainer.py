"""An education-brand thumbnail that turns a curriculum into a visual system."""

import os

from quickthumb import Canvas
from quickthumb.models import Shadow

FILE_DIR = os.path.dirname(__file__)
ASSETS_DIR = os.path.join(FILE_DIR, "..", "assets")
OUTPUT_PATH = os.path.join(FILE_DIR, "youtube_tutorial_explainer.png")
DISPLAY = os.path.join(ASSETS_DIR, "fonts", "NotoSans-Black.ttf")
SANS = os.path.join(ASSETS_DIR, "fonts", "Roboto-Medium.ttf")

canvas = Canvas(1280, 720).background(color="#101B35")

canvas.text(
    content="LEARNING MAP  /  01",
    font=SANS,
    size=18,
    color="#AFC6FF",
    weight=700,
    letter_spacing=3,
    position=(62, 54),
)
canvas.text(
    content="30 DAYS.\nONE SYSTEM.",
    font=DISPLAY,
    size=82,
    color="#F7F2E9",
    weight=700,
    line_height=1.08,
    letter_spacing=-4,
    position=(62, 140),
)
canvas.text(
    content="A hands-on Python lab\nfor people who learn by shipping",
    font=SANS,
    size=25,
    color="#AFC6FF",
    weight=400,
    position=(66, 396),
    max_width=520,
    line_height=1.35,
)

steps = [
    ("01", "READ", "See the pattern"),
    ("02", "BUILD", "Make it real"),
    ("03", "SHIP", "Share the work"),
]
for index, (number, title, detail) in enumerate(steps):
    x = 650 + index * 196
    canvas.shape(
        shape="rectangle",
        position=(x, 142),
        width=164,
        height=430,
        color="#F1EDDF" if index != 1 else "#B8FF5A",
        border_radius=82,
        effects=[Shadow(offset_x=0, offset_y=12, color="#07130F44", blur_radius=18)],
    )
    canvas.text(
        content=number,
        font=SANS,
        size=18,
        color="#69716D" if index != 1 else "#243411",
        weight=700,
        position=(x + 82, 190),
        align=("center", "middle"),
    )
    canvas.text(
        content=title,
        font=DISPLAY,
        size=30,
        color="#101B35",
        weight=700,
        position=(x + 82, 348),
        align=("center", "middle"),
    )
    canvas.text(
        content=detail,
        font=SANS,
        size=16,
        color="#68746E" if index != 1 else "#243411",
        weight=500,
        position=(x + 82, 506),
        align=("center", "middle"),
    )

canvas.text(
    content="DAY 01 — 30",
    font=SANS,
    size=16,
    color="#AFC6FF",
    weight=700,
    letter_spacing=2,
    position=(62, 660),
)
canvas.render(OUTPUT_PATH)

print(f"✓ Curriculum thumbnail created: {OUTPUT_PATH}")
