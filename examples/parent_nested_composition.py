"""Static boundaries at several layout depths travel through one affine parent rig.

Run from the repository root:
    uv run python examples/parent_nested_composition.py --output-dir /tmp/parent-nested-composition
"""

import argparse
from pathlib import Path
from tempfile import gettempdir

from quickthumb import (
    AnimationSpec,
    Background,
    Canvas,
    GifOptions,
    GroupLayer,
    KeyframeSpec,
    LayerClip,
    LayerMask,
    RotationTrack,
    ScaleXTrack,
    Shadow,
    ShapeLayer,
    TextLayer,
    TimingSpec,
)

ROOT = Path(__file__).resolve().parents[1]
FONT = str(ROOT / "assets/fonts/Roboto-Medium.ttf")


def track(kind, first, last):
    return kind(keyframes=[KeyframeSpec(time=0, value=first), KeyframeSpec(time=1.5, value=last)])


def motion(*tracks):
    return AnimationSpec.timeline(*tracks, timing=TimingSpec(duration=1.5), easing="linear")


def build_scene() -> Canvas:
    canvas = Canvas(820, 400).background(color="#101820")
    canvas.text(
        "NESTED BOUNDARIES, SHARED MOTION",
        position=(26, 23),
        font=FONT,
        size=26,
        color="#FFFFFF",
    )
    canvas.text(
        "Leaf clips and nested group masks become one moving source",
        position=(26, 61),
        font=FONT,
        size=17,
        color="#A5BCC7",
    )
    for index, label in enumerate(("PARTIAL ALPHA", "INVERTED CUTOUT")):
        left = 20 + index * 410
        canvas.shape("rectangle", (left, 106), 370, 219, "#182833", border_radius=18)
        canvas.null(
            (left + 31, 146),
            id=f"rig-{index}",
            animation=motion(track(RotationTrack, 12, -12), track(ScaleXTrack, 1.1, 0.9)),
        )
        # Every boundary uses this top-level group's parent-local plane, even
        # when its owner sits several auto-layout levels below the group.
        # Percentages still use 820 x 400, not a child's measured layout box.
        content = GroupLayer(
            type="group",
            padding=6,
            gap=17,
            mask=LayerMask(
                shape="ellipse" if index else "rectangle",
                position=(168, 69) if index else (20, 62),
                width=65 if index else 244,
                height=76 if index else 100,
                opacity=1 if index else 0.58,
                invert=bool(index),
            ),
            children=[
                ShapeLayer(
                    type="shape",
                    shape="rectangle",
                    position=(0, 0),
                    width=248,
                    height=28,
                    color="#349DD1",
                    effects=[Shadow(color="#050B12", offset_x=4, offset_y=4, blur_radius=2)],
                    clip=LayerClip(position=(24, "17%"), width=231, height=31, border_radius=9),
                ),
                TextLayer(
                    type="text",
                    content="NESTED SOURCE",
                    font=FONT,
                    size=23,
                    color="#F2F8FC",
                    effects=[Background(color="#365477", padding=7, border_radius=6)],
                ),
            ],
        )
        canvas.group(
            [
                ShapeLayer(
                    type="shape",
                    shape="rectangle",
                    position=(0, 0),
                    width=248,
                    height=32,
                    color="#42CEB7",
                    clip=LayerClip(position=(18, 14), width=226, height=24, border_radius=10),
                ),
                GroupLayer(
                    type="group",
                    padding=8,
                    clip=LayerClip(position=(18, 61), width=243, height=103, border_radius=13),
                    children=[content],
                ),
            ],
            position=(0, 0),
            padding=10,
            gap=12,
            parent=f"rig-{index}",
            id=f"group-{index}",
            clip=LayerClip(position=(6, 5), width=271, height=167, border_radius=15),
            animation=motion(track(RotationTrack, -12, 18)),
        )
        # This linked marker uses the full group frame and escapes every source
        # boundary above; it is not an auto-layout descendant.
        canvas.shape("ellipse", (303, 76), 14, 14, "#FFCF56", parent=f"group-{index}")
        canvas.text(
            label,
            position=(left + 185, 337),
            align="top-center",
            font=FONT,
            size=17,
            color="#FFCF56",
        )
    canvas.text(
        "Full layout stays intact. Yellow markers inherit geometry and remain independent.",
        position=(410, 372),
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
        default=Path(gettempdir()) / "quickthumb-parent-nested-composition",
    )
    output = parser.parse_args().output_dir
    output.mkdir(parents=True, exist_ok=True)
    scene = build_scene()
    scene.render(
        str(output / "parent_nested_composition.gif"),
        animation=GifOptions(fps=24, quality="high"),
    )
    scene.render_frame(0.75).save(output / "parent_nested_composition.png")
    scene.render(str(output / "parent_nested_composition.html"))
    (output / "parent_nested_composition.json").write_text(scene.to_json(), encoding="utf-8")
