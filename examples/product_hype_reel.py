"""결 — 리듬에 맞춰 전개되는 한국어 세로형 제품 필름.

The example builds an eight-scene fitness-app ad on one Reels-safe
layout grid. It demonstrates platform-aware diagnostics, layered gradients,
animated product-metric cards, native Pretendard typography, and slide transitions
in GIF/WebM/MP4 with a soundtrack mixed at render time.

Run:
    uv run python examples/product_hype_reel.py
"""

from pathlib import Path

from quickthumb import (
    AudioTrack,
    Canvas,
    Deck,
    Dissolve,
    Fade,
    GifOptions,
    Glow,
    InnerShadow,
    LinearGradient,
    QuickthumbError,
    RadialGradient,
    Shadow,
    Stroke,
    VideoOptions,
    Wipe,
)
from quickthumb import transitions as tr

FILE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = FILE_DIR.parent / "assets"
SOUNDTRACK = ASSETS_DIR / "audio" / "hype_beat.wav"
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
    """Return the eight-scene, 48-beat GYEOL reel."""
    hook = build_hook_scene()
    problem = build_problem_scene()
    solution = build_solution_scene()
    live_sync = build_live_sync_scene()
    ai_coach = build_ai_coach_scene()
    streak = build_streak_scene()
    proof = build_social_proof_scene()
    cta = build_cta_scene()

    # Longer scenes leave a calm reading window while every incoming
    # transition stays aligned to a beat.
    return (
        Deck(WIDTH, HEIGHT)
        .slide(
            hook,
            transition=tr.Cut(advance_after=SCENE_DURATION),
            duration=SCENE_DURATION,
        )
        .slide(
            problem,
            transition=tr.Wipe(direction="up", duration=BEAT, advance_after=SCENE_HOLD),
            duration=SCENE_DURATION,
        )
        .slide(
            solution,
            transition=tr.Push(direction="up", duration=BEAT, advance_after=SCENE_HOLD),
            duration=SCENE_DURATION,
        )
        .slide(
            live_sync,
            transition=tr.Push(direction="left", duration=BEAT, advance_after=SCENE_HOLD),
            duration=SCENE_DURATION,
        )
        .slide(
            ai_coach,
            transition=tr.Push(direction="left", duration=BEAT, advance_after=SCENE_HOLD),
            duration=SCENE_DURATION,
        )
        .slide(
            streak,
            transition=tr.Push(direction="left", duration=BEAT, advance_after=SCENE_HOLD),
            duration=SCENE_DURATION,
        )
        .slide(
            proof,
            transition=tr.Fade(duration=BEAT, advance_after=SCENE_HOLD),
            duration=SCENE_DURATION,
        )
        .slide(
            cta,
            transition=tr.Zoom(direction="in", duration=BEAT, advance_after=SCENE_HOLD),
            duration=SCENE_DURATION,
        )
    )


def build_hook_scene() -> Canvas:
    """Open with a bold promise and a live heart-rate product card."""
    canvas = base_scene(0, PINK)
    canvas = add_copy(
        canvas,
        eyebrow="NEW  ·  PERSONAL FITNESS OS",
        headline="내 몸의 리듬을\n다시 만나다.",
        body="심박부터 회복까지, 오늘의 몸을 한눈에 읽습니다.",
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
        content="●  실시간 심박",
        font=PRETENDARD[700],
        size=48,
        color=PINK,
        position=(144, 1018),
        align=("left", "top"),
        animation=Fade(duration=MOTION_FAST, trigger="with_previous"),
    )
    canvas = canvas.text(
        content="구간 4",
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
        content="심박수  ·  운동 강도",
        font=PRETENDARD[500],
        size=48,
        color=MUTED,
        position=(144, 1340),
        align=("left", "top"),
        animation=Fade(duration=MOTION_FAST, trigger="after_previous"),
    )
    return add_footer(
        canvas,
        "GYEOL  ·  나를 읽는 피트니스 OS",
        animation=Fade(duration=MOTION_FAST, trigger="with_previous"),
    )


def build_problem_scene() -> Canvas:
    """Frame inconsistent exercise as a feedback problem, not a willpower problem."""
    canvas = base_scene(1, VIOLET)
    canvas = add_copy(
        canvas,
        eyebrow="꾸준함의 조건",
        headline="의지보다 먼저\n필요한 것.",
        body="피드백이 늦으면 마음도 금세 멀어집니다.",
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
        content="평균 이탈 시점",
        font=PRETENDARD[700],
        size=48,
        color=MUTED,
        position=(140, 1035),
        align=("left", "top"),
        animation=Fade(duration=MOTION_FAST, trigger="with_previous"),
    )
    canvas = canvas.text(
        content="3일째",
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
        content="실시간 피드백",
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
        "늦은 피드백은 움직일 마음을 놓칩니다.",
        animation=Fade(duration=MOTION_FAST, trigger="with_previous"),
    )


def build_solution_scene() -> Canvas:
    """Introduce GYEOL as one clear daily readiness signal."""
    canvas = base_scene(2, CYAN)
    canvas = add_copy(
        canvas,
        eyebrow="MEET GYEOL",
        headline="흩어진 신호가\n하나의 리듬으로.",
        body="복잡한 몸의 신호를 오늘의 점수로 바꿉니다.",
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
        content="회복 점수",
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
        content="수면 92  ·  에너지 81\n스트레스 24",
        font=PRETENDARD[500],
        size=48,
        color=MUTED,
        position=(144, 1280),
        align=("left", "top"),
        max_width=704,
        max_height=120,
        auto_scale=True,
        min_size=48,
        letter_spacing=2,
        line_height=1.1,
        animation=Fade(duration=MOTION_FAST, trigger="after_previous"),
    )
    return add_footer(
        canvas,
        "오늘의 몸을 한눈에 읽어보세요.",
        animation=Fade(duration=MOTION_FAST, trigger="with_previous"),
    )


def build_live_sync_scene() -> Canvas:
    """Show the first feature: live heart-rate synchronization."""
    canvas = base_scene(3, PINK)
    canvas = add_copy(
        canvas,
        eyebrow="01  ·  LIVE SYNC",
        headline="움직이는 순간을\n놓치지 않게.",
        body="심박 구간과 운동 강도를 실시간으로 읽습니다.",
        accent=PINK,
        headline_size=93,
        headline_letter_spacing=0,
    )
    canvas = add_metric_card(
        canvas,
        label="실시간 심박",
        status="SYNCED",
        value="142",
        unit="BPM",
        unit_x=500,
        detail="워밍업  ·  지방 연소  ·  유산소",
        accent=PINK,
    )
    return add_footer(
        canvas,
        "APPLE WATCH  ·  GALAXY WATCH 연동",
        animation=Fade(duration=MOTION_FAST, trigger="with_previous"),
    )


def build_ai_coach_scene() -> Canvas:
    """Show the second feature: an adaptive daily training load."""
    canvas = base_scene(4, CYAN)
    canvas = add_copy(
        canvas,
        eyebrow="02  ·  AI COACH",
        headline="오늘의 속도는\n몸이 정하니까.",
        body="회복 상태에 맞춰 시간과 강도를 조정합니다.",
        accent=CYAN,
        headline_size=95,
        headline_letter_spacing=0,
    )
    canvas = add_metric_card(
        canvas,
        label="오늘의 운동량",
        status="AUTO",
        value="68",
        unit="%",
        unit_x=390,
        detail="24 MIN  ·  MODERATE",
        accent=CYAN,
    )
    return add_footer(
        canvas,
        "매일 달라지는 나에게 맞춘 코칭.",
        animation=Fade(duration=MOTION_FAST, trigger="with_previous"),
    )


def build_streak_scene() -> Canvas:
    """Show the third feature: a motivating twenty-one-day streak."""
    canvas = base_scene(5, LIME)
    canvas = add_copy(
        canvas,
        eyebrow="03  ·  SMART STREAK",
        headline="작은 사흘이\n스물하루가 되도록.",
        body="작은 성공을 오래가는 습관으로 연결합니다.",
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
        content="꾸준함",
        font=PRETENDARD[700],
        size=48,
        color=LIME,
        position=(144, 1018),
        align=("left", "top"),
        animation=Fade(duration=MOTION_FAST, trigger="with_previous"),
    )
    canvas = canvas.text(
        content="최고 기록",
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
        content="일 연속",
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
        "꾸준함이 보이면 습관은 계속됩니다.",
        animation=Fade(duration=MOTION_FAST, trigger="with_previous"),
    )


def build_social_proof_scene() -> Canvas:
    """Land the product story with a credible, high-contrast testimonial."""
    canvas = base_scene(6, VIOLET)
    canvas = add_copy(
        canvas,
        eyebrow="4.9  ·  2,841개의 기록",
        headline="조금 더 오래,\n조금 더 멀리.",
        body="결과 함께 만든 변화는 숫자로 남습니다.",
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
        content="확인된 후기",
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
        content="“처음으로 5KM를\n끝까지 달렸어요.”",
        font=PRETENDARD[800],
        size=68,
        color=WHITE,
        line_height=1.16,
        position=(140, 1140),
        align=("left", "top"),
        animation=Wipe(direction="up", duration=MOTION_STANDARD, trigger="after_previous"),
    )
    canvas = canvas.text(
        content="베타 테스터  ·  8주차",
        font=PRETENDARD[500],
        size=48,
        color=MUTED,
        position=(140, 1338),
        align=("left", "top"),
        animation=Fade(duration=MOTION_FAST, trigger="after_previous"),
    )
    return add_footer(
        canvas,
        "다음 기록은 오늘 여기서 시작됩니다.",
        animation=Fade(duration=MOTION_FAST, trigger="with_previous"),
    )


def build_cta_scene() -> Canvas:
    """Finish on a focused, single-action download screen."""
    canvas = base_scene(7, PINK)
    canvas = add_copy(
        canvas,
        eyebrow="GYEOL  ·  START TODAY",
        headline="오늘, 다시 시작\n나답게 움직이기",
        body="내 몸을 이해하는 가장 선명한 방법.",
        accent=PINK,
        headline_size=124,
    )
    canvas = canvas.shape(
        shape="pill",
        position=(CONTENT_X, 1010),
        width=CONTENT_WIDTH,
        height=132,
        color=PINK,
        align=("left", "top"),
        effects=BUTTON_EFFECTS,
        animation=Dissolve(duration=MOTION_STANDARD, trigger="after_previous"),
    )
    canvas = canvas.text(
        content="무료로 시작하기",
        font=PRETENDARD[800],
        size=56,
        color=WHITE,
        position=(CONTENT_CENTER, 1076),
        align=("center", "middle"),
        animation=Fade(duration=MOTION_FAST, trigger="with_previous"),
    )
    canvas = canvas.text(
        content="평점 4.9  ·  7일 무료  ·  언제든 해지",
        font=PRETENDARD[700],
        size=48,
        color=OFFWHITE,
        position=(CONTENT_X, 1220),
        align=("left", "top"),
        max_width=CONTENT_WIDTH,
        auto_scale=True,
        min_size=48,
        animation=Fade(duration=MOTION_FAST, trigger="after_previous"),
    )
    return canvas.text(
        content="GYEOL.APP  ↗",
        font=PRETENDARD[900],
        size=54,
        color=OFFWHITE,
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
        content="GYEOL",
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
        position=(unit_x, 1214),
        align=("left", "top"),
        animation=Fade(duration=MOTION_FAST, trigger="with_previous"),
    )
    return canvas.text(
        content=detail,
        font=PRETENDARD[500],
        size=48,
        color=MUTED,
        position=(144, 1280),
        align=("left", "top"),
        max_width=704,
        max_height=120,
        auto_scale=True,
        min_size=48,
        line_height=1.1,
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
    # GIF keeps every frame in memory, so use a smaller canvas and palette while
    # retaining enough frames for a useful preview of the full reel.
    deck.render(
        str(OUT_GIF),
        animation=GifOptions(fps=8, max_size=(540, 960), colors=128),
    )

    for output in (OUT_PPTX, OUT_HTML):
        try:
            deck.render(str(output))
        except QuickthumbError as error:
            print(f"⚠ Skipped {output.suffix.removeprefix('.').upper()} ({error})")

    soundtrack = AudioTrack(path=str(SOUNDTRACK), volume=0.16, loop=True)
    for output in (OUT_MP4, OUT_WEBM):
        try:
            deck.render(str(output), animation=VideoOptions(soundtrack=soundtrack))
        except QuickthumbError as error:
            print(f"⚠ Skipped {output.suffix.removeprefix('.').upper()} ({error})")

    print(f"✓ {OUT_GIF}")
    print(f"  {OUT_PPTX}")
    print(f"  {OUT_HTML}")
    print(f"  {OUT_MP4}")
    print(f"  {OUT_WEBM}")
    print(f"  {len(deck)} scenes · 36 seconds · beat-synced timeline")


if __name__ == "__main__":
    main()
