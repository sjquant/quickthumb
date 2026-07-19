"""PULSE — an audio-led vertical product film.

Eight English voiceovers remain intact while every scene uses a distinct visual
idea: live rhythm, broken momentum, readiness, heart-rate sync, adaptive load,
habit formation, proof, and one clear action. Scene lengths follow the actual
narration and land on 128 BPM beat boundaries.

Run:
    uv run python examples/product_hype_reel.py
"""

from pathlib import Path

from quickthumb import (
    AudioTrack,
    Canvas,
    Deck,
    Fade,
    GifOptions,
    QuickthumbError,
    VideoOptions,
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
OUT_PPTX = FILE_DIR / "product_hype_reel.pptx"
OUT_HTML = FILE_DIR / "product_hype_reel.html"

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
CONTENT_X = 96
CONTENT_WIDTH = 888
BEAT = 60.0 / 128.0
SCENE_BEATS = (10, 10, 10, 8, 10, 9, 9, 8)
SCENE_DURATIONS = tuple(beats * BEAT for beats in SCENE_BEATS)
MOTION_FAST = BEAT * 0.55
MOTION_STANDARD = BEAT * 0.85

INK = "#080A0E"
SURFACE = "#10141B"
BLUE = "#147CE5"
BLUE_SOFT = "#5EA8FF"
WHITE = "#F5F5F7"
MUTED = "#9A9BA1"
RULE = "#30343C"


def main() -> None:
    """Build, diagnose, and export the complete audio-led reel."""
    deck = build_deck()
    print_diagnostics(deck)
    export_reel(deck)


def build_deck() -> Deck:
    """Return eight beat-aligned scenes without truncating any narration."""
    scenes = [
        build_hook_scene(),
        build_problem_scene(),
        build_solution_scene(),
        build_live_sync_scene(),
        build_ai_coach_scene(),
        build_streak_scene(),
        build_social_proof_scene(),
        build_cta_scene(),
    ]
    transitions = [
        tr.Cut(advance_after=SCENE_DURATIONS[0]),
        tr.Fade(duration=BEAT, advance_after=SCENE_DURATIONS[1] - BEAT),
        tr.Wipe(direction="up", duration=BEAT, advance_after=SCENE_DURATIONS[2] - BEAT),
        tr.Cut(advance_after=SCENE_DURATIONS[3]),
        tr.Wipe(direction="right", duration=BEAT, advance_after=SCENE_DURATIONS[4] - BEAT),
        tr.Cut(advance_after=SCENE_DURATIONS[5]),
        tr.Fade(duration=BEAT, advance_after=SCENE_DURATIONS[6] - BEAT),
        tr.Fade(duration=BEAT, advance_after=SCENE_DURATIONS[7] - BEAT),
    ]

    deck = Deck(WIDTH, HEIGHT)
    for index, scene in enumerate(scenes):
        deck = deck.slide(
            scene,
            transition=transitions[index],
            audio=str(VOICEOVERS[index]),
            duration=SCENE_DURATIONS[index],
        )
    return deck


def build_hook_scene() -> Canvas:
    """Open on live rhythm rather than a generic product card."""
    canvas = dark_scene()
    canvas = add_brand(canvas, color=WHITE)
    canvas = add_intro_copy(
        canvas,
        eyebrow="PERSONAL FITNESS OS",
        headline="TRAINING,\nMADE PERSONAL.",
        body="From heart rate to recovery, see your rhythm at a glance.",
    )
    canvas = canvas.text(
        content="148",
        font=PRETENDARD[900],
        size=280,
        color=WHITE,
        letter_spacing=-12,
        position=(CONTENT_X, 1050),
        animation=Fade(duration=MOTION_STANDARD, trigger="after_previous"),
    )
    canvas = canvas.text(
        content="BPM  ·  LIVE",
        font=PRETENDARD[800],
        size=48,
        color=WHITE,
        letter_spacing=2,
        position=(CONTENT_X + 8, 1370),
        animation=Fade(duration=MOTION_FAST, trigger="with_previous"),
    )
    return add_pulse_bars(canvas, y=1510, color=WHITE)


def build_problem_scene() -> Canvas:
    """Show momentum breaking on day three as a timeline, not a dashboard."""
    canvas = dark_scene()
    canvas = add_section_copy(
        canvas,
        eyebrow="THE PROBLEM",
        headline="CONSISTENCY\nNEEDS A SYSTEM.",
        body="When feedback arrives late, motivation follows.",
    )
    canvas = canvas.shape(
        shape="rectangle",
        position=(392, 1125),
        width=496,
        height=4,
        color=RULE,
    )
    canvas = canvas.shape(
        shape="rectangle",
        position=(104, 1125),
        width=288,
        height=4,
        color=BLUE,
        animation=Wipe(direction="right", duration=MOTION_STANDARD, trigger="after_previous"),
    )
    for index, x in enumerate((104, 248, 392, 536, 680, 824)):
        active = index < 3
        canvas = canvas.shape(
            shape="ellipse",
            position=(x, 1127),
            width=22 if active else 14,
            height=22 if active else 14,
            color=BLUE if active else RULE,
            align=("center", "middle"),
            animation=Fade(duration=MOTION_FAST, trigger="with_previous"),
        )
    canvas = canvas.text(
        content="DAY 01        DAY 02        DAY 03",
        font=PRETENDARD[700],
        size=48,
        color=MUTED,
        letter_spacing=1,
        position=(104, 1180),
        max_width=670,
        auto_scale=True,
        min_size=48,
    )
    canvas = canvas.text(
        content="FEEDBACK\nARRIVES HERE",
        font=PRETENDARD[800],
        size=58,
        color=WHITE,
        line_height=1.05,
        position=(CONTENT_X, 1320),
        animation=Fade(duration=MOTION_STANDARD, trigger="after_previous"),
    )
    return canvas.text(
        content="TOO LATE",
        font=PRETENDARD[900],
        size=58,
        color=BLUE_SOFT,
        position=(CONTENT_X, 1485),
        animation=Fade(duration=MOTION_FAST, trigger="with_previous"),
    )


def build_solution_scene() -> Canvas:
    """Resolve scattered inputs into one dominant readiness signal."""
    canvas = dark_scene()
    canvas = add_section_copy(
        canvas,
        eyebrow="MEET PULSE",
        headline="FIND YOUR\nDAILY RHYTHM.",
        body="Turn scattered signals into one clear daily score.",
    )
    canvas = canvas.shape(
        shape="ellipse",
        position=(470, 1190),
        width=650,
        height=650,
        color=BLUE,
        opacity=0.16,
        align=("center", "middle"),
    )
    canvas = canvas.text(
        content="84",
        font=PRETENDARD[900],
        size=310,
        color=WHITE,
        letter_spacing=-14,
        position=(CONTENT_X, 980),
        animation=Fade(duration=MOTION_STANDARD, trigger="after_previous"),
    )
    canvas = canvas.text(
        content="RECOVERY / 100",
        font=PRETENDARD[800],
        size=48,
        color=BLUE_SOFT,
        letter_spacing=2,
        position=(CONTENT_X + 8, 1285),
    )
    return add_signal_rows(canvas, start_y=1360)


def build_live_sync_scene() -> Canvas:
    """Turn the current heart rate into a full-screen live instrument."""
    canvas = dark_scene()
    canvas = add_section_copy(
        canvas,
        eyebrow="01  /  LIVE SYNC",
        headline="NEVER MISS\nA BEAT.",
        body="Track heart-rate zones and workout intensity live.",
    )
    canvas = canvas.text(
        content="142",
        font=PRETENDARD[900],
        size=300,
        color=WHITE,
        letter_spacing=-12,
        position=(CONTENT_X, 980),
        animation=Fade(duration=MOTION_STANDARD, trigger="after_previous"),
    )
    canvas = canvas.text(
        content="BPM   ZONE 3",
        font=PRETENDARD[800],
        size=48,
        color=BLUE_SOFT,
        letter_spacing=2,
        position=(CONTENT_X + 8, 1320),
    )
    canvas = add_pulse_bars(canvas, y=1440, color=BLUE)
    return canvas.text(
        content="LIVE  /  SYNCED",
        font=PRETENDARD[700],
        size=48,
        color=MUTED,
        letter_spacing=2,
        position=(CONTENT_X, 1560),
    )


def build_ai_coach_scene() -> Canvas:
    """Show the training plan visibly adapting to recovery."""
    canvas = dark_scene()
    canvas = add_section_copy(
        canvas,
        eyebrow="02  /  ADAPTIVE COACH",
        headline="AI SETS\nTODAY'S PACE.",
        body="Adapt duration and intensity to your recovery.",
    )
    canvas = canvas.text(
        content="PLANNED",
        font=PRETENDARD[700],
        size=48,
        color=MUTED,
        letter_spacing=2,
        position=(CONTENT_X, 1010),
    )
    canvas = canvas.text(
        content="32 MIN  /  HIGH",
        font=PRETENDARD[800],
        size=68,
        color="#666971",
        position=(CONTENT_X, 1070),
    )
    canvas = canvas.shape(
        shape="rectangle",
        position=(CONTENT_X, 1123),
        width=610,
        height=4,
        color=BLUE_SOFT,
        animation=Wipe(direction="right", duration=MOTION_FAST, trigger="after_previous"),
    )
    canvas = canvas.text(
        content="↓  RECOVERY 84",
        font=PRETENDARD[800],
        size=48,
        color=BLUE_SOFT,
        position=(CONTENT_X, 1230),
        animation=Fade(duration=MOTION_FAST, trigger="after_previous"),
    )
    canvas = canvas.text(
        content="TODAY",
        font=PRETENDARD[700],
        size=48,
        color=MUTED,
        letter_spacing=2,
        position=(CONTENT_X, 1360),
    )
    canvas = canvas.text(
        content="24 MIN",
        font=PRETENDARD[900],
        size=150,
        color=WHITE,
        letter_spacing=-5,
        position=(CONTENT_X, 1410),
        animation=Fade(duration=MOTION_STANDARD, trigger="after_previous"),
    )
    return canvas.text(
        content="MODERATE  /  AUTO-ADJUSTED",
        font=PRETENDARD[800],
        size=48,
        color=BLUE_SOFT,
        letter_spacing=1,
        position=(CONTENT_X, 1560),
    )


def build_streak_scene() -> Canvas:
    """Make twenty-one accumulated days the visual proof of habit."""
    canvas = dark_scene()
    canvas = add_section_copy(
        canvas,
        eyebrow="03  /  SMART STREAK",
        headline="TURN THREE DAYS\nINTO TWENTY-ONE.",
        body="Link small wins into a habit that lasts.",
        headline_size=92,
    )
    canvas = canvas.text(
        content="21",
        font=PRETENDARD[900],
        size=330,
        color=WHITE,
        letter_spacing=-16,
        position=(CONTENT_X, 930),
        animation=Fade(duration=MOTION_STANDARD, trigger="after_previous"),
    )
    canvas = canvas.text(
        content="DAY STREAK",
        font=PRETENDARD[800],
        size=48,
        color=BLUE_SOFT,
        letter_spacing=2,
        position=(CONTENT_X + 10, 1300),
    )
    return add_streak_grid(canvas, start_y=1360)


def build_social_proof_scene() -> Canvas:
    """Use a measurable outcome as proof instead of a testimonial card."""
    canvas = dark_scene()
    canvas = add_section_copy(
        canvas,
        eyebrow="PROOF  /  WEEK 8",
        headline="GO LONGER.\nGO FARTHER.",
        body="Progress built with PULSE shows up in the numbers.",
    )
    canvas = canvas.shape(
        shape="rectangle",
        position=(CONTENT_X, 995),
        width=8,
        height=510,
        color=BLUE,
        animation=Wipe(direction="up", duration=MOTION_STANDARD, trigger="after_previous"),
    )
    canvas = canvas.text(
        content="5K",
        font=PRETENDARD[900],
        size=320,
        color=WHITE,
        letter_spacing=-14,
        position=(CONTENT_X + 54, 960),
        animation=Fade(duration=MOTION_STANDARD, trigger="with_previous"),
    )
    canvas = canvas.text(
        content="FIRST FINISH\n+32% DISTANCE",
        font=PRETENDARD[800],
        size=48,
        color=BLUE_SOFT,
        letter_spacing=1,
        line_height=1.1,
        position=(CONTENT_X + 62, 1300),
    )
    canvas = canvas.text(
        content="“I FINALLY RAN\nMY FIRST 5K.”",
        font=PRETENDARD[800],
        size=56,
        color=WHITE,
        line_height=1.05,
        position=(CONTENT_X + 62, 1440),
        animation=Wipe(direction="up", duration=MOTION_STANDARD, trigger="after_previous"),
    )
    return canvas.text(
        content="VERIFIED BETA USER",
        font=PRETENDARD[700],
        size=48,
        color=MUTED,
        letter_spacing=2,
        position=(CONTENT_X + 62, 1570),
    )


def build_cta_scene() -> Canvas:
    """Close with one action on a clean product-blue field."""
    canvas = Canvas.for_platform("instagram-reels").background(color=BLUE)
    canvas = add_brand(canvas, color=WHITE)
    canvas = canvas.text(
        content="TIME TO\nMOVE.",
        font=PRETENDARD[900],
        size=150,
        color=INK,
        line_height=0.98,
        letter_spacing=-5,
        position=(CONTENT_X, 500),
        animation=Fade(duration=MOTION_STANDARD),
    )
    canvas = canvas.text(
        content="The fastest way to understand your body.",
        font=PRETENDARD[500],
        size=50,
        color="#E8F2FF",
        line_height=1.3,
        position=(CONTENT_X, 850),
        max_width=790,
        animation=Fade(duration=MOTION_FAST, trigger="after_previous"),
    )
    canvas = canvas.text(
        content="START FREE  →",
        font=PRETENDARD[900],
        size=76,
        color=WHITE,
        position=(CONTENT_X, 1120),
        animation=Wipe(direction="right", duration=MOTION_STANDARD, trigger="after_previous"),
    )
    canvas = canvas.shape(
        shape="rectangle",
        position=(CONTENT_X, 1225),
        width=520,
        height=5,
        color=WHITE,
    )
    canvas = canvas.text(
        content="7 DAYS FREE  /  CANCEL ANYTIME",
        font=PRETENDARD[700],
        size=48,
        color="#D7E9FF",
        letter_spacing=1,
        position=(CONTENT_X, 1320),
    )
    return canvas.text(
        content="PULSE.APP",
        font=PRETENDARD[900],
        size=54,
        color=WHITE,
        letter_spacing=3,
        position=(CONTENT_X, 1560),
    )


def dark_scene() -> Canvas:
    """Create a restrained dark stage with one semantic brand accent."""
    return Canvas.for_platform("instagram-reels").background(color=INK)


def add_brand(canvas: Canvas, *, color: str) -> Canvas:
    """Add the wordmark only where it anchors the story."""
    return canvas.text(
        content="PULSE",
        font=BRAND_FONT,
        size=48,
        color=color,
        letter_spacing=7,
        position=(CONTENT_X, 250),
    )


def add_intro_copy(canvas: Canvas, *, eyebrow: str, headline: str, body: str) -> Canvas:
    """Place the opening copy below the one-time wordmark."""
    return add_copy(canvas, eyebrow=eyebrow, headline=headline, body=body, top=360)


def add_section_copy(
    canvas: Canvas,
    *,
    eyebrow: str,
    headline: str,
    body: str,
    headline_size: int = 108,
) -> Canvas:
    """Place copy on the shared safe grid without persistent reel chrome."""
    return add_copy(
        canvas,
        eyebrow=eyebrow,
        headline=headline,
        body=body,
        top=280,
        headline_size=headline_size,
    )


def add_copy(
    canvas: Canvas,
    *,
    eyebrow: str,
    headline: str,
    body: str,
    top: int,
    headline_size: int = 108,
) -> Canvas:
    """Build one concise narrative stack for the current scene."""
    canvas = canvas.text(
        content=eyebrow,
        font=PRETENDARD[800],
        size=48,
        color=BLUE_SOFT,
        letter_spacing=3,
        position=(CONTENT_X, top),
        animation=Wipe(direction="right", duration=MOTION_FAST),
    )
    canvas = canvas.text(
        content=headline,
        font=PRETENDARD[900],
        size=headline_size,
        color=WHITE,
        line_height=1.02,
        letter_spacing=-3,
        position=(CONTENT_X, top + 78),
        max_width=CONTENT_WIDTH,
        max_height=270,
        auto_scale=True,
        min_size=78,
        animation=Fade(duration=MOTION_STANDARD, trigger="after_previous"),
    )
    return canvas.text(
        content=body,
        font=PRETENDARD[500],
        size=48,
        color=MUTED,
        line_height=1.3,
        position=(CONTENT_X, top + 390),
        max_width=CONTENT_WIDTH,
        max_height=130,
        auto_scale=True,
        min_size=48,
        animation=Fade(duration=MOTION_FAST, trigger="after_previous"),
    )


def add_pulse_bars(canvas: Canvas, *, y: int, color: str) -> Canvas:
    """Draw a beat trace whose uneven amplitude communicates live motion."""
    heights = (24, 46, 82, 160, 72, 38, 54, 118, 48, 28, 74, 132, 60, 32)
    for index, height in enumerate(heights):
        canvas = canvas.shape(
            shape="pill",
            position=(CONTENT_X + index * 58, y - height // 2),
            width=12,
            height=height,
            color=color,
            opacity=1.0 if index in (3, 7, 11) else 0.52,
            animation=Fade(duration=MOTION_FAST, trigger="with_previous"),
        )
    return canvas


def add_signal_rows(canvas: Canvas, *, start_y: int) -> Canvas:
    """Show the three inputs that resolve into the recovery score."""
    rows = (("SLEEP", "92", 0.92), ("ENERGY", "81", 0.81), ("STRESS", "24", 0.24))
    for index, (label, value, ratio) in enumerate(rows):
        y = start_y + index * 100
        canvas = canvas.text(
            content=f"{label}  {value}",
            font=PRETENDARD[700],
            size=48,
            color=MUTED,
            letter_spacing=1,
            position=(CONTENT_X, y),
        )
        canvas = canvas.shape(
            shape="rectangle",
            position=(430, y + 18),
            width=int(460 * ratio),
            height=8,
            color=BLUE,
            animation=Wipe(direction="right", duration=MOTION_STANDARD, trigger="with_previous"),
        )
    return canvas


def add_streak_grid(canvas: Canvas, *, start_y: int) -> Canvas:
    """Render twenty-one completed days as one accumulated field."""
    for index in range(21):
        row, column = divmod(index, 7)
        canvas = canvas.shape(
            shape="ellipse",
            position=(CONTENT_X + column * 112, start_y + row * 94),
            width=34,
            height=34,
            color=BLUE if index < 20 else WHITE,
            opacity=0.55 + index * 0.02,
            animation=Fade(duration=MOTION_FAST, trigger="with_previous"),
        )
    return canvas


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
    """Export every format with narration and a quiet looping soundtrack."""
    deck.render(
        str(OUT_GIF),
        animation=GifOptions(fps=8, max_size=(540, 960), colors=128),
    )

    for output in (OUT_PPTX, OUT_HTML):
        try:
            deck.render(str(output))
        except QuickthumbError as error:
            print(f"⚠ Skipped {output.suffix.removeprefix('.').upper()} ({error})")

    soundtrack = AudioTrack(path=str(SOUNDTRACK), volume=0.13, loop=True)
    for output in (OUT_MP4, OUT_WEBM):
        try:
            deck.render(str(output), animation=VideoOptions(soundtrack=soundtrack))
        except QuickthumbError as error:
            print(f"⚠ Skipped {output.suffix.removeprefix('.').upper()} ({error})")

    total_duration = sum(SCENE_DURATIONS)
    print(f"✓ {OUT_GIF}")
    print(f"  {OUT_PPTX}")
    print(f"  {OUT_HTML}")
    print(f"  {OUT_MP4}")
    print(f"  {OUT_WEBM}")
    print(f"  {len(deck)} scenes · {total_duration:.2f} seconds · narration-led timeline")


if __name__ == "__main__":
    main()
