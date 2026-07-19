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
            position=(704, 0),
            width=576,
            height=720,
            color=BLUE,
        )
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
            content="PYTHON  /  RUN",
            size=16,
            color="#FFFFFFB8",
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
                TextPart(text="PYTHON.", color=BLUE, weight=800),
            ],
            size=148,
            line_height=0.88,
            letter_spacing=-4,
            position=(50, 136),
        )
        .text(
            content="in 30 days — from scratch",
            size=27,
            color=GRAY,
            weight=500,
            position=(58, 474),
        )
        .text(
            content="BUILD  /  RUN  /  SHIP",
            size=15,
            color="#A1A1A6",
            weight=700,
            letter_spacing=3,
            position=(60, 646),
        )
        .text(
            content=[
                TextPart(text="def ", color="#FFFFFFB8", weight=500),
                TextPart(text="ship", color="#1D1D1F", weight=800),
                TextPart(text="(idea):\n", color="#FFFFFF", weight=500),
                TextPart(text="    build(idea)\n", color="#FFFFFF", weight=500),
                TextPart(text="    return ", color="#FFFFFFB8", weight=500),
                TextPart(text='"LIVE"', color="#1D1D1F", weight=800),
            ],
            size=42,
            line_height=1.55,
            position=(744, 168),
        )
        .shape(
            shape="rectangle",
            position=(744, 474),
            width=480,
            height=1,
            color="#FFFFFF66",
        )
        .text(
            content=">>>  SHIPPED / LIVE",
            size=36,
            color="#FFFFFF",
            weight=700,
            letter_spacing=1,
            position=(744, 510),
        )
    )

    canvas.render(OUTPUT_PATH)

    print(f"✓ Tutorial / explainer thumbnail created: {OUTPUT_PATH}")
    print("  Swap the step labels and headline text for any how-to topic.")


if __name__ == "__main__":
    main()
