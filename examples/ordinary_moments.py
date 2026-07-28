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
SCENE_DURATION = 7.5
VIDEO_END = 7.8
VIDEO_POSITION = (72, 174)
VIDEO_SIZE = (720, 405)
SOURCE_ENDS = {
    "ordinary-city.mp4": 4.8,
    "ordinary-coffee.mp4": 7.1,
    "ordinary-sunrise.mp4": 7.2,
}
SAFE_X, SAFE_RIGHT = 72, 1208
INK = "#191817"
SURFACE = "#F3EFE7"
TEXT = "#211F1D"
CREAM = "#F8F3E9"
MUTED = "#5F5852"
ACCENT = "#E45B45"
RULE = "#D8D0C5"

# Each source is a different visual beat. The deliberate reuse is non-adjacent
# and only happens when the story needs a familiar visual anchor.
SCENES = (
    (
        "ordinary-city.mp4",
        "01  /  아이디어",
        "한 번 만든 장면.\n어디서나.",
        "화면이 달라도, 이야기는 흔들리지 않게.",
        "이야기부터 시작합니다.",
    ),
    (
        "ordinary-notebook.mp4",
        "02  /  원본",
        "원본을 다듬고.\n의도를 남기고.",
        "필요한 순간만 남겨, 장면의 힘을 키웁니다.",
        "자르고. 맞추고. 배치합니다.",
    ),
    (
        "ordinary-coffee.mp4",
        "03  /  구성",
        "정렬이\n완성도를 만듭니다.",
        "영상과 텍스트가 같은 기준선 위에 놓입니다.",
        "모든 요소에는 자리가 있습니다.",
    ),
    (
        "ordinary-phone.mp4",
        "04  /  자막",
        "자막은\n정확한 순간에.",
        "말이 이미지보다 늦게 도착하지 않도록.",
        "타이밍이 메시지를 만듭니다.",
    ),
    (
        "ordinary-sunrise.mp4",
        "05  /  타임라인",
        "움직임은\n기억에 남게.",
        "자르고, 늦추고, 전환해도 타임라인은 정확합니다.",
        "모든 프레임이 같은 이야기를 합니다.",
    ),
    (
        "ordinary-city.mp4",
        "06  /  사운드",
        "소리는\n화면을 따라가고.",
        "영상의 길이가 달라져도 리듬은 흐트러지지 않습니다.",
        "화면과 소리 사이, 오차 없이.",
    ),
    (
        "ordinary-notebook.mp4",
        "07  /  결과물",
        "하나의 구성.\n세 가지 결과.",
        "피드에는 MP4, 웹에는 WebM, 미리보기에는 GIF.",
        "MP4  /  WEBM  /  GIF",
    ),
    (
        "ordinary-coffee.mp4",
        "08  /  QUICKTHUMB",
        "한 번 만들고.\n모두에게 보냅니다.",
        "구성은 한 번, 전달은 어디서나.",
        "의도를 담아, 바로 보냅니다.",
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
    )
    deck = Deck(WIDTH, HEIGHT)
    for index, scene in enumerate(SCENES):
        deck = deck.slide(build_scene(index, *scene), transition=transitions[index])
    return deck


def build_scene(
    index: int,
    source_name: str,
    eyebrow: str,
    headline: str,
    detail: str,
    caption: str,
) -> Canvas:
    """Build one scene on the shared 72px editorial grid."""
    source = str(VIDEO_DIR / source_name)
    trim_start = min(0.8, index * 0.11)
    # Source clips have different durations; slow shorter shots down instead
    # of asking the exporter to read beyond a validated media boundary.
    trim_end = SOURCE_ENDS.get(source_name, VIDEO_END)
    speed = (trim_end - trim_start) / SCENE_DURATION
    canvas = Canvas(WIDTH, HEIGHT).background(color=INK)
    canvas.video(
        source,
        position=VIDEO_POSITION,
        width=VIDEO_SIZE[0],
        height=VIDEO_SIZE[1],
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
                # VideoCaption positions are center anchors, not top-left corners.
                "font": FONT_BOLD,
                "position": (
                    VIDEO_POSITION[0] + VIDEO_SIZE[0] // 2,
                    VIDEO_POSITION[1] + VIDEO_SIZE[1] - 42,
                ),
                "size": 20,
                "color": CREAM,
                "background": INK,
                "background_opacity": 0.82,
                "padding": (6, 12, 7, 12),
                "border_radius": 4,
            }
        ],
    )
    canvas = canvas.shape(
        shape="rectangle",
        position=(SAFE_X, 32),
        width=1136,
        height=72,
        color=SURFACE,
        opacity=1.0,
    )
    canvas = canvas.shape(
        shape="rectangle",
        position=(SAFE_X, 104),
        width=1136,
        height=2,
        color=RULE,
    )
    canvas = canvas.text(
        content="QUICKTHUMB  /  VIDEO COMPOSITION",
        font=FONT_BOLD,
        size=18,
        color=TEXT,
        letter_spacing=1,
        position=(SAFE_X + 24, 57),
        animation=Fade(duration=0.25, trigger="after_previous"),
    )
    canvas = canvas.text(
        content=f"{index + 1:02d}  /  08",
        font=FONT_BOLD,
        size=18,
        color=ACCENT,
        letter_spacing=1,
        position=(SAFE_RIGHT - 84, 57),
        animation=Fade(duration=0.25, trigger="with_previous"),
    )
    canvas = canvas.shape(
        shape="rectangle",
        position=(840, 174),
        width=368,
        height=405,
        color=SURFACE,
        opacity=1.0,
    )
    canvas = canvas.text(
        content=eyebrow,
        font=FONT_BOLD,
        size=18,
        color=ACCENT,
        letter_spacing=2,
        position=(1024, 206),
        align=("center", "top"),
    )
    canvas = canvas.text(
        content=headline,
        font=FONT_BOLD,
        size=42,
        color=TEXT,
        line_height=0.98,
        letter_spacing=-1,
        position=(1024, 256),
        align=("center", "top"),
        max_width=300,
        auto_scale=True,
        min_size=30,
    )
    canvas = canvas.text(
        content="—",
        font=FONT_BOLD,
        size=24,
        color=ACCENT,
        position=(1024, 410),
        align=("center", "top"),
        animation=Wipe(direction="right", duration=0.3, trigger="after_previous"),
    )
    canvas = canvas.text(
        content=detail,
        font=FONT,
        size=20,
        color=MUTED,
        line_height=1.2,
        position=(1024, 446),
        align=("center", "top"),
        max_width=292,
        auto_scale=True,
        min_size=17,
    )
    return canvas.text(
        content="한 번의 구성, 모든 포맷",
        font=FONT_BOLD,
        size=18,
        color=MUTED,
        letter_spacing=1,
        position=(1024, 548),
        align=("center", "top"),
    )


def main() -> None:
    """Diagnose and export the finished composition."""
    deck = build_deck()
    findings = deck.diagnose()
    errors = [finding for finding in findings if finding.severity == "error"]
    if errors:
        raise RuntimeError(f"ordinary_moments has diagnostics: {errors}")

    soundtrack = AudioTrack(path=str(SOUNDTRACK), volume=0.16, loop=True)
    OUT_MP4.write_bytes(deck.to_animated_mp4(fps=24, soundtrack=soundtrack))
    OUT_WEBM.write_bytes(deck.to_webm(fps=24, soundtrack=soundtrack))
    # VideoLayer supplies the timeline; zero avoids adding a second settled hold.
    OUT_GIF.write_bytes(build_scene(0, *SCENES[0]).to_gif(fps=10, hold=0))
    print(f"Wrote {OUT_MP4}")
    print(f"Wrote {OUT_WEBM}")
    print(f"Wrote {OUT_GIF}")


if __name__ == "__main__":
    main()
