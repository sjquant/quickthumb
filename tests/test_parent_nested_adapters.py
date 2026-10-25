"""Static descendant boundaries remain atomic through parent export adapters."""

import base64
import re
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image
from quickthumb import (
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
from tests.test_parent_html import bake, css_row, motion, source_image, track


def nested_scene(invert=False):
    return (
        Canvas(180, 140)
        .null(
            (55, 35),
            id="root",
            animation=motion(track(RotationTrack, -15, 20), track(ScaleXTrack, 1.1, 0.8)),
        )
        .group(
            [
                ShapeLayer(
                    type="shape",
                    position=(0, 0),
                    shape="rectangle",
                    width=50,
                    height=24,
                    color="#E64A31",
                    clip=LayerClip(position=(14, 10), width=40, height=17, border_radius=4),
                ),
                GroupLayer(
                    type="group",
                    padding=3,
                    mask=LayerMask(
                        shape="ellipse",
                        position=("10%", "30%"),
                        width=38,
                        height=24,
                        opacity=0.65,
                        invert=invert,
                    ),
                    children=[
                        GroupLayer(
                            type="group",
                            padding=2,
                            clip=LayerClip(position=(17, 43), width=35, height=21),
                            children=[
                                ShapeLayer(
                                    type="shape",
                                    position=(0, 0),
                                    shape="rectangle",
                                    width=46,
                                    height=22,
                                    color="#2479CE",
                                )
                            ],
                        )
                    ],
                ),
            ],
            position=(6, 4),
            gap=5,
            padding=4,
            parent="root",
            id="group",
            clip=LayerClip(position=(8, 6), width=60, height=70, border_radius=5),
            animation=motion(track(PositionTrack, (0, 0), (8, 4)), track(RotationTrack, 12, -15)),
        )
        .shape("rectangle", (72, 28), 9, 7, "#16A66A", parent="group", id="marker")
    )


def remove_boundaries(layer):
    layer.clip = layer.mask = None
    for child in getattr(layer, "children", ()):
        remove_boundaries(child)


@pytest.mark.parametrize("invert", [False, True])
def test_nested_html_embeds_one_composed_source_and_independent_linked_child(invert):
    canvas = nested_scene(invert)
    original = canvas.to_json()
    baked = bake(canvas)
    nodes = [baked.sources[id(layer)] for layer in canvas.layers[1:]]
    stage = HtmlExporter(canvas).render_stage()
    payloads = re.findall(r"data:image/png;base64,([A-Za-z0-9+/=]+)", stage.body)
    assert len(payloads) == len(stage.timeline) == 2
    for payload, node, event in zip(payloads, nodes, stage.timeline, strict=True):
        actual = Image.open(BytesIO(base64.b64decode(payload))).convert("RGBA")
        assert (actual.size, actual.tobytes()) == (
            (node.width, node.height),
            source_image(node).tobytes(),
        )
        assert event["initial"] == css_row(node.rows[0])
        assert event["final"] == css_row(node.rows[-1])
    bare = Canvas.from_json(original)
    group = bare.layers[1]
    assert isinstance(group, GroupLayer)
    for child in group.children:
        remove_boundaries(child)
    uncomposed = bake(bare)
    bare_nodes = [uncomposed.sources[id(layer)] for layer in bare.layers[1:]]
    assert source_image(nodes[0]).tobytes() != source_image(bare_nodes[0]).tobytes()
    assert source_image(nodes[1]).tobytes() == source_image(bare_nodes[1]).tobytes()
    assert all(
        item.support == "partial" and item.fallback is None
        for item in canvas.validate_export("html")
    )
    assert canvas.to_json() == original


@pytest.mark.parametrize("kind", ["svg", "pdf", "pptx"])
def test_nested_document_fallback_preserves_authored_pixels_and_strict_destination(tmp_path, kind):
    canvas = nested_scene(invert=True)
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
    path = tmp_path / ("nested." + kind)
    result = canvas.export(path)
    assert next(item for item in result.capability_report if item.feature == "parent").fallback == (
        "static"
    )
    for method in (canvas.render, canvas.export):
        path.write_bytes(b"existing")
        with pytest.raises(RenderingError, match="authored-static"):
            method(str(path), policy=ExportPolicy(unsupported_motion="error"))
        assert path.read_bytes() == b"existing"


@pytest.mark.parametrize(
    "policy",
    [
        ExportPolicy(reduced_motion=True),
        ExportPolicy(unsupported_motion="static"),
        ExportPolicy(unsupported_motion="rasterize"),
    ],
)
def test_nested_html_static_policy_freezes_the_authored_scene(policy):
    canvas = nested_scene()
    expected = canvas._render_to_image()
    actual = embedded_png(canvas.to_html(policy=policy), "html")
    assert (actual.size, actual.tobytes()) == (expected.size, expected.tobytes())
    assert all(item.fallback == "static" for item in canvas.validate_export("html", policy))


def test_nested_html_strict_policy_preserves_existing_destination(tmp_path):
    path = tmp_path / "nested.html"
    path.write_bytes(b"existing")
    with pytest.raises(RenderingError, match="sampled approximation"):
        nested_scene().export(path, policy=ExportPolicy(unsupported_motion="error"))
    assert path.read_bytes() == b"existing"


@pytest.mark.parametrize("quality", ["standard", "high"])
def test_nested_composition_serial_and_spawn_gif_bytes_match(tmp_path, quality):
    canvas = nested_scene(invert=True)
    serial, parallel = tmp_path / "serial.gif", tmp_path / "parallel.gif"
    for workers, path in ((1, serial), (2, parallel)):
        canvas.render(str(path), animation=GifOptions(fps=4, quality=quality, workers=workers))
    assert serial.read_bytes() == parallel.read_bytes()
    with Image.open(serial) as gif:
        assert getattr(gif, "n_frames", 1) >= 4


def test_parent_nested_composition_visual_snapshot():
    from examples.parent_nested_composition import build_scene

    actual = build_scene().render_frame(0.75)
    expected = Image.open(
        Path(__file__).parent / "snapshots/parent_nested_composition.png"
    ).convert("RGBA")
    assert (actual.size, actual.tobytes()) == (expected.size, expected.tobytes())
