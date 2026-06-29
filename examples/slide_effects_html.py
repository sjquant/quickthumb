"""
HTML slideshow showcase: the same polished deck as slide_effects_deck.py,
exported as a self-contained browser slideshow.

Demonstrates:
- `deck.render("slides.html")` — one self-contained, navigable HTML file
- Per-layer entrance animations (`Fade`, `Wipe`, `Box`, `Wheel`) playing in
  the browser with the same `on_click` / `after_previous` sequencing
- A `group` animation that drives several children as a single effect
- Scale-to-fit responsive layout (the fixed-size stage fills any viewport)

Open the resulting `.html` in any modern browser and click (or press
ArrowRight / Space) to advance the animations and slides.
"""

import os

from quickthumb import Box, Canvas, Deck, Fade, LinearGradient, Wheel, Wipe
from quickthumb.models import Shadow

FILE_DIR = os.path.dirname(__file__)
ASSETS_DIR = os.path.join(FILE_DIR, "..", "assets")
OUTPUT_PATH = os.path.join(FILE_DIR, "slide_effects.html")

os.environ["QUICKTHUMB_FONT_DIR"] = os.path.join(ASSETS_DIR, "fonts")
os.environ["QUICKTHUMB_DEFAULT_FONT"] = "Roboto"

INK = "#0A1626"
LIME = "#B8FF00"
SKY = "#7DD3FC"
WHITE = "#F8FAFC"
MUTED = "#8FA3B8"

NAVY_WASH = LinearGradient(angle=135, stops=[("#0A1626", 0.0), ("#13294A", 1.0)])
GREEN_WASH = LinearGradient(angle=135, stops=[("#07140C", 0.0), ("#0F2A1B", 1.0)])
HEADLINE_FILL = LinearGradient(angle=20, stops=[(LIME, 0.0), (SKY, 1.0)])

SOFT_SHADOW = Shadow(offset_x=0, offset_y=10, color="#00000066", blur_radius=22)


def accent_bar(canvas: Canvas, x: str, y: str, *, align=None, animation=None) -> Canvas:
    return canvas.shape(
        shape="rectangle",
        position=(x, y),
        width=72,
        height=8,
        color=LIME,
        border_radius=4,
        align=align,
        animation=animation,
    )


# Slide 1 — title
cover = (
    Canvas()
    .background(gradient=NAVY_WASH)
    .shape(shape="ellipse", position=("88%", "12%"), width=520, height=520,
           color="#163358", opacity=0.35, align=("center", "middle"))
)
cover = accent_bar(cover, "8%", "30%")
cover = (
    cover
    .text(
        content="Building what\nactually matters",
        size=104,
        fill=HEADLINE_FILL,
        weight=900,
        line_height=1.02,
        position=("8%", "45%"),
        effects=[SOFT_SHADOW],
        animation=Fade(duration=0.6),
    )
    .text(
        content="QUARTERLY BUSINESS REVIEW",
        size=28,
        color=SKY,
        weight=700,
        letter_spacing=6,
        position=("8%", "35%"),
        animation=Fade(trigger="after_previous"),
    )
    .text(
        content="FY25  ·  Q3  ·  Product & Growth",
        size=34,
        color=MUTED,
        position=("8%", "82%"),
        animation=Fade(trigger="after_previous"),
    )
)

# Slide 2 — agenda; each row wipes in on its own click
agenda_items = [
    ("01", "Revenue & growth"),
    ("02", "What we shipped"),
    ("03", "What we learned"),
    ("04", "Where we go next"),
]
agenda = Canvas().background(gradient=NAVY_WASH)
agenda = accent_bar(agenda, "8%", "15%")
agenda = agenda.text(
    content="Agenda",
    size=72,
    color=WHITE,
    weight=900,
    position=("8%", "19%"),
    animation=Fade(),
)
for index, (number, label) in enumerate(agenda_items):
    agenda = agenda.group(
        children=[
            {"type": "text", "content": number, "size": 56, "color": LIME, "weight": 900},
            {"type": "text", "content": label, "size": 52, "color": WHITE, "weight": 500},
        ],
        direction="row",
        gap=40,
        position=("9%", f"{40 + index * 14}%"),
        align=("left", "middle"),
        item_align="center",
        animation=Wipe(direction="left", duration=0.4),
    )

# Slide 3 — hero metric; the gradient number boxes in, caption and stats follow
metric = (
    Canvas()
    .background(gradient=GREEN_WASH)
    .text(
        content="+38%",
        size=300,
        fill=LinearGradient(angle=20, stops=[(LIME, 0.0), ("#5EEAD4", 1.0)]),
        weight=900,
        position=("50%", "50%"),
        align="center",
        effects=[SOFT_SHADOW],
        animation=Box(direction="in", duration=0.5),
    )
    .text(
        content="Active teams, year over year",
        size=30,
        color=SKY,
        weight=700,
        letter_spacing=4,
        position=("50%", "22%"),
        align="center",
        animation=Fade(trigger="after_previous"),
    )
    .group(
        children=[
            {"type": "text", "content": "2.4M", "size": 60, "color": SKY, "weight": 900},
            {"type": "text", "content": "monthly users", "size": 32, "color": MUTED},
            {"type": "text", "content": "·", "size": 40, "color": "#33506E"},
            {"type": "text", "content": "+120", "size": 60, "color": SKY, "weight": 900},
            {"type": "text", "content": "new enterprises", "size": 32, "color": MUTED},
        ],
        direction="row",
        gap=22,
        position=("50%", "82%"),
        align=("center", "middle"),
        item_align="center",
        animation=Wheel(spokes=3, trigger="after_previous"),
    )
)

# Slide 4 — closing; no animations, just a strong outro
closing = (
    Canvas()
    .background(gradient=NAVY_WASH)
    .shape(shape="ellipse", position=("12%", "88%"), width=520, height=520,
           color="#163358", opacity=0.35, align=("center", "middle"))
)
closing = accent_bar(closing, "50%", "38%", align="center")
closing = (
    closing
    .text(
        content="Let's build it.",
        size=120,
        fill=HEADLINE_FILL,
        weight=900,
        position=("50%", "50%"),
        align="center",
        effects=[SOFT_SHADOW],
    )
    .text(
        content="Questions, ideas, and bold bets welcome.",
        size=36,
        color=MUTED,
        position=("50%", "66%"),
        align="center",
    )
)

deck = (
    Deck(1280, 720)
    .slide(cover)
    .slide(agenda)
    .slide(metric)
    .slide(closing)
)

deck.render(OUTPUT_PATH)

print(f"✓ HTML slideshow: {OUTPUT_PATH}")
print(f"  {len(deck)} slides — open in a browser and click to advance.")
print("  ArrowRight / Space → next  |  ArrowLeft → back")
