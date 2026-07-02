"""
Vela Analytics — Series A investor deck.

A production-quality HTML slideshow demonstrating:
  - NotoSerif display headlines mixed with Roboto UI copy
  - Gradient text fills, layered depth, and shape accents
  - Carefully choreographed, per-slide entrance animations
  - Five varied layouts: cover → problem → product → traction → CTA

Run:
    uv run python examples/investor_deck.py
    open examples/investor_deck.html
"""

import os

from quickthumb import Box, Canvas, Deck, Fade, LinearGradient, Wipe
from quickthumb import transitions as tr
from quickthumb.models import Glow, Shadow

FILE_DIR = os.path.dirname(__file__)
ASSETS_DIR = os.path.join(FILE_DIR, "..", "assets")
OUT_HTML = os.path.join(FILE_DIR, "investor_deck.html")
OUT_PPTX = os.path.join(FILE_DIR, "investor_deck.pptx")


os.environ["QUICKTHUMB_FONT_DIR"] = os.path.join(ASSETS_DIR, "fonts")
os.environ["QUICKTHUMB_DEFAULT_FONT"] = "Roboto"

# ── Palette ────────────────────────────────────────────────────────────────────

INK = "#08070E"
SURFACE = "#12111C"
PURPLE = "#8B5CF6"
CYAN = "#22D3EE"
GREEN = "#10B981"
WHITE = "#F8F8FF"
OFFWHITE = "#C4C4D4"
MUTED = "#64748B"
RULE = "#1E1D2F"

BRAND = LinearGradient(angle=90, stops=[(PURPLE, 0.0), (CYAN, 1.0)])
HERO = LinearGradient(angle=110, stops=[(CYAN, 0.0), (PURPLE, 1.0)])
DEPTH = LinearGradient(angle=160, stops=[(INK, 0.0), (SURFACE, 1.0)])
CTA_BG = LinearGradient(angle=140, stops=[(PURPLE, 0.0), ("#4338CA", 1.0)])

DROP = Shadow(offset_x=0, offset_y=6, color="#00000077", blur_radius=18)


# ── Design helpers ─────────────────────────────────────────────────────────────


def dark_stage(width=1280, height=720) -> Canvas:
    return Canvas(width, height).background(gradient=DEPTH)


def brand_bar(c: Canvas) -> Canvas:
    """2 px two-tone rule pinned to the top edge (PURPLE → CYAN)."""
    return c.shape(shape="rectangle", position=(0, 0), width=640, height=2, color=PURPLE).shape(
        shape="rectangle", position=(640, 0), width=640, height=2, color=CYAN
    )


def logo(c: Canvas, x: str = "10%", y: str = "8.5%") -> Canvas:
    return c.text(
        content="VELA",
        font="Roboto",
        size=18,
        color=PURPLE,
        weight=700,
        letter_spacing=4,
        position=(x, y),
    )


def label(c: Canvas, text: str, x: str, y: str, *, animation=None) -> Canvas:
    return c.text(
        content=text,
        font="Roboto",
        size=19,
        color=MUTED,
        weight=400,
        letter_spacing=3,
        position=(x, y),
        animation=animation,
    )


def divider(c: Canvas, y: str, *, x: str = "10%", w: int = 960, animation=None) -> Canvas:
    return c.shape(
        shape="rectangle",
        position=(x, y),
        width=w,
        height=1,
        color=RULE,
        animation=animation,
    )


# ══════════════════════════════════════════════════════════════════════════════
# Slide 1 — Cover
# ══════════════════════════════════════════════════════════════════════════════

s1 = dark_stage()
s1 = brand_bar(s1)

# Decorative depth blobs — add dimensionality without distraction.
s1 = s1.shape(
    shape="ellipse",
    position=("92%", "14%"),
    width=560,
    height=560,
    color=PURPLE,
    opacity=0.07,
    align=("center", "middle"),
)
s1 = s1.shape(
    shape="ellipse",
    position=("4%", "90%"),
    width=320,
    height=320,
    color=CYAN,
    opacity=0.06,
    align=("center", "middle"),
)

s1 = logo(s1)
s1 = label(s1, "SERIES A  ·  INVESTOR PRESENTATION", "10%", "17.5%", animation=Fade(duration=0.45))

# Three-line display headline; gradient fill draws the eye across the break.
s1 = s1.text(
    content="Make better\ndecisions,\nfaster.",
    font="NotoSerif",
    size=108,
    fill=BRAND,
    weight=900,
    line_height=1.02,
    position=("10%", "27%"),
    effects=[DROP],
    animation=Box(direction="in", duration=0.55, trigger="after_previous"),
)

# Thin accent rule under the headline before the sub-copy.
s1 = divider(s1, "77%", animation=Wipe(direction="right", duration=0.4, trigger="after_previous"))

s1 = s1.text(
    content=(
        "Vela surfaces the signals that matter in your product data\n"
        "so your team stops guessing and starts shipping with confidence."
    ),
    font="Roboto",
    size=27,
    color=OFFWHITE,
    weight=300,
    line_height=1.6,
    position=("10%", "81%"),
    animation=Fade(duration=0.45, trigger="after_previous"),
)

s1 = s1.text(
    content="Confidential",
    font="Roboto",
    size=17,
    color=MUTED,
    weight=300,
    position=("90%", "93%"),
    align=("right", "top"),
)

# ══════════════════════════════════════════════════════════════════════════════
# Slide 2 — The Problem
# ══════════════════════════════════════════════════════════════════════════════

s2 = dark_stage()
s2 = brand_bar(s2)
s2 = logo(s2)
s2 = label(s2, "THE PROBLEM", "50%", "8.5%")

# Oversized stat is the entire argument.
s2 = s2.text(
    content="73%",
    font="NotoSerif",
    size=210,
    fill=BRAND,
    weight=900,
    position=("50%", "24%"),
    align="center",
    effects=[DROP],
    animation=Box(direction="in", duration=0.6),
)

s2 = s2.text(
    content="of product decisions are made without reliable data.",
    font="Roboto",
    size=30,
    color=OFFWHITE,
    weight=300,
    position=("50%", "73%"),
    align="center",
    animation=Fade(duration=0.4, trigger="after_previous"),
)

s2 = divider(
    s2,
    "81.5%",
    x="50%",
    w=800,
    animation=Wipe(direction="left", duration=0.35, trigger="after_previous"),
)

# Three root-causes as a single inline group; same animation = one reveal.
s2 = s2.group(
    children=[
        {
            "type": "text",
            "content": "Siloed dashboards",
            "font": "Roboto",
            "size": 24,
            "color": MUTED,
            "weight": 300,
        },
        {"type": "text", "content": "·", "font": "Roboto", "size": 24, "color": RULE},
        {
            "type": "text",
            "content": "Alert fatigue",
            "font": "Roboto",
            "size": 24,
            "color": MUTED,
            "weight": 300,
        },
        {"type": "text", "content": "·", "font": "Roboto", "size": 24, "color": RULE},
        {
            "type": "text",
            "content": "No clear owner",
            "font": "Roboto",
            "size": 24,
            "color": MUTED,
            "weight": 300,
        },
    ],
    direction="row",
    gap=32,
    position=("50%", "87%"),
    align=("center", "top"),
    item_align="center",
    animation=Fade(duration=0.4, trigger="after_previous"),
)

# ══════════════════════════════════════════════════════════════════════════════
# Slide 3 — The Product (three feature columns)
# ══════════════════════════════════════════════════════════════════════════════

FEATURES = [
    (
        "28%",
        "Signal\nDetection",
        PURPLE,
        "10B981",
        "Automatically surfaces\nanomalies and trends\nbefore they become incidents.",
    ),
    (
        "50%",
        "Smart\nAlerts",
        CYAN,
        "22D3EE",
        "Context-aware notifications\nthat cut through noise and\nreach the right person.",
    ),
    (
        "72%",
        "Team\nSync",
        GREEN,
        "10B981",
        "One-click shared views\nthat turn findings into\naligned decisions fast.",
    ),
]

s3 = dark_stage()
s3 = brand_bar(s3)
s3 = logo(s3)
s3 = label(s3, "THE PRODUCT", "50%", "8.5%")

s3 = s3.text(
    content="One platform. Every signal.",
    font="NotoSerif",
    size=64,
    fill=HERO,
    weight=900,
    position=("50%", "20%"),
    align="center",
    effects=[DROP],
    animation=Fade(duration=0.5),
)

s3 = divider(
    s3,
    "35%",
    x="50%",
    w=1040,
    animation=Wipe(direction="right", duration=0.4, trigger="after_previous"),
)

for x_pct, title, accent, _hex, body in FEATURES:
    grad = LinearGradient(angle=100, stops=[(accent, 0.0), (WHITE, 0.85)])

    # Soft ring + crisp inner dot as a visual anchor for the column.
    s3 = s3.shape(
        shape="ellipse",
        position=(x_pct, "44%"),
        width=56,
        height=56,
        color=accent,
        opacity=0.15,
        align=("center", "middle"),
        animation=Fade(duration=0.4),
    )
    s3 = s3.shape(
        shape="ellipse",
        position=(x_pct, "44%"),
        width=24,
        height=24,
        color=accent,
        align=("center", "middle"),
        effects=[Glow(radius=6, color=accent, opacity=0.3)],
        animation=Fade(duration=0.4, trigger="with_previous"),
    )

    s3 = s3.text(
        content=title,
        font="Roboto",
        size=38,
        fill=grad,
        weight=700,
        line_height=1.1,
        position=(x_pct, "53%"),
        align="center",
        animation=Wipe(direction="up", duration=0.35, trigger="with_previous"),
    )

    s3 = s3.text(
        content=body,
        font="Roboto",
        size=22,
        color=OFFWHITE,
        weight=300,
        line_height=1.6,
        position=(x_pct, "70%"),
        align="center",
        animation=Fade(duration=0.35, trigger="with_previous"),
    )

# ══════════════════════════════════════════════════════════════════════════════
# Slide 4 — Traction (three headline metrics)
# ══════════════════════════════════════════════════════════════════════════════

METRICS = [
    ("25%", "2,400+", "Active teams", PURPLE),
    ("50%", "94%", "Retention rate", CYAN),
    ("75%", "$1.8M", "ARR", GREEN),
]

s4 = dark_stage()
s4 = brand_bar(s4)
s4 = logo(s4)
s4 = label(s4, "TRACTION", "50%", "8.5%")

s4 = s4.text(
    content="Growing fast.\nCustomers love it.",
    font="NotoSerif",
    size=72,
    fill=BRAND,
    weight=900,
    line_height=1.08,
    position=("50%", "27%"),
    align="center",
    effects=[DROP],
    animation=Fade(duration=0.5),
)

for x_pct, value, sublabel, accent in METRICS:
    num_grad = LinearGradient(angle=90, stops=[(accent, 0.0), (WHITE, 0.85)])

    s4 = s4.text(
        content=value,
        font="NotoSerif",
        size=92,
        fill=num_grad,
        weight=900,
        position=(x_pct, "50%"),
        align="center",
        effects=[DROP],
        animation=Box(direction="in", duration=0.45),
    )
    s4 = s4.text(
        content=sublabel,
        font="Roboto",
        size=25,
        color=MUTED,
        weight=400,
        letter_spacing=1,
        position=(x_pct, "72%"),
        align="center",
        animation=Fade(duration=0.3, trigger="after_previous"),
    )

s4 = divider(
    s4,
    "84%",
    x="50%",
    w=960,
    animation=Wipe(direction="right", duration=0.35, trigger="after_previous"),
)

s4 = s4.text(
    content='"Vela cut our incident response time in half." — Head of Product, Series B fintech',
    font="Roboto",
    size=22,
    color=MUTED,
    weight=300,
    italic=True,
    position=("50%", "89%"),
    align="center",
    animation=Fade(duration=0.4, trigger="after_previous"),
)

# ══════════════════════════════════════════════════════════════════════════════
# Slide 5 — CTA
# ══════════════════════════════════════════════════════════════════════════════

s5 = Canvas(1280, 720).background(gradient=CTA_BG)
s5 = brand_bar(s5)

# Soft depth ring in the opposite corner.
s5 = s5.shape(
    shape="ellipse",
    position=("88%", "18%"),
    width=640,
    height=640,
    color=WHITE,
    opacity=0.04,
    align=("center", "middle"),
)
s5 = s5.shape(
    shape="ellipse",
    position=("8%", "82%"),
    width=380,
    height=380,
    color=WHITE,
    opacity=0.03,
    align=("center", "middle"),
)

s5 = logo(s5, "10%", "8.5%")

s5 = s5.text(
    content="Ready to surface\nthe signal?",
    font="NotoSerif",
    size=108,
    color=WHITE,
    weight=900,
    line_height=1.02,
    position=("50%", "28%"),
    align="center",
    effects=[DROP],
    animation=Box(direction="in", duration=0.55),
)

s5 = s5.text(
    content="Book a 20-minute demo  ·  vela.so/demo",
    font="Roboto",
    size=28,
    color="#DDD6FE",
    weight=300,
    letter_spacing=1,
    position=("50%", "72%"),
    align="center",
    animation=Fade(duration=0.5, trigger="after_previous"),
)

s5 = s5.text(
    content="hello@vela.so",
    font="Roboto",
    size=21,
    color="#A78BFA",
    weight=400,
    letter_spacing=1,
    position=("50%", "84%"),
    align="center",
    animation=Fade(duration=0.4, trigger="after_previous"),
)

# ══════════════════════════════════════════════════════════════════════════════
# Assemble and export
# ══════════════════════════════════════════════════════════════════════════════

# A distinct slide transition per slide — these play in the HTML slideshow
# (and in PPTX/HTML export). The cover slide cross-fades in by default.
deck = (
    Deck(1280, 720)
    .slide(s1)
    .slide(s2, transition=tr.Push(direction="left", duration=0.6))
    .slide(s3, transition=tr.Wipe(direction="up", duration=0.5))
    .slide(s4, transition=tr.Push(direction="left", duration=0.6))
    .slide(s5, transition=tr.Cover(direction="up", duration=0.6))
)

deck.render(OUT_HTML)
deck.render(OUT_PPTX)

print(f"✓ {OUT_HTML}")
print(f"  {len(deck)} slides — open in a browser.")
print("  Click / Space → advance   ArrowLeft → back")
