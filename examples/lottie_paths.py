"""Static native Lottie curves; unsupported paints and clipping fail explicitly."""

from quickthumb import Canvas, LottieOptions


def build_canvas() -> Canvas:
    return (
        Canvas(240, 180)
        .path(
            "M8 40Q40 0 72 40T136 40L136 68H8Z",
            (5, 5),
            140,
            80,
            "#159A8C",
            view_box=(0, 0, 140, 80),
            id="quadratic",
        )
        .path(
            "M12 40A28 28 25 1 1 68 40A28 28 25 1 1 12 40Z M30 30H50V50H30Z",
            (150, 5),
            80,
            80,
            "#E75A4080",
            view_box=(0, 0, 80, 80),
            id="arc-hole",
        )
        .path(
            "M8 25C8 8 48 8 48 25S88 42 88 25",
            (5, 105),
            120,
            60,
            None,
            view_box=(0, 0, 100, 50),
            stroke="#3757A0",
            stroke_width=3,
            line_cap="round",
            id="cubic",
        )
        .path(
            "M12 32C12 4 52 4 52 32C52 60 12 60 12 32Z",
            (160, 105),
            64,
            64,
            "#ABCDEF80",
            view_box=(0, 0, 64, 64),
            stroke="#3757A0",
            stroke_width=2,
            opacity=0.6,
            id="closed",
        )
    )


if __name__ == "__main__":
    build_canvas().export("paths.lot", animation=LottieOptions(fps=30, hold=3))
