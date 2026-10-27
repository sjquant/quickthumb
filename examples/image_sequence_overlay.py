"""Export a lower third as PNG, matted JPEG and lossless WebP animation frames.

Run from the repository root (the destination must not already exist):
    uv run python examples/image_sequence_overlay.py
"""

from pathlib import Path

from quickthumb import Canvas, Fade, ImageSequenceOptions

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
    scene = build_scene()
    options = ImageSequenceOptions(fps=24, hold=2, render_quality="high", workers=2)
    for result in [
        scene.export_image_sequence(output / "image_sequence_overlay_png", options=options),
        scene.export_image_sequence(
            output / "image_sequence_overlay_jpeg",
            format="jpeg",
            quality=90,
            matte="white",
            options=options,
        ),
        scene.export_image_sequence(
            output / "image_sequence_overlay_webp",
            format="webp",
            lossless=True,
            options=options,
        ),
    ]:
        print(f"{result.encoding}: {result.frame_count} frames; {result.manifest_path}")
