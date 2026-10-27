"""Native, asset-free static Lottie; see docs/exports.md for the bounded subset."""

from quickthumb import Canvas, LottieOptions


def build_canvas() -> Canvas:
    return (
        Canvas(240, 160)
        .background(color="#F8F7F3")
        .shape("rectangle", (12, 12), 72, 40, "#159A8C", id="card")
        .shape("ellipse", (105, 15), 50, 38, "#E75A4080", opacity=0.75, id="ellipse")
        .shape("triangle", (175, 12), 45, 40, "#3757A0", id="triangle")
        .path(
            "M4 4H52V44H4Z M16 16V32H40V16Z",
            (12, 80),
            84,
            66,
            "#159A8C",
            view_box=(0, 0, 56, 44),
            id="hole",
        )
        .path(
            "M8 20H52",
            (125, 95),
            90,
            45,
            None,
            view_box=(0, 0, 60, 30),
            stroke="#3757A0",
            stroke_width=3,
            line_cap="round",
            id="stroke",
        )
    )


if __name__ == "__main__":
    build_canvas().export("scene.lot", animation=LottieOptions(fps=30, hold=3))
