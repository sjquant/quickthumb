"""
Slide effects showcase: a polished, presentation-ready PowerPoint deck with
transitions and per-layer entrance/exit animations.

Demonstrates:
- A `Deck` with a default slide `Transition` plus per-slide overrides
- Typed effect objects (`Fade`, `Wipe`, `Box`, `Wheel`), each carrying only the
  options it supports
- Sequencing that leads with the main element, then reveals the supporting
  detail, using `on_click` / `after_previous` triggers
- A `group` animation that drives several children as a single effect
- Gradient backgrounds, gradient-filled headlines, and accent shapes that stay
  crisp and editable in PowerPoint

Slide effects only affect PPTX output, so this renders to `.pptx`. Open it in
PowerPoint (or Keynote / LibreOffice Impress) and start the slideshow to watch
the transitions and animations play.
"""

import os

from quickthumb import Box, Canvas, Deck, Fade, LinearGradient, Wheel, Wipe
from quickthumb.models import Shadow
from quickthumb.transitions import Fade as FadeTransition
from quickthumb.transitions import Push, Zoom

FILE_DIR = os.path.dirname(__file__)
ASSETS_DIR = os.path.join(FILE_DIR, "..", "assets")
OUTPUT_PATH = os.path.join(FILE_DIR, "slide_effects_deck.pptx")

os.environ["QUICKTHUMB_FONT_DIR"] = os.path.join(ASSETS_DIR, "fonts")
os.environ["QUICKTHUMB_DEFAULT_FONT"] = "Roboto"

# A small, cohesive palette keeps the whole deck on-brand.
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
    """A short lime rule used as a kicker accent above headings."""
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


# Slide 1 — title. The accent bar wipes in, the gradient headline fades up, then
# the kicker + subtitle arrive together.
cover = (
    Canvas()
    .background(gradient=NAVY_WASH)
    # a large, faint ring in the corner adds depth without stealing focus
    .shape(shape="ellipse", position=("88%", "12%"), width=520, height=520,
           color="#163358", opacity=0.35, align=("center", "middle"))
)
# The accent bar is static framing; the headline (the main element) leads the
# animation, and the eyebrow and subtitle follow as supporting detail.
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
        animation=Fade(duration=0.6),  # main: leads on the first click
    )
    .text(
        content="QUARTERLY BUSINESS REVIEW",
        size=28,
        color=SKY,
        weight=700,
        letter_spacing=6,
        position=("8%", "35%"),
        animation=Fade(trigger="after_previous"),  # supporting: follows
    )
    .text(
        content="FY25  ·  Q3  ·  Product & Growth",
        size=34,
        color=MUTED,
        position=("8%", "82%"),
        animation=Fade(trigger="after_previous"),  # supporting: follows
    )
)

# Slide 2 — agenda. Each row is a group (big numeral + label) that wipes in on
# its own click, building the list up one point at a time. No tight text
# backgrounds, so it stays perfectly aligned in PowerPoint.
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

# Slide 3 — the hero metric. The big gradient number is the star: it boxes in
# first, then the caption above and the supporting stats below follow.
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
        animation=Box(direction="in", duration=0.5),  # main: the number lands first
    )
    .text(
        content="Active teams, year over year",
        size=30,
        color=SKY,
        weight=700,
        letter_spacing=4,
        position=("50%", "22%"),
        align="center",
        animation=Fade(trigger="after_previous"),  # supporting caption
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
        animation=Wheel(spokes=3, trigger="after_previous"),  # supporting stats
    )
)

# Slide 4 — closing. Clean and confident, no animations — just a strong outro.
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
    # Every slide fades in by default...
    .transition(FadeTransition(duration=0.4))
    .slide(cover)
    .slide(agenda)
    # ...but individual slides can override that default with their own effect.
    .slide(metric, transition=Zoom(direction="in", duration=0.6))
    .slide(closing, transition=Push(direction="left"))
)

written = deck.render(OUTPUT_PATH)

# A still preview of the opening slide for documentation. The transitions and
# entrance/exit animations themselves only live in the .pptx; a raster render
# just shows each slide's final composition.
preview_path = os.path.join(FILE_DIR, "slide_effects_deck.png")
deck[0].render(preview_path)

print(f"✓ Slide-effects deck created: {written[0]}")
print(f"  {len(deck)} slides — open it in PowerPoint and start the slideshow to see")
print("  the transitions and entrance/exit animations play.")
print(f"  Static preview of the opening slide: {preview_path}")
