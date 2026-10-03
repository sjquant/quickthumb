"""Parent stagger keeps partial raster capability and honest static observations."""

from typing import Any, cast

import pytest
from quickthumb import AnimationSpec, Canvas, ExportPolicy, GroupLayer, StaggerSpec, TextLayer
from quickthumb._export_video import _SlideAnimator
from quickthumb._parent_render import ParentNode
from quickthumb.errors import RenderingError
from quickthumb.motion import capabilities_for

from tests.test_parent_stagger import FONT, group_scene, text_scene


@pytest.mark.parametrize("target", ["raster", "video"])
@pytest.mark.parametrize("group", [False, True])
def test_supported_parent_stagger_keeps_partial_stagger_report(target, group):
    canvas = group_scene() if group else text_scene()
    report = canvas.validate_export(target)
    assert next(item for item in report if item.feature == "parent").support == "full"
    assert capabilities_for(target)["stagger"].support == "partial"
    assert next(item for item in report if item.feature == "stagger").support == "fallback"


def test_authored_static_inspection_does_not_paint_or_split(monkeypatch):
    from quickthumb import _export_video as video

    canvas = text_scene(rotation=7, align="center")
    original = canvas.to_json()
    fixed = Canvas.from_json(original)
    cast(Any, fixed.layers[-1]).animation = None
    expected = fixed.inspect()
    monkeypatch.setattr(ParentNode, "render_source", lambda *a, **k: pytest.fail("source paint"))
    monkeypatch.setattr(canvas, "_render_layer", lambda *a, **k: pytest.fail("paint"))
    monkeypatch.setattr(video, "split_into_bands", lambda *a, **k: pytest.fail("target crops"))
    assert canvas.inspect() == expected
    assert canvas.to_json() == original
    motion = canvas.inspect_motion(target="video", fps=4).slides[0].layers[-1]
    assert motion.parent == "root"
    assert len(motion.targets) == 3
    assert motion.events[0].stagger == {"delay": 0.4, "target": "lines", "order": "document"}
    # Inspection remains a local canonical timeline, without invented target/world samples.
    assert motion.duration == 0.5
    assert motion.initial_state["position"] == [15, 24]


def test_reduced_motion_debug_and_diagnostic_pixels_use_whole_authored_source():
    from tests.test_parent_diagnostics import composite, setup

    canvas = text_scene(rotation=7, align="center")
    fixed = Canvas.from_json(canvas.to_json())
    cast(Any, fixed.layers[-1]).animation = None
    expected = fixed._render_to_image()
    assert canvas._render_to_image().tobytes() == expected.tobytes()
    assert (
        canvas._render_to_image(debug=True).tobytes()
        == fixed._render_to_image(debug=True).tobytes()
    )
    animator = _SlideAnimator(canvas, {}, reduced_motion=True)
    assert not animator._units[-1].target_images
    for instant in (0, 0.5, 3):
        assert animator.frame_at(instant).tobytes() == expected.tobytes()
    sources, measured = setup(canvas)
    assert composite(canvas, sources, measured).tobytes() == expected.tobytes()
    assert sources.occurrences["leaf"].animated
    canvas.diagnose()


@pytest.mark.parametrize("kind", ["html", "svg", "pptx", "pdf"])
def test_document_fallback_pixels_and_strict_destination_protection(tmp_path, kind):
    from tests.test_parent_documents import embedded_png

    canvas = text_scene(color="#203040")
    canvas.layers = [
        *Canvas(canvas.width, canvas.height).background(color="#FFFFFF").layers,
        *canvas.layers,
    ]
    expected = canvas._render_to_image()
    assert expected.tobytes() != canvas.render_frame(0.1).tobytes()
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
        assert actual.tobytes() == expected.tobytes()
    path = tmp_path / ("stagger." + kind)
    result = canvas.export(path)
    assert {"parent", "stagger"} <= {item.feature for item in result.capability_report}
    assert all(item.fallback == "static" for item in result.capability_report)
    path.write_bytes(b"existing")
    with pytest.raises(RenderingError):
        canvas.export(path, policy=ExportPolicy(unsupported_motion="error"))
    assert path.read_bytes() == b"existing"


@pytest.mark.parametrize("delay", [0, 0.4])
@pytest.mark.parametrize("content", ["ONE", "ONE\nTWO\nTHREE"])
def test_staggered_nodes_cannot_parent_explicit_children_even_without_target_separation(
    delay, content
):
    canvas = text_scene(content=content)
    cast(Any, canvas.layers[-1]).animation.stagger = StaggerSpec(delay=delay, target="lines")
    canvas.shape("rectangle", (0, 0), 5, 5, "#FF0000", parent="leaf")
    report = canvas.validate_export("raster")
    parent = next(item for item in report if item.feature == "parent")
    assert parent.support == "unsupported"
    assert "cannot be a parent" in parent.message
    for operation in (
        lambda: canvas.render_frame(0.5),
        canvas.inspect,
        canvas.diagnose,
        canvas.to_html,
        canvas.to_svg,
        canvas.to_pptx,
        canvas.to_pdf,
    ):
        with pytest.raises(RenderingError, match="cannot be a parent"):
            operation()


@pytest.mark.parametrize("group", [False, True])
@pytest.mark.parametrize("kind", ["png", "gif", "html", "svg", "pptx", "pdf"])
def test_intrinsic_counter_stagger_is_rejected_before_output_writes(tmp_path, group, kind):
    counter = cast(TextLayer, Canvas(180, 150).counter(1, 100, 1, font=FONT, size=20).layers[0])
    spec = AnimationSpec.rise(duration=0.5, stagger=0.4, target="children" if group else "lines")
    leaf = (
        GroupLayer(type="group", children=[counter], parent="root", animation=spec)
        if group
        else (cast(Any, counter).model_copy(update={"parent": "root", "animation": spec}))
    )
    canvas = Canvas(180, 150).null(id="root")
    canvas.layers = [*canvas.layers, leaf]
    report = canvas.validate_export("video")
    assert next(item for item in report if item.feature == "parent").support == "unsupported"
    path = tmp_path / ("existing." + kind)
    path.write_bytes(b"existing")
    with pytest.raises(RenderingError, match="static text or group"):
        canvas.render(str(path))
    assert path.read_bytes() == b"existing"


@pytest.mark.parametrize("kind", ["png", "gif", "html", "svg", "pptx", "pdf"])
def test_stagger_as_parent_rejection_preserves_existing_output(tmp_path, kind):
    canvas = text_scene(content="ONE", animation=AnimationSpec.rise(stagger=0, target="lines"))
    canvas.shape("rectangle", (0, 0), 5, 5, "#FF0000", parent="leaf")
    path = tmp_path / ("existing." + kind)
    path.write_bytes(b"existing")
    with pytest.raises(RenderingError, match="cannot be a parent"):
        canvas.render(str(path))
    assert path.read_bytes() == b"existing"


@pytest.mark.parametrize("kind", ["image", "video", "chart", "qr"])
def test_dynamic_leaf_source_kinds_remain_guarded_before_paint(tmp_path, monkeypatch, kind):
    from PIL import Image
    from quickthumb import BarChartSpec

    canvas = Canvas(100, 100).null(id="root")
    if kind == "image":
        path = tmp_path / "image.png"
        Image.new("RGB", (20, 20), "red").save(path)
        canvas.image(str(path), (0, 0), width=20, height=20, parent="root")
    elif kind == "video":
        path = tmp_path / "video.mp4"
        path.write_bytes(b"guard must precede decoding")
        canvas.video(str(path), (0, 0), 20, 20, parent="root")
    elif kind == "chart":
        canvas.chart(BarChartSpec(data=[1, 2]), (0, 0), 40, 40, parent="root")
    else:
        canvas.qr_code("guard", (0, 0), size=32, parent="root")
    cast(Any, canvas.layers[-1]).animation = AnimationSpec.rise(stagger=0.1)
    monkeypatch.setattr(ParentNode, "render_source", lambda *a, **k: pytest.fail("source paint"))
    assert (
        next(item for item in canvas.validate_export("video") if item.feature == "parent").support
        == "unsupported"
    )
    with pytest.raises(RenderingError, match="static text or group"):
        canvas.render_frame(0.5)


def test_gif_export_keeps_existing_policy_labels_without_replacing_partial_motion(tmp_path):
    from quickthumb import GifOptions

    canvas = group_scene()
    outputs = []
    for policy, fallback in [
        (None, "fade"),
        (ExportPolicy(unsupported_motion="static"), "static"),
        (ExportPolicy(unsupported_motion="rasterize"), "rasterize"),
    ]:
        path = tmp_path / (fallback + ".gif")
        result = canvas.export(path, policy=policy, animation=GifOptions(fps=5))
        stagger = next(item for item in result.capability_report if item.feature == "stagger")
        assert (stagger.support, stagger.fallback) == ("fallback", fallback)
        outputs.append(path.read_bytes())
    assert outputs[0] == outputs[1] == outputs[2]
    strict = tmp_path / "strict.gif"
    strict.write_bytes(b"existing")
    with pytest.raises(RenderingError, match="stagger"):
        canvas.export(strict, policy=ExportPolicy(unsupported_motion="error"))
    assert strict.read_bytes() == b"existing"
