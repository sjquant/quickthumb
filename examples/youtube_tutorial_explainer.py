"""
YouTube Tutorial / Explainer Thumbnail

Clean numbered-steps layout on a gradient background:
- Deep blue gradient (no background photo needed)
- "HOW TO" badge using shape + text
- Large two-tone headline with method chaining
- Three numbered step badges built with a helper function
- Vertical divider separating headline from steps
"""

import os

from quickthumb import Canvas, LinearGradient, Shadow, Stroke, TextPart

FILE_DIR = os.path.dirname(__file__)
ASSETS_DIR = os.path.join(FILE_DIR, "..", "assets")
OUTPUT_PATH = os.path.join(FILE_DIR, "youtube_tutorial_explainer.png")

os.environ["QUICKTHUMB_FONT_DIR"] = os.path.join(ASSETS_DIR, "fonts")
os.environ["QUICKTHUMB_DEFAULT_FONT"] = "Roboto"

BLUE = "#3B82F6"
DARK = "#0F172A"


def main():
    """Render the tutorial thumbnail."""
    canvas = (
        Canvas(1280, 720)
        # Deep blue diagonal gradient background
        .background(
            gradient=LinearGradient(
                angle=135,
                stops=[("#0F172A", 0.0), ("#1E3A5F", 0.6), ("#0F172A", 1.0)],
            )
        )
        # Subtle left-edge accent glow
        .background(
            gradient=LinearGradient(
                angle=90,
                stops=[(BLUE + "22", 0.0), (BLUE + "00", 0.55)],
            )
        )
        # "HOW TO" label badge
        .shape(
            shape="rectangle",
            position=(52, 52),
            width=168,
            height=48,
            color=BLUE,
            border_radius=6,
            effects=[Shadow(offset_x=0, offset_y=4, color="#00000055", blur_radius=8)],
        )
        .text(
            content="HOW TO",
            size=22,
            color="#FFFFFF",
            weight=900,
            letter_spacing=2,
            position=(136, 76),
            align=("center", "middle"),
        )
        # Two-tone headline
        .text(
            content=[
                TextPart(text="MASTER\n", color="#FFFFFF", weight=900),
                TextPart(text="PYTHON", color="#60A5FA", weight=900),
            ],
            size=112,
            line_height=0.95,
            position=(52, 135),
            align=("left", "top"),
            effects=[
                Stroke(width=1, color=DARK),
                Shadow(offset_x=0, offset_y=7, color="#00000088", blur_radius=12),
            ],
        )
        # Subtitle
        .text(
            content="in 30 days — from scratch",
            size=32,
            color="#94A3B8",
            weight=500,
            position=(52, 418),
            effects=[Shadow(offset_x=0, offset_y=3, color="#00000066", blur_radius=6)],
        )
        # Thin vertical divider between headline area and steps
        .shape(
            shape="rectangle",
            position=(696, 148),
            width=2,
            height=390,
            color="#3B82F630",
            border_radius=2,
        )
    )

    add_step(canvas, 1, "Learn the basics", 754, 210)
    add_step(canvas, 2, "Build real projects", 754, 330)
    add_step(canvas, 3, "Ship and deploy", 754, 450)

    canvas.outline(width=4, color=BLUE)
    canvas.render(OUTPUT_PATH)

    print(f"✓ Tutorial / explainer thumbnail created: {OUTPUT_PATH}")
    print("  Swap the step labels and headline text for any how-to topic.")


def add_step(canvas, number, label, x, y):
    """Render a numbered circular badge followed by a step label."""
    canvas.shape(
        shape="rectangle",
        position=(x - 36, y - 46),
        width=478,
        height=92,
        color="#FFFFFF0A",
        border_radius=18,
        effects=[Stroke(width=1, color="#FFFFFF14")],
    )
    canvas.shape(
        shape="ellipse",
        position=(x, y),
        width=58,
        height=58,
        color=BLUE,
        align=("center", "middle"),
        effects=[Shadow(offset_x=0, offset_y=5, color="#00000055", blur_radius=10)],
    )
    canvas.text(
        content=str(number),
        size=30,
        color="#FFFFFF",
        weight=900,
        position=(x, y),
        align=("center", "middle"),
    )
    canvas.text(
        content=label,
        size=32,
        color="#E2E8F0",
        weight=700,
        position=(x + 44, y),
        align=("left", "middle"),
        effects=[Shadow(offset_x=0, offset_y=3, color="#00000088", blur_radius=6)],
    )
    return canvas


if __name__ == "__main__":
    main()
