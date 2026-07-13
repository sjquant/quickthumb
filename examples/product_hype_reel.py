"""
Pulse — vertical app-launch hype reel.

A production-quality animated GIF/MP4/WebM export demonstrating:
  - Vertical 1080x1920 Reels/TikTok/Stories deck, three quick-cut slides
  - Per-layer entrance animations (Box, Wipe, Fade, Dissolve) staggered with
    `with_previous` / `after_previous`, exactly as they'd play in HTML export
  - Slide transitions (Push, Zoom) rendered as real frames, not approximations
  - The bytes-returning tunable API (`to_gif` / `to_mp4` / `to_webm`) with a
    snappy `slide_duration` tuned for short-form video pacing

Run:
    uv run python examples/product_hype_reel.py
"""

import os

from quickthumb import Box, Canvas, Deck, Dissolve, Fade, Glow, LinearGradient, RenderingError, Wipe
from quickthumb import transitions as tr

FILE_DIR = os.path.dirname(__file__)
ASSETS_DIR = os.path.join(FILE_DIR, "..", "assets")
OUT_GIF = os.path.join(FILE_DIR, "product_hype_reel.gif")
OUT_MP4 = os.path.join(FILE_DIR, "product_hype_reel.mp4")
OUT_WEBM = os.path.join(FILE_DIR, "product_hype_reel.webm")

os.environ["QUICKTHUMB_FONT_DIR"] = os.path.join(ASSETS_DIR, "fonts")
os.environ["QUICKTHUMB_DEFAULT_FONT"] = "Roboto"

# ── Palette ────────────────────────────────────────────────────────────────────

INK = "#0B0B12"
SURFACE = "#181622"
CORAL = "#FF6B5B"
GOLD = "#FFC857"
WHITE = "#FFFFFF"
OFFWHITE = "#F1EEF5"
MUTED = "#9691A8"
RULE = "#2A2735"

HYPE = LinearGradient(angle=100, stops=[(CORAL, 0.0), (GOLD, 1.0)])
DEPTH = LinearGradient(angle=165, stops=[(INK, 0.0), (SURFACE, 1.0)])
GLOW_ACCENT = Glow(radius=18, color=CORAL, opacity=0.4)


# ── Design helpers ─────────────────────────────────────────────────────────────


def dark_stage() -> Canvas:
    return Canvas(1080, 1920).background(gradient=DEPTH)


def brand_mark(c: Canvas) -> Canvas:
    return c.text(
        content="PULSE",
        font="Roboto",
        size=26,
        color=CORAL,
        weight=700,
        letter_spacing=5,
        position=("50%", "6%"),
        align="center",
    )


def eyebrow(c: Canvas, text: str, *, animation=None) -> Canvas:
    return c.text(
        content=text,
        font="Roboto",
        size=24,
        color=GOLD,
        weight=700,
        letter_spacing=4,
        position=("50%", "14%"),
        align="center",
        animation=animation,
    )


def divider(c: Canvas, y: str, *, animation=None) -> Canvas:
    return c.shape(
        shape="rectangle",
        position=("50%", y),
        width=520,
        height=1,
        color=RULE,
        align=("center", "middle"),
        animation=animation,
    )


# ══════════════════════════════════════════════════════════════════════════════
# Slide 1 — The Hook
# ══════════════════════════════════════════════════════════════════════════════

s1 = dark_stage()
s1 = brand_mark(s1)
s1 = eyebrow(s1, "NEW APP DROP", animation=Wipe(direction="right", duration=0.4))

s1 = s1.text(
    content="Stop\nscrolling.",
    font="NotoSerif",
    size=138,
    fill=HYPE,
    weight=900,
    line_height=1.0,
    position=("50%", "34%"),
    align="center",
    animation=Box(direction="in", duration=0.55, trigger="after_previous"),
)

s1 = s1.text(
    content="Your workout, reinvented.",
    font="Roboto",
    size=32,
    color=OFFWHITE,
    weight=300,
    position=("50%", "56%"),
    align="center",
    animation=Fade(duration=0.4, trigger="after_previous"),
)

s1 = s1.text(
    content="SWIPE UP",
    font="Roboto",
    size=20,
    color=MUTED,
    weight=400,
    letter_spacing=3,
    position=("50%", "92%"),
    align="center",
    animation=Fade(duration=0.35, delay=0.3, trigger="after_previous"),
)

# ══════════════════════════════════════════════════════════════════════════════
# Slide 2 — Feature Reveal
# ══════════════════════════════════════════════════════════════════════════════

FEATURES = [
    ("34%", "Live heart-rate sync"),
    ("44%", "AI-paced workouts"),
    ("54%", "Streaks that stick"),
]

s2 = dark_stage()
s2 = brand_mark(s2)
s2 = eyebrow(s2, "MEET PULSE")

s2 = s2.text(
    content="Built to keep\nyou moving.",
    font="NotoSerif",
    size=84,
    fill=HYPE,
    weight=900,
    line_height=1.05,
    position=("50%", "22%"),
    align="center",
    animation=Wipe(direction="up", duration=0.5),
)

for y_pct, text in FEATURES:
    s2 = s2.shape(
        shape="ellipse",
        position=("28%", y_pct),
        width=16,
        height=16,
        color=CORAL,
        align=("center", "middle"),
        effects=[GLOW_ACCENT],
        animation=Dissolve(duration=0.3, trigger="after_previous"),
    )
    s2 = s2.text(
        content=text,
        font="Roboto",
        size=34,
        color=OFFWHITE,
        weight=400,
        position=("34%", y_pct),
        align="left",
        animation=Fade(duration=0.3, trigger="with_previous"),
    )

s2 = divider(s2, "66%", animation=Wipe(direction="right", duration=0.4, trigger="after_previous"))

s2 = s2.text(
    content='"I actually finished a 5k." — beta tester',
    font="Roboto",
    size=26,
    color=MUTED,
    weight=300,
    italic=True,
    position=("50%", "72%"),
    align="center",
    animation=Fade(duration=0.35, trigger="after_previous"),
)

# ══════════════════════════════════════════════════════════════════════════════
# Slide 3 — Call to Action
# ══════════════════════════════════════════════════════════════════════════════

s3 = Canvas(1080, 1920).background(gradient=HYPE)

s3 = s3.shape(
    shape="ellipse",
    position=("50%", "20%"),
    width=900,
    height=900,
    color=WHITE,
    opacity=0.06,
    align=("center", "middle"),
)

s3 = s3.text(
    content="Your move.",
    font="NotoSerif",
    size=118,
    color=WHITE,
    weight=900,
    position=("50%", "36%"),
    align="center",
    animation=Box(direction="in", duration=0.55),
)

s3 = s3.text(
    content="Download Pulse — free this week.",
    font="Roboto",
    size=30,
    color="#FFF3E8",
    weight=400,
    position=("50%", "48%"),
    align="center",
    animation=Fade(duration=0.4, trigger="after_previous"),
)

s3 = s3.shape(
    shape="rectangle",
    position=("50%", "60%"),
    width=440,
    height=96,
    color=INK,
    border_radius=48,
    align=("center", "middle"),
    animation=Dissolve(duration=0.4, trigger="after_previous"),
)
s3 = s3.text(
    content="GET THE APP",
    font="Roboto",
    size=28,
    color=WHITE,
    weight=700,
    letter_spacing=2,
    position=("50%", "60%"),
    align=("center", "middle"),
    animation=Fade(duration=0.3, trigger="with_previous"),
)

s3 = s3.text(
    content="pulse.app",
    font="Roboto",
    size=22,
    color="#FFE8D6",
    weight=300,
    position=("50%", "92%"),
    align="center",
    animation=Fade(duration=0.35, trigger="after_previous"),
)

# ══════════════════════════════════════════════════════════════════════════════
# Assemble and export
# ══════════════════════════════════════════════════════════════════════════════

deck = (
    Deck(1080, 1920)
    .slide(s1)
    .slide(s2, transition=tr.Push(direction="up", duration=0.5))
    .slide(s3, transition=tr.Zoom(direction="in", duration=0.45))
)

# Short-form pacing: hold each slide for 1.8s instead of the 3s default.
# .to_gif()/.to_mp4()/.to_webm() return bytes; .render() (used in
# investor_deck.py) writes straight to a path chosen by extension instead.
# MP4/WebM also accept `soundtrack=` to mux in a music/voiceover track.
with open(OUT_GIF, "wb") as f:
    f.write(deck.to_gif(fps=12, slide_duration=1.8, loop=0))

try:
    with open(OUT_MP4, "wb") as f:
        f.write(deck.to_mp4(fps=30, slide_duration=1.8))
    with open(OUT_WEBM, "wb") as f:
        f.write(deck.to_webm(fps=30, slide_duration=1.8))
except RenderingError as error:
    print(f"⚠ Skipped MP4/WebM ({error})")

print(f"✓ {OUT_GIF}")
print(f"  {len(deck)} slides, 1.8s hold each — open the GIF or play the MP4/WebM clip.")
