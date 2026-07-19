"""
YouTube Tutorial / Explainer Thumbnail

Focused curriculum layout built from a single headline and a structured step list:
- Near-black background with one system-blue accent
- Large two-tone headline as the only hero element
- Three steps separated by rules instead of cards or badges
- Compact metadata aligned to a consistent grid
"""

import os

from quickthumb import Canvas, TextPart

FILE_DIR = os.path.dirname(__file__)
ASSETS_DIR = os.path.join(FILE_DIR, "..", "assets")
OUTPUT_PATH = os.path.join(FILE_DIR, "youtube_tutorial_explainer.png")

os.environ["QUICKTHUMB_FONT_DIR"] = os.path.join(ASSETS_DIR, "fonts")
os.environ["QUICKTHUMB_DEFAULT_FONT"] = "Roboto"

BLUE = "#0A84FF"
WHITE = "#F5F5F7"
GRAY = "#86868B"


def main():
    """Render the tutorial thumbnail."""
    canvas = (
        Canvas(1280, 720)
        .background(color="#000000")
        .shape(
            shape="rectangle",
            position=(56, 58),
            width=10,
            height=10,
            color=BLUE,
        )
        .text(
            content="HOW TO  /  PYTHON",
            size=17,
            color="#A1A1A6",
            weight=700,
            letter_spacing=3,
            position=(88, 52),
        )
        .text(
            content="30 DAYS  /  FROM SCRATCH",
            size=16,
            color=GRAY,
            weight=700,
            letter_spacing=2,
            position=(1224, 52),
            align=("right", "top"),
        )
        .shape(
            shape="rectangle",
            position=(56, 96),
            width=1168,
            height=1,
            color="#FFFFFF33",
        )
        .text(
            content=[
                TextPart(text="MASTER\n", color=WHITE, weight=700),
                TextPart(text="PYTHON", color=BLUE, weight=700),
            ],
            size=128,
            line_height=0.94,
            letter_spacing=-3,
            position=(56, 150),
        )
        .text(
            content="in 30 days — from scratch",
            size=27,
            color=GRAY,
            weight=500,
            position=(60, 445),
        )
        .text(
            content="LEARN  /  BUILD  /  SHIP",
            size=15,
            color="#A1A1A6",
            weight=700,
            letter_spacing=3,
            position=(60, 646),
        )
    )

    add_step(canvas, "01", "Learn the basics", 760, 174)
    add_step(canvas, "02", "Build real projects", 760, 298)
    add_step(canvas, "03", "Ship and deploy", 760, 422)

    canvas.render(OUTPUT_PATH)

    print(f"✓ Tutorial / explainer thumbnail created: {OUTPUT_PATH}")
    print("  Swap the step labels and headline text for any how-to topic.")


def add_step(canvas, number, label, x, y):
    """Render one curriculum row on the shared grid."""
    canvas.shape(
        shape="rectangle",
        position=(x, y),
        width=464,
        height=1,
        color="#FFFFFF33",
    )
    canvas.text(
        content=number,
        size=17,
        color=BLUE,
        weight=700,
        letter_spacing=2,
        position=(x, y + 30),
    )
    canvas.text(
        content=label,
        size=32,
        color=WHITE,
        weight=600,
        position=(x + 70, y + 20),
    )
    return canvas


if __name__ == "__main__":
    main()
