"""A composed leaf group's separated rows carry their source boundaries.

Run from the repository root:
    uv run python examples/parent_group_stagger.py --output-dir /tmp/parent-group-stagger
"""

import argparse
from pathlib import Path
from tempfile import gettempdir

from PIL import Image
from quickthumb import (
    AnimationSpec,
    Canvas,
    ColorTrack,
    GifOptions,
    GroupLayer,
    KeyframeSpec,
    LayerClip,
    LayerMask,
    OpacityTrack,
    PositionTrack,
    RotationTrack,
    ScaleXTrack,
    ShapeLayer,
    StaggerSpec,
    TextLayer,
    TimingSpec,
)

ROOT = Path(__file__).resolve().parents[1]
FONT = str(ROOT / "assets/fonts/Roboto-Medium.ttf")


def track(kind, first, last, duration):
    return kind(
        keyframes=[KeyframeSpec(time=0, value=first), KeyframeSpec(time=duration, value=last)]
    )


def build_scene() -> Canvas:
    canvas = Canvas(750, 360).background(color="#101820")
    canvas.text(
        "GROUP BOUNDARIES + STAGGER", position=(24, 22), font=FONT, size=26, color="#FFFFFF"
    )
    canvas.text(
        "Clipped source pieces travel through a shared parent transform",
        position=(24, 60),
        font=FONT,
        size=16,
        color="#A5BCC7",
    )
    for index, label in enumerate(("ROUNDED CLIP", "CLIP + PARTIAL MASK", "ONE BAND REMOVED")):
        center = 125 + index * 250
        canvas.shape("rectangle", (16 + index * 250, 101), 218, 178, "#182833", border_radius=18)
        canvas.null(
            (center, 170),
            id=f"rig-{index}",
            animation=AnimationSpec.timeline(
                track(RotationTrack, -12, 8, 0.35),
                track(ScaleXTrack, 1.1, 0.9, 0.35),
                timing=TimingSpec(duration=0.35),
                easing="linear",
            ),
        )
        rows = AnimationSpec.timeline(
            track(PositionTrack, (22, 0), (0, 0), 0.7),
            track(OpacityTrack, 0.2, 1, 0.7),
            track(ColorTrack, "#FFCF56", "#42CEB7", 0.7),
            timing=TimingSpec(duration=0.7),
            easing="linear",
        )
        rows.stagger = StaggerSpec(delay=0.35, target="children")
        children = [
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
                        width=8,
                        height=20,
                        color="#FFFFFF",
                    ),
                    TextLayer(type="text", content=text, font=FONT, size=22, color="#FFFFFF"),
                ],
            )
            for text in ("SOURCE", "PIECES", "TRAVEL")
        ]
        canvas.group(
            children,
            position=(-65, -42),
            padding=6,
            gap=12,
            parent=f"rig-{index}",
            anchor=(0, 0.5),
            clip=LayerClip(position=(-59, -42), width=110, height=117, border_radius=10),
            mask=LayerMask(
                position=(-65, -42),
                width=125,
                height=117 if index == 1 else 70,
                opacity=0.6 if index == 1 else 1,
            )
            if index
            else None,
            animation=rows,
        )
        canvas.text(
            label, position=(center, 294), align="top-center", font=FONT, size=13, color="#FFCF56"
        )
    canvas.text(
        "Three declared children require three alpha bands; otherwise the whole source moves",
        position=(375, 322),
        align="top-center",
        font=FONT,
        size=14,
        color="#A5BCC7",
    )
    return canvas


def snapshot() -> Image.Image:
    scene = build_scene()
    strip = Image.new("RGBA", (scene.width, scene.height * 3))
    for index, instant in enumerate((0.2, 0.8, 1.4)):
        strip.paste(scene.render_frame(instant), (0, index * scene.height))
    return strip


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir", type=Path, default=Path(gettempdir()) / "quickthumb-parent-group-stagger"
    )
    output = parser.parse_args().output_dir
    output.mkdir(parents=True, exist_ok=True)
    scene = build_scene()
    scene.render(
        str(output / "parent_group_stagger.gif"), animation=GifOptions(fps=24, quality="high")
    )
    snapshot().save(output / "parent_group_stagger.png")
    scene.render(str(output / "parent_group_stagger.html"))
    (output / "parent_group_stagger.json").write_text(scene.to_json(), encoding="utf-8")
