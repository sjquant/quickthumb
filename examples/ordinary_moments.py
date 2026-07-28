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
FONT = str(ASSETS / "fonts" / "NotoSans-Regular.ttf")
FONT_BOLD = str(ASSETS / "fonts" / "NotoSans-Bold.ttf")
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
INK = "#080A0E"
SURFACE = "#11161D"
SURFACE_2 = "#1B222C"
WHITE = "#F5F5F7"
MUTED = "#AAB2BE"
ACCENT = "#FFB454"
RULE = "#303A48"

# Each source is a different visual beat. The deliberate reuse is non-adjacent
# and only happens when the story needs a familiar visual anchor.
SCENES = (
    (
        "ordinary-city.mp4",
        "THE PROBLEM",
        "ONE IDEA.\nEVERYWHERE.",
        "A story should not be rebuilt for every screen.",
        "START WITH THE STORY.",
    ),
    (
        "ordinary-notebook.mp4",
        "THE SOURCE",
        "MAKE THE\nFRAME YOURS.",
        "Trim the moment. Keep the intent.",
        "TRIM. FIT. PLACE.",
    ),
    (
        "ordinary-coffee.mp4",
        "THE COMPOSITION",
        "LAYOUT THAT\nHOLDS TOGETHER.",
        "A safe grid keeps every element in its lane.",
        "EVERY PIXEL HAS A JOB.",
    ),
    (
        "ordinary-phone.mp4",
        "THE VOICE",
        "CAPTIONS\nON CUE.",
        "Words arrive with the image, not after it.",
        "MAKE IT LAND.",
    ),
    (
        "ordinary-sunrise.mp4",
        "THE TIMELINE",
        "MOTION WITH\nA MEMORY.",
        "Trim, speed, and transitions stay deterministic.",
        "SAME TIMELINE. EVERY FRAME.",
    ),
    (
        "ordinary-city.mp4",
        "THE HANDOFF",
        "AUDIO THAT\nFOLLOWS.",
        "The soundtrack respects the visual duration.",
        "NO DRIFT. NO SURPRISES.",
    ),
    (
        "ordinary-notebook.mp4",
        "THE OUTPUT",
        "ONE BUILD.\nTHREE DELIVERIES.",
        "MP4 for the feed. WebM for the web. GIF for the preview.",
        "MP4  /  WEBM  /  GIF",
    ),
    (
        "ordinary-coffee.mp4",
        "QUICKTHUMB",
        "BUILD ONCE.\nSHIP WITH CONFIDENCE.",
        "A finished composition, ready for everywhere.",
        "COMPOSE WITH INTENT.",
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
    canvas = canvas.shape(
        shape="rectangle",
        position=(56, 158),
        width=752,
        height=437,
        color=SURFACE,
        opacity=1.0,
    )
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
                "position": (VIDEO_POSITION[0] + 24, VIDEO_POSITION[1] + VIDEO_SIZE[1] - 42),
                "size": 20,
                "color": WHITE,
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
        color=WHITE,
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
        position=(872, 206),
        animation=Fade(duration=0.3, trigger="after_previous"),
    )
    canvas = canvas.text(
        content=headline,
        font=FONT_BOLD,
        size=42,
        color=WHITE,
        line_height=0.98,
        letter_spacing=-1,
        position=(872, 256),
        max_width=300,
        auto_scale=True,
        min_size=30,
        animation=Fade(duration=0.4, trigger="with_previous"),
    )
    canvas = canvas.text(
        content="—",
        font=FONT_BOLD,
        size=24,
        color=ACCENT,
        position=(872, 410),
        animation=Wipe(direction="right", duration=0.3, trigger="after_previous"),
    )
    canvas = canvas.text(
        content=detail,
        font=FONT,
        size=20,
        color=MUTED,
        line_height=1.2,
        position=(872, 446),
        max_width=292,
        auto_scale=True,
        min_size=17,
        animation=Fade(duration=0.35, trigger="with_previous"),
    )
    return canvas.text(
        content="DETERMINISTIC BY DESIGN",
        font=FONT_BOLD,
        size=18,
        color=MUTED,
        letter_spacing=1,
        position=(872, 548),
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
