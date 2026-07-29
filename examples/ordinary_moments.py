"""QuickThumb in motion: one composition, every delivery.

This 60-second landscape film is a compact product story rather than a feature
checklist. It starts with a raw idea, composes it on a shared grid, then proves
that the same deterministic timeline can ship as MP4, WebM, and GIF.

Run from the repository root with::

    uv run python examples/ordinary_moments.py

FFmpeg is required for the MP4, WebM, and GIF outputs.
"""

from pathlib import Path

from quickthumb import AudioTrack, Canvas, Deck, Fade, Wipe
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
SOURCE_ENDS = {
    "ordinary-city.mp4": 4.8,
    "ordinary-coffee.mp4": 7.1,
    "ordinary-sunrise.mp4": 7.2,
}
INK = "#101820"
CREAM = "#F5F3ED"
ACCENT = "#D0A464"

# Each source is a different visual beat. The deliberate reuse is non-adjacent
# and only happens when the story needs a familiar visual anchor.
SCENES = (
    (
        "ordinary-city.mp4",
        "01  /  START WITH THE MOMENT",
        "장면 하나로\n시작합니다.",
        "아이디어가 생기는 순간부터, 화면은 움직이기 시작하니까.",
        "아이디어를 움직이세요.",
    ),
    (
        "ordinary-notebook.mp4",
        "02  /  SHAPE THE RAW",
        "필요한 순간만\n남깁니다.",
        "자르고, 맞추고, 배치하면 원본은 메시지가 됩니다.",
        "자르고. 맞추고. 배치합니다.",
    ),
    (
        "ordinary-coffee.mp4",
        "03  /  FIND THE FRAME",
        "정렬된 순간은\n더 오래 남습니다.",
        "영상과 텍스트가 하나의 기준선 위에서 같은 이야기를 합니다.",
        "모든 요소에는 자리가 있습니다.",
    ),
    (
        "ordinary-phone.mp4",
        "04  /  LET WORDS LAND",
        "말은\n정확한 순간에.",
        "자막의 위치와 타이밍까지, 장면 안에서 함께 설계합니다.",
        "타이밍이 메시지를 만듭니다.",
    ),
    (
        "ordinary-sunrise.mp4",
        "05  /  MAKE IT MOVE",
        "움직임은\n기억을 만듭니다.",
        "속도와 전환을 바꿔도, 모든 프레임은 같은 타임라인을 따릅니다.",
        "모든 프레임이 같은 이야기를 합니다.",
    ),
    (
        "ordinary-city.mp4",
        "06  /  KEEP THE RHYTHM",
        "소리도\n화면을 따라갑니다.",
        "영상의 길이와 오디오의 길이가 어긋나지 않도록 함께 흐릅니다.",
        "화면과 소리 사이, 오차 없이.",
    ),
    (
        "ordinary-notebook.mp4",
        "07  /  ONE TIMELINE",
        "하나의 구성.\n세 가지 결과.",
        "피드에는 MP4, 웹에는 WebM, 미리보기에는 GIF로 바로 이어집니다.",
        "MP4  /  WEBM  /  GIF",
    ),
    (
        "ordinary-coffee.mp4",
        "08  /  QUICKTHUMB",
        "한 번 만들고.\n바로 보냅니다.",
        "의도는 하나로, 전달되는 모든 포맷은 정확하게.",
        "한 번의 구성, 모든 포맷",
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
                "start": 1.0,
                "end": 6.5,
                "font": FONT_BOLD,
                # Bottom-panel scenes reserve the lower band for the overlay,
                # so the cue sits just above it instead of being covered.
                "position": (
                    WIDTH // 2,
                    380 if index % 4 == 2 else 630 if index % 2 else 650,
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
    panel_styles = (
        ("left", (48, 104, 510, 468), 0.82),
        ("right", (744, 104, 488, 468), 0.84),
        ("bottom", (0, 420, 1280, 240), 0.82),
        ("top", (0, 0, 1280, 330), 0.76),
    )
    panel_style, (panel_x, panel_y, panel_width, panel_height), panel_opacity = panel_styles[
        index % len(panel_styles)
    ]
    canvas = canvas.shape(
        shape="rectangle",
        position=(panel_x, panel_y),
        width=panel_width,
        height=panel_height,
        color=INK,
        opacity=panel_opacity,
    )
    canvas = canvas.shape(
        shape="rectangle",
        position=(0, 0),
        width=WIDTH,
        height=56,
        color=INK,
        opacity=0.48,
    )
    if panel_style in {"left", "right"}:
        accent_x = panel_x + (panel_width - 8 if panel_style == "right" else 0)
        canvas = canvas.shape(
            shape="rectangle",
            position=(accent_x, panel_y),
            width=8,
            height=panel_height,
            color=ACCENT,
            animation=Wipe(direction="down", duration=0.4),
        )
    else:
        canvas = canvas.shape(
            shape="rectangle",
            position=(72, panel_y + panel_height - 8),
            width=280 if panel_style == "bottom" else 440,
            height=8,
            color=ACCENT,
            animation=Wipe(direction="right", duration=0.4),
        )
    text_x = panel_x + 48
    text_top = panel_y + (88 if panel_style == "top" else 20 if panel_style == "bottom" else 40)
    text_width = panel_width - 96
    canvas = canvas.text(
        content="QUICKTHUMB  /  VIDEO COMPOSITION",
        font=FONT_BOLD,
        size=16,
        color=CREAM,
        letter_spacing=1,
        position=(72, 32),
        animation=Fade(duration=0.2),
    )
    canvas = canvas.text(
        content=eyebrow,
        font=FONT_BOLD,
        size=16,
        color=ACCENT,
        letter_spacing=1,
        position=(text_x, text_top),
        align=("left", "top"),
        max_width=text_width,
        auto_scale=True,
        min_size=12,
    )
    canvas = canvas.text(
        content=headline,
        font=FONT_BOLD,
        size=54 if panel_style in {"left", "right"} else 46,
        color=CREAM,
        line_height=0.98,
        position=(text_x, text_top + 54),
        align=("left", "top"),
        max_width=text_width,
        auto_scale=True,
        min_size=28,
        animation=Wipe(direction="up", duration=0.45, trigger="after_previous"),
    )
    canvas = canvas.text(
        content="—",
        font=FONT_BOLD,
        size=22,
        color=ACCENT,
        position=(text_x, panel_y + panel_height - 78),
        align=("left", "top"),
        animation=Wipe(direction="right", duration=0.3, trigger="after_previous"),
    )
    canvas = canvas.text(
        content=detail,
        font=FONT,
        size=19,
        color=CREAM,
        line_height=1.2,
        position=(text_x, panel_y + panel_height - 48),
        align=("left", "bottom"),
        max_width=text_width,
        auto_scale=True,
        min_size=14,
    )
    return canvas


def main() -> None:
    """Diagnose and export the finished composition."""
    deck = build_deck()
    findings = deck.diagnose()
    errors = [finding for finding in findings if finding.severity == "error"]
    if errors:
        raise RuntimeError(f"ordinary_moments has diagnostics: {errors}")

    soundtrack = AudioTrack(path=str(SOUNDTRACK), volume=0.16, loop=True, fade_out=1.4)
    OUT_MP4.write_bytes(deck.to_animated_mp4(fps=24, soundtrack=soundtrack))
    OUT_WEBM.write_bytes(deck.to_webm(fps=24, soundtrack=soundtrack))
    # VideoLayer supplies the timeline; zero avoids adding a second settled hold.
    OUT_GIF.write_bytes(build_scene(0, *SCENES[0]).to_gif(fps=10, hold=0))
    print(f"Wrote {OUT_MP4}")
    print(f"Wrote {OUT_WEBM}")
    print(f"Wrote {OUT_GIF}")


if __name__ == "__main__":
    main()
