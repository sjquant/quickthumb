"""QuickThumb in motion: one composition, every delivery.

This 60-second landscape product film turns one ordinary moment into a complete
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
SCENE_DURATION = 7.25
VIDEO_END = 7.8
CAPTION_START = 1.0
CAPTION_END = 6.5
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


# Each source is a different visual beat. The deliberate reuse is non-adjacent
# and only happens when the story needs a familiar visual anchor.
SCENES = (
    (
        "ordinary-city.mp4",
        "01  /  THE INPUT",
        "하나의 장면에서\n시작합니다.",
        "좋은 아이디어는 포맷마다 다시 만들 필요가 없습니다.",
        "아이디어를 움직이세요.",
    ),
    (
        "ordinary-notebook.mp4",
        "02  /  TRIM",
        "필요한 순간만\n남깁니다.",
        "원본에서 메시지가 시작되는 순간까지 정확하게 자릅니다.",
        "자르고. 맞추고. 배치합니다.",
    ),
    (
        "ordinary-coffee.mp4",
        "03  /  FIT",
        "같은 장면을\n모든 화면에.",
        "cover, contain, placement. 프레임은 의도대로 남습니다.",
        "모든 포맷에 같은 의도.",
    ),
    (
        "ordinary-phone.mp4",
        "04  /  CAPTIONS",
        "말은\n정확한 순간에.",
        "자막도 타임라인의 일부입니다. 위치, 배경, 시작과 끝까지.",
        "자막은 타이밍입니다.",
    ),
    (
        "ordinary-sunrise.mp4",
        "05  /  TIMELINE",
        "움직임과 소리를\n함께 맞춥니다.",
        "속도, 볼륨, 전환, 페이드아웃이 하나의 시간축을 공유합니다.",
        "화면과 소리, 오차 없이.",
    ),
    (
        "ordinary-city.mp4",
        "06  /  OUTPUT",
        "한 번 만들고.\n세 곳에 보냅니다.",
        "같은 구성에서 필요한 전달 포맷을 바로 출력합니다.",
        "필요한 포맷으로 바로 보냅니다.",
    ),
    (
        "ordinary-notebook.mp4",
        "07  /  DETERMINISTIC",
        "같은 타임라인.\n같은 프레임.",
        "다시 렌더링해도 장면과 오디오의 기준은 흔들리지 않습니다.",
        "같은 입력은 같은 결과를 만듭니다.",
    ),
    (
        "ordinary-coffee.mp4",
        "08  /  QUICKTHUMB",
        "구성은 한 번.\n전달은 어디서나.",
        "Trim. Fit. Place. Move. 아이디어를 다시 만들지 마세요.",
        "한 번의 구성, 모든 포맷.",
    ),
)


def build_deck() -> Deck:
    """Build the public 60-second QuickThumb composition."""
    transition_duration = 0.35
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
        tr.Wipe(
            direction="up",
            duration=transition_duration,
            advance_after=SCENE_DURATION - transition_duration,
        ),
        tr.Cut(advance_after=SCENE_DURATION),
        tr.Fade(duration=0.5, advance_after=SCENE_DURATION - 0.5),
        tr.Fade(duration=0.5, advance_after=1.5),
    )
    deck = Deck(WIDTH, HEIGHT)
    for index, scene in enumerate(SCENES):
        deck = deck.slide(build_scene(index, *scene), transition=transitions[index])
    deck = deck.slide(build_outro(), transition=transitions[-1])
    return deck


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
    speed = (trim_end - trim_start) / SCENE_DURATION
    trim_status = f"TRIM {_format_timestamp(trim_start)} → {_format_timestamp(trim_end)}"
    timeline_status = (
        f"SPEED {speed:.2f}×   VOL {SOUNDTRACK_VOLUME:.0%}   "
        f"FADE {SOUNDTRACK_FADE_OUT:.1f}s"
    )
    caption_status = f"CUE {_format_timestamp(CAPTION_START)} → {_format_timestamp(CAPTION_END)}"
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
        captions=[
            {
                "text": caption,
                "start": CAPTION_START,
                "end": CAPTION_END,
                "font": FONT_BOLD,
                "vertical_align": "center",
                # Bottom-panel scenes reserve the lower band for the overlay,
                # so the cue sits just above it instead of being covered.
                "position": (
                    WIDTH // 2,
                    390 if index == 3 else 320 if index == 5 else 104 if index == 2 else 650,
                ),
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
            .shape(shape="rectangle", position=(72, 104), width=8, height=300, color=ACCENT)
            .text(
                content=eyebrow,
                font=FONT_BOLD,
                size=18,
                color=ACCENT,
                letter_spacing=1,
                position=(120, 112),
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
            )
            .text(
                content="RAW  →  COMPOSE  →  DELIVER",
                font=FONT_BOLD,
                size=16,
                color=ACCENT,
                letter_spacing=1,
                position=(120, 548),
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
            )
            .text(
                content="COVER  /  CONTAIN  /  PLACE",
                font=FONT_BOLD,
                size=15,
                color=ACCENT,
                letter_spacing=1,
                position=(64, 678),
            )
        )
        for x, label in ((610, "16:9"), (810, "1:1"), (1010, "9:16")):
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
                    position=(x + 14, 488),
                    width=122 if label == "16:9" else 96,
                    height=6 if label == "16:9" else 96,
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
            .text(
                content=timeline_status,
                font=FONT_BOLD,
                size=15,
                color=ACCENT,
                letter_spacing=1,
                position=(768, 450),
            )
            .text(
                content=detail,
                font=FONT,
                size=18,
                color=CREAM,
                line_height=1.2,
                position=(768, 494),
                max_width=350,
                auto_scale=True,
                min_size=14,
            )
        )
    elif index == 5:
        canvas = (
            canvas.shape(
                shape="rectangle",
                position=(0, 0),
                width=WIDTH,
                height=250,
                color=INK,
                opacity=0.78,
            )
            .text(
                content=eyebrow,
                font=FONT_BOLD,
                size=16,
                color=ACCENT,
                letter_spacing=1,
                position=(64, 64),
            )
            .text(
                content=headline,
                font=FONT_BOLD,
                size=48,
                color=CREAM,
                line_height=0.98,
                position=(64, 110),
                max_width=520,
                auto_scale=True,
                min_size=32,
            )
        )
        for x, label, detail_label in (
            (64, "MP4", "FEED"),
            (444, "WEBM", "WEB"),
            (824, "GIF", "PREVIEW"),
        ):
            canvas = (
                canvas.shape(
                    shape="rectangle",
                    position=(x, 392),
                    width=320,
                    height=230,
                    color=INK,
                    opacity=0.88,
                    animation=Wipe(direction="up", duration=0.35, trigger="after_previous"),
                )
                .shape(shape="rectangle", position=(x, 392), width=320, height=8, color=ACCENT)
                .text(
                    content=label,
                    font=FONT_BOLD,
                    size=34,
                    color=CREAM,
                    position=(x + 28, 438),
                )
                .text(
                    content=detail_label,
                    font=FONT_BOLD,
                    size=14,
                    color=ACCENT,
                    letter_spacing=1,
                    position=(x + 28, 570),
                )
            )
    elif index == 6:
        canvas = (
            canvas.shape(
                shape="rectangle",
                position=(56, 74),
                width=520,
                height=570,
                color=INK,
                opacity=0.86,
            )
            .text(
                content=eyebrow,
                font=FONT_BOLD,
                size=16,
                color=ACCENT,
                letter_spacing=1,
                position=(104, 116),
            )
            .text(
                content=headline,
                font=FONT_BOLD,
                size=48,
                color=CREAM,
                line_height=0.98,
                position=(104, 170),
                max_width=420,
                auto_scale=True,
                min_size=32,
            )
            .shape(shape="rectangle", position=(104, 400), width=420, height=2, color="#64727A")
            .shape(shape="rectangle", position=(104, 400), width=420, height=2, color=ACCENT)
            .text(
                content="RENDER CHECK",
                font=FONT_BOLD,
                size=18,
                color=CREAM,
                position=(104, 430),
            )
            .text(
                content=detail,
                font=FONT,
                size=18,
                color=CREAM,
                line_height=1.2,
                position=(104, 510),
                max_width=390,
                auto_scale=True,
                min_size=14,
            )
            .shape(
                shape="rectangle",
                position=(688, 184),
                width=480,
                height=176,
                color=INK,
                opacity=0.82,
            )
            .shape(shape="rectangle", position=(688, 184), width=8, height=176, color=ACCENT)
            .text(content="RUN 01", font=FONT_BOLD, size=16, color=ACCENT, position=(736, 220))
            .text(content="00:42.000", font=FONT_BOLD, size=34, color=CREAM, position=(736, 262))
            .shape(
                shape="rectangle",
                position=(688, 392),
                width=480,
                height=176,
                color=INK,
                opacity=0.82,
            )
            .shape(shape="rectangle", position=(688, 392), width=8, height=176, color=ACCENT)
            .text(content="RUN 02", font=FONT_BOLD, size=16, color=ACCENT, position=(736, 428))
            .text(content="00:42.000", font=FONT_BOLD, size=34, color=CREAM, position=(736, 470))
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
