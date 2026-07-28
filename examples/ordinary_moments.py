"""Make the ordinary impossible to skip.

An 112-second, 16:9 editorial film built from two locally bundled stock clips.
The story uses VideoLayer for the moving image, timed captions for the voice of
the film, and the existing motion/export pipeline for the final deliverables.

Run from the repository root with:

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
SOUNDTRACK = ASSETS / "audio" / "hype_beat.wav"

OUT_DIR = ROOT / "examples"
OUT_MP4 = OUT_DIR / "ordinary_moments.mp4"
OUT_WEBM = OUT_DIR / "ordinary_moments.webm"
OUT_GIF = OUT_DIR / "ordinary_moments_preview.gif"

WIDTH, HEIGHT = 1280, 720
SCENE_DURATION = 14.0
VIDEO_END = 7.0
INK = "#080A0E"
WHITE = "#F5F5F7"
MUTED = "#D6D8DE"
ACCENT = "#FFB454"

SCENES = (
    ("ordinary-sunrise.mp4", "BEFORE THE WORLD WAKES", "Someone starts."),
    ("ordinary-coffee.mp4", "THE WORK LOOKS ORDINARY", "The effort is not."),
    ("ordinary-sunrise.mp4", "MOST MOMENTS", "Do not announce themselves."),
    ("ordinary-coffee.mp4", "THEY HAPPEN", "Between the big moments."),
    ("ordinary-sunrise.mp4", "A FRAME", "Can hold a feeling."),
    ("ordinary-coffee.mp4", "A CAPTION", "Can make it impossible to miss."),
    ("ordinary-sunrise.mp4", "MAKE THE ORDINARY", "Impossible to skip."),
    ("ordinary-coffee.mp4", "DESIGN ONCE", "EXPORT EVERYWHERE."),
)


def build_deck() -> Deck:
    """Build the complete human-first VideoLayer showcase."""
    deck = Deck(WIDTH, HEIGHT)
    transitions = (
        tr.Cut(advance_after=SCENE_DURATION),
        tr.Fade(duration=0.6, advance_after=SCENE_DURATION - 0.6),
        tr.Wipe(direction="left", duration=0.6, advance_after=SCENE_DURATION - 0.6),
        tr.Cut(advance_after=SCENE_DURATION),
        tr.Fade(duration=0.6, advance_after=SCENE_DURATION - 0.6),
        tr.Wipe(direction="up", duration=0.6, advance_after=SCENE_DURATION - 0.6),
        tr.Cut(advance_after=SCENE_DURATION),
        tr.Fade(duration=0.8, advance_after=SCENE_DURATION - 0.8),
    )
    for index, scene in enumerate(SCENES):
        deck = deck.slide(build_scene(index, *scene), transition=transitions[index])
    return deck


def build_scene(index: int, source_name: str, heading: str, line: str) -> Canvas:
    """Build one scene with a moving image and an editorial caption system."""
    source = str(VIDEO_DIR / source_name)
    trim_start = min(1.2, index * 0.18)
    speed = (VIDEO_END - trim_start) / SCENE_DURATION
    caption_color = ACCENT if index in (1, 5, 7) else WHITE
    canvas = Canvas(WIDTH, HEIGHT)
    canvas.video(
        source,
        position=(0, 0),
        width=WIDTH,
        height=HEIGHT,
        fit="cover",
        trim_start=trim_start,
        trim_end=VIDEO_END,
        duration=SCENE_DURATION,
        speed=speed,
        captions=[
            {
                "text": heading,
                "start": 0.45,
                "end": 4.8,
                "position": (76, 92),
                "size": 28,
                "color": MUTED,
                "background": INK,
                "background_opacity": 0.62,
                "padding": (7, 14, 8, 14),
                "border_radius": 4,
            },
            {
                "text": line,
                "start": 5.0,
                "end": 11.8,
                "position": (WIDTH // 2, 590),
                "size": 48,
                "color": caption_color,
                "background": INK,
                "background_opacity": 0.78,
                "padding": (12, 22, 14, 22),
                "border_radius": 6,
            },
        ],
    )
    canvas = canvas.shape(
        shape="rectangle",
        position=(48, 32),
        width=1184,
        height=112,
        color=INK,
        opacity=0.62,
    )
    canvas = canvas.shape(
        shape="rectangle",
        position=(76, 152),
        width=82,
        height=4,
        color=ACCENT,
        animation=Wipe(direction="right", duration=0.5, trigger="after_previous"),
    )
    canvas = canvas.text(
        content=f"{index + 1:02d}  /  ORDINARY MOMENTS",
        font=FONT_BOLD,
        size=20,
        color=WHITE,
        letter_spacing=2,
        position=(76, 52),
        animation=Fade(duration=0.45, trigger="after_previous"),
    )
    return canvas.text(
        content="MAKE IT MATTER",
        font=FONT_BOLD,
        size=18,
        color=WHITE,
        letter_spacing=3,
        position=(WIDTH - 270, 52),
        animation=Fade(duration=0.45, trigger="with_previous"),
    )


def main() -> None:
    """Diagnose and export the production example in three useful formats."""
    deck = build_deck()
    findings = deck.diagnose()
    errors = [finding for finding in findings if finding.severity == "error"]
    if errors:
        raise RuntimeError(f"ordinary_moments has diagnostics: {errors}")

    soundtrack = AudioTrack(path=str(SOUNDTRACK), volume=0.18, loop=True)
    OUT_MP4.write_bytes(deck.to_animated_mp4(fps=24, soundtrack=soundtrack))
    OUT_WEBM.write_bytes(deck.to_webm(fps=24, soundtrack=soundtrack))
    # The VideoLayer already supplies the 14-second timeline; ``hold`` is an
    # additional settled-composition hold, so zero keeps the preview concise.
    OUT_GIF.write_bytes(build_scene(0, *SCENES[0]).to_gif(fps=10, hold=0))
    print(f"Wrote {OUT_MP4}")
    print(f"Wrote {OUT_WEBM}")
    print(f"Wrote {OUT_GIF}")


if __name__ == "__main__":
    main()
