"""Atomic composed group sources retain document and encoding adapter contracts."""

import base64
import re
from io import BytesIO
from pathlib import Path
from typing import Any, cast

import pytest
from PIL import Image
from quickthumb import (
    AnimationSpec,
    Canvas,
    ExportPolicy,
    GifOptions,
    GroupLayer,
    LayerClip,
    LayerMask,
    PositionTrack,
    RotationTrack,
    ScaleXTrack,
    ShapeLayer,
)
from quickthumb._export_html import HtmlExporter
from quickthumb.errors import RenderingError

from tests.test_parent_documents import embedded_png
from tests.test_parent_html import adapter, motion, track


def group_scene(boundary="both"):
    children = [
        ShapeLayer(
            type="shape", position=(0, 0), shape="rectangle", width=28, height=20, color="#E64A31"
        ),
        GroupLayer(
            type="group",
            children=[
                ShapeLayer(
                    type="shape",
                    position=(0, 0),
                    shape="ellipse",
                    width=22,
                    height=16,
                    color="#2479CE",
                )
            ],
            padding=2,
        ),
    ]
    return (
        Canvas(180, 140)
        .null(
            (55, 40),
            id="root",
            animation=motion(track(RotationTrack, -12, 22), track(ScaleXTrack, 1, 1.2)),
        )
        .group(
            children,
            position=(6, 4),
            direction="row",
            gap=5,
            padding=4,
            parent="root",
            id="group",
            clip=(
                LayerClip(position=(9, 7), width=42, height=20, border_radius=6)
                if boundary != "mask"
                else None
            ),
            mask=(
                LayerMask(shape="ellipse", position=(4, 4), width=62, height=28, opacity=0.7)
                if boundary != "clip"
                else None
            ),
            animation=motion(track(PositionTrack, (0, 0), (10, 4))),
        )
        .shape("rectangle", (66, 22), 9, 7, "#16A66A", parent="group", id="marker")
    )


@pytest.mark.parametrize("boundary", ["clip", "mask", "both"])
def test_eligible_html_embeds_composed_group_source_and_separate_explicit_child(boundary):
    canvas = group_scene(boundary)
    original = canvas.to_json()
    baked = adapter(canvas)
    group_node = baked.plan.nodes[id(canvas.layers[1])]
    marker_node = baked.plan.nodes[id(canvas.layers[2])]
    stage = HtmlExporter(canvas).render_stage()
    payloads = re.findall(r"data:image/png;base64,([A-Za-z0-9+/=]+)", stage.body)
    assert len(payloads) == len(stage.timeline) == 2
    for payload, node, event in zip(
        payloads, (group_node, marker_node), stage.timeline, strict=True
    ):
        actual = Image.open(BytesIO(base64.b64decode(payload))).convert("RGBA")
        assert node.image is not None
        assert (actual.size, actual.tobytes()) == (node.image.size, node.image.tobytes())
        assert event["initial"] == baked.values[id(node)][0]
        assert event["final"] == baked.values[id(node)][-1]
    bare = Canvas.from_json(original)
    group = cast(GroupLayer, bare.layers[1])
    group.clip = group.mask = None
    bare_adapter = adapter(bare)
    bare_group = bare_adapter.plan.nodes[id(bare.layers[1])]
    bare_marker = bare_adapter.plan.nodes[id(bare.layers[2])]
    assert group_node.image.tobytes() != bare_group.image.tobytes()
    assert marker_node.image.tobytes() == bare_marker.image.tobytes()
    assert all(
        item.support == "partial" and item.fallback is None
        for item in canvas.validate_export("html")
    )
    assert canvas.to_json() == original


@pytest.mark.parametrize("kind", ["svg", "pdf", "pptx"])
def test_document_fallback_uses_authored_group_composition_and_protects_destination(tmp_path, kind):
    canvas = group_scene()
    canvas.layers = [*Canvas(180, 140).background(color="#FFFFFF").layers, *canvas.layers]
    expected = canvas._render_to_image()
    assert expected.tobytes() != canvas.render_frame(0).tobytes()
    assert expected.tobytes() != canvas.render_frame(1).tobytes()
    if kind == "pdf":
        import pypdfium2

        with pypdfium2.PdfDocument(canvas.to_pdf()) as document:
            page = document[0]
            bitmap = page.render(scale=1)
            assert bitmap.to_pil().convert("RGB").tobytes() == expected.convert("RGB").tobytes()
            bitmap.close()
            page.close()
    else:
        actual = embedded_png(getattr(canvas, "to_" + kind)(), kind)
        assert (actual.size, actual.tobytes()) == (expected.size, expected.tobytes())
    path = tmp_path / ("group." + kind)
    result = canvas.export(path)
    assert next(item for item in result.capability_report if item.feature == "parent").fallback == (
        "static"
    )
    for method in (canvas.render, canvas.export):
        path.write_bytes(b"existing")
        with pytest.raises(RenderingError, match="authored-static"):
            method(str(path), policy=ExportPolicy(unsupported_motion="error"))
        assert path.read_bytes() == b"existing"


def test_eligible_html_strict_policy_preserves_existing_destination(tmp_path):
    path = tmp_path / "group.html"
    path.write_bytes(b"existing")
    with pytest.raises(RenderingError, match="sampled approximation"):
        group_scene().export(path, policy=ExportPolicy(unsupported_motion="error"))
    assert path.read_bytes() == b"existing"


@pytest.mark.parametrize(
    "policy",
    [
        ExportPolicy(reduced_motion=True),
        ExportPolicy(unsupported_motion="static"),
        ExportPolicy(unsupported_motion="rasterize"),
    ],
)
def test_explicit_html_static_policy_uses_whole_authored_group_scene(policy):
    canvas = group_scene()
    expected = canvas._render_to_image()
    actual = embedded_png(canvas.to_html(policy=policy), "html")
    assert actual.tobytes() == expected.tobytes()
    assert all(item.fallback == "static" for item in canvas.validate_export("html", policy))


def test_overridden_descendant_motion_keeps_existing_html_static_fallback():
    canvas = group_scene()
    group = cast(GroupLayer, canvas.layers[1])
    cast(Any, group.children[0]).animation = AnimationSpec.fade(duration=0.4)
    stage = HtmlExporter(canvas).render_stage()
    assert not stage.timeline
    assert embedded_png(stage.body, "html").tobytes() == canvas._render_to_image().tobytes()
    assert all(item.fallback == "static" for item in canvas.validate_export("html"))


@pytest.mark.parametrize("quality", ["standard", "high"])
def test_composed_group_serial_and_spawn_gif_bytes_match(tmp_path, quality):
    canvas = group_scene()
    serial, parallel = tmp_path / "serial.gif", tmp_path / "parallel.gif"
    for workers, path in ((1, serial), (2, parallel)):
        canvas.render(str(path), animation=GifOptions(fps=4, quality=quality, workers=workers))
    assert serial.read_bytes() == parallel.read_bytes()
    with Image.open(serial) as gif:
        assert getattr(gif, "n_frames", 1) >= 4


def test_parent_group_composition_visual_snapshot():
    from examples.parent_group_composition import build_scene

    actual = build_scene().render_frame(0.75)
    expected = Image.open(Path(__file__).parent / "snapshots/parent_group_composition.png").convert(
        "RGBA"
    )
    assert (actual.size, actual.tobytes()) == (expected.size, expected.tobytes())
