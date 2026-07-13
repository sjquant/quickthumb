"""
PULSE — Korean-style vertical app-launch hype reel.

A production-quality animated GIF/MP4/WebM export demonstrating:
  - Vertical 1080x1920 Reels/TikTok/Stories deck, three quick-cut slides
  - Korean (Hangul) copy set in Noto Sans KR, fetched from Google Fonts
    (font_source="google") and cached locally after the first run
  - A K-style promo palette (hot pink -> violet) with sparkle/badge accents
  - Per-layer entrance animations (Box, Wipe, Fade, Dissolve, Wheel) staggered
    with `with_previous` / `after_previous`, exactly as they'd play in HTML export
  - Slide transitions (Push, Zoom) rendered as real frames, not approximations
  - The bytes-returning tunable API (`to_gif` / `to_mp4` / `to_webm`) with a
    snappy `slide_duration` tuned for short-form video pacing, and a looping
    soundtrack muxed into the MP4/WebM output

Run:
    uv run python examples/product_hype_reel.py

Requires network access on first run to fetch Noto Sans KR from Google
Fonts (cached under the platform font-cache directory afterward).
"""

import os

from quickthumb import (
    Box,
    Canvas,
    Deck,
    Dissolve,
    Fade,
    Glow,
    LinearGradient,
    QuickthumbError,
    Wheel,
    Wipe,
)
from quickthumb import transitions as tr

FILE_DIR = os.path.dirname(__file__)
ASSETS_DIR = os.path.join(FILE_DIR, "..", "assets")
SOUNDTRACK = os.path.join(ASSETS_DIR, "audio", "hype_beat.wav")
OUT_GIF = os.path.join(FILE_DIR, "product_hype_reel.gif")
OUT_MP4 = os.path.join(FILE_DIR, "product_hype_reel.mp4")
OUT_WEBM = os.path.join(FILE_DIR, "product_hype_reel.webm")

os.environ["QUICKTHUMB_FONT_DIR"] = os.path.join(ASSETS_DIR, "fonts")
os.environ["QUICKTHUMB_DEFAULT_FONT"] = "Roboto"

# Hangul isn't in the bundled Roboto/NotoSerif files, so every Korean text
# layer below sets font=KR_FONT, font_source="google" explicitly to fetch
# Noto Sans KR from Google Fonts instead of falling back to QUICKTHUMB_DEFAULT_FONT.
KR_FONT = "Noto Sans KR"

# ── Palette ────────────────────────────────────────────────────────────────────
# Hot pink -> violet is the K-beauty/K-pop promo staple; gold sparkles and a
# pill "NEW" badge are the corner details Korean app-store teasers lean on.

INK = "#0B0714"
SURFACE = "#171126"
PINK = "#FF3D81"
VIOLET = "#7C3AED"
GOLD = "#FFD166"
WHITE = "#FFFFFF"
OFFWHITE = "#F5EEFF"
MUTED = "#A99BC2"
RULE = "#2E2640"

HYPE = LinearGradient(angle=100, stops=[(PINK, 0.0), (VIOLET, 1.0)])
DEPTH = LinearGradient(angle=165, stops=[(INK, 0.0), (SURFACE, 1.0)])
GLOW_ACCENT = Glow(radius=18, color=PINK, opacity=0.45)


# ── Design helpers ─────────────────────────────────────────────────────────────


def dark_stage() -> Canvas:
    return Canvas(1080, 1920).background(gradient=DEPTH)


def brand_mark(c: Canvas) -> Canvas:
    return c.text(
        content="PULSE",
        font="Roboto",
        size=26,
        color=PINK,
        weight=700,
        letter_spacing=5,
        position=("50%", "6%"),
        align="center",
    )


def new_badge(c: Canvas) -> Canvas:
    """Top-right "NEW" pill, the corner detail Korean app teasers flag a launch with."""
    c = c.shape(
        shape="pill",
        position=("86%", "4.8%"),
        width=112,
        height=40,
        color=PINK,
        align=("center", "middle"),
    )
    return c.text(
        content="신규 출시",
        font=KR_FONT,
        font_source="google",
        size=17,
        color=WHITE,
        weight=800,
        position=("86%", "4.8%"),
        align=("center", "middle"),
    )


def sparkle(c: Canvas, x: str, y: str, size: int, *, animation=None) -> Canvas:
    return c.shape(
        shape="star",
        position=(x, y),
        width=size,
        height=size,
        color=GOLD,
        star_points=4,
        inner_radius=0.35,
        align=("center", "middle"),
        opacity=0.85,
        animation=animation,
    )


def eyebrow(c: Canvas, text: str, *, animation=None) -> Canvas:
    return c.text(
        content=text,
        font=KR_FONT,
        font_source="google",
        size=24,
        color=GOLD,
        weight=700,
        letter_spacing=2,
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
# Slide 1 — 훅 (The Hook)
# ══════════════════════════════════════════════════════════════════════════════

s1 = dark_stage()
s1 = brand_mark(s1)
s1 = new_badge(s1)
s1 = eyebrow(s1, "신규 앱 출시", animation=Wipe(direction="right", duration=0.4))

s1 = s1.text(
    content="스크롤은\n여기까지.",
    font=KR_FONT,
    font_source="google",
    size=132,
    fill=HYPE,
    weight=900,
    line_height=1.08,
    position=("50%", "34%"),
    align="center",
    animation=Box(direction="in", duration=0.55, trigger="after_previous"),
)

s1 = sparkle(s1, "82%", "30%", 46, animation=Wheel(duration=0.4, trigger="with_previous"))
s1 = sparkle(s1, "16%", "46%", 30, animation=Wheel(duration=0.4, trigger="with_previous"))

s1 = s1.text(
    content="당신의 운동, 완전히 새롭게.",
    font=KR_FONT,
    font_source="google",
    size=32,
    color=OFFWHITE,
    weight=400,
    position=("50%", "56%"),
    align="center",
    animation=Fade(duration=0.4, trigger="after_previous"),
)

s1 = s1.text(
    content="위로 스와이프",
    font=KR_FONT,
    font_source="google",
    size=20,
    color=MUTED,
    weight=500,
    letter_spacing=2,
    position=("50%", "92%"),
    align="center",
    animation=Fade(duration=0.35, delay=0.3, trigger="after_previous"),
)

# ══════════════════════════════════════════════════════════════════════════════
# Slide 2 — 기능 소개 (Feature Reveal)
# ══════════════════════════════════════════════════════════════════════════════

FEATURES = [
    ("34%", "실시간 심박수 동기화"),
    ("44%", "AI 맞춤 운동 코칭"),
    ("54%", "꾸준함을 만드는 스트릭"),
]

s2 = dark_stage()
s2 = brand_mark(s2)
s2 = eyebrow(s2, "지금, 펄스")

s2 = s2.text(
    content="당신을 계속\n움직이게 합니다.",
    font=KR_FONT,
    font_source="google",
    size=76,
    fill=HYPE,
    weight=900,
    line_height=1.1,
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
        color=PINK,
        align=("center", "middle"),
        effects=[GLOW_ACCENT],
        animation=Dissolve(duration=0.3, trigger="after_previous"),
    )
    s2 = s2.text(
        content=text,
        font=KR_FONT,
        font_source="google",
        size=32,
        color=OFFWHITE,
        weight=500,
        position=("34%", y_pct),
        align="left",
        animation=Fade(duration=0.3, trigger="with_previous"),
    )

s2 = divider(s2, "66%", animation=Wipe(direction="right", duration=0.4, trigger="after_previous"))

s2 = s2.text(
    content='"드디어 5km를 완주했어요." — 베타 테스터',
    font=KR_FONT,
    font_source="google",
    size=25,
    color=MUTED,
    weight=400,
    position=("50%", "72%"),
    align="center",
    animation=Fade(duration=0.35, trigger="after_previous"),
)

# ══════════════════════════════════════════════════════════════════════════════
# Slide 3 — 시작하기 (Call to Action)
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
    content="이제,\n당신 차례.",
    font=KR_FONT,
    font_source="google",
    size=116,
    color=WHITE,
    weight=900,
    line_height=1.08,
    position=("50%", "36%"),
    align="center",
    animation=Box(direction="in", duration=0.55),
)

# Sparkles join the headline's own animation group instead of preceding it
# (matching slide 1's pattern), so they don't add a lead-in delay before
# the CTA slide's payoff beat.
s3 = sparkle(s3, "78%", "30%", 44, animation=Wheel(duration=0.4, trigger="with_previous"))
s3 = sparkle(s3, "20%", "40%", 30, animation=Wheel(duration=0.4, trigger="with_previous"))

s3 = s3.text(
    content="이번 주, 펄스 무료 다운로드.",
    font=KR_FONT,
    font_source="google",
    size=30,
    color="#FFF3E8",
    weight=400,
    position=("50%", "50%"),
    align="center",
    animation=Fade(duration=0.4, trigger="after_previous"),
)

s3 = s3.shape(
    shape="pill",
    position=("50%", "62%"),
    width=440,
    height=96,
    color=INK,
    align=("center", "middle"),
    animation=Dissolve(duration=0.4, trigger="after_previous"),
)
s3 = s3.text(
    content="지금 다운로드",
    font=KR_FONT,
    font_source="google",
    size=28,
    color=WHITE,
    weight=700,
    letter_spacing=1,
    position=("50%", "62%"),
    align=("center", "middle"),
    animation=Fade(duration=0.3, trigger="with_previous"),
)

s3 = s3.text(
    content="pulse.app",
    font=KR_FONT,
    font_source="google",
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
# MP4/WebM mux in `soundtrack` (any file ffmpeg decodes); loop_audio=True
# (the default) repeats the 3.75s beat loop seamlessly across the reel.
with open(OUT_GIF, "wb") as f:
    f.write(deck.to_gif(fps=12, slide_duration=1.8, loop=0))

try:
    with open(OUT_MP4, "wb") as f:
        f.write(deck.to_mp4(fps=30, slide_duration=1.8, soundtrack=SOUNDTRACK))
    with open(OUT_WEBM, "wb") as f:
        f.write(deck.to_webm(fps=30, slide_duration=1.8, soundtrack=SOUNDTRACK))
except QuickthumbError as error:
    # RenderingError (e.g. ffmpeg missing) or ValidationError (e.g. the
    # soundtrack asset wasn't checked out) both degrade the same way here.
    print(f"⚠ Skipped MP4/WebM ({error})")

print(f"✓ {OUT_GIF}")
print(f"  {len(deck)} slides, 1.8s hold each — open the GIF or play the MP4/WebM clip.")
