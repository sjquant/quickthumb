"""
PULSE — Korean-style vertical app-launch hype reel.

A production-quality animated GIF/MP4/WebM export demonstrating:
  - Vertical 1080x1920 Reels/TikTok/Stories deck with a full 8-scene ad arc
    (hook -> pain point -> solution -> three features -> social proof -> CTA)
    and a Stories-style segmented progress bar, instead of a 3-card teaser
  - Native-register Korean (Hangul) copy set in Pretendard, the typeface
    behind most current Korean tech/startup product design (Toss, Naver,
    Danggeun, ...), bundled locally per weight under assets/fonts (see
    PRETENDARD below) so the example needs no network access to render
  - A K-style promo palette (hot pink -> violet) with sparkle/badge accents
  - Per-layer entrance animations (Box, Wipe, Fade, Dissolve, Wheel) staggered
    with `with_previous` / `after_previous`, exactly as they'd play in HTML export
  - Slide transitions (Wipe, Push, Zoom) rendered as real frames, not
    approximations, with direction chosen to match the story beat: vertical
    Wipe/Push for the "scroll" open, horizontal Push for the feature carousel,
    Zoom for the closing CTA punch
  - Cut points locked to the soundtrack's tempo via `advance_after` (see BEAT
    below), so every slide change lands on a downbeat instead of drifting
    against the music on its own independent clock
  - The bytes-returning tunable API (`to_gif` / `to_mp4` / `to_webm`) and a
    looping soundtrack muxed into the MP4/WebM output

Run:
    uv run python examples/product_hype_reel.py
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

# assets/audio/hype_beat.wav is a 128 BPM, 2-bar (3.75s) loop. Every slide's
# on-screen time below is a whole multiple of one beat so each cut lands
# exactly on the music instead of drifting against it on its own clock.
BEAT = 60.0 / 128.0

# Pretendard ships one static file per weight rather than a variable font, so
# each usage below picks the matching bundled file directly instead of passing
# a `weight=` kwarg -- a font loaded by direct path silently ignores
# bold/italic/weight flags (no warning, unlike the webfont-URL path) since
# the file itself *is* the weight.
_PRETENDARD_DIR = os.path.join(ASSETS_DIR, "fonts")
PRETENDARD = {
    400: os.path.join(_PRETENDARD_DIR, "Pretendard-Regular.woff2"),
    500: os.path.join(_PRETENDARD_DIR, "Pretendard-Medium.woff2"),
    700: os.path.join(_PRETENDARD_DIR, "Pretendard-Bold.woff2"),
    800: os.path.join(_PRETENDARD_DIR, "Pretendard-ExtraBold.woff2"),
    900: os.path.join(_PRETENDARD_DIR, "Pretendard-Black.woff2"),
}

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

SCENE_COUNT = 8


# ── Design helpers ─────────────────────────────────────────────────────────────


def dark_stage() -> Canvas:
    return Canvas(1080, 1920).background(gradient=DEPTH)


def progress_bar(c: Canvas, index: int) -> Canvas:
    """Instagram-Stories-style segmented bar marking scene `index` of SCENE_COUNT."""
    margin, gap = 40, 8
    width = (1080 - 2 * margin - (SCENE_COUNT - 1) * gap) / SCENE_COUNT
    for i in range(SCENE_COUNT):
        c = c.shape(
            shape="pill",
            position=(round(margin + i * (width + gap)), 30),
            width=round(width),
            height=4,
            color=WHITE,
            opacity=1.0 if i == index else 0.28,
        )
    return c


def brand_mark(c: Canvas) -> Canvas:
    return c.text(
        content="PULSE",
        font="Roboto",
        size=24,
        color=PINK,
        weight=700,
        letter_spacing=5,
        position=("50%", "7.5%"),
        align="center",
    )


def new_badge(c: Canvas) -> Canvas:
    """Top-right "NEW" pill, the corner detail Korean app teasers flag a launch with."""
    c = c.shape(
        shape="pill",
        position=("86%", "6.8%"),
        width=112,
        height=40,
        color=PINK,
        align=("center", "middle"),
    )
    return c.text(
        content="신규 출시",
        font=PRETENDARD[800],
        size=17,
        color=WHITE,
        position=("86%", "6.8%"),
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


def backdrop_glow(c: Canvas, x: str, y: str, size: int, color: str, opacity: float) -> Canvas:
    """Soft out-of-focus circle that gives an otherwise flat slide some depth."""
    return c.shape(
        shape="ellipse", position=(x, y), width=size, height=size,
        color=color, opacity=opacity, align=("center", "middle"),
    )  # fmt: skip


def eyebrow(c: Canvas, text: str, *, animation=None) -> Canvas:
    return c.text(
        content=text,
        font=PRETENDARD[700],
        size=23,
        color=GOLD,
        letter_spacing=2,
        position=("50%", "16%"),
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


def feature_slide(index: int, number: str, title: str, description: str) -> Canvas:
    """One numbered feature card in the mid-reel carousel (scenes 4-6)."""
    c = dark_stage()
    c = progress_bar(c, index)
    c = brand_mark(c)
    c = backdrop_glow(c, "50%", "30%", 640, VIOLET, 0.10)
    c = c.text(
        content=number,
        font=PRETENDARD[900],
        size=220,
        fill=HYPE,
        opacity=0.9,
        position=("50%", "26%"),
        align="center",
        animation=Box(direction="in", duration=0.4, trigger="after_previous"),
    )
    c = c.text(
        content=title,
        font=PRETENDARD[900],
        size=54,
        color=WHITE,
        letter_spacing=-2,
        line_height=1.15,
        position=("50%", "48%"),
        align="center",
        animation=Wipe(direction="up", duration=0.35, trigger="after_previous"),
    )
    return c.text(
        content=description,
        font=PRETENDARD[400],
        size=27,
        color=OFFWHITE,
        max_width="76%",
        line_height=1.5,
        position=("50%", "58%"),
        align="center",
        animation=Fade(duration=0.3, trigger="after_previous"),
    )


# ══════════════════════════════════════════════════════════════════════════════
# Scene 1 — 훅 (The Hook)
# ══════════════════════════════════════════════════════════════════════════════

s1 = dark_stage()
s1 = progress_bar(s1, 0)
s1 = brand_mark(s1)
s1 = new_badge(s1)
s1 = eyebrow(s1, "신규 앱 출시", animation=Wipe(direction="right", duration=0.4))

s1 = s1.text(
    content="스크롤은\n여기까지.",
    font=PRETENDARD[900],
    size=128,
    fill=HYPE,
    line_height=1.08,
    letter_spacing=-3,
    position=("50%", "35%"),
    align="center",
    animation=Box(direction="in", duration=0.55, trigger="after_previous"),
)

s1 = sparkle(s1, "82%", "31%", 46, animation=Wheel(duration=0.4, trigger="with_previous"))
s1 = sparkle(s1, "16%", "47%", 30, animation=Wheel(duration=0.4, trigger="with_previous"))

s1 = s1.text(
    content="운동이 완전히 달라집니다.",
    font=PRETENDARD[400],
    size=32,
    color=OFFWHITE,
    position=("50%", "57%"),
    align="center",
    animation=Fade(duration=0.4, trigger="after_previous"),
)

# ══════════════════════════════════════════════════════════════════════════════
# Scene 2 — 공감 (The Pain Point)
# ══════════════════════════════════════════════════════════════════════════════
# A deliberately quiet, sparkle-free beat -- the contrast against scenes 1 and
# 8 makes the hype hit harder when it comes back.

s2 = dark_stage()
s2 = progress_bar(s2, 1)
s2 = brand_mark(s2)

s2 = s2.text(
    content="작심삼일,\n이제 그만.",
    font=PRETENDARD[900],
    size=118,
    color=WHITE,
    line_height=1.1,
    letter_spacing=-3,
    position=("50%", "40%"),
    align="center",
    animation=Box(direction="in", duration=0.5),
)

s2 = s2.text(
    content="혼자 하는 운동은 오래가지 않아요.",
    font=PRETENDARD[400],
    size=30,
    color=MUTED,
    position=("50%", "58%"),
    align="center",
    animation=Fade(duration=0.4, trigger="after_previous"),
)

# ══════════════════════════════════════════════════════════════════════════════
# Scene 3 — 솔루션 (Meet Pulse)
# ══════════════════════════════════════════════════════════════════════════════

s3 = dark_stage()
s3 = progress_bar(s3, 2)
s3 = brand_mark(s3)
s3 = backdrop_glow(s3, "50%", "22%", 560, PINK, 0.08)
s3 = eyebrow(s3, "펄스를 소개합니다")

s3 = s3.text(
    content="매일 움직이는\n습관을 만듭니다.",
    font=PRETENDARD[900],
    size=74,
    fill=HYPE,
    line_height=1.1,
    letter_spacing=-2,
    position=("50%", "24%"),
    align="center",
    animation=Wipe(direction="up", duration=0.5),
)

s3 = s3.text(
    content="꼭 맞는 운동 파트너.",
    font=PRETENDARD[400],
    size=30,
    color=OFFWHITE,
    position=("50%", "42%"),
    align="center",
    animation=Fade(duration=0.35, trigger="after_previous"),
)

# ══════════════════════════════════════════════════════════════════════════════
# Scenes 4-6 — 기능 (Feature Carousel)
# ══════════════════════════════════════════════════════════════════════════════

s4 = feature_slide(3, "01", "실시간 심박수 동기화", "운동 중 심박수를 실시간으로 확인하세요.")
s5 = feature_slide(4, "02", "AI 맞춤 운동 코칭", "체력에 맞춰 강도를 자동으로 조절해요.")
s6 = feature_slide(5, "03", "꾸준함을 만드는 스트릭", "매일의 작은 기록이 큰 변화를 만듭니다.")

# ══════════════════════════════════════════════════════════════════════════════
# Scene 7 — 후기 (Social Proof)
# ══════════════════════════════════════════════════════════════════════════════

s7 = dark_stage()
s7 = progress_bar(s7, 6)
s7 = brand_mark(s7)
s7 = backdrop_glow(s7, "50%", "40%", 720, PINK, 0.07)

star_size, star_step, star_count = 30, 42, 5
stars_start = (1080 - (star_step * (star_count - 1) + star_size)) // 2
for i in range(star_count):
    # A trigger on the very first node in a slide never matters -- there's no
    # prior group for it to join or wait on -- so all five can share
    # "with_previous" and still land in one simultaneous reveal group.
    s7 = s7.shape(
        shape="star",
        position=(stars_start + i * star_step, "34%"),
        width=star_size,
        height=star_size,
        color=GOLD,
        star_points=5,
        inner_radius=0.45,
        align=("left", "middle"),
        animation=Dissolve(duration=0.25, trigger="with_previous"),
    )

s7 = s7.text(
    content='"드디어 5km를 완주했어요."',
    font=PRETENDARD[700],
    size=42,
    color=WHITE,
    line_height=1.3,
    max_width="76%",
    position=("50%", "44%"),
    align="center",
    animation=Fade(duration=0.35, trigger="after_previous"),
)

s7 = divider(s7, "56%", animation=Wipe(direction="right", duration=0.35, trigger="after_previous"))

s7 = s7.text(
    content="베타 테스터 김O진 님",
    font=PRETENDARD[400],
    size=24,
    color=MUTED,
    position=("50%", "60%"),
    align="center",
    animation=Fade(duration=0.3, trigger="after_previous"),
)

# ══════════════════════════════════════════════════════════════════════════════
# Scene 8 — 시작하기 (Call to Action)
# ══════════════════════════════════════════════════════════════════════════════

s8 = Canvas(1080, 1920).background(gradient=HYPE)
s8 = progress_bar(s8, 7)

s8 = s8.shape(
    shape="ellipse",
    position=("50%", "20%"),
    width=900,
    height=900,
    color=WHITE,
    opacity=0.06,
    align=("center", "middle"),
)

s8 = s8.text(
    content="이제,\n움직일 시간.",
    font=PRETENDARD[900],
    size=112,
    color=WHITE,
    line_height=1.08,
    letter_spacing=-3,
    position=("50%", "37%"),
    align="center",
    animation=Box(direction="in", duration=0.55),
)

# Sparkles join the headline's own animation group instead of preceding it
# (matching scene 1's pattern), so they don't add a lead-in delay before
# the CTA scene's payoff beat.
s8 = sparkle(s8, "78%", "31%", 44, animation=Wheel(duration=0.4, trigger="with_previous"))
s8 = sparkle(s8, "20%", "41%", 30, animation=Wheel(duration=0.4, trigger="with_previous"))

s8 = s8.text(
    content="이번 주, 펄스를 무료로 다운로드하세요.",
    font=PRETENDARD[400],
    size=29,
    color="#FFF3E8",
    position=("50%", "51%"),
    align="center",
    animation=Fade(duration=0.4, trigger="after_previous"),
)

s8 = s8.shape(
    shape="pill",
    position=("50%", "63%"),
    width=440,
    height=96,
    color=INK,
    align=("center", "middle"),
    animation=Dissolve(duration=0.4, trigger="after_previous"),
)
s8 = s8.text(
    content="지금 다운로드",
    font=PRETENDARD[700],
    size=28,
    color=WHITE,
    letter_spacing=1,
    position=("50%", "63%"),
    align=("center", "middle"),
    animation=Fade(duration=0.3, trigger="with_previous"),
)

s8 = s8.text(
    content="pulse.app",
    font=PRETENDARD[400],
    size=22,
    color="#FFE8D6",
    position=("50%", "92%"),
    align="center",
    animation=Fade(duration=0.35, trigger="after_previous"),
)

# ══════════════════════════════════════════════════════════════════════════════
# Assemble and export
# ══════════════════════════════════════════════════════════════════════════════

# `advance_after` counts from the end of the slide's own transition, so a
# slide's total on-screen time is transition duration + advance_after. Every
# transition below is a snappy one beat, and `advance_after` is picked so
# each scene's total lands on a whole-beat count -- six beats for a normal
# scene, eight for the CTA's bigger finish. Direction follows the story:
# vertical Wipe/Push carries the "scroll" open (scenes 1-3), horizontal Push
# reads as swiping through the feature carousel (scenes 3-7), and Zoom lands
# the closing CTA punch (scene 8).
deck = (
    Deck(1080, 1920)
    # Cut's own `duration` field is unused here -- the exporter forces a hard
    # cut to 0s regardless of it -- only `advance_after` does anything.
    .slide(s1, transition=tr.Cut(advance_after=6 * BEAT))
    .slide(s2, transition=tr.Wipe(direction="up", duration=BEAT, advance_after=5 * BEAT))
    .slide(s3, transition=tr.Push(direction="up", duration=BEAT, advance_after=5 * BEAT))
    .slide(s4, transition=tr.Push(direction="left", duration=BEAT, advance_after=5 * BEAT))
    .slide(s5, transition=tr.Push(direction="left", duration=BEAT, advance_after=5 * BEAT))
    .slide(s6, transition=tr.Push(direction="left", duration=BEAT, advance_after=5 * BEAT))
    .slide(s7, transition=tr.Push(direction="left", duration=BEAT, advance_after=5 * BEAT))
    .slide(s8, transition=tr.Zoom(direction="in", duration=BEAT, advance_after=7 * BEAT))
)

# .to_gif()/.to_mp4()/.to_webm() return bytes; .render() (used in
# investor_deck.py) writes straight to a path chosen by extension instead.
# `slide_duration` is omitted -- every slide above sets its own
# `advance_after`, so the deck-level fallback never applies. MP4/WebM mux in
# `soundtrack`; loop_audio=True (the default) repeats the beat loop
# seamlessly for as long as the beat-locked edit runs. The GIF drops to 10fps
# (vs. 30 for MP4/WebM) to keep the preview file a reasonable size across an
# 8-scene, ~23s reel -- open the MP4/WebM for the full-quality motion.
with open(OUT_GIF, "wb") as f:
    f.write(deck.to_gif(fps=10, loop=0))

try:
    with open(OUT_MP4, "wb") as f:
        f.write(deck.to_mp4(fps=30, soundtrack=SOUNDTRACK))
    with open(OUT_WEBM, "wb") as f:
        f.write(deck.to_webm(fps=30, soundtrack=SOUNDTRACK))
except QuickthumbError as error:
    # RenderingError (e.g. ffmpeg missing) or ValidationError (e.g. the
    # soundtrack asset wasn't checked out) both degrade the same way here.
    print(f"⚠ Skipped MP4/WebM ({error})")

print(f"✓ {OUT_GIF}")
print(f"  {len(deck)} scenes, cut on the beat — open the GIF or play the MP4/WebM clip.")
