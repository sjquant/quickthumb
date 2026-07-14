"""PULSE — a polished, beat-synced vertical product hype reel.

The example builds an eight-scene Korean fitness-app ad on one Reels-safe
layout grid. It demonstrates platform-aware diagnostics, layered gradients,
animated product-metric cards, native Pretendard typography, slide transitions
in GIF/WebM, and per-scene Korean voiceovers in the static MP4 export.

Run:
    uv run python examples/product_hype_reel.py
"""

import subprocess
import tempfile
from pathlib import Path

from quickthumb import (
    AudioTrack,
    Canvas,
    Deck,
    Dissolve,
    Fade,
    Glow,
    InnerShadow,
    LinearGradient,
    QuickthumbError,
    RadialGradient,
    Shadow,
    Stroke,
    Wipe,
)
from quickthumb import transitions as tr

FILE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = FILE_DIR.parent / "assets"
SOUNDTRACK = ASSETS_DIR / "audio" / "hype_beat.wav"
VOICEOVER_DIR = ASSETS_DIR / "audio" / "product_hype_reel_voiceover"
VOICEOVERS = [VOICEOVER_DIR / f"scene-{index:02d}.wav" for index in range(1, 9)]
OUT_GIF = FILE_DIR / "product_hype_reel.gif"
OUT_MP4 = FILE_DIR / "product_hype_reel.mp4"
OUT_WEBM = FILE_DIR / "product_hype_reel.webm"

PRETENDARD = {
    400: str(ASSETS_DIR / "fonts" / "Pretendard-Regular.woff2"),
    500: str(ASSETS_DIR / "fonts" / "Pretendard-Medium.woff2"),
    700: str(ASSETS_DIR / "fonts" / "Pretendard-Bold.woff2"),
    800: str(ASSETS_DIR / "fonts" / "Pretendard-ExtraBold.woff2"),
    900: str(ASSETS_DIR / "fonts" / "Pretendard-Black.woff2"),
}
BRAND_FONT = str(ASSETS_DIR / "fonts" / "Roboto-Bold.ttf")

WIDTH = 1080
HEIGHT = 1920
SCENE_COUNT = 8
CONTENT_X = 96
CONTENT_WIDTH = 800
CONTENT_RIGHT = CONTENT_X + CONTENT_WIDTH
CONTENT_CENTER = CONTENT_X + CONTENT_WIDTH // 2
BEAT = 60.0 / 128.0
SCENE_DURATION = 4.5
SCENE_HOLD = SCENE_DURATION - BEAT
COPY_LEAD_IN = BEAT / 2
MOTION_FAST = BEAT * 0.6
MOTION_STANDARD = BEAT * 0.8
MOTION_HERO = BEAT * 0.9

INK = "#090711"
SURFACE = "#100D1D"
SURFACE_RAISED = "#12101E"
PINK = "#FF4F9A"
VIOLET = "#9A6BFF"
CYAN = "#5DE8FF"
LIME = "#C9FF63"
WHITE = "#FFFFFF"
OFFWHITE = "#F8F4FF"
MUTED = "#C7BDD9"
RULE = "#403653"

DEPTH = LinearGradient(angle=165, stops=[(INK, 0.0), (SURFACE, 1.0)])
HYPE = LinearGradient(angle=115, stops=[(PINK, 0.0), (VIOLET, 1.0)])
CARD_EFFECTS = [
    Shadow(offset_x=0, offset_y=24, color="#00000080", blur_radius=34),
    Stroke(width=2, color="#3A304E"),
    InnerShadow(offset_x=0, offset_y=2, color=WHITE, blur_radius=10, opacity=0.06),
]
BUTTON_EFFECTS = [
    Shadow(offset_x=0, offset_y=22, color="#3A0C4E70", blur_radius=30),
    Glow(radius=20, color=WHITE, opacity=0.18),
]


def main() -> None:
    """Build, diagnose, and export the complete reel."""
    deck = build_deck()
    print_diagnostics(deck)
    export_reel(deck)


def build_deck() -> Deck:
    """Return the eight-scene, 48-beat PULSE reel."""
    hook = build_hook_scene()
    problem = build_problem_scene()
    solution = build_solution_scene()
    live_sync = build_live_sync_scene()
    ai_coach = build_ai_coach_scene()
    streak = build_streak_scene()
    proof = build_social_proof_scene()
    cta = build_cta_scene()

    # Longer scenes give the Korean narration room to breathe while keeping
    # every incoming transition aligned to a beat.
    return (
        Deck(WIDTH, HEIGHT)
        .slide(
            hook,
            transition=tr.Cut(advance_after=SCENE_DURATION),
            audio=str(VOICEOVERS[0]),
            duration=SCENE_DURATION,
        )
        .slide(
            problem,
            transition=tr.Wipe(direction="up", duration=BEAT, advance_after=SCENE_HOLD),
            audio=str(VOICEOVERS[1]),
            duration=SCENE_DURATION,
        )
        .slide(
            solution,
            transition=tr.Push(direction="up", duration=BEAT, advance_after=SCENE_HOLD),
            audio=str(VOICEOVERS[2]),
            duration=SCENE_DURATION,
        )
        .slide(
            live_sync,
            transition=tr.Push(direction="left", duration=BEAT, advance_after=SCENE_HOLD),
            audio=str(VOICEOVERS[3]),
            duration=SCENE_DURATION,
        )
        .slide(
            ai_coach,
            transition=tr.Push(direction="left", duration=BEAT, advance_after=SCENE_HOLD),
            audio=str(VOICEOVERS[4]),
            duration=SCENE_DURATION,
        )
        .slide(
            streak,
            transition=tr.Push(direction="left", duration=BEAT, advance_after=SCENE_HOLD),
            audio=str(VOICEOVERS[5]),
            duration=SCENE_DURATION,
        )
        .slide(
            proof,
            transition=tr.Fade(duration=BEAT, advance_after=SCENE_HOLD),
            audio=str(VOICEOVERS[6]),
            duration=SCENE_DURATION,
        )
        .slide(
            cta,
            transition=tr.Zoom(direction="in", duration=BEAT, advance_after=SCENE_HOLD),
            audio=str(VOICEOVERS[7]),
            duration=SCENE_DURATION,
        )
    )


def build_hook_scene() -> Canvas:
    """Open with a bold promise and a live heart-rate product card."""
    canvas = base_scene(0, PINK)
    canvas = add_copy(
        canvas,
        eyebrow="NEW  ·  PERSONAL FITNESS OS",
        headline="TRAINING,\nMADE PERSONAL.",
        body="From heart rate to recovery, see your rhythm at a glance.",
        accent=PINK,
        headline_size=108,
    )
    canvas = add_card(
        canvas,
        y=965,
        height=450,
        animation=Dissolve(duration=MOTION_STANDARD, trigger="after_previous"),
    )
    canvas = canvas.text(
        content="●  LIVE HEART RATE",
        font=PRETENDARD[700],
        size=48,
        color=PINK,
        position=(144, 1018),
        align=("left", "top"),
        animation=Fade(duration=MOTION_FAST, trigger="with_previous"),
    )
    canvas = canvas.text(
        content="ZONE 4",
        font=PRETENDARD[700],
        size=48,
        color=MUTED,
        position=(848, 1018),
        align=("right", "top"),
        animation=Fade(duration=MOTION_FAST, trigger="with_previous"),
    )
    canvas = canvas.text(
        content="148",
        font=PRETENDARD[900],
        size=176,
        color=WHITE,
        position=(140, 1092),
        align=("left", "top"),
        effects=[Glow(radius=20, color=PINK, opacity=0.3)],
        animation=Fade(duration=MOTION_STANDARD, trigger="after_previous"),
    )
    canvas = canvas.text(
        content="BPM",
        font=PRETENDARD[800],
        size=52,
        color=PINK,
        position=(520, 1230),
        align=("left", "top"),
        animation=Fade(duration=MOTION_FAST, trigger="with_previous"),
    )
    canvas = canvas.text(
        content="HEART RATE  ·  PERFORMANCE",
        font=PRETENDARD[500],
        size=48,
        color=MUTED,
        position=(144, 1340),
        align=("left", "top"),
        animation=Fade(duration=MOTION_FAST, trigger="after_previous"),
    )
    return add_footer(
        canvas,
        "PULSE  ·  PERSONAL FITNESS OS",
        animation=Fade(duration=MOTION_FAST, trigger="with_previous"),
    )


def build_problem_scene() -> Canvas:
    """Frame inconsistent exercise as a feedback problem, not a willpower problem."""
    canvas = base_scene(1, VIOLET)
    canvas = add_copy(
        canvas,
        eyebrow="THE PROBLEM",
        headline="CONSISTENCY\nNEEDS A SYSTEM.",
        body="When feedback arrives late, motivation follows.",
        accent=VIOLET,
        headline_size=96,
    )
    canvas = add_card(
        canvas,
        y=980,
        height=195,
        animation=Dissolve(duration=MOTION_STANDARD, trigger="after_previous"),
    )
    canvas = canvas.text(
        content="AVERAGE DROP-OFF",
        font=PRETENDARD[700],
        size=48,
        color=MUTED,
        position=(140, 1035),
        align=("left", "top"),
        animation=Fade(duration=MOTION_FAST, trigger="with_previous"),
    )
    canvas = canvas.text(
        content="DAY 03",
        font=PRETENDARD[900],
        size=82,
        color=VIOLET,
        position=(848, 1077),
        align=("right", "top"),
        animation=Fade(duration=MOTION_STANDARD, trigger="with_previous"),
    )
    canvas = add_card(
        canvas,
        y=1200,
        height=195,
        animation=Dissolve(duration=MOTION_STANDARD, trigger="after_previous"),
    )
    canvas = canvas.text(
        content="LIVE FEEDBACK",
        font=PRETENDARD[700],
        size=48,
        color=MUTED,
        position=(140, 1255),
        align=("left", "top"),
        animation=Fade(duration=MOTION_FAST, trigger="with_previous"),
    )
    canvas = canvas.text(
        content="0%",
        font=PRETENDARD[900],
        size=90,
        color=PINK,
        position=(848, 1234),
        align=("right", "top"),
        animation=Fade(duration=MOTION_STANDARD, trigger="with_previous"),
    )
    return add_footer(
        canvas,
        "LATE FEEDBACK KILLS MOMENTUM.",
        animation=Fade(duration=MOTION_FAST, trigger="with_previous"),
    )


def build_solution_scene() -> Canvas:
    """Introduce PULSE as one clear daily readiness signal."""
    canvas = base_scene(2, CYAN)
    canvas = add_copy(
        canvas,
        eyebrow="MEET PULSE",
        headline="FIND YOUR\nDAILY RHYTHM.",
        body="Turn scattered signals into one clear daily score.",
        accent=CYAN,
        headline_size=108,
        headline_letter_spacing=0,
    )
    canvas = add_card(
        canvas,
        y=965,
        height=450,
        animation=Dissolve(duration=MOTION_STANDARD, trigger="after_previous"),
    )
    canvas = canvas.text(
        content="RECOVERY",
        font=PRETENDARD[700],
        size=48,
        color=CYAN,
        position=(144, 1018),
        align=("left", "top"),
        animation=Fade(duration=MOTION_FAST, trigger="with_previous"),
    )
    canvas = canvas.text(
        content="84",
        font=PRETENDARD[900],
        size=176,
        color=WHITE,
        position=(140, 1092),
        align=("left", "top"),
        effects=[Glow(radius=20, color=CYAN, opacity=0.28)],
        animation=Fade(duration=MOTION_STANDARD, trigger="after_previous"),
    )
    canvas = canvas.text(
        content="/ 100",
        font=PRETENDARD[800],
        size=52,
        color=CYAN,
        position=(430, 1230),
        align=("left", "top"),
        animation=Fade(duration=MOTION_FAST, trigger="with_previous"),
    )
    canvas = canvas.text(
        content="SLEEP 92  ·  ENERGY 81  ·  STRESS 24",
        font=PRETENDARD[500],
        size=48,
        color=MUTED,
        position=(144, 1340),
        align=("left", "top"),
        max_width=704,
        auto_scale=True,
        min_size=48,
        letter_spacing=2,
        animation=Fade(duration=MOTION_FAST, trigger="after_previous"),
    )
    return add_footer(
        canvas,
        "READ TODAY'S BODY AT A GLANCE.",
        animation=Fade(duration=MOTION_FAST, trigger="with_previous"),
    )


def build_live_sync_scene() -> Canvas:
    """Show the first feature: live heart-rate synchronization."""
    canvas = base_scene(3, PINK)
    canvas = add_copy(
        canvas,
        eyebrow="01  ·  LIVE SYNC",
        headline="NEVER MISS\nA BEAT.",
        body="Track heart-rate zones and workout intensity live.",
        accent=PINK,
        headline_size=93,
        headline_letter_spacing=0,
    )
    canvas = add_metric_card(
        canvas,
        label="LIVE HEART RATE",
        status="SYNCED",
        value="142",
        unit="BPM",
        unit_x=500,
        detail="WARM-UP  ·  FAT BURN  ·  CARDIO",
        accent=PINK,
    )
    return add_footer(
        canvas,
        "APPLE WATCH  ·  GALAXY WATCH",
        animation=Fade(duration=MOTION_FAST, trigger="with_previous"),
    )


def build_ai_coach_scene() -> Canvas:
    """Show the second feature: an adaptive daily training load."""
    canvas = base_scene(4, CYAN)
    canvas = add_copy(
        canvas,
        eyebrow="02  ·  AI COACH",
        headline="AI SETS\nTODAY'S PACE.",
        body="Adapt duration and intensity to your recovery.",
        accent=CYAN,
        headline_size=95,
        headline_letter_spacing=0,
    )
    canvas = add_metric_card(
        canvas,
        label="TODAY'S LOAD",
        status="AUTO",
        value="68",
        unit="%",
        unit_x=390,
        detail="INTERVAL 24 MIN  ·  RECOMMENDED: MODERATE",
        accent=CYAN,
    )
    return add_footer(
        canvas,
        "A COACHING PLAN THAT ADAPTS EVERY DAY.",
        animation=Fade(duration=MOTION_FAST, trigger="with_previous"),
    )


def build_streak_scene() -> Canvas:
    """Show the third feature: a motivating twenty-one-day streak."""
    canvas = base_scene(5, LIME)
    canvas = add_copy(
        canvas,
        eyebrow="03  ·  SMART STREAK",
        headline="TURN THREE DAYS\nINTO TWENTY-ONE.",
        body="Link small wins into a habit that lasts.",
        accent=LIME,
        headline_size=96,
    )
    canvas = add_card(
        canvas,
        y=965,
        height=450,
        animation=Dissolve(duration=MOTION_STANDARD, trigger="after_previous"),
    )
    canvas = canvas.text(
        content="CONSISTENCY",
        font=PRETENDARD[700],
        size=48,
        color=LIME,
        position=(144, 1018),
        align=("left", "top"),
        animation=Fade(duration=MOTION_FAST, trigger="with_previous"),
    )
    canvas = canvas.text(
        content="BEST",
        font=PRETENDARD[700],
        size=48,
        color=MUTED,
        position=(848, 1018),
        align=("right", "top"),
        animation=Fade(duration=MOTION_FAST, trigger="with_previous"),
    )
    canvas = canvas.text(
        content="21",
        font=PRETENDARD[900],
        size=176,
        color=WHITE,
        position=(140, 1092),
        align=("left", "top"),
        effects=[Glow(radius=20, color=LIME, opacity=0.24)],
        animation=Fade(duration=MOTION_STANDARD, trigger="after_previous"),
    )
    canvas = canvas.text(
        content="DAY STREAK",
        font=PRETENDARD[800],
        size=52,
        color=LIME,
        position=(430, 1230),
        align=("left", "top"),
        animation=Fade(duration=MOTION_FAST, trigger="with_previous"),
    )
    canvas = canvas.text(
        content="●  ●  ●  ●  ●  ●  ●",
        font=PRETENDARD[700],
        size=48,
        color=LIME,
        position=(144, 1340),
        align=("left", "top"),
        animation=Fade(duration=MOTION_FAST, trigger="after_previous"),
    )
    return add_footer(
        canvas,
        "WHEN CONSISTENCY IS VISIBLE, HABITS KEEP GOING.",
        animation=Fade(duration=MOTION_FAST, trigger="with_previous"),
    )


def build_social_proof_scene() -> Canvas:
    """Land the product story with a credible, high-contrast testimonial."""
    canvas = base_scene(6, VIOLET)
    canvas = add_copy(
        canvas,
        eyebrow="4.9  ·  2,841 REVIEWS",
        headline="GO LONGER.\nGO FARTHER.",
        body="Progress built with PULSE shows up in the numbers.",
        accent=VIOLET,
        headline_size=100,
    )
    canvas = add_card(
        canvas,
        y=950,
        height=465,
        animation=Dissolve(duration=MOTION_STANDARD, trigger="after_previous"),
    )
    canvas = canvas.text(
        content="VERIFIED REVIEW",
        font=PRETENDARD[700],
        size=48,
        color=LIME,
        letter_spacing=2,
        position=(140, 1004),
        align=("left", "top"),
        animation=Fade(duration=MOTION_FAST, trigger="with_previous"),
    )
    canvas = canvas.text(
        content="4.9",
        font=PRETENDARD[900],
        size=72,
        color=VIOLET,
        position=(848, 996),
        align=("right", "top"),
        animation=Fade(duration=MOTION_STANDARD, trigger="with_previous"),
    )
    canvas = canvas.text(
        content="★★★★★",
        font=PRETENDARD[700],
        size=48,
        color=LIME,
        letter_spacing=3,
        position=(140, 1072),
        align=("left", "top"),
        animation=Fade(duration=MOTION_FAST, trigger="with_previous"),
    )
    canvas = canvas.text(
        content="“I FINALLY RAN\nMY FIRST 5K.”",
        font=PRETENDARD[800],
        size=68,
        color=WHITE,
        line_height=1.16,
        position=(140, 1140),
        align=("left", "top"),
        animation=Wipe(direction="up", duration=MOTION_STANDARD, trigger="after_previous"),
    )
    canvas = canvas.text(
        content="BETA TESTER  ·  RUNNING, WEEK 8",
        font=PRETENDARD[500],
        size=48,
        color=MUTED,
        position=(140, 1338),
        align=("left", "top"),
        animation=Fade(duration=MOTION_FAST, trigger="after_previous"),
    )
    return add_footer(
        canvas,
        "YOUR NEXT PERSONAL BEST STARTS HERE.",
        animation=Fade(duration=MOTION_FAST, trigger="with_previous"),
    )


def build_cta_scene() -> Canvas:
    """Finish on a bright, single-action download screen."""
    canvas = bright_scene(7)
    canvas = add_copy(
        canvas,
        eyebrow="PULSE  ·  START TODAY",
        headline="TIME TO\nMOVE.",
        body="The fastest way to understand your body.",
        accent=INK,
        headline_size=124,
        bright=True,
    )
    canvas = canvas.shape(
        shape="pill",
        position=(CONTENT_X, 1010),
        width=CONTENT_WIDTH,
        height=132,
        color=INK,
        align=("left", "top"),
        effects=BUTTON_EFFECTS,
        animation=Dissolve(duration=MOTION_STANDARD, trigger="after_previous"),
    )
    canvas = canvas.text(
        content="START FREE",
        font=PRETENDARD[800],
        size=56,
        color=WHITE,
        position=(CONTENT_CENTER, 1076),
        align=("center", "middle"),
        animation=Fade(duration=MOTION_FAST, trigger="with_previous"),
    )
    canvas = canvas.text(
        content="4.9 RATING  ·  7 DAYS FREE  ·  CANCEL ANYTIME",
        font=PRETENDARD[700],
        size=48,
        color=INK,
        position=(CONTENT_X, 1220),
        align=("left", "top"),
        max_width=CONTENT_WIDTH,
        auto_scale=True,
        min_size=48,
        animation=Fade(duration=MOTION_FAST, trigger="after_previous"),
    )
    return canvas.text(
        content="PULSE.APP  ↗",
        font=PRETENDARD[900],
        size=54,
        color=INK,
        letter_spacing=2,
        position=(CONTENT_X, 1450),
        align=("left", "top"),
        animation=Fade(duration=MOTION_FAST, trigger="after_previous"),
    )


def base_scene(index: int, accent: str) -> Canvas:
    """Create a dark Reels-safe stage with layered ambient color."""
    canvas = (
        Canvas.for_platform("instagram-reels")
        .background(gradient=DEPTH)
        .background(
            gradient=RadialGradient(
                center=(0.82, 0.2),
                stops=[(f"{accent}10", 0.0), (f"{accent}00", 1.0)],
            )
        )
        .background(
            gradient=RadialGradient(
                center=(0.08, 0.78),
                stops=[(f"{CYAN}08", 0.0), (f"{CYAN}00", 0.72)],
            )
        )
    )
    return add_chrome(canvas, index, bright=False)


def bright_scene(index: int) -> Canvas:
    """Create the bright gradient stage used for the final CTA."""
    canvas = (
        Canvas.for_platform("instagram-reels")
        .background(gradient=HYPE)
        .background(
            gradient=RadialGradient(
                center=(0.82, 0.24),
                stops=[("#FFFFFF48", 0.0), ("#FFFFFF00", 0.72)],
            )
        )
    )
    return add_chrome(canvas, index, bright=True)


def add_chrome(canvas: Canvas, index: int, *, bright: bool) -> Canvas:
    """Add a safe-area progress rail and consistently aligned reel header."""
    gap = 10
    segment_width = (CONTENT_WIDTH - gap * (SCENE_COUNT - 1)) // SCENE_COUNT
    for segment in range(SCENE_COUNT):
        if bright:
            color = WHITE if segment == index else "#D640A9"
            opacity = 1.0 if segment == index else 0.55
        elif segment < index:
            color = PINK
            opacity = 0.8
        elif segment == index:
            color = WHITE
            opacity = 1.0
        else:
            color = RULE
            opacity = 0.7
        canvas = canvas.shape(
            shape="pill",
            position=(CONTENT_X + segment * (segment_width + gap), 244),
            width=segment_width,
            height=8,
            color=color,
            opacity=opacity,
            align=("left", "top"),
        )

    header_color = INK if bright else OFFWHITE
    canvas = canvas.text(
        content="PULSE",
        font=BRAND_FONT,
        size=48,
        color=header_color,
        letter_spacing=7,
        position=(CONTENT_X, 290),
        align=("left", "top"),
    )
    return canvas.text(
        content=f"{index + 1:02d} / {SCENE_COUNT:02d}",
        font=PRETENDARD[700],
        size=48,
        color=header_color if bright else MUTED,
        letter_spacing=3,
        position=(CONTENT_RIGHT, 290),
        align=("right", "top"),
    )


def add_copy(
    canvas: Canvas,
    *,
    eyebrow: str,
    headline: str,
    body: str,
    accent: str,
    headline_size: int,
    headline_letter_spacing: int = -3,
    bright: bool = False,
) -> Canvas:
    """Place the shared eyebrow, headline, and body on one explicit grid."""
    canvas = canvas.text(
        content=eyebrow,
        font=PRETENDARD[800],
        size=48,
        color=accent,
        letter_spacing=2,
        position=(CONTENT_X, 410),
        align=("left", "top"),
        max_width=CONTENT_WIDTH,
        auto_scale=True,
        min_size=48,
        animation=Wipe(direction="right", duration=MOTION_FAST, delay=COPY_LEAD_IN),
    )
    canvas = canvas.text(
        content=headline,
        font=PRETENDARD[900],
        size=headline_size,
        color=INK if bright else WHITE,
        line_height=1.05,
        letter_spacing=headline_letter_spacing,
        position=(CONTENT_X, 500),
        align=("left", "top"),
        max_width=CONTENT_WIDTH,
        max_height=270,
        auto_scale=True,
        min_size=80,
        animation=Fade(duration=MOTION_HERO, trigger="after_previous"),
    )
    return canvas.text(
        content=body,
        font=PRETENDARD[500],
        size=52,
        color="#32112F" if bright else MUTED,
        line_height=1.35,
        position=(CONTENT_X, 805),
        align=("left", "top"),
        max_width=CONTENT_WIDTH,
        max_height=130,
        auto_scale=True,
        min_size=48,
        animation=Fade(duration=MOTION_FAST, trigger="after_previous"),
    )


def add_card(
    canvas: Canvas,
    *,
    y: int,
    height: int,
    animation: Dissolve,
) -> Canvas:
    """Add the shared elevated product-card surface."""
    return canvas.shape(
        shape="rectangle",
        position=(CONTENT_X, y),
        width=CONTENT_WIDTH,
        height=height,
        color=SURFACE_RAISED,
        border_radius=42,
        align=("left", "top"),
        effects=CARD_EFFECTS,
        animation=animation,
    )


def add_metric_card(
    canvas: Canvas,
    *,
    label: str,
    status: str,
    value: str,
    unit: str,
    unit_x: int,
    detail: str,
    accent: str,
) -> Canvas:
    """Add a reusable animated feature metric card."""
    canvas = add_card(
        canvas,
        y=965,
        height=450,
        animation=Dissolve(duration=MOTION_STANDARD, trigger="after_previous"),
    )
    canvas = canvas.text(
        content=label,
        font=PRETENDARD[700],
        size=48,
        color=accent,
        position=(144, 1018),
        align=("left", "top"),
        animation=Fade(duration=MOTION_FAST, trigger="with_previous"),
    )
    canvas = canvas.text(
        content=status,
        font=PRETENDARD[700],
        size=48,
        color=MUTED,
        position=(848, 1018),
        align=("right", "top"),
        animation=Fade(duration=MOTION_FAST, trigger="with_previous"),
    )
    canvas = canvas.text(
        content=value,
        font=PRETENDARD[900],
        size=176,
        color=WHITE,
        position=(140, 1092),
        align=("left", "top"),
        effects=[Glow(radius=20, color=accent, opacity=0.28)],
        animation=Fade(duration=MOTION_STANDARD, trigger="after_previous"),
    )
    canvas = canvas.text(
        content=unit,
        font=PRETENDARD[800],
        size=52,
        color=accent,
        position=(unit_x, 1230),
        align=("left", "top"),
        animation=Fade(duration=MOTION_FAST, trigger="with_previous"),
    )
    return canvas.text(
        content=detail,
        font=PRETENDARD[500],
        size=48,
        color=MUTED,
        position=(144, 1340),
        align=("left", "top"),
        max_width=704,
        auto_scale=True,
        min_size=48,
        animation=Fade(duration=MOTION_FAST, trigger="after_previous"),
    )


def add_footer(canvas: Canvas, text: str, *, animation: Fade) -> Canvas:
    """Add the final safe-area caption on the shared left edge."""
    return canvas.text(
        content=text,
        font=PRETENDARD[700],
        size=48,
        color=OFFWHITE,
        position=(CONTENT_X, 1496),
        align=("left", "top"),
        max_width=CONTENT_WIDTH,
        auto_scale=True,
        min_size=48,
        animation=animation,
    )


def print_diagnostics(deck: Deck) -> None:
    """Print every layout finding before spending time on video encoding."""
    findings = deck.diagnose()
    for finding in findings:
        location = (
            f"scene {finding.slide_index + 1}, layer {finding.layer_index}"
            if finding.slide_index is not None
            else "deck"
        )
        print(f"[{finding.severity}] {location}: {finding.code} — {finding.message}")
    if not findings:
        print("✓ diagnose(): all 8 scenes pass layout and legibility checks")


def export_reel(deck: Deck) -> None:
    """Render all supported outputs without truncating an existing file on failure."""
    # A 1080×1920 GIF stores every frame in memory; 2fps keeps this longer
    # reel below the export budget while MP4/WebM preserve smooth 30fps motion.
    OUT_GIF.write_bytes(deck.to_gif(fps=2, loop=0))

    try:
        with tempfile.TemporaryDirectory() as directory:
            soundtrack = Path(directory) / "soundtrack.m4a"
            _mix_soundtrack(soundtrack)
            audio = AudioTrack(path=str(soundtrack), volume=0.9)
            deck.render(str(OUT_MP4), soundtrack=audio)
            deck.render(str(OUT_WEBM), soundtrack=audio)
    except QuickthumbError as error:
        print(f"⚠ Skipped MP4/WebM ({error})")

    print(f"✓ {OUT_GIF}")
    print(f"  {len(deck)} scenes · 36 seconds · narration-first timeline")


def _mix_soundtrack(output_path: Path) -> None:
    """Mix the looping music bed and slide voiceovers during export."""
    command = ["ffmpeg", "-y", "-stream_loop", "-1", "-i", str(SOUNDTRACK)]
    for voiceover in VOICEOVERS:
        command.extend(["-i", str(voiceover)])
    delays = ";".join(
        f"[{index}:a]adelay={int((index - 1) * SCENE_DURATION * 1000)}:all=1[v{index}]"
        for index in range(1, len(VOICEOVERS) + 1)
    )
    voices = "".join(f"[v{index}]" for index in range(1, len(VOICEOVERS) + 1))
    command.extend(
        [
            "-filter_complex",
            f"[0:a]volume=0.16,atrim=duration=36[bg];{delays};[bg]{voices}amix=inputs=9:duration=first:normalize=0[a]",
            "-map",
            "[a]",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            str(output_path),
        ]
    )
    subprocess.run(command, check=True, capture_output=True)


if __name__ == "__main__":
    main()
