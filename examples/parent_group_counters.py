"""Counters keep their clocks inside one moving group boundary.

Run from the repository root:
    uv run python examples/parent_group_counters.py --output-dir /tmp/parent-group-counters
"""

import argparse
from pathlib import Path
from tempfile import gettempdir

from PIL import Image
from quickthumb import (
    AnimatedTextValue,
    AnimationSpec,
    Background,
    Canvas,
    GifOptions,
    GroupLayer,
    KeyframeSpec,
    LayerClip,
    LayerMask,
    RotationTrack,
    ShapeLayer,
    TextLayer,
    TimingSpec,
)

ROOT = Path(__file__).resolve().parents[1]
FONT = str(ROOT / "assets/fonts/Roboto-Medium.ttf")


def build_scene() -> Canvas:
    canvas = Canvas(780, 340).background(color="#101820")
    canvas.text(
        "COUNTERS WITH GROUP BOUNDARIES",
        position=(24, 22),
        font=FONT,
        size=26,
        color="#FFFFFF",
    )
    canvas.text(
        "Changing paint, settled slots. Yellow markers inherit the full group frame.",
        position=(24, 60),
        font=FONT,
        size=16,
        color="#A5BCC7",
    )
    for index, style in enumerate(("plain", "odometer", "flip")):
        center = 130 + index * 260
        canvas.shape(
            "rectangle",
            (16 + index * 260, 102),
            228,
            170,
            "#182833",
            border_radius=18,
        )
        canvas.text(
            style.upper(),
            position=(center, 115),
            align="top-center",
            font=FONT,
            size=16,
            color="#A5BCC7",
        )
        canvas.null(
            (center, 190),
            id=f"rig-{index}",
            animation=AnimationSpec.timeline(
                RotationTrack(
                    keyframes=[KeyframeSpec(time=0, value=-8), KeyframeSpec(time=0.35, value=8)]
                ),
                timing=TimingSpec(duration=0.35),
                easing="linear",
            ),
        )
        children = [
            TextLayer(
                type="text",
                content="0",
                font=FONT,
                size=38,
                color="#FFFFFF",
                effects=[Background(color="#247CBA", padding=7)],
                value=AnimatedTextValue.model_validate(
                    {
                        "from": -1250,
                        "to": 250,
                        "duration": 1.2,
                        "delay": 0.2,
                        "prefix": "$",
                        "style": style,
                        "easing": "linear",
                    }
                ),
            ),
            GroupLayer(
                type="group",
                direction="row",
                gap=10,
                item_align="center",
                children=[
                    ShapeLayer(
                        type="shape",
                        shape="rectangle",
                        position=(0, 0),
                        width=9,
                        height=22,
                        color="#32BAA5",
                    ),
                    TextLayer(
                        type="text",
                        content="0",
                        font=FONT,
                        size=23,
                        color="#D9F4F1",
                        value=AnimatedTextValue.model_validate(
                            {
                                "from": 99,
                                "to": 108,
                                "duration": 1.1,
                                "delay": 0.7,
                                "suffix": " units",
                                "style": style,
                                "easing": "linear",
                            }
                        ),
                    ),
                ],
            ),
        ]
        canvas.group(
            children,
            position=(-85, -35),
            padding=8,
            gap=12,
            parent=f"rig-{index}",
            id=f"group-{index}",
            clip=LayerClip(position=(-84, -36), width=170, height=101, border_radius=14),
            mask=(
                LayerMask(position=(-95, -45), width=190, height=120, opacity=0.65)
                if index == 1
                else LayerMask(
                    shape="ellipse",
                    position=(5, -42),
                    width=66,
                    height=54,
                    opacity=0.65,
                    invert=True,
                )
                if index == 2
                else None
            ),
        )
        canvas.shape("ellipse", (184, 36), 12, 12, "#FFCF56", parent=f"group-{index}")
        canvas.text(
            ("ROUNDED CLIP", "CLIP + PARTIAL MASK", "CLIP + INVERTED MASK")[index],
            position=(center, 286),
            align="top-center",
            font=FONT,
            size=13,
            color="#FFCF56",
        )
    canvas.text(
        "The rig settles at 0.35s; independent counters continue through 1.8s",
        position=(390, 316),
        align="top-center",
        font=FONT,
        size=14,
        color="#A5BCC7",
    )
    return canvas


def snapshot() -> Image.Image:
    scene = build_scene()
    strip = Image.new("RGBA", (scene.width, scene.height * 3))
    for index, instant in enumerate((0, 0.83, 1.8)):
        strip.paste(scene.render_frame(instant), (0, index * scene.height))
    return strip


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(gettempdir()) / "quickthumb-parent-group-counters",
    )
    output = parser.parse_args().output_dir
    output.mkdir(parents=True, exist_ok=True)
    scene = build_scene()
    scene.render(
        str(output / "parent_group_counters.gif"), animation=GifOptions(fps=24, quality="high")
    )
    snapshot().save(output / "parent_group_counters.png")
    scene.render(str(output / "parent_group_counters.html"))
