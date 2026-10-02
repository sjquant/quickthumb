"""A transparent lower third for compositing over footage in a WebM-alpha or ProRes editor.

Run from the repository root:
    uv run python examples/transparent_lower_third.py
"""

from pathlib import Path

from quickthumb import Canvas, Fade, VideoOptions

ROOT = Path(__file__).resolve().parents[1]
FONT = str(ROOT / "assets/fonts/Roboto-Medium.ttf")


def build_scene() -> Canvas:
    canvas = Canvas(480, 180)
    entrance = Fade(duration=0.8)
    canvas.shape("rectangle", (24, 86), 400, 72, "#142839D0", border_radius=8, animation=entrance)
    canvas.shape("rectangle", (24, 86), 6, 72, "#45E4C1", animation=entrance)
    canvas.text(
        "ALEX MORGAN",
        position=(46, 99),
        size=23,
        font=FONT,
        color="#FFFFFF",
        animation=entrance,
    )
    canvas.text(
        "DESIGN DIRECTOR",
        position=(46, 131),
        size=12,
        font=FONT,
        color="#B5D8E5",
        animation=entrance,
    )
    return canvas


if __name__ == "__main__":
    output = ROOT / "examples/output"
    output.mkdir(exist_ok=True)
    build_scene().render(
        str(output / "transparent_lower_third.webm"),
        animation=VideoOptions(transparent=True, fps=24, quality="high", workers=2),
    )

    build_scene().render(
        str(output / "transparent_lower_third.mov"),
        animation=VideoOptions(transparent=True, fps=24, quality="high", workers=2),
    )
