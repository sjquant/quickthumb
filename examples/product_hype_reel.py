"""PULSE — an audio-led vertical product film.

Eight English voiceovers remain intact while every scene is built on its own
visual idea: a live trace, a timeline that runs past its point, three signals
converging into one score, a full instrument, an adapting plan, an accumulated
field, an eight-week chart, and one clear action. Scene lengths follow the
actual narration and land on 128 BPM beat boundaries.

Run:
    uv run python examples/product_hype_reel.py
"""

import math
from pathlib import Path

from quickthumb import (
    AnimationSpec,
    AudioTrack,
    Canvas,
    Deck,
    Fade,
    GifOptions,
    KeyframeSpec,
    PositionTrack,
    QuickthumbError,
    RadialGradient,
    ScaleTrack,
    TimingSpec,
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
# Pretendard is the film's voice; Roboto is reserved for the wordmark, so the
# brand never reads as one more line of body copy.
BRAND_FONT = str(ASSETS_DIR / "fonts" / "Roboto-Bold.ttf")

PLATFORM = "instagram-reels"
# The preset owns both the frame size and the safe-area diagnostics, so the
# layout grid is derived from it instead of restating 1080x1920 beside it.
WIDTH = Canvas.for_platform(PLATFORM).width
HEIGHT = Canvas.for_platform(PLATFORM).height
CONTENT_X = 96
# Reels hangs its action rail down the right edge of the lower two thirds, so
# the column stops short of it: a text block is measured by the width it was
# given, not by its ink, and a full-width one would reach under the rail.
RAIL_X = 920
CONTENT_WIDTH = RAIL_X - CONTENT_X

# Vertical video is watched at phone scale, where anything under 2.5% of the
# frame height is unreadable; 48px is that floor on a 1920-tall canvas. The
# supporting scale therefore separates by weight, colour and tracking, and only
# the values a scene is actually about grow past it.
LABEL_SIZE = 48
BODY_SIZE = 54
LEAD_SIZE = 64
DATA_SIZE = 76
TITLE_SIZE = 108
DISPLAY_SIZE = 250

BEAT = 60.0 / 128.0
SCENE_BEATS = (10, 10, 10, 8, 10, 9, 9, 8)
SCENE_DURATIONS = tuple(beats * BEAT for beats in SCENE_BEATS)
# A scene is nearly five seconds long. Entrances short enough to finish in the
# first second leave the rest of it frozen, and eight frozen scenes in a row
# read as stuttering, so each beat of the choreography is given room to land.
MOTION_FAST = BEAT * 0.85
MOTION_STANDARD = BEAT * 1.25
# Long enough for a number to be read as it moves rather than as a flicker.
COUNT_DURATION = BEAT * 4.5
# One frame at the exporter's default 30fps for animated video.
FRAME = 1 / 30
# `odometer` reserves one fixed-width slot per digit so a growing number cannot
# shift sideways mid-count. Pretendard Black sets a far narrower `1` than that
# slot, so any reading that passes through a 1 is set `plain` instead and the
# mechanical roll is kept for the one readout whose digits all fill their slot.
DIGIT_STYLE = "plain"
# The headline arrives line by line, so it settles a stagger step after its own
# duration. Anything sized against the copy stack has to count that step too.
HEADLINE_IN = MOTION_STANDARD + MOTION_FAST
COPY_SETTLED = MOTION_FAST + HEADLINE_IN + MOTION_FAST

INK = "#080A0E"
SURFACE = "#161B23"
BLUE = "#147CE5"
BLUE_SOFT = "#5EA8FF"
WHITE = "#F5F5F7"
MUTED = "#9A9BA1"
RULE = "#30343C"
# The value a later row supersedes: a step below MUTED so it reads as no longer
# current, but still clear of the contrast floor against the panel it sits on.
SPENT = "#7C838D"
# Rules and dots can sit at RULE, but text at that value falls under the 2.0
# contrast floor, so unreached weeks and days are labelled one step brighter.
DIM = "#6E747D"

# Flat black reads as an absent background rather than a stage. One soft light
# per act gives the graphics somewhere to sit, and its colour carries the arc:
# steel while the film states the problem, blue once PULSE answers it.
COOL_LIGHT = RadialGradient(stops=[("#1B222C", 0.0), (INK, 1.0)], center=(0.26, 0.22))
BLUE_LIGHT = RadialGradient(stops=[("#0F2537", 0.0), (INK, 1.0)], center=(0.5, 0.6))
PROOF_LIGHT = RadialGradient(stops=[("#16324C", 0.0), (INK, 1.0)], center=(0.66, 0.54))
# The closing field is the one place the film goes to colour, and white type
# has to hold on it. A light that climbs above the accent takes the type below
# the contrast floor, so this one deepens outward instead of brightening in.
CTA_LIGHT = RadialGradient(stops=[(BLUE, 0.0), ("#0E68C0", 1.0)], center=(0.28, 0.26))


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
    for scene, transition, voiceover, duration in zip(
        scenes, transitions, VOICEOVERS, SCENE_DURATIONS, strict=True
    ):
        # The transition owns the visual length and ``duration`` owns the
        # narration slot; both are given so a voiceover can never stretch a
        # scene past the beat it was cut to.
        deck = deck.slide(scene, transition=transition, audio=str(voiceover), duration=duration)
    return deck


def build_hook_scene() -> Canvas:
    """Open on a live reading rather than a generic product card."""
    canvas = stage(COOL_LIGHT)
    canvas = add_brand(canvas, color=WHITE)
    canvas = add_copy(
        canvas,
        eyebrow="PERSONAL FITNESS OS",
        headline="TRAINING,\nMADE PERSONAL.",
        body="From heart rate to recovery, see your rhythm at a glance.",
        top=372,
    )
    canvas = canvas.counter(
        96,
        148,
        COUNT_DURATION,
        delay=MOTION_STANDARD,
        style=DIGIT_STYLE,
        position=(CONTENT_X, 900),
        size=DISPLAY_SIZE,
        color=WHITE,
        letter_spacing=-10,
        font=PRETENDARD[900],
    )
    canvas = canvas.text(
        content="BPM  ·  LIVE",
        font=PRETENDARD[800],
        size=LABEL_SIZE,
        color=WHITE,
        letter_spacing=2,
        position=(CONTENT_X + 6, 1190),
        animation=Fade(duration=MOTION_FAST, trigger="after_previous"),
    )
    return add_pulse_trace(
        canvas,
        y=1370,
        color=WHITE,
        height=220,
        start=COPY_SETTLED + MOTION_FAST,
        end=SCENE_DURATIONS[0],
    )


def build_problem_scene() -> Canvas:
    """Let a running playhead outlast the lit days instead of describing it."""
    canvas = stage(COOL_LIGHT)
    canvas = add_copy(
        canvas,
        eyebrow="THE PROBLEM",
        headline="CONSISTENCY\nNEEDS A SYSTEM.",
        body="When feedback arrives late, motivation follows.",
        top=300,
    )
    canvas = add_day_timeline(canvas, y=1060, lit_days=3, duration=SCENE_DURATIONS[1])
    canvas = canvas.text(
        content="FEEDBACK ARRIVES HERE",
        font=PRETENDARD[700],
        size=LABEL_SIZE,
        color=MUTED,
        letter_spacing=3,
        position=(CONTENT_X, 1240),
        animation=Fade(duration=MOTION_FAST, trigger="after_previous"),
    )
    return canvas.text(
        content="TOO LATE",
        font=PRETENDARD[900],
        size=150,
        color=BLUE_SOFT,
        letter_spacing=-4,
        position=(CONTENT_X, 1300),
        animation=Fade(duration=MOTION_STANDARD, trigger="after_previous"),
    )


def build_solution_scene() -> Canvas:
    """Resolve three scattered signals downward into one dominant score."""
    canvas = stage(BLUE_LIGHT)
    canvas = add_copy(
        canvas,
        eyebrow="MEET PULSE",
        headline="FIND YOUR\nDAILY RHYTHM.",
        body="Turn scattered signals into one clear daily score.",
        top=260,
    )
    canvas = add_signal_rows(canvas, start_y=812)
    # The collector rule is where the three readings stop being separate; the
    # score below it is the same information with one number left.
    canvas = canvas.shape(
        shape="rectangle",
        position=(CONTENT_X, 1104),
        width=724,
        height=3,
        color=RULE,
        animation=Wipe(direction="right", duration=MOTION_STANDARD, trigger="after_previous"),
    )
    canvas = canvas.shape(
        shape="ellipse",
        position=(WIDTH // 2, 1324),
        width=560,
        height=560,
        color=BLUE,
        align=("center", "middle"),
        fill=RadialGradient(stops=[(f"{BLUE}59", 0.0), (f"{BLUE}00", 1.0)]),
    )
    # 0 to 84 never passes through a narrow digit, so the score can roll.
    canvas = canvas.counter(
        0,
        84,
        COUNT_DURATION,
        delay=MOTION_STANDARD,
        style="odometer",
        position=(WIDTH // 2, 1170),
        align=("center", "top"),
        size=290,
        color=WHITE,
        letter_spacing=-12,
        font=PRETENDARD[900],
    )
    return canvas.text(
        content="RECOVERY / 100",
        font=PRETENDARD[800],
        size=LABEL_SIZE,
        color=BLUE_SOFT,
        letter_spacing=3,
        position=(WIDTH // 2, 1474),
        align=("center", "top"),
        animation=Fade(duration=MOTION_FAST, trigger="after_previous"),
    )


def build_live_sync_scene() -> Canvas:
    """Lead with the instrument, then name what it is reading."""
    canvas = stage(BLUE_LIGHT)
    canvas = add_copy(
        canvas,
        eyebrow="01 · LIVE SYNC",
        headline="NEVER MISS\nA BEAT.",
        body="Track heart-rate zones and workout intensity live.",
        top=260,
    )
    canvas = canvas.counter(
        118,
        142,
        COUNT_DURATION,
        delay=MOTION_FAST,
        style=DIGIT_STYLE,
        position=(CONTENT_X, 1080),
        size=DISPLAY_SIZE,
        color=WHITE,
        letter_spacing=-10,
        font=PRETENDARD[900],
    )
    # The hook put the number first and the trace under it; here the trace
    # arrives first, so the two heart-rate scenes never read as one layout.
    canvas = add_pulse_trace(
        canvas,
        y=900,
        color=BLUE,
        height=260,
        start=COPY_SETTLED,
        end=SCENE_DURATIONS[3],
    )
    # This is the shortest scene, and the trace holds the rest of it. The two
    # labels therefore arrive alongside it on their own delays: chained behind
    # a scene-long animation they would never get their turn.
    canvas = canvas.text(
        content="BPM   ZONE 3",
        font=PRETENDARD[800],
        size=LABEL_SIZE,
        color=BLUE_SOFT,
        letter_spacing=2,
        position=(CONTENT_X + 6, 1372),
        animation=Fade(duration=MOTION_FAST, delay=MOTION_FAST, trigger="with_previous"),
    )
    return canvas.text(
        content="LIVE  /  SYNCED",
        font=PRETENDARD[700],
        size=LABEL_SIZE,
        color=MUTED,
        letter_spacing=2,
        position=(CONTENT_X, 1500),
        animation=Fade(duration=MOTION_FAST, delay=MOTION_FAST * 2, trigger="with_previous"),
    )


def build_ai_coach_scene() -> Canvas:
    """Show the plan adapting as a length that shrinks, not as a struck-out line."""
    canvas = stage(BLUE_LIGHT)
    canvas = add_copy(
        canvas,
        eyebrow="02 · ADAPTIVE COACH",
        headline="AI SETS\nTODAY'S PACE.",
        body="Adapt duration and intensity to your recovery.",
        top=260,
    )
    panel_x, panel_y, panel_width, panel_height = CONTENT_X, 840, 824, 560
    inset = 56
    canvas = canvas.shape(
        shape="rectangle",
        position=(panel_x, panel_y),
        width=panel_width,
        height=panel_height,
        color=SURFACE,
        animation=Fade(duration=MOTION_STANDARD, trigger="after_previous"),
    )
    # The accent caps the panel rather than sitting inside it, so the two never
    # read as one shape stacked on another.
    canvas = canvas.shape(
        shape="rectangle",
        position=(panel_x, panel_y - 4),
        width=panel_width,
        height=4,
        color=BLUE,
    )
    # Both bars are drawn at the same 20px per minute, so the plan shortening
    # from 32 to 24 minutes is a length the viewer can compare, not a claim.
    minute = 20
    canvas = canvas.text(
        content="PLANNED",
        font=PRETENDARD[700],
        size=LABEL_SIZE,
        color=MUTED,
        letter_spacing=3,
        position=(panel_x + inset, panel_y + 50),
    )
    canvas = canvas.text(
        content="32 MIN  ·  HIGH",
        font=PRETENDARD[800],
        size=DATA_SIZE,
        color=SPENT,
        position=(panel_x + inset, panel_y + 106),
    )
    canvas = canvas.shape(
        shape="rectangle",
        position=(panel_x + inset, panel_y + 200),
        width=32 * minute,
        height=14,
        color=RULE,
        animation=AnimationSpec.bar_grow(duration=MOTION_FAST, trigger="after_previous"),
    )
    canvas = canvas.text(
        content="TODAY",
        font=PRETENDARD[700],
        size=LABEL_SIZE,
        color=BLUE_SOFT,
        letter_spacing=3,
        position=(panel_x + inset, panel_y + 290),
    )
    canvas = canvas.text(
        content="↓  RECOVERY 84",
        font=PRETENDARD[800],
        size=LABEL_SIZE,
        color=BLUE_SOFT,
        position=(panel_x + panel_width - inset, panel_y + 290),
        align=("right", "top"),
        animation=Fade(duration=MOTION_FAST, trigger="after_previous"),
    )
    # 32 to 24 is the one readout whose digits all fill an odometer slot, so it
    # is the one that rolls — and it rolls down, in step with the bar below it.
    canvas = canvas.counter(
        32,
        24,
        COUNT_DURATION,
        delay=MOTION_STANDARD,
        style="odometer",
        suffix=" MIN",
        position=(panel_x + inset, panel_y + 346),
        size=100,
        color=WHITE,
        letter_spacing=-3,
        font=PRETENDARD[900],
    )
    canvas = canvas.shape(
        shape="rectangle",
        position=(panel_x + inset, panel_y + 470),
        width=24 * minute,
        height=14,
        color=BLUE,
        animation=AnimationSpec.bar_grow(
            duration=COUNT_DURATION, delay=MOTION_STANDARD, trigger="with_previous"
        ),
    )
    return canvas.text(
        content="MODERATE  ·  AUTO-ADJUSTED",
        font=PRETENDARD[800],
        size=LABEL_SIZE,
        color=MUTED,
        letter_spacing=2,
        position=(CONTENT_X, 1460),
        animation=Fade(duration=MOTION_FAST, trigger="after_previous"),
    )


def build_streak_scene() -> Canvas:
    """Make twenty-one accumulated days the visual proof of habit."""
    canvas = stage(BLUE_LIGHT)
    canvas = add_copy(
        canvas,
        eyebrow="03 · SMART STREAK",
        headline="TURN THREE DAYS\nINTO TWENTY-ONE.",
        body="Link small wins into a habit that lasts.",
        top=260,
        headline_size=92,
    )
    canvas = canvas.counter(
        3,
        21,
        COUNT_DURATION,
        delay=MOTION_STANDARD,
        style=DIGIT_STYLE,
        position=(CONTENT_X, 740),
        size=300,
        color=WHITE,
        letter_spacing=-14,
        font=PRETENDARD[900],
    )
    canvas = canvas.text(
        content="DAY STREAK",
        font=PRETENDARD[800],
        size=LABEL_SIZE,
        color=BLUE_SOFT,
        letter_spacing=3,
        position=(CONTENT_X + 8, 1084),
        animation=Fade(duration=MOTION_FAST, trigger="after_previous"),
    )
    return add_streak_grid(canvas, start_y=1170)


def build_social_proof_scene() -> Canvas:
    """Use eight weeks of measured distance as proof instead of a testimonial card."""
    canvas = stage(PROOF_LIGHT)
    canvas = add_copy(
        canvas,
        eyebrow="PROOF · WEEK 8",
        headline="GO LONGER.\nGO FARTHER.",
        body="Progress built with PULSE shows up in the numbers.",
        top=280,
    )
    # The chart carries the claim, so the callout only names its final column
    # instead of restating the distance as a fourth oversized number.
    canvas = canvas.text(
        content="DISTANCE",
        font=PRETENDARD[700],
        size=LABEL_SIZE,
        color=MUTED,
        letter_spacing=3,
        position=(CONTENT_X, 856),
        animation=Fade(duration=MOTION_FAST, trigger="after_previous"),
    )
    canvas = canvas.text(
        content="FIRST 5K  ·  +32%",
        font=PRETENDARD[800],
        size=LABEL_SIZE,
        color=BLUE_SOFT,
        letter_spacing=2,
        position=(RAIL_X - 30, 856),
        align=("right", "top"),
        animation=Fade(duration=MOTION_FAST, trigger="with_previous"),
    )
    canvas = add_week_chart(canvas, baseline=1260, peak=340)
    canvas = canvas.text(
        content="EIGHT WEEKS.\nFIRST 5K.",
        font=PRETENDARD[800],
        size=LEAD_SIZE,
        color=WHITE,
        line_height=1.1,
        position=(CONTENT_X, 1368),
        animation=Wipe(direction="up", duration=MOTION_STANDARD, trigger="after_previous"),
    )
    return canvas.text(
        content="ILLUSTRATIVE PROGRAM DATA",
        font=PRETENDARD[700],
        size=LABEL_SIZE,
        color=MUTED,
        letter_spacing=2,
        position=(CONTENT_X, 1530),
        animation=Fade(duration=MOTION_FAST, trigger="after_previous"),
    )


def build_cta_scene() -> Canvas:
    """Close with one action on a clean product-blue field."""
    canvas = Canvas.for_platform(PLATFORM).background(color=BLUE, gradient=CTA_LIGHT)
    canvas = add_brand(canvas, color=WHITE)
    canvas = canvas.text(
        content="TIME TO\nMOVE.",
        font=PRETENDARD[900],
        size=160,
        color=INK,
        line_height=0.98,
        letter_spacing=-6,
        position=(CONTENT_X, 520),
        animation=Fade(duration=MOTION_STANDARD, trigger="after_previous"),
    )
    canvas = canvas.text(
        content="The fastest way to understand your body.",
        font=PRETENDARD[500],
        size=BODY_SIZE,
        color=WHITE,
        line_height=1.3,
        position=(CONTENT_X, 920),
        max_width=CONTENT_WIDTH,
        animation=Fade(duration=MOTION_FAST, trigger="after_previous"),
    )
    canvas = canvas.text(
        content="START FREE  →",
        font=PRETENDARD[900],
        size=84,
        color=WHITE,
        position=(CONTENT_X, 1180),
        animation=Wipe(direction="right", duration=MOTION_STANDARD, trigger="after_previous"),
    )
    canvas = canvas.shape(
        shape="rectangle",
        position=(CONTENT_X, 1294),
        width=560,
        height=5,
        color=WHITE,
        animation=Wipe(direction="right", duration=MOTION_FAST, trigger="after_previous"),
    )
    canvas = canvas.text(
        content="7 DAYS FREE  ·  CANCEL ANYTIME",
        font=PRETENDARD[700],
        size=LABEL_SIZE,
        color=WHITE,
        letter_spacing=1,
        position=(CONTENT_X, 1370),
        animation=Fade(duration=MOTION_FAST, trigger="after_previous"),
    )
    return canvas.text(
        content="PULSE.APP",
        font=PRETENDARD[900],
        size=54,
        color=WHITE,
        letter_spacing=3,
        position=(CONTENT_X, 1500),
        animation=Fade(duration=MOTION_FAST, trigger="after_previous"),
    )


def stage(light: RadialGradient) -> Canvas:
    """Create a restrained dark stage lit by one soft source."""
    return Canvas.for_platform(PLATFORM).background(color=INK, gradient=light)


def add_brand(canvas: Canvas, *, color: str) -> Canvas:
    """Add the wordmark only where it anchors the story."""
    return canvas.text(
        content="PULSE",
        font=BRAND_FONT,
        size=LABEL_SIZE,
        color=color,
        letter_spacing=7,
        position=(CONTENT_X, 250),
    )


def add_copy(
    canvas: Canvas,
    *,
    eyebrow: str,
    headline: str,
    body: str,
    top: int,
    headline_size: int = TITLE_SIZE,
    body_width: int = CONTENT_WIDTH,
) -> Canvas:
    """Build one concise narrative stack for the current scene.

    The body sits under the headline it actually has, so a shorter title never
    leaves a dead band above the copy that follows it.
    """
    headline_height = round(len(headline.split("\n")) * headline_size * 1.02)
    canvas = canvas.text(
        content=eyebrow,
        font=PRETENDARD[800],
        size=LABEL_SIZE,
        color=BLUE_SOFT,
        letter_spacing=3,
        position=(CONTENT_X, top),
        # The default trigger is on_click, which leaves the HTML slideshow
        # waiting for a click before a scene starts and the whole chain with
        # it. A scene begins when it arrives.
        animation=Wipe(direction="right", duration=MOTION_FAST, trigger="after_previous"),
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
        max_height=headline_height,
        auto_scale=True,
        min_size=78,
        animation=AnimationSpec.rise(
            from_="bottom",
            distance=24,
            duration=MOTION_STANDARD,
            trigger="after_previous",
            stagger=MOTION_FAST,
            target="lines",
            easing="ease_out_cubic",
        ),
    )
    return canvas.text(
        content=body,
        font=PRETENDARD[500],
        size=BODY_SIZE,
        color=MUTED,
        line_height=1.3,
        position=(CONTENT_X, top + 78 + headline_height + 44),
        max_width=body_width,
        max_height=150,
        auto_scale=True,
        min_size=BODY_SIZE,
        animation=Fade(duration=MOTION_FAST, trigger="after_previous"),
    )


def add_pulse_trace(
    canvas: Canvas, *, y: int, color: str, height: int, start: float, end: float
) -> Canvas:
    """Draw a heart-rate trace that arrives left to right and then keeps reading."""
    amplitudes = (
        0.18, 0.30, 0.52, 1.00, 0.44, 0.24, 0.34, 0.74,
        0.30, 0.17, 0.46, 0.82, 0.38, 0.20, 0.29, 0.62,
    )  # fmt: skip
    bar_width, pitch = 14, 54
    for index, amplitude in enumerate(amplitudes):
        bar_height = round(height * amplitude)
        canvas = canvas.shape(
            shape="pill",
            position=(CONTENT_X + index * pitch, y - bar_height // 2),
            width=bar_width,
            height=bar_height,
            color=color,
            opacity=1.0 if amplitude > 0.7 else 0.55,
            animation=_live_bar(end - start, order=index),
        )
    return canvas


def _live_bar(window: float, *, order: int) -> AnimationSpec:
    """Grow one trace bar in on its own beat, then keep it reading for the scene.

    Arrival and life are one curve rather than an entrance effect plus a second
    animation: a unit in animated export carries either legacy effects or one
    canonical timeline, so a layer that needs both has to say both here. The
    wave only ever shortens a bar, because swinging above its drawn height would
    push the tallest ones into the label above them.
    """
    # A stagger shorter than one frame collapses: two bars land on the same
    # frame and the sweep pops in clumps instead of travelling. The whole
    # arrival is then held inside the window, so a short scene compresses the
    # sweep rather than scheduling a curve that runs past its own end.
    reveal = min(MOTION_FAST, window * 0.25)
    arrive = min(order * FRAME * 2, max(0.0, window * 0.5 - reveal))
    settled = arrive + reveal
    low, high = 0.58, 1.0
    middle, swing = (high + low) / 2, (high - low) / 2
    cycles, steps = 5, 40
    phase = order / 5.0
    keyframes = [KeyframeSpec(time=0.0, value=0.0)]
    if arrive > 0:
        keyframes.append(KeyframeSpec(time=arrive, value=0.0))
    keyframes.append(KeyframeSpec(time=settled, value=1.0))
    for step in range(1, steps + 1):
        time = settled + (window - settled) * step / steps
        progress = (time - settled) / (window - settled)
        keyframes.append(
            KeyframeSpec(
                time=time,
                value=middle + swing * math.sin(2 * math.pi * (cycles * progress + phase)),
            )
        )
    return AnimationSpec.timeline(
        ScaleTrack(keyframes=keyframes),
        # Relative timing, not an absolute start: the HTML runtime schedules a
        # slide as a chain of groups, so a bar that names its own place on the
        # slide clock lands at that offset *after* the group it joins. Every bar
        # follows the copy as one group and carries its own arrival in the
        # curve above.
        timing=TimingSpec(
            trigger="after_previous" if order == 0 else "with_previous", duration=window
        ),
        easing="linear",
    )


def add_day_timeline(canvas: Canvas, *, y: int, lit_days: int, duration: float) -> Canvas:
    """Draw six days, light the first few, and run a playhead past all of them."""
    days, pitch = 6, 130
    track_width = pitch * days
    canvas = canvas.text(
        content="DAY",
        font=PRETENDARD[700],
        size=LABEL_SIZE,
        color=MUTED,
        letter_spacing=3,
        position=(CONTENT_X, y - 80),
        animation=Fade(duration=MOTION_FAST, trigger="after_previous"),
    )
    canvas = canvas.shape(
        shape="rectangle",
        position=(CONTENT_X, y),
        width=track_width,
        height=4,
        color=RULE,
    )
    canvas = canvas.shape(
        shape="rectangle",
        position=(CONTENT_X, y),
        width=pitch * lit_days,
        height=4,
        color=BLUE,
        animation=AnimationSpec.bar_grow(duration=MOTION_STANDARD, trigger="after_previous"),
    )
    for index in range(days):
        lit = index < lit_days
        # A day is a span rather than an instant, so its marker sits in the
        # middle of its own segment; that also keeps the first and last numerals
        # clear of the safe-area margins the track itself runs up to.
        x = CONTENT_X + round((index + 0.5) * pitch)
        canvas = canvas.shape(
            shape="ellipse",
            position=(x, y + 2),
            width=26 if lit else 16,
            height=26 if lit else 16,
            color=BLUE if lit else RULE,
            align=("center", "middle"),
            animation=Fade(duration=MOTION_FAST, delay=index * FRAME * 2, trigger="with_previous"),
        )
        # Numerals sit centred on their own dot, so the row can never drift out
        # of alignment the way a single hand-spaced caption string does.
        canvas = canvas.text(
            content=f"{index + 1:02d}",
            font=PRETENDARD[700],
            size=LABEL_SIZE,
            color=WHITE if lit else DIM,
            position=(x, y + 46),
            align=("center", "top"),
        )
    # The playhead crosses every day at the scene's own rate: the lit stretch
    # ends at day three and time keeps going, which is the scene's whole point.
    return canvas.shape(
        shape="rectangle",
        position=(CONTENT_X, y - 32),
        width=8,
        height=70,
        color=WHITE,
        animation=AnimationSpec.timeline(
            PositionTrack(
                keyframes=[
                    KeyframeSpec(time=0.0, value=(0.0, 0.0)),
                    KeyframeSpec(time=duration, value=(float(track_width), 0.0)),
                ]
            ),
            timing=TimingSpec(start=0.0, duration=duration),
            easing="linear",
        ),
    )


def add_signal_rows(canvas: Canvas, *, start_y: int) -> Canvas:
    """Show the three inputs that resolve into the recovery score."""
    rows = (("SLEEP", "92", 0.92), ("ENERGY", "81", 0.81), ("STRESS", "24", 0.24))
    bar_x, bar_width = 400, 420
    for index, (label, value, ratio) in enumerate(rows):
        y = start_y + index * 92
        canvas = canvas.text(
            content=label,
            font=PRETENDARD[700],
            size=LABEL_SIZE,
            color=MUTED,
            letter_spacing=2,
            position=(CONTENT_X, y),
            animation=Fade(
                duration=MOTION_FAST,
                delay=index * 0.08,
                trigger="with_previous" if index else "after_previous",
            ),
        )
        canvas = canvas.text(
            content=value,
            font=PRETENDARD[800],
            size=LABEL_SIZE,
            color=WHITE,
            position=(bar_x - 32, y),
            align=("right", "top"),
        )
        canvas = canvas.shape(
            shape="rectangle",
            position=(bar_x, y + 22),
            width=round(bar_width * ratio),
            height=10,
            color=BLUE,
            animation=AnimationSpec.bar_grow(
                duration=MOTION_STANDARD, delay=index * 0.08, trigger="with_previous"
            ),
        )
    return canvas


def add_streak_grid(canvas: Canvas, *, start_y: int) -> Canvas:
    """Render twenty-one completed days as one accumulated field."""
    columns, pitch, row_pitch, dot = 7, 118, 128, 48
    for index in range(21):
        row, column = divmod(index, columns)
        canvas = canvas.shape(
            shape="ellipse",
            position=(CONTENT_X + column * pitch, start_y + row * row_pitch),
            width=dot,
            height=dot,
            color=WHITE if index == 20 else BLUE,
            opacity=0.55 + index * 0.02,
            animation=Fade(
                duration=MOTION_FAST,
                delay=index * FRAME * 1.6,
                trigger="with_previous" if index else "after_previous",
            ),
        )
    return canvas


def add_week_chart(canvas: Canvas, *, baseline: int, peak: int) -> Canvas:
    """Chart eight weeks of distance so the outcome is shown, not asserted."""
    ratios = (0.25, 0.33, 0.42, 0.52, 0.63, 0.75, 0.87, 1.0)
    bar_width, pitch = 66, 104
    for index, ratio in enumerate(ratios):
        final = index == len(ratios) - 1
        height = round(peak * ratio)
        x = CONTENT_X + index * pitch
        canvas = canvas.shape(
            shape="rectangle",
            position=(x, baseline - height),
            width=bar_width,
            height=height,
            color=WHITE if final else BLUE,
            opacity=1.0 if final else 0.4 + ratio * 0.5,
            # clip_progress reveals left to right, so a rising bar needs the
            # directional wipe rather than the bar_grow preset.
            animation=Wipe(
                direction="up",
                duration=MOTION_STANDARD,
                delay=index * 0.07,
                trigger="with_previous" if index else "after_previous",
            ),
        )
        canvas = canvas.text(
            content=f"W{index + 1}",
            font=PRETENDARD[700],
            size=LABEL_SIZE,
            color=WHITE if final else DIM,
            position=(x + bar_width // 2, baseline + 20),
            align=("center", "top"),
        )
    return canvas.shape(
        shape="rectangle",
        position=(CONTENT_X, baseline),
        width=pitch * (len(ratios) - 1) + bar_width,
        height=3,
        color=RULE,
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
        print(f"✓ diagnose(): all {len(deck)} scenes pass layout and legibility checks")


def export_reel(deck: Deck) -> None:
    """Export every format with narration and a quiet looping soundtrack."""
    deck.render(
        str(OUT_GIF),
        animation=GifOptions(fps=8, max_size=(432, 768), colors=64),
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
