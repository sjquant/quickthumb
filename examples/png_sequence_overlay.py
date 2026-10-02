"""Export a transparent lower third as independent, silent RGBA8 PNG frames.

Run from the repository root (the destination must not already exist):
    uv run python examples/png_sequence_overlay.py
"""

from pathlib import Path

from quickthumb import Canvas, Fade, PngSequenceOptions

ROOT = Path(__file__).resolve().parents[1]


def build_scene() -> Canvas:
    entrance = Fade(duration=0.4)
    return (
        Canvas(240, 90)
        .shape("rectangle", (12, 42), 216, 36, "#142839D0", border_radius=5, animation=entrance)
        .shape("rectangle", (12, 42), 4, 36, "#45E4C1", animation=entrance)
        .text(
            "ALEX MORGAN",
            position=(25, 49),
            size=14,
            font=str(ROOT / "assets/fonts/Roboto-Medium.ttf"),
            color="#FFFFFF",
            animation=entrance,
        )
    )


if __name__ == "__main__":
    output = ROOT / "examples/output"
    output.mkdir(exist_ok=True)
    result = build_scene().export_png_sequence(
        output / "png_sequence_overlay",
        options=PngSequenceOptions(fps=24, hold=2, quality="high", workers=2),
    )
    print(f"{result.frame_count} frames; {result.duration:g}s; {result.manifest_path}")
