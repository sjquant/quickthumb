"""Render the homepage's thumbnail, sustainability deck, and animated video.

From the repository root:
    python examples/cleaner_future.py --output-dir /tmp/cleaner-future --video

The source images are AI-generated and included in assets/images/cleaner-future.
MP4 needs FFmpeg; add --pptx to export PowerPoint with the pptx extra installed.
Files with the same names in the output directory are replaced.
"""

import argparse
from pathlib import Path

from quickthumb import Canvas, Deck, Fade, VideoOptions, Wipe

ROOT = Path(__file__).resolve().parents[1]
IMAGES = ROOT / "assets/images/cleaner-future"
FONT = str(ROOT / "assets/fonts/Roboto-Regular.ttf")
BOLD = str(ROOT / "assets/fonts/Roboto-Bold.ttf")
HEAVY = str(ROOT / "assets/fonts/Roboto-Black.ttf")
INK = "#101D32"
BLUE = "#155BD7"
MUTED = "#5B6D83"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path.cwd())
    parser.add_argument("--video", action="store_true", help="also render MP4 (requires FFmpeg)")
    parser.add_argument(
        "--pptx", action="store_true", help="also render PPTX (requires pptx extra)"
    )
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    thumbnail().render(str(args.output_dir / "python-for-creators.png"))
    slides = presentation()
    deck = Deck(1280, 720)
    for index, canvas in enumerate(slides, 1):
        canvas.render(str(args.output_dir / f"cleaner-future-{index}.png"))
        deck.slide(canvas)
    deck.render(str(args.output_dir / "cleaner-future.html"))
    if args.pptx:
        deck.render(str(args.output_dir / "cleaner-future.pptx"))
    if args.video:
        motion().render(
            str(args.output_dir / "brighter-planet.mp4"), animation=VideoOptions(fps=12, hold=2)
        )
        motion().render_frame(2).save(args.output_dir / "brighter-planet-poster.png")


def thumbnail() -> Canvas:
    canvas = Canvas(1280, 720).image(str(IMAGES / "creator.png"), (0, 0), 1280, 720, fit="cover")
    canvas.text("PYTHON", position=(720, 110), font=HEAVY, size=118, color="#FFFFFF")
    canvas.text("FOR", position=(722, 250), font=HEAVY, size=92, color="#FFFFFF")
    canvas.shape("rectangle", (710, 380), 515, 132, "#FFD400", rotation=-3)
    canvas.text("CREATORS", position=(733, 399), font=HEAVY, size=88, color="#111923", rotation=-3)
    canvas.text(
        "MAKE MORE WITH CODE",
        position=(738, 585),
        font=BOLD,
        size=25,
        color="#B8C9DF",
        letter_spacing=2,
    )
    return canvas


def presentation() -> list[Canvas]:
    cover = Canvas(1280, 720).background(color="#FFFFFF")
    cover.text("01", position=(70, 65), font=BOLD, size=23, color="#8091A7")
    cover.text(
        "A cleaner\nfuture is\npossible.",
        position=(70, 175),
        font=HEAVY,
        size=74,
        color=INK,
        line_height=1.02,
    )
    cover.text(
        "Technology. People. A healthier planet.",
        position=(72, 460),
        font=FONT,
        size=25,
        color=MUTED,
        max_width=500,
    )
    cover.image(str(IMAGES / "mountains.png"), (700, 62), 520, 570, fit="cover")
    footer(cover, "01")

    opportunity = page("The opportunity", "02")
    opportunity.text(
        "Better decisions.\nA lighter footprint.",
        position=(70, 150),
        font=HEAVY,
        size=64,
        color=INK,
        line_height=1.08,
    )
    opportunity.text(
        "An illustrative view of progress toward a cleaner future.",
        position=(72, 350),
        font=FONT,
        size=25,
        color=MUTED,
        max_width=480,
    )
    for index, height in enumerate((100, 170, 245, 330)):
        opportunity.shape(
            "rectangle",
            (720 + index * 105, 550 - height),
            65,
            height,
            BLUE if index == 3 else "#A9C9E8",
        )
    opportunity.text(
        "ILLUSTRATIVE DATA", position=(720, 580), font=BOLD, size=15, color=MUTED, letter_spacing=1
    )

    vision = page("A more sustainable tomorrow", "03")
    vision.text(
        "Small changes.\nLasting impact.",
        position=(70, 170),
        font=HEAVY,
        size=66,
        color=INK,
        line_height=1.08,
    )
    vision.text(
        "Build systems that work for people and the planet.",
        position=(72, 390),
        font=FONT,
        size=26,
        color=MUTED,
        max_width=470,
    )
    vision.image(str(IMAGES / "mountains.png"), (700, 125), 510, 420, fit="cover")

    close = Canvas(1280, 720).background(color="#0A1C35")
    close.text("Thank you.", position=(80, 220), font=HEAVY, size=108, color="#FFFFFF")
    close.text(
        "Let's build a brighter future together.",
        position=(84, 380),
        font=FONT,
        size=31,
        color="#BBD2EB",
    )
    close.image(str(IMAGES / "mountains.png"), (785, 0), 495, 720, fit="cover")
    return [cover, opportunity, vision, close]


def page(title: str, number: str) -> Canvas:
    canvas = Canvas(1280, 720).background(color="#FFFFFF")
    canvas.text(title.upper(), position=(70, 62), font=BOLD, size=20, color=BLUE, letter_spacing=2)
    footer(canvas, number)
    return canvas


def footer(canvas: Canvas, number: str) -> None:
    canvas.shape("rectangle", (70, 658), 1140, 2, "#DFE7EF")
    canvas.text("CLEANER FUTURE  /  CONCEPT", position=(70, 674), font=BOLD, size=14, color=MUTED)
    canvas.text(
        number, position=(1208, 674), align=("right", "top"), font=BOLD, size=14, color=MUTED
    )


def motion() -> Canvas:
    canvas = Canvas(1280, 720).image(str(IMAGES / "earth.png"), (0, 0), 1280, 720, fit="cover")
    canvas.text(
        "A brighter\nplanet.",
        position=(78, 240),
        font=HEAVY,
        size=90,
        color="#FFFFFF",
        line_height=1.02,
        animation=Fade(duration=1),
    )
    canvas.shape(
        "rectangle",
        (83, 490),
        160,
        7,
        "#62B7FF",
        animation=Wipe(direction="right", duration=0.8, trigger="after_previous"),
    )
    canvas.text(
        "IDEAS IN MOTION",
        position=(82, 530),
        font=BOLD,
        size=20,
        color="#C2DDFA",
        letter_spacing=2,
        animation=Fade(duration=0.5, trigger="after_previous"),
    )
    return canvas


if __name__ == "__main__":
    main()
