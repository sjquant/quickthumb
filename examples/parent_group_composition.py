"""Static group boundaries travel with the group while linked markers stay free.

Run from the repository root:
    uv run python examples/parent_group_composition.py --output-dir /tmp/parent-group-composition
"""

import argparse
from pathlib import Path
from tempfile import gettempdir

from quickthumb import (
    AnimationSpec,
    Canvas,
    GifOptions,
    GroupLayer,
    KeyframeSpec,
    LayerClip,
    LayerMask,
    RotationTrack,
    ScaleXTrack,
    ShapeLayer,
    TextLayer,
    TimingSpec,
)

ROOT = Path(__file__).resolve().parents[1]
FONT = str(ROOT / "assets/fonts/Roboto-Medium.ttf")


def build_scene() -> Canvas:
    canvas = Canvas(760, 350).background(color="#101820")
    canvas.text(
        "ONE GROUP, ONE SOURCE BOUNDARY", position=(26, 22), font=FONT, size=24, color="#FFFFFF"
    )
    canvas.text(
        "Static layout is clipped once; linked markers keep the full group frame",
        position=(26, 57),
        font=FONT,
        size=16,
        color="#A5BCC7",
    )
    for index, label in enumerate(("CLIPPED LAYOUT", "MASKED LAYOUT")):
        x = 180 + index * 380
        canvas.null(
            (x, 184),
            id=f"rig-{index}",
            animation=AnimationSpec.timeline(
                RotationTrack(
                    keyframes=[KeyframeSpec(time=0, value=-14), KeyframeSpec(time=1.5, value=18)]
                ),
                ScaleXTrack(
                    keyframes=[KeyframeSpec(time=0, value=1), KeyframeSpec(time=1.5, value=1.2)]
                ),
                timing=TimingSpec(duration=1.5),
                easing="linear",
            ),
        )
        children = [
            ShapeLayer(
                type="shape",
                position=(0, 0),
                shape="rectangle",
                width=160,
                height=27,
                color="#32BAA5",
            ),
            GroupLayer(
                type="group",
                direction="row",
                gap=8,
                item_align="center",
                children=[
                    ShapeLayer(
                        type="shape",
                        position=(0, 0),
                        shape="ellipse",
                        width=22,
                        height=22,
                        color="#FFCF56",
                    ),
                    TextLayer(
                        type="text", content="LOCAL GROUP", font=FONT, size=18, color="#FFFFFF"
                    ),
                ],
            ),
            ShapeLayer(
                type="shape",
                position=(0, 0),
                shape="rectangle",
                width=160,
                height=27,
                color="#247CBA",
            ),
        ]
        canvas.group(
            children,
            position=(-90, -52),
            gap=10,
            padding=10,
            parent=f"rig-{index}",
            id=f"group-{index}",
            clip=(
                LayerClip(position=(-70, -45), width=125, height=96, border_radius=20)
                if index == 0
                else None
            ),
            mask=(
                LayerMask(
                    shape="polygon",
                    position=(-84, -49),
                    width=170,
                    height=105,
                    points=[(0.08, 0), (0.9, 0.08), (1, 0.8), (0.2, 1)],
                    opacity=0.75,
                )
                if index == 1
                else None
            ),
        )
        canvas.shape("ellipse", (194, 48), 14, 14, "#FFCF56", parent=f"group-{index}")
        canvas.text(
            label,
            position=(x, 285),
            align="top-center",
            font=FONT,
            size=17,
            color="#FFCF56",
        )
    canvas.text(
        "Detached yellow dots are linked children outside source boundaries",
        position=(380, 317),
        align="top-center",
        font=FONT,
        size=14,
        color="#A5BCC7",
    )
    return canvas


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(gettempdir()) / "quickthumb-parent-group-composition",
    )
    output = parser.parse_args().output_dir
    output.mkdir(parents=True, exist_ok=True)
    scene = build_scene()
    scene.render(
        str(output / "parent_group_composition.gif"),
        animation=GifOptions(fps=24, quality="high"),
    )
    scene.render_frame(0.75).save(output / "parent_group_composition.png")
    scene.render(str(output / "parent_group_composition.html"))
