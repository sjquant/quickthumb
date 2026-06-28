"""
Slide effects example: a multi-slide PowerPoint deck with transitions and
per-layer entrance/exit animations.

Demonstrates:
- A `Deck` with a default slide transition plus per-slide overrides
- Typed effect objects (`Fade`, `Wipe`, `Box`, `Wheel`, ...), each carrying only
  the options it supports
- A list of animations on one layer, played in order (enter, then exit)
- A `group` animation that drives all of its children as a single effect
- `entrance` and `exit` animations with click / after-previous sequencing

Slide effects only affect PPTX output, so this example renders to `.pptx`. Open
the file in PowerPoint (or Keynote / LibreOffice Impress) and run the slideshow
to see the transitions and animations play.
"""

import os

from quickthumb import Box, Canvas, Deck, Fade, Transition, Wheel, Wipe
from quickthumb.models import Background, Shadow

FILE_DIR = os.path.dirname(__file__)
ASSETS_DIR = os.path.join(FILE_DIR, "..", "assets")
OUTPUT_PATH = os.path.join(FILE_DIR, "slide_effects_deck.pptx")

os.environ["QUICKTHUMB_FONT_DIR"] = os.path.join(ASSETS_DIR, "fonts")
os.environ["QUICKTHUMB_DEFAULT_FONT"] = "Roboto"

INK = "#0B1B2B"
ACCENT = "#B8FF00"
SKY = "#8CE1FF"

# Slide 1 — title. The headline fades in on the first click; the kicker pill and
# label form a group that wheels in together as one effect on the next click.
cover = (
    Canvas()
    .background(color=INK)
    .text(
        content="QUARTERLY REVIEW",
        size=110,
        color=ACCENT,
        weight=900,
        position=("50%", "42%"),
        align="center",
        effects=[Shadow(offset_x=0, offset_y=8, color="#00000088", blur_radius=18)],
        animation=Fade(duration=0.6),
    )
    .group(
        children=[
            {"type": "shape", "shape": "pill", "width": 18, "height": 18, "color": SKY},
            {"type": "text", "content": "FY25 · Q3 · Product", "size": 40, "color": SKY},
        ],
        direction="row",
        gap=16,
        position=("50%", "60%"),
        align=("center", "middle"),
        item_align="center",
        animation=Wheel(spokes=4, trigger="after_previous"),
    )
)

# Slide 2 — agenda. Each row wipes in from the left, one click at a time, so the
# list builds up point by point.
agenda_rows = ["Revenue & growth", "What shipped", "What we learned", "Next quarter"]
agenda = Canvas().background(color=INK).text(
    content="Agenda",
    size=72,
    color="#FFFFFF",
    weight=900,
    position=("8%", "16%"),
    animation=Fade(),
)
for index, label in enumerate(agenda_rows):
    agenda = agenda.text(
        content=f"{index + 1}.  {label}",
        size=48,
        color=SKY if index % 2 == 0 else "#FFFFFF",
        position=("10%", f"{38 + index * 13}%"),
        effects=[Background(color="#13314A", padding=(10, 20), border_radius=10)],
        animation=Wipe(direction="left", duration=0.4),
    )

# Slide 3 — a single metric that boxes in, holds, then fades out to clear the
# stage. Passing a list of animations plays them in order on the same layer.
metric = (
    Canvas()
    .background(color="#101A0B")
    .text(
        content="+38%",
        size=240,
        color=ACCENT,
        weight=900,
        position=("50%", "44%"),
        align="center",
        animation=[
            Box(direction="in", duration=0.5),
            Fade(animate="exit", trigger="after_previous", delay=1.0),
        ],
    )
    .text(
        content="year-over-year active teams",
        size=44,
        color="#D7E8C4",
        position=("50%", "70%"),
        align="center",
        animation=Fade(trigger="with_previous"),
    )
)

# Slide 4 — closing card, no animations, just a clean outro.
closing = (
    Canvas()
    .background(color=INK)
    .text(
        content="Questions?",
        size=120,
        color="#FFFFFF",
        weight=900,
        position=("50%", "45%"),
        align="center",
    )
    .text(
        content="thanks for watching",
        size=40,
        color=SKY,
        position=("50%", "62%"),
        align="center",
    )
)

deck = (
    Deck(1280, 720)
    # Every slide fades in by default...
    .transition("fade", duration=0.4)
    .slide(cover)
    .slide(agenda)
    # ...but individual slides can override that default.
    .slide(metric, transition=Transition(effect="zoom", direction="in", duration=0.6))
    .slide(closing, transition="push")
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
