"""Self-contained static glyph outlines, retaining the resolved font and layout."""

from quickthumb import Canvas, LottieOptions


def build_canvas() -> Canvas:
    return (
        Canvas(640, 280)
        .text(
            "O",
            position=(70, 75),
            size=80,
            align="center",
            color="#3757A0",
            opacity=0.7,
            id="default-face",
        )
        .text(
            "B O8",
            position=(360, 75),
            size=80,
            font="assets/fonts/NotoSans-Bold.ttf",
            letter_spacing=6,
            align="center",
            color="#159A8C",
            opacity=0.5,
            id="spaced-holes",
        )
        .text(
            "Agyp",
            position=(600, 235),
            size=76,
            font="assets/fonts/NotoSerif-Italic.ttf",
            letter_spacing=5,
            align="bottom-right",
            color="#C6496D",
            opacity=0.8,
            id="descenders",
        )
    )


if __name__ == "__main__":
    build_canvas().export("text.lot", animation=LottieOptions(fps=30, hold=3))
