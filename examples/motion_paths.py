"""Curved infographic motion with arc-distance sampling and tangent orientation.

Run from the repository root: uv run python examples/motion_paths.py
GIF/PNG include animated color. HTML uses a separate geometry-only scene,
because adding a ColorTrack would make its whole animation fall back to static.
"""

from pathlib import Path

from quickthumb import (
    AnimationSpec,
    Canvas,
    ColorTrack,
    GifOptions,
    KeyframeSpec,
    PositionKeyframeSpec,
    PositionTrack,
    TimingSpec,
)

ROOT = Path(__file__).resolve().parents[1]
FONT = str(ROOT / "assets/fonts/Roboto-Medium.ttf")
ORIGIN = (76, 240)


def path_keyframes() -> list[PositionKeyframeSpec]:
    """Offsets from the arrow's authored position; handles are relative too."""
    return [
        PositionKeyframeSpec(time=0, value=(0, 0), out_tangent=(70, -130)),
        PositionKeyframeSpec(time=2, value=(244, -88), in_tangent=(-75, 0), out_tangent=(75, 0)),
        PositionKeyframeSpec(time=4, value=(488, 0), in_tangent=(-70, -130)),
    ]


def add_route(canvas: Canvas, keys: list[PositionKeyframeSpec]) -> None:
    """Draw a static dotted guide from the same cubic control points."""
    for left, right in zip(keys, keys[1:], strict=False):
        outgoing = left.out_tangent or (0, 0)
        incoming = right.in_tangent or (0, 0)
        controls = (
            left.value,
            tuple(p + h for p, h in zip(left.value, outgoing, strict=True)),
            tuple(p + h for p, h in zip(right.value, incoming, strict=True)),
            right.value,
        )
        for index in range(31):
            t = index / 30
            weights = ((1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t**2, t**3)
            x, y = (
                sum(weight * point[axis] for weight, point in zip(weights, controls, strict=True))
                for axis in (0, 1)
            )
            canvas.shape(
                "ellipse", (round(ORIGIN[0] + x) - 2, round(ORIGIN[1] + y) - 2), 4, 4, "#647887"
            )


def build_scene(*, animate_color: bool = True) -> Canvas:
    canvas = Canvas(640, 360).background(color="#101820")
    canvas.text("FROM SIGNAL TO STORY", position=(36, 26), font=FONT, size=32, color="#F1F5F9")
    canvas.text(
        "A curved route, a changing state"
        if animate_color
        else "A curved route with tangent heading",
        position=(36, 70),
        font=FONT,
        size=19,
        color="#B6C5D0",
    )
    keys = path_keyframes()
    add_route(canvas, keys)
    for key in keys:
        x, y = ORIGIN[0] + key.value[0], ORIGIN[1] + key.value[1]
        canvas.shape("ellipse", (x - 5, y - 5), 10, 10, "#F1F5F9")
    for label, position in (
        ("1  COLLECT", (36, 276)),
        ("2  REFINE", (273, 192)),
        ("3  DELIVER", (514, 276)),
    ):
        canvas.text(label, position=position, font=FONT, size=17, color="#F1F5F9")
    canvas.text(
        "4 seconds / linear distance / tangent heading",
        position=(36, 325),
        font=FONT,
        size=16,
        color="#B6C5D0",
    )

    path = PositionTrack(keyframes=keys, auto_orient=True)
    color = ColorTrack(
        keyframes=[
            KeyframeSpec(time=0, value="#FF8866"),
            KeyframeSpec(time=2, value="#FFCD66"),
            KeyframeSpec(time=4, value="#42CEB7"),
        ]
    )
    motion = AnimationSpec.timeline(
        *([path, color] if animate_color else [path]),
        timing=TimingSpec(duration=4, trigger="after_previous"),
        easing="linear",
    )
    # Right-facing artwork: auto_orient replaces its animated rotation with
    # the tangent angle. Its centre begins at ORIGIN; positions are offsets.
    canvas.shape(
        "polygon",
        (ORIGIN[0] - 18, ORIGIN[1] - 12),
        36,
        24,
        "#FF8866",
        points=[(0, 0.15), (0.55, 0.15), (0.55, 0), (1, 0.5), (0.55, 1), (0.55, 0.85), (0, 0.85)],
        animation=motion,
    )
    return canvas


def main() -> None:
    output = ROOT / "examples/output"
    output.mkdir(parents=True, exist_ok=True)
    scene = build_scene()
    scene.render(str(output / "motion_paths.gif"), animation=GifOptions(fps=24))
    scene.render_frame(1).save(output / "motion_paths.png")
    geometry_scene = build_scene(animate_color=False)
    (output / "motion_paths.html").write_text(geometry_scene.to_html(), encoding="utf-8")


if __name__ == "__main__":
    main()
