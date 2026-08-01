"""QuickThumb in motion: one composition, every delivery.

This short landscape product film turns one ordinary moment into a complete
delivery system. Each scene demonstrates one composition decision, then the
same deterministic timeline branches into MP4, WebM, and GIF.

Run from the repository root with::

    uv run python examples/ordinary_moments.py

FFmpeg is required for the MP4, WebM, and GIF outputs.
"""

from pathlib import Path

from quickthumb import AudioTrack, Canvas, Deck, Wipe
from quickthumb import transitions as tr

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
VIDEO_DIR = ASSETS / "video"
FONT = str(ASSETS / "fonts" / "Pretendard-Regular.woff2")
FONT_BOLD = str(ASSETS / "fonts" / "Pretendard-ExtraBold.woff2")
SOUNDTRACK = ASSETS / "audio" / "ordinary_moments_vastness.mp3"

OUT_DIR = ROOT / "examples"
OUT_MP4 = OUT_DIR / "ordinary_moments.mp4"
OUT_WEBM = OUT_DIR / "ordinary_moments.webm"
OUT_GIF = OUT_DIR / "ordinary_moments_preview.gif"

WIDTH, HEIGHT = 1280, 720
SCENE_DURATION = 6.0
VIDEO_END = 7.8
CAPTION_START = 0.85
CAPTION_END = 5.0
SOUNDTRACK_VOLUME = 0.16
SOUNDTRACK_FADE_OUT = 1.4
SOURCE_ENDS = {
    "ordinary-city.mp4": 4.8,
    "ordinary-coffee.mp4": 7.1,
    "ordinary-sunrise.mp4": 7.2,
}
INK = "#101820"
CREAM = "#F5F3ED"
ACCENT = "#D0A464"
PANEL_PADDING_X = 48
PANEL_PADDING_TOP = 40
EYEBROW_TO_HEADLINE = 54
BOTTOM_RULE_OFFSET = 60
BOTTOM_DETAIL_OFFSET = 38
SIDE_RULE_OFFSET = 78
SIDE_DETAIL_OFFSET = 48


def _format_timestamp(seconds: float) -> str:
    """Format a short media timestamp for the on-screen demo controls."""
    minutes, remainder = divmod(seconds, 60)
    return f"{int(minutes):02d}:{remainder:04.1f}"


def _add_foreground_caption(canvas: Canvas, content: str) -> Canvas:
    """Place a high-contrast caption above scene-wide shade layers."""
    width = 300 if len(content) > 12 else 248
    return canvas.shape(
        shape="rectangle",
        position=((WIDTH - width) // 2, 629),
        width=width,
        height=42,
        color=INK,
        opacity=0.9,
    ).text(
        content=content,
        font=FONT_BOLD,
        size=20,
        color=CREAM,
        position=(WIDTH // 2, 650),
        align=("center", "middle"),
        max_width=width - 28,
        auto_scale=True,
        min_size=16,
    )


def _caption_position(index: int) -> tuple[int, int]:
    """Keep captions in scene-specific negative space, clear of later panels."""
    if index == 2:
        return WIDTH // 2, 104
    if index == 3:
        return WIDTH // 2, 390
    if index == 4:
        return 550, 650
    return WIDTH // 2, 650


# Each source appears once. The final proof scene is intentionally graphic so
# the film changes visual grammar before the end card instead of looping footage.
SCENES = (
    (
        "ordinary-city.mp4",
        "01  /  THE INPUT",
        "같은 장면을\n다시 만들고 있나요?",
        "아이디어 하나를 포맷마다 다시 만드는 순간, 속도가 멈춥니다.",
        "한 번 구성하면 됩니다.",
    ),
    (
        "ordinary-notebook.mp4",
        "02  /  TRIM",
        "필요한 순간만\n남깁니다.",
        "원본에서 메시지가 시작되는 순간까지 정확하게 자릅니다.",
        "TRIM. FIT. PLACE.",
    ),
    (
        "ordinary-coffee.mp4",
        "03  /  FIT",
        "가로에서\n세로까지.",
        "cover, contain, placement. 프레임의 의도는 화면이 바뀌어도 남습니다.",
        "한 장면. 세 화면.",
    ),
    (
        "ordinary-phone.mp4",
        "04  /  CAPTIONS",
        "말은\n정확한 순간에.",
        "자막도 타임라인의 일부입니다. 위치, 배경, 시작과 끝까지.",
        "보이는 말은 타이밍입니다.",
    ),
    (
        "ordinary-sunrise.mp4",
        "05  /  TIMELINE",
        "움직임과 소리를\n한 타임라인에.",
        "속도, 볼륨, 전환, 페이드아웃이 하나의 시간축을 공유합니다.",
        "화면과 소리, 함께.",
    ),
)


def build_deck() -> Deck:
    """Build the public short-form QuickThumb composition."""
    transition_duration = 0.45
    transitions = (
        tr.Cut(advance_after=SCENE_DURATION),
        tr.Fade(duration=transition_duration, advance_after=SCENE_DURATION - transition_duration),
        tr.Wipe(
            direction="left",
            duration=transition_duration,
            advance_after=SCENE_DURATION - transition_duration,
        ),
        tr.Cut(advance_after=SCENE_DURATION),
        tr.Fade(duration=transition_duration, advance_after=SCENE_DURATION - transition_duration),
        tr.Wipe(direction="up", duration=0.5, advance_after=3.4),
        tr.Fade(duration=0.6, advance_after=3.4),
    )
    deck = Deck(WIDTH, HEIGHT)
    for index, scene in enumerate(SCENES):
        deck = deck.slide(build_scene(index, *scene), transition=transitions[index])
    deck = deck.slide(build_output_scene(), transition=transitions[len(SCENES)])
    deck = deck.slide(build_outro(), transition=transitions[-1])
    return deck


def build_output_scene() -> Canvas:
    """Break the footage rhythm with a concise, animated delivery proof."""
    canvas = (
        Canvas(WIDTH, HEIGHT)
        .background(color=INK)
        .shape(shape="rectangle", position=(72, 82), width=8, height=556, color=ACCENT)
        .text(
            content="06  /  OUTPUT",
            font=FONT_BOLD,
            size=18,
            color=ACCENT,
            letter_spacing=1,
            position=(120, 116),
        )
        .text(
            content="한 번 만들고.\n세 곳에 보냅니다.",
            font=FONT_BOLD,
            size=62,
            color=CREAM,
            line_height=0.98,
            position=(120, 188),
            max_width=560,
            auto_scale=True,
            min_size=42,
            animation=Wipe(direction="up", duration=0.45),
        )
        .text(
            content="같은 구성에서 필요한 전달 포맷을 바로 출력합니다.",
            font=FONT,
            size=21,
            color=CREAM,
            position=(120, 410),
            max_width=520,
            auto_scale=True,
            min_size=16,
            animation=Wipe(direction="up", duration=0.4, trigger="after_previous"),
        )
    )
    canvas.shape(
        shape="rectangle",
        position=(108, 500),
        width=140,
        height=78,
        color="#1B2730",
        opacity=0.95,
    )
    canvas.counter(
        1,
        100,
        1.8,
        position=(120, 516),
        size=68,
        color=ACCENT,
        style="flip",
    )
    canvas.text(
        content="FRAMES COMPOSED",
        font=FONT_BOLD,
        size=18,
        color=CREAM,
        letter_spacing=1,
        position=(120, 590),
    )
    for index, (label, sublabel) in enumerate(
        (("MP4", "MASTER"), ("WEBM", "WEB"), ("GIF", "PREVIEW"))
    ):
        x = 744 + index * 152
        canvas = (
            canvas.shape(
                shape="rectangle",
                position=(x, 176),
                width=128,
                height=250,
                color="#25313A",
                opacity=0.96,
                animation=Wipe(direction="up", duration=0.38, trigger="after_previous"),
            ).shape(shape="rectangle", position=(x, 176), width=128, height=8, color=ACCENT)
            .text(
                content=label,
                font=FONT_BOLD,
                size=28,
                color=CREAM,
                position=(x + 22, 234),
            )
            .text(
                content=sublabel,
                font=FONT_BOLD,
                size=12,
                color=ACCENT,
                letter_spacing=1,
                position=(x + 22, 362),
            )
        )
    return canvas


def build_outro() -> Canvas:
    """Build a quiet two-second end card so the film lands instead of stopping."""
    return (
        Canvas(WIDTH, HEIGHT)
        .background(color=INK)
        .shape(
            shape="rectangle",
            position=(72, 132),
            width=8,
            height=456,
            color=ACCENT,
        )
        .text(
            content="QUICKTHUMB",
            font=FONT_BOLD,
            size=18,
            color=ACCENT,
            letter_spacing=1,
            position=(120, 144),
        )
        .text(
            content="한 번의 구성.\n모든 포맷.",
            font=FONT_BOLD,
            size=64,
            color=CREAM,
            line_height=0.98,
            position=(120, 216),
            max_width=720,
            auto_scale=True,
            min_size=42,
        )
        .text(
            content="Trim. Fit. Place. Move.",
            font=FONT,
            size=22,
            color=CREAM,
            position=(120, 430),
        )
        .text(
            content="MP4  /  WEBM  /  GIF",
            font=FONT_BOLD,
            size=18,
            color=ACCENT,
            letter_spacing=1,
            position=(120, 548),
        )
        .shape(
            shape="rectangle",
            position=(792, 180),
            width=400,
            height=360,
            color="#18232B",
        )
        .text(
            content="START COMPOSING",
            font=FONT_BOLD,
            size=16,
            color=ACCENT,
            letter_spacing=1,
            position=(840, 228),
        )
        .text(
            content="uv add quickthumb",
            font=FONT_BOLD,
            size=30,
            color=CREAM,
            position=(840, 292),
        )
        .shape(
            shape="rectangle",
            position=(840, 354),
            width=280,
            height=2,
            color=ACCENT,
        )
        .text(
            content="github.com/sjquant/quickthumb",
            font=FONT,
            size=18,
            color=CREAM,
            position=(840, 396),
            max_width=300,
            auto_scale=True,
            min_size=14,
        )
    )


def build_scene(
    index: int,
    source_name: str,
    eyebrow: str,
    headline: str,
    detail: str,
    caption: str,
) -> Canvas:
    """Build one full-bleed advertising scene with varied overlay treatment."""
    source = str(VIDEO_DIR / source_name)
    trim_start = min(0.8, index * 0.11)
    # Source clips have different durations; slow shorter shots down instead
    # of asking the exporter to read beyond a validated media boundary.
    trim_end = SOURCE_ENDS.get(source_name, VIDEO_END)
    speed = min(1.0, (trim_end - trim_start) / SCENE_DURATION)
    trim_status = f"TRIM {_format_timestamp(trim_start)} → {_format_timestamp(trim_end)}"
    caption_status = f"CUE {_format_timestamp(CAPTION_START)} → {_format_timestamp(CAPTION_END)}"
    foreground_caption = index == 0
    caption_x, caption_y = _caption_position(index)
    canvas = Canvas(WIDTH, HEIGHT).background(color=INK)
    canvas.video(
        source,
        position=(0, 0),
        width=WIDTH,
        height=HEIGHT,
        fit="cover",
        trim_start=trim_start,
        trim_end=trim_end,
        duration=SCENE_DURATION,
        speed=speed,
        captions=[]
        if foreground_caption
        else [
            {
                "text": caption,
                "start": CAPTION_START,
                "end": CAPTION_END,
                "font": FONT_BOLD,
                "vertical_align": "optical-center",
                # Bottom-panel scenes reserve the lower band for the overlay,
                # so the cue sits just above it instead of being covered.
                "position": (caption_x, caption_y),
                "size": 20,
                "color": CREAM,
                "background": INK,
                "background_opacity": 0.9,
                "padding": (6, 14, 6, 14),
                "border_radius": 2,
            }
        ],
    )
    if index == 0:
        canvas = (
            canvas.shape(
                shape="rectangle",
                position=(0, 0),
                width=WIDTH,
                height=HEIGHT,
                color=INK,
                opacity=0.55,
            )
            .shape(
                shape="rectangle",
                position=(72, 104),
                width=8,
                height=300,
                color=ACCENT,
                animation=Wipe(direction="down", duration=0.28),
            )
            .text(
                content=eyebrow,
                font=FONT_BOLD,
                size=18,
                color=ACCENT,
                letter_spacing=1,
                position=(120, 112),
                animation=Wipe(direction="right", duration=0.25, trigger="after_previous"),
            )
            .text(
                content=headline,
                font=FONT_BOLD,
                size=66,
                color=CREAM,
                line_height=0.98,
                position=(120, 176),
                max_width=620,
                auto_scale=True,
                min_size=42,
                animation=Wipe(direction="up", duration=0.42, trigger="after_previous"),
            )
            .text(
                content=detail,
                font=FONT,
                size=22,
                color=CREAM,
                position=(120, 360),
                max_width=620,
                auto_scale=True,
                min_size=16,
                animation=Wipe(direction="up", duration=0.32, trigger="after_previous"),
            )
            .text(
                content="RAW  →  COMPOSE  →  DELIVER",
                font=FONT_BOLD,
                size=16,
                color=ACCENT,
                letter_spacing=1,
                position=(120, 548),
                animation=Wipe(direction="right", duration=0.28, trigger="after_previous"),
            )
        )
    elif index == 1:
        canvas = (
            canvas.shape(
                shape="rectangle",
                position=(64, 88),
                width=460,
                height=544,
                color=INK,
                opacity=0.86,
            )
            .shape(
                shape="rectangle",
                position=(64, 88),
                width=8,
                height=544,
                color=ACCENT,
                animation=Wipe(direction="down", duration=0.4),
            )
            .text(
                content=eyebrow,
                font=FONT_BOLD,
                size=16,
                color=ACCENT,
                letter_spacing=1,
                position=(112, 128),
                animation=Wipe(direction="right", duration=0.25, trigger="after_previous"),
            )
            .text(
                content=headline,
                font=FONT_BOLD,
                size=54,
                color=CREAM,
                line_height=0.98,
                position=(112, 190),
                max_width=340,
                auto_scale=True,
                min_size=34,
                animation=Wipe(direction="up", duration=0.45, trigger="after_previous"),
            )
            .shape(shape="rectangle", position=(112, 508), width=120, height=6, color=ACCENT)
            .text(
                content=detail,
                font=FONT,
                size=18,
                color=CREAM,
                line_height=1.2,
                position=(112, 544),
                max_width=340,
                auto_scale=True,
                min_size=14,
                animation=Wipe(direction="up", duration=0.35, trigger="after_previous"),
            )
            .text(
                content=trim_status,
                font=FONT_BOLD,
                size=14,
                color=ACCENT,
                position=(650, 584),
            )
        )
    elif index == 2:
        canvas = (
            canvas.shape(
                shape="rectangle",
                position=(0, 432),
                width=WIDTH,
                height=288,
                color=INK,
                opacity=0.88,
            )
            .text(
                content=eyebrow,
                font=FONT_BOLD,
                size=16,
                color=ACCENT,
                letter_spacing=1,
                position=(64, 466),
                animation=Wipe(direction="right", duration=0.24, trigger="after_previous"),
            )
            .text(
                content=headline,
                font=FONT_BOLD,
                size=42,
                color=CREAM,
                line_height=0.98,
                position=(64, 514),
                max_width=390,
                auto_scale=True,
                min_size=28,
                animation=Wipe(direction="up", duration=0.34, trigger="after_previous"),
            )
            .text(
                content="COVER  /  CONTAIN  /  PLACE",
                font=FONT_BOLD,
                size=15,
                color=ACCENT,
                letter_spacing=1,
                position=(64, 678),
                animation=Wipe(direction="right", duration=0.24, trigger="after_previous"),
            )
        )
        for x, label, marker_width, marker_height in (
            (610, "16:9", 122, 69),
            (810, "1:1", 96, 96),
            (1010, "9:16", 54, 96),
        ):
            canvas = (
                canvas.shape(
                    shape="rectangle",
                    position=(x, 474),
                    width=150,
                    height=174,
                    color="#25313A",
                    opacity=0.96,
                    animation=Wipe(direction="up", duration=0.35, trigger="after_previous"),
                )
                .shape(
                    shape="rectangle",
                    position=(
                        x + (150 - marker_width) // 2,
                        488 + (96 - marker_height) // 2,
                    ),
                    width=marker_width,
                    height=marker_height,
                    color=ACCENT,
                    opacity=0.9,
                )
                .text(
                    content=label,
                    font=FONT_BOLD,
                    size=18,
                    color=CREAM,
                    position=(x + 16, 612),
                )
            )
    elif index == 3:
        canvas = (
            canvas.shape(
                shape="rectangle",
                position=(56, 72),
                width=560,
                height=270,
                color=INK,
                opacity=0.82,
            )
            .text(
                content=eyebrow,
                font=FONT_BOLD,
                size=16,
                    color=ACCENT,
                    letter_spacing=1,
                    position=(96, 110),
                    animation=Wipe(direction="right", duration=0.24, trigger="after_previous"),
            )
            .text(
                content=headline,
                font=FONT_BOLD,
                size=54,
                color=CREAM,
                line_height=0.98,
                position=(96, 164),
                max_width=440,
                auto_scale=True,
                min_size=34,
                animation=Wipe(direction="up", duration=0.38, trigger="after_previous"),
            )
            .shape(
                shape="rectangle",
                position=(0, 488),
                width=WIDTH,
                height=144,
                color=INK,
                opacity=0.92,
            )
            .text(
                content="CAPTION TIMELINE",
                font=FONT_BOLD,
                size=15,
                color=ACCENT,
                letter_spacing=1,
                position=(72, 516),
            )
            .shape(shape="rectangle", position=(72, 556), width=1000, height=4, color="#64727A")
            .shape(shape="rectangle", position=(72, 556), width=420, height=4, color=ACCENT)
            .shape(shape="rectangle", position=(492, 544), width=4, height=28, color=CREAM)
            .text(
                content=caption_status,
                font=FONT_BOLD,
                size=16,
                color=CREAM,
                position=(72, 588),
                animation=Wipe(direction="right", duration=0.28, trigger="after_previous"),
            )
        )
    elif index == 4:
        canvas = (
            canvas.shape(
                shape="rectangle",
                position=(720, 74),
                width=488,
                height=572,
                color=INK,
                opacity=0.88,
            )
            .shape(shape="rectangle", position=(1200, 74), width=8, height=572, color=ACCENT)
            .text(
                content=eyebrow,
                font=FONT_BOLD,
                size=16,
                color=ACCENT,
                letter_spacing=1,
                position=(768, 116),
            )
            .text(
                content=headline,
                font=FONT_BOLD,
                size=48,
                color=CREAM,
                line_height=0.98,
                position=(768, 170),
                max_width=380,
                auto_scale=True,
                min_size=32,
                animation=Wipe(direction="up", duration=0.38, trigger="after_previous"),
            )
            .shape(shape="rectangle", position=(768, 384), width=320, height=4, color="#64727A")
            .shape(shape="rectangle", position=(768, 384), width=232, height=4, color=ACCENT)
            .text(
                content="AUDIO TRACK",
                font=FONT_BOLD,
                size=15,
                color=CREAM,
                position=(768, 418),
            )
            .counter(
                0,
                speed,
                0.9,
                position=(768, 450),
                size=30,
                color=ACCENT,
                suffix=" SPEED",
                style="odometer",
                animation=Wipe(direction="right", duration=0.3, trigger="after_previous"),
            )
            .text(
                content=f"VOL {SOUNDTRACK_VOLUME:.0%}   FADE {SOUNDTRACK_FADE_OUT:.1f}s",
                font=FONT_BOLD,
                size=13,
                color=CREAM,
                letter_spacing=1,
                position=(768, 492),
            )
            .text(
                content=detail,
                font=FONT,
                size=18,
                color=CREAM,
                line_height=1.2,
                position=(768, 532),
                max_width=330,
                auto_scale=True,
                min_size=14,
                animation=Wipe(direction="right", duration=0.3, trigger="after_previous"),
            )
        )
    else:
        canvas = (
            canvas.shape(
                shape="rectangle",
                position=(0, 0),
                width=WIDTH,
                height=HEIGHT,
                color=INK,
                opacity=0.62,
            )
            .shape(shape="rectangle", position=(72, 118), width=8, height=430, color=ACCENT)
            .text(
                content=eyebrow,
                font=FONT_BOLD,
                size=18,
                color=ACCENT,
                letter_spacing=1,
                position=(120, 128),
            )
            .text(
                content=headline,
                font=FONT_BOLD,
                size=68,
                color=CREAM,
                line_height=0.98,
                position=(120, 194),
                max_width=720,
                auto_scale=True,
                min_size=44,
            )
            .text(
                content=detail,
                font=FONT,
                size=22,
                color=CREAM,
                position=(120, 410),
                max_width=720,
                auto_scale=True,
                min_size=16,
            )
            .text(
                content="COMPOSE ONCE",
                font=FONT_BOLD,
                size=18,
                color=ACCENT,
                letter_spacing=1,
                position=(120, 530),
            )
        )
    if foreground_caption:
        canvas = _add_foreground_caption(canvas, caption)
    return canvas


def main() -> None:
    """Diagnose and export the finished composition."""
    deck = build_deck()
    findings = deck.diagnose()
    errors = [finding for finding in findings if finding.severity == "error"]
    if errors:
        raise RuntimeError(f"ordinary_moments has diagnostics: {errors}")

    soundtrack = AudioTrack(
        path=str(SOUNDTRACK),
        volume=SOUNDTRACK_VOLUME,
        loop=True,
        fade_out=SOUNDTRACK_FADE_OUT,
    )
    OUT_MP4.write_bytes(deck.to_animated_mp4(fps=24, soundtrack=soundtrack))
    OUT_WEBM.write_bytes(deck.to_webm(fps=24, soundtrack=soundtrack))
    # VideoLayer supplies the timeline; zero avoids adding a second settled hold.
    OUT_GIF.write_bytes(build_scene(0, *SCENES[0]).to_gif(fps=10, hold=0))
    print(f"Wrote {OUT_MP4}")
    print(f"Wrote {OUT_WEBM}")
    print(f"Wrote {OUT_GIF}")


if __name__ == "__main__":
    main()
