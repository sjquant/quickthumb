"""A bold culture-criticism thumbnail inspired by independent print journals."""

import os

from quickthumb import Canvas, LinearGradient

FILE_DIR = os.path.dirname(__file__)
ASSETS_DIR = os.path.join(FILE_DIR, "..", "assets")
OUTPUT_PATH = os.path.join(FILE_DIR, "youtube_reaction.png")
DISPLAY = os.path.join(ASSETS_DIR, "fonts", "NotoSans-Black.ttf")
SANS = os.path.join(ASSETS_DIR, "fonts", "Roboto-Medium.ttf")

(
    Canvas(1280, 720)
    .background(color="#DCE5FF")
    .background(
        gradient=LinearGradient(
            angle=135,
            stops=[("#E7ECFF", 0.0), ("#C7D6FF", 1.0)],
        )
    )
    .shape(
        shape="ellipse",
        position=(1034, 336),
        width=390,
        height=390,
        color="#FF4B36",
        align=("center", "middle"),
    )
    .shape(
        shape="ellipse",
        position=(1034, 336),
        width=246,
        height=246,
        color="#111827",
        align=("center", "middle"),
    )
    .text(
        content="01",
        font=DISPLAY,
        size=82,
        color="#F8F5ED",
        weight=700,
        position=(1034, 336),
        align=("center", "middle"),
    )
    .text(
        content="CULTURE CHECK  /  ESSAY 09",
        font=SANS,
        size=18,
        color="#68706A",
        weight=700,
        letter_spacing=3,
        position=(62, 56),
    )
    .text(
        content="WHY DOES\nEVERYTHING\nLOOK THE SAME?",
        font=DISPLAY,
        size=78,
        color="#111827",
        weight=700,
        line_height=1.08,
        letter_spacing=-3,
        position=(62, 138),
    )
    .shape(
        shape="rectangle",
        position=(64, 534),
        width=620,
        height=2,
        color="#111827",
    )
    .text(
        content="A field guide to taste in the age of infinite references",
        font=SANS,
        size=25,
        color="#4F5853",
        weight=400,
        position=(64, 570),
    )
    .text(
        content="TREND ≠ TASTE",
        font=SANS,
        size=16,
        color="#111827",
        weight=700,
        letter_spacing=2,
        position=(1216, 664),
        align=("right", "bottom"),
    )
    .render(OUTPUT_PATH)
)

print(f"✓ Culture commentary thumbnail created: {OUTPUT_PATH}")
