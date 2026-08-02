"""ORDINARY MOMENTS — a 60-second product film about composing once.

The film argues one thing: making the same video again for every screen is the
expensive part, and a composition you write once removes it. Nine scenes carry
that argument — hook, cost, turn, three proofs, the delivery payoff, and a
close — and every visual device on screen is one of QuickThumb's primitives
doing the job it is being talked about.

Run from the repository root with::

    uv run python examples/ordinary_moments.py

FFmpeg is required for the MP4, WebM, and GIF outputs.
"""

from pathlib import Path

from quickthumb import (
    AnimationSpec,
    AudioTrack,
    BackdropBlur,
    Background,
    Canvas,
    Deck,
    Fade,
    KeyframeSpec,
    LinearGradient,
    PositionTrack,
    Shadow,
    TimingSpec,
    Wipe,
)
from quickthumb import transitions as tr

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
VIDEO_DIR = ASSETS / "video"
SOUNDTRACK = ASSETS / "audio" / "ordinary_moments_vastness.mp3"

OUT_DIR = ROOT / "examples"
OUT_MP4 = OUT_DIR / "ordinary_moments.mp4"
OUT_WEBM = OUT_DIR / "ordinary_moments.webm"
OUT_GIF = OUT_DIR / "ordinary_moments_preview.gif"

# Korean copy is set in Pretendard; every functional readout is set in Roboto so
# on-screen product data never competes with the film's voice.
KR = str(ASSETS / "fonts" / "Pretendard-Regular.woff2")
KR_BOLD = str(ASSETS / "fonts" / "Pretendard-Bold.woff2")
KR_HEAVY = str(ASSETS / "fonts" / "Pretendard-ExtraBold.woff2")
UI = str(ASSETS / "fonts" / "Roboto-Medium.ttf")

WIDTH, HEIGHT = 1280, 720
FPS = 24
MARGIN = 80

# Amber is the "composed once" colour. Act one is deliberately colourless: the
# accent is introduced at the turn and grows until the delivery scene.
INK = "#0A0E12"
SURFACE = "#141B22"
CREAM = "#F2EFE9"
MUTE = "#8A949C"
ACCENT = "#E8A552"

DISPLAY_SIZE = 66
HEADLINE_SIZE = 46
BODY_SIZE = 20
LABEL_SIZE = 13
DATA_SIZE = 22

# Scene lengths carry the pacing: act one breathes, the proofs move, the payoff
# is held the longest, and the close settles under the soundtrack fade.
HOOK_DURATION = 7.0
COST_DURATION = 6.1
TURN_DURATION = 7.0
FIT_DURATION = 6.0
CUE_DURATION = 6.8
TIME_DURATION = 6.7
DELIVER_DURATION = 7.9
RESOLVE_DURATION = 6.6
CLOSE_DURATION = 5.9
FILM_DURATION = 60.0
GIF_PREVIEW_DURATION = 4.0

# Real values, printed on screen by the scenes that set them. The speed readout
# is derived from the trim it labels, so the two cannot drift apart.
TIME_TRIM = (0.2, 5.0)
TIME_SPEED = (TIME_TRIM[1] - TIME_TRIM[0]) / TIME_DURATION
SOUNDTRACK_VOLUME = 0.16
SOUNDTRACK_FADE_OUT = 1.4
FIRST_CUE = (0.9, 3.3)
SECOND_CUE = (3.5, 6.4)


def main() -> None:
    """Diagnose the film, then export every delivery format from one deck."""
    deck = build_deck()
    errors = [finding for finding in deck.diagnose() if finding.severity == "error"]
    if errors:
        raise RuntimeError(f"ordinary_moments has diagnostics: {errors}")

    soundtrack = AudioTrack(
        path=str(SOUNDTRACK),
        volume=SOUNDTRACK_VOLUME,
        loop=True,
        fade_out=SOUNDTRACK_FADE_OUT,
    )
    OUT_MP4.write_bytes(deck.to_animated_mp4(fps=FPS, soundtrack=soundtrack))
    OUT_WEBM.write_bytes(deck.to_webm(fps=FPS, soundtrack=soundtrack))
    # The payoff scene carries its own timeline, so the preview needs no settled
    # hold — just a shorter cut of the same composition.
    OUT_GIF.write_bytes(build_deliver_scene(duration=GIF_PREVIEW_DURATION).to_gif(fps=10, hold=0))
    print(f"Wrote {OUT_MP4}")
    print(f"Wrote {OUT_WEBM}")
    print(f"Wrote {OUT_GIF}")


def build_deck() -> Deck:
    """Assemble the nine scenes into one 60-second timeline."""
    # A transition holds its slide for ``advance_after`` and then plays for
    # ``duration``, so each pair below is one scene's full screen time. The cut
    # into the turn and the wipe into the payoff are the film's two gear changes.
    plan = (
        (build_hook_scene(), tr.Fade(duration=0.4, advance_after=HOOK_DURATION - 0.4)),
        (build_cost_scene(), tr.Cut(advance_after=COST_DURATION)),
        (
            build_turn_scene(),
            tr.Wipe(direction="left", duration=0.5, advance_after=TURN_DURATION - 0.5),
        ),
        (build_fit_scene(), tr.Cut(advance_after=FIT_DURATION)),
        (build_cue_scene(), tr.Fade(duration=0.4, advance_after=CUE_DURATION - 0.4)),
        (
            build_time_scene(),
            tr.Wipe(direction="up", duration=0.5, advance_after=TIME_DURATION - 0.5),
        ),
        (build_deliver_scene(), tr.Fade(duration=0.5, advance_after=DELIVER_DURATION - 0.5)),
        (build_resolve_scene(), tr.Fade(duration=0.6, advance_after=RESOLVE_DURATION - 0.6)),
        (build_close_scene(), tr.Fade(duration=0.6, advance_after=CLOSE_DURATION - 0.6)),
    )
    deck = Deck(WIDTH, HEIGHT)
    for canvas, transition in plan:
        deck = deck.slide(canvas, transition=transition)
    return deck


def build_hook_scene() -> Canvas:
    """Open on the question the whole film answers, over an unhurried city."""
    canvas = _full_bleed(Canvas(WIDTH, HEIGHT), "ordinary-city.mp4", HOOK_DURATION, 0.0, 5.0)
    _scrim(canvas, edge="bottom", boundary=410, fade=230, peak=0.8)
    return (
        canvas.text(
            content="같은 영상을\n몇 번이나 다시 만드나요?",
            font=KR_HEAVY,
            size=DISPLAY_SIZE,
            color=CREAM,
            line_height=1.1,
            position=(MARGIN, 434),
            max_width=WIDTH - MARGIN * 2,
            auto_scale=True,
            min_size=48,
            effects=[Shadow(offset_x=0, offset_y=2, color="#000000", blur_radius=28)],
            animation=Wipe(direction="up", duration=0.7),
        )
        .shape(
            shape="rectangle",
            position=(MARGIN, 606),
            width=104,
            height=3,
            color=MUTE,
            animation=Wipe(direction="right", duration=0.4, trigger="after_previous", delay=0.5),
        )
        .text(
            content="가로 하나. 세로 하나. 미리보기 하나.",
            font=KR,
            size=BODY_SIZE,
            color=CREAM,
            opacity=0.82,
            position=(MARGIN, 634),
            animation=Fade(duration=0.5, trigger="after_previous"),
        )
    )


def build_cost_scene() -> Canvas:
    """Name the cost: one idea, remade three times, counted on screen."""
    canvas = _full_bleed(Canvas(WIDTH, HEIGHT), "ordinary-notebook.mp4", COST_DURATION, 0.5, 6.6)
    column_x = 624
    text_x = column_x + 64
    return (
        canvas.shape(
            shape="rectangle",
            position=(column_x, 0),
            width=WIDTH - column_x,
            height=HEIGHT,
            color=INK,
            opacity=0.88,
        )
        .shape(shape="rectangle", position=(column_x, 0), width=2, height=HEIGHT, color=MUTE)
        .text(
            content="가로로 한 번.",
            font=KR_BOLD,
            size=38,
            color=CREAM,
            position=(text_x, 152),
            max_width=WIDTH - text_x - MARGIN,
            auto_scale=True,
            min_size=28,
            animation=Wipe(direction="up", duration=0.4),
        )
        # One line per remake, each arriving on its own beat: the repetition is
        # the argument, so the sequence has to carry it.
        .text(
            content="세로로 한 번.",
            font=KR_BOLD,
            size=38,
            color=CREAM,
            position=(text_x, 209),
            max_width=WIDTH - text_x - MARGIN,
            auto_scale=True,
            min_size=28,
            animation=Wipe(direction="up", duration=0.4, trigger="after_previous"),
        )
        .text(
            content="미리보기로 또 한 번.",
            font=KR_BOLD,
            size=38,
            color=CREAM,
            position=(text_x, 266),
            max_width=WIDTH - text_x - MARGIN,
            auto_scale=True,
            min_size=28,
            animation=Wipe(direction="up", duration=0.4, trigger="after_previous"),
        )
        .counter(
            1,
            3,
            1.2,
            delay=0.7,
            position=(text_x, 404),
            size=104,
            color=MUTE,
            suffix="배",
            font=KR_HEAVY,
            style="odometer",
        )
        .text(
            content="아이디어는 하나인데,\n시간은 세 배로 듭니다.",
            font=KR,
            size=BODY_SIZE,
            color=MUTE,
            line_height=1.5,
            position=(text_x, 556),
            max_width=WIDTH - text_x - MARGIN,
            auto_scale=True,
            min_size=16,
            animation=Fade(duration=0.5, trigger="after_previous", delay=0.3),
        )
    )


def build_turn_scene() -> Canvas:
    """The pivot: one sentence, the brand, and the first amber on screen."""
    canvas = _full_bleed(Canvas(WIDTH, HEIGHT), "ordinary-coffee.mp4", TURN_DURATION, 0.25, 7.25)
    canvas.shape(
        shape="rectangle", position=(0, 0), width=WIDTH, height=HEIGHT, color=INK, opacity=0.28
    )
    _scrim(canvas, edge="bottom", boundary=400, fade=220, peak=0.82)
    return (
        canvas.text(
            content="QUICKTHUMB",
            font=UI,
            size=14,
            color=ACCENT,
            letter_spacing=4,
            position=(MARGIN, 424),
            animation=Fade(duration=0.5),
        )
        # The rule sweeps the frame once, left to right, before the line lands.
        .shape(
            shape="rectangle",
            position=(MARGIN, 464),
            width=WIDTH - MARGIN * 2,
            height=3,
            color=ACCENT,
            animation=Wipe(direction="right", duration=0.75, trigger="after_previous"),
        )
        .text(
            content="구성은 한 번이면 됩니다.",
            font=KR_HEAVY,
            size=DISPLAY_SIZE,
            color=CREAM,
            position=(MARGIN, 502),
            max_width=WIDTH - MARGIN * 2,
            auto_scale=True,
            min_size=48,
            effects=[Shadow(offset_x=0, offset_y=2, color="#000000", blur_radius=28)],
            animation=Wipe(direction="up", duration=0.6, trigger="after_previous"),
        )
        .text(
            content="화면도, 자막도, 소리도 같은 타임라인 위에 남습니다.",
            font=KR,
            size=BODY_SIZE,
            color=CREAM,
            opacity=0.86,
            position=(MARGIN, 612),
            max_width=760,
            auto_scale=True,
            min_size=16,
            animation=Fade(duration=0.5, trigger="after_previous", delay=0.2),
        )
    )


def build_fit_scene() -> Canvas:
    """Proof one: the same second of footage, live in three frame shapes."""
    canvas = Canvas(WIDTH, HEIGHT).background(color=INK)
    canvas = _copy_block(
        canvas,
        label="FIT & PLACE",
        headline="화면이 달라져도\n의도는 그대로.",
        body="한 소스의 같은 구간을 세 화면이 그대로 나눠 씁니다. 자르는 방식만 화면을 따릅니다.",
        top=88,
        width=560,
    )
    # The readout names the single clip and window every frame below is cut
    # from, so "same moment" is stated as fact rather than asserted in copy.
    source_name, trim_start, trim_end = "ordinary-phone.mp4", 1.0, 7.0
    canvas.text(
        content="ONE SOURCE",
        font=UI,
        size=LABEL_SIZE,
        color=MUTE,
        letter_spacing=2,
        position=(WIDTH - MARGIN, 88),
        align=("right", "top"),
    )
    canvas.text(
        content=source_name,
        font=UI,
        size=18,
        color=CREAM,
        position=(WIDTH - MARGIN, 114),
        align=("right", "top"),
    )
    canvas.text(
        content=f"TRIM {_timestamp(trim_start)} – {_timestamp(trim_end)}",
        font=UI,
        size=14,
        color=MUTE,
        letter_spacing=1,
        position=(WIDTH - MARGIN, 146),
        align=("right", "top"),
    )
    # Three live crops of one source, sharing a baseline so only the frame
    # shape — never the moment inside it — changes across the row.
    frame_top, frame_height, gap = 348, 232, 172
    x = MARGIN
    for label, frame_width in (("16:9", 412), ("1:1", 232), ("9:16", 131)):
        canvas.shape(
            shape="rectangle",
            position=(x, frame_top - 16),
            width=frame_width,
            height=3,
            color=ACCENT,
            animation=Wipe(direction="right", duration=0.4, trigger="after_previous"),
        )
        _clip(
            canvas,
            source_name,
            FIT_DURATION,
            trim_start,
            trim_end,
            (x, frame_top),
            frame_width,
            frame_height,
            border_radius=4,
        )
        canvas.text(
            content=label,
            font=UI,
            size=16,
            color=CREAM,
            letter_spacing=1,
            position=(x, frame_top + frame_height + 22),
        )
        canvas.text(
            content="cover",
            font=UI,
            size=LABEL_SIZE,
            color=MUTE,
            letter_spacing=2,
            position=(x, frame_top + frame_height + 48),
        )
        x += frame_width + gap
    return canvas


def build_cue_scene() -> Canvas:
    """Proof two: two captions that prove their own cue times as they play."""
    canvas = _full_bleed(
        Canvas(WIDTH, HEIGHT),
        "ordinary-notebook.mp4",
        CUE_DURATION,
        1.2,
        8.0,
        captions=[
            _caption("말은 정확한 순간에 나타나고", *FIRST_CUE),
            _caption("정확한 순간에 사라집니다.", *SECOND_CUE),
        ],
    )
    _scrim(canvas, edge="top", boundary=250, fade=180, peak=0.85)
    canvas.text(
        content="자막도 타임라인입니다.",
        font=KR_HEAVY,
        size=HEADLINE_SIZE,
        color=CREAM,
        position=(MARGIN, 88),
        max_width=640,
        auto_scale=True,
        min_size=32,
        animation=Wipe(direction="up", duration=0.55),
    )
    # The strip is the scene's clock. Each block is drawn across at exactly its
    # own cue window, so the bar fills while its caption is on screen and stops
    # the moment the caption leaves.
    track_x, track_y, track_width = MARGIN, 186, 620
    canvas.shape(
        shape="rectangle",
        position=(track_x, track_y),
        width=track_width,
        height=2,
        color=CREAM,
        opacity=0.45,
    )
    for index, (start, end) in enumerate((FIRST_CUE, SECOND_CUE)):
        block_x = track_x + round(track_width * start / CUE_DURATION)
        block_width = round(track_width * (end - start) / CUE_DURATION)
        canvas.shape(
            shape="rectangle",
            position=(block_x, track_y - 6),
            width=block_width,
            height=14,
            color=ACCENT,
            opacity=0.22,
        )
        canvas.shape(
            shape="rectangle",
            position=(block_x, track_y - 6),
            width=block_width,
            height=14,
            color=ACCENT,
            animation=Wipe(
                direction="right",
                duration=end - start,
                start=start,
                easing="linear",
            ),
        )
        canvas.text(
            content=f"CUE {index + 1}   {_timestamp(start)} – {_timestamp(end)}",
            font=UI,
            size=14,
            color=CREAM,
            opacity=0.75,
            letter_spacing=1,
            position=(block_x, track_y + 26),
        )
    return canvas.shape(
        shape="rectangle",
        position=(track_x, track_y - 14),
        width=3,
        height=30,
        color=CREAM,
        animation=_sweep(track_width, CUE_DURATION),
    )


def build_time_scene() -> Canvas:
    """Proof three: speed, volume, and fade are three dials on one timeline."""
    canvas = _full_bleed(Canvas(WIDTH, HEIGHT), "ordinary-city.mp4", TIME_DURATION, *TIME_TRIM)
    _scrim(canvas, edge="bottom", boundary=420, fade=210, peak=0.8)
    panel_x, panel_y, panel_width = 744, 104, 456
    canvas.shape(
        shape="rectangle",
        position=(panel_x, panel_y),
        width=panel_width,
        height=214,
        color=INK,
        opacity=0.62,
        # A frosted panel keeps the reading over live footage instead of hiding
        # it. Backdrop-dependent layers are rasterised with everything beneath
        # them, so this one stays unanimated and the readouts above it move.
        effects=[BackdropBlur(radius=16)],
    )
    canvas.shape(
        shape="rectangle", position=(panel_x, panel_y), width=panel_width, height=3, color=ACCENT
    )
    for index, (label, value) in enumerate(
        (
            ("SPEED", f"{TIME_SPEED:.2f}×"),
            ("VOLUME", f"{SOUNDTRACK_VOLUME:.0%}"),
            ("FADE OUT", f"{SOUNDTRACK_FADE_OUT:.1f}s"),
        )
    ):
        row_y = panel_y + 46 + index * 54
        canvas.text(
            content=label,
            font=UI,
            size=14,
            color=CREAM,
            opacity=0.7,
            letter_spacing=2,
            position=(panel_x + 32, row_y + 7),
        )
        canvas.text(
            content=value,
            font=UI,
            size=DATA_SIZE,
            color=CREAM if index else ACCENT,
            position=(panel_x + panel_width - 32, row_y),
            align=("right", "top"),
        )
    # The scene's own progress bar, riding the bottom edge of the frame and
    # taking exactly as long to fill as the scene takes to play. It anchors the
    # timeline, so the headline runs alongside it rather than after it.
    canvas.shape(
        shape="rectangle", position=(0, 708), width=WIDTH, height=6, color=MUTE, opacity=0.45
    )
    canvas.shape(
        shape="rectangle",
        position=(0, 708),
        width=WIDTH,
        height=6,
        color=ACCENT,
        animation=Wipe(direction="right", duration=TIME_DURATION, easing="linear"),
    )
    canvas.shape(
        shape="rectangle",
        position=(0, 702),
        width=3,
        height=18,
        color=CREAM,
        animation=_sweep(WIDTH - 3, TIME_DURATION),
    )
    return canvas.text(
        content="속도도 소리도\n같은 타임라인 위에.",
        font=KR_HEAVY,
        size=HEADLINE_SIZE + 6,
        color=CREAM,
        line_height=1.12,
        position=(MARGIN, 452),
        max_width=620,
        auto_scale=True,
        min_size=34,
        effects=[Shadow(offset_x=0, offset_y=2, color="#000000", blur_radius=24)],
        animation=Wipe(direction="up", duration=0.6, trigger="with_previous", delay=0.15),
    )


def build_deliver_scene(duration: float = DELIVER_DURATION) -> Canvas:
    """The payoff: one composition leaves as three files, counted to 100%.

    ``duration`` is shortened for the standalone GIF preview, which needs the
    same composition in fewer frames than the film gives it.
    """
    canvas = Canvas(WIDTH, HEIGHT).background(color=INK)
    canvas = _copy_block(
        canvas,
        label="OUTPUT",
        headline="한 번의 구성에서\n세 개의 파일.",
        body="같은 타임라인이 MP4, WebM, GIF로 그대로 나갑니다.",
        top=110,
        width=470,
    )
    canvas.text(
        content="RENDER",
        font=UI,
        size=LABEL_SIZE,
        color=MUTE,
        letter_spacing=2,
        position=(MARGIN, 402),
    )
    canvas.counter(
        0,
        100,
        1.8,
        delay=0.6,
        position=(MARGIN, 428),
        size=88,
        color=ACCENT,
        suffix="%",
        font=UI,
        style="odometer",
    )
    canvas.text(
        content="RUN 01 = RUN 02",
        font=UI,
        size=LABEL_SIZE,
        color=INK,
        letter_spacing=2,
        position=(MARGIN, 556),
        effects=[Background(color=ACCENT, padding=(14, 9), border_radius=2)],
        animation=Fade(duration=0.4, trigger="after_previous", delay=0.4),
    )
    canvas.text(
        content="같은 구성은 언제나 같은 결과를 냅니다.",
        font=KR,
        size=BODY_SIZE - 2,
        color=MUTE,
        position=(MARGIN, 606),
        max_width=470,
        auto_scale=True,
        min_size=14,
        animation=Fade(duration=0.4, trigger="after_previous"),
    )
    frame_x, frame_y, frame_width, frame_height = 640, 108, 560, 315
    canvas.shape(
        shape="rectangle",
        position=(frame_x, frame_y - 14),
        width=frame_width,
        height=3,
        color=ACCENT,
    )
    _clip(
        canvas,
        "ordinary-coffee.mp4",
        duration,
        0.0,
        7.25,
        (frame_x, frame_y),
        frame_width,
        frame_height,
        border_radius=4,
    )
    card_width, card_gap = 170, 25
    for index, (name, role) in enumerate((("MP4", "MASTER"), ("WEBM", "WEB"), ("GIF", "PREVIEW"))):
        card_x = frame_x + index * (card_width + card_gap)
        canvas.shape(
            shape="rectangle",
            position=(card_x, 466),
            width=card_width,
            height=96,
            color=SURFACE,
            animation=Wipe(
                direction="up",
                duration=0.4,
                delay=0.16 * index,
                trigger="with_previous" if index else "after_previous",
            ),
        )
        canvas.text(content=name, font=UI, size=26, color=CREAM, position=(card_x + 22, 492))
        canvas.text(
            content=role,
            font=UI,
            size=11,
            color=ACCENT,
            letter_spacing=2,
            position=(card_x + 22, 528),
        )
    return canvas.text(
        content=f"1280 × 720   ·   {FPS} FPS   ·   {FILM_DURATION:.0f} SEC",
        font=UI,
        size=LABEL_SIZE,
        color=MUTE,
        letter_spacing=2,
        position=(frame_x, 600),
    )


def build_resolve_scene() -> Canvas:
    """Land the argument on the film's last piece of footage."""
    canvas = _full_bleed(Canvas(WIDTH, HEIGHT), "ordinary-sunrise.mp4", RESOLVE_DURATION, 0.7, 7.3)
    _scrim(canvas, edge="bottom", boundary=396, fade=220, peak=0.78)
    return (
        canvas.shape(
            shape="rectangle",
            position=(MARGIN, 424),
            width=96,
            height=3,
            color=ACCENT,
            animation=Wipe(direction="right", duration=0.45),
        )
        .text(
            content="다시 만들지 마세요.",
            font=KR_HEAVY,
            size=DISPLAY_SIZE,
            color=CREAM,
            position=(MARGIN, 462),
            max_width=WIDTH - MARGIN * 2,
            auto_scale=True,
            min_size=46,
            effects=[Shadow(offset_x=0, offset_y=2, color="#000000", blur_radius=28)],
            animation=Wipe(direction="up", duration=0.65, trigger="after_previous"),
        )
        .text(
            content="한 번 구성하세요.",
            font=KR_HEAVY,
            size=DISPLAY_SIZE,
            color=CREAM,
            position=(MARGIN, 535),
            max_width=WIDTH - MARGIN * 2,
            auto_scale=True,
            min_size=46,
            effects=[Shadow(offset_x=0, offset_y=2, color="#000000", blur_radius=28)],
            animation=Wipe(direction="up", duration=0.65, trigger="after_previous"),
        )
    )


def build_close_scene() -> Canvas:
    """Close on the one centred card in the film, so the ending reads as an end."""
    centre = WIDTH // 2
    return (
        Canvas(WIDTH, HEIGHT)
        .background(color=INK)
        .shape(
            shape="rectangle",
            position=(centre - 24, 176),
            width=48,
            height=3,
            color=ACCENT,
            animation=Fade(duration=0.4),
        )
        .text(
            content="QUICKTHUMB",
            font=KR_HEAVY,
            size=44,
            color=CREAM,
            letter_spacing=8,
            position=(centre, 230),
            align=("center", "top"),
            animation=Wipe(direction="up", duration=0.55, trigger="after_previous"),
        )
        .text(
            content="한 번의 구성, 모든 포맷.",
            font=KR,
            size=24,
            color=MUTE,
            position=(centre, 302),
            align=("center", "top"),
            animation=Fade(duration=0.5, trigger="after_previous"),
        )
        .text(
            content="uv add quickthumb",
            font=UI,
            size=26,
            color=INK,
            position=(centre, 396),
            align=("center", "top"),
            effects=[Background(color=ACCENT, padding=(26, 16), border_radius=3)],
            animation=Wipe(direction="up", duration=0.5, trigger="after_previous"),
        )
        .text(
            content="github.com/sjquant/quickthumb",
            font=UI,
            size=17,
            color=MUTE,
            position=(centre, 494),
            align=("center", "top"),
            animation=Fade(duration=0.5, trigger="after_previous"),
        )
        .text(
            content="MP4   ·   WEBM   ·   GIF",
            font=UI,
            size=LABEL_SIZE,
            color=MUTE,
            letter_spacing=3,
            position=(centre, 562),
            align=("center", "top"),
            animation=Fade(duration=0.5, trigger="after_previous"),
        )
    )


def _copy_block(
    canvas: Canvas,
    *,
    label: str,
    headline: str,
    body: str,
    top: int,
    width: int,
) -> Canvas:
    """Set the shared label → headline → body stack used by the graphic scenes."""
    headline_height = round(len(headline.split("\n")) * HEADLINE_SIZE * 1.14)
    return (
        canvas.text(
            content=label,
            font=UI,
            size=LABEL_SIZE,
            color=ACCENT,
            letter_spacing=2,
            position=(MARGIN, top),
            animation=Fade(duration=0.4),
        )
        .text(
            content=headline,
            font=KR_HEAVY,
            size=HEADLINE_SIZE,
            color=CREAM,
            line_height=1.14,
            position=(MARGIN, top + 34),
            max_width=width,
            auto_scale=True,
            min_size=32,
            animation=Wipe(direction="up", duration=0.5, trigger="after_previous"),
        )
        .text(
            content=body,
            font=KR,
            size=BODY_SIZE,
            color=MUTE,
            line_height=1.5,
            position=(MARGIN, top + 34 + headline_height + 30),
            max_width=width,
            auto_scale=True,
            min_size=16,
            animation=Fade(duration=0.5, trigger="after_previous"),
        )
    )


def _full_bleed(
    canvas: Canvas,
    source_name: str,
    duration: float,
    trim_start: float,
    trim_end: float,
    captions: list[dict] | None = None,
) -> Canvas:
    """Fill the frame with one clip stretched to the scene's exact length."""
    return _clip(
        canvas,
        source_name,
        duration,
        trim_start,
        trim_end,
        (0, 0),
        WIDTH,
        HEIGHT,
        captions=captions,
    )


def _clip(
    canvas: Canvas,
    source_name: str,
    duration: float,
    trim_start: float,
    trim_end: float,
    position: tuple[int, int],
    width: int,
    height: int,
    captions: list[dict] | None = None,
    border_radius: int = 0,
) -> Canvas:
    """Place one clip, slowing shorter footage instead of reading past its end."""
    # Sources run 5.0s to 8.0s, so a scene longer than its clip plays slower
    # rather than asking the exporter for frames the media does not have.
    speed = min(1.0, (trim_end - trim_start) / duration)
    return canvas.video(
        str(VIDEO_DIR / source_name),
        position=position,
        width=width,
        height=height,
        fit="cover",
        trim_start=trim_start,
        trim_end=trim_end,
        duration=duration,
        speed=speed,
        captions=captions or [],
        border_radius=border_radius,
    )


def _caption(text: str, start: float, end: float) -> dict:
    """Style one caption cue; every cue in the film shares this treatment."""
    return {
        "text": text,
        "start": start,
        "end": end,
        "font": KR_BOLD,
        "vertical_align": "optical-center",
        "position": (WIDTH // 2, 636),
        "size": 24,
        "color": CREAM,
        "background": INK,
        "background_opacity": 0.9,
        "padding": (20, 12),
        "border_radius": 2,
    }


def _sweep(distance: int, duration: float) -> AnimationSpec:
    """Carry a playhead across its track at exactly the scene's own rate."""
    return AnimationSpec.timeline(
        PositionTrack(
            keyframes=[
                KeyframeSpec(time=0.0, value=(0.0, 0.0)),
                KeyframeSpec(time=duration, value=(float(distance), 0.0)),
            ]
        ),
        timing=TimingSpec(start=0.0, duration=duration),
        easing="linear",
    )


def _scrim(canvas: Canvas, *, edge: str, boundary: int, fade: int, peak: float) -> Canvas:
    """Hold ink solid behind the copy, then fall off smoothly into the shot.

    One gradient-filled rectangle covers both parts: the stop at ``boundary``
    is where the ramp reaches full strength, and everything past it stays there.
    """
    alpha = f"{round(peak * 255):02X}"
    if edge == "top":
        top, height = 0, boundary + fade
        stops = [(f"{INK}{alpha}", 0.0), (f"{INK}{alpha}", boundary / height), (f"{INK}00", 1.0)]
    else:
        top, height = boundary - fade, HEIGHT - boundary + fade
        stops = [(f"{INK}00", 0.0), (f"{INK}{alpha}", fade / height), (f"{INK}{alpha}", 1.0)]
    return canvas.shape(
        shape="rectangle",
        position=(0, top),
        width=WIDTH,
        height=height,
        color=INK,
        fill=LinearGradient(angle=90, stops=stops),
    )


def _timestamp(seconds: float) -> str:
    """Format one cue time the way the caption timeline prints it."""
    minutes, remainder = divmod(seconds, 60)
    return f"{int(minutes):02d}:{remainder:04.1f}"


if __name__ == "__main__":
    main()
