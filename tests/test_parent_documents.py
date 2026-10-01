"""Document adapters preserve parent geometry with explicit whole-scene fallback."""

import base64
import re
from io import BytesIO
from zipfile import ZipFile

import pytest
from PIL import Image
from quickthumb import (
    AnimationSpec,
    Canvas,
    Deck,
    ExportPolicy,
    KeyframeSpec,
    LayerClip,
    Morph,
    PositionTrack,
    TimingSpec,
)
from quickthumb.errors import RenderingError


def scene():
    animation = AnimationSpec.timeline(
        PositionTrack(
            keyframes=[KeyframeSpec(time=0, value=(60, 0)), KeyframeSpec(time=1, value=(100, 0))]
        ),
        timing=TimingSpec(duration=1),
    )
    return (
        Canvas(140, 130)
        .background(color="#FFFFFF")
        .null((40, 30), id="root", rotation=25, animation=animation)
        .null((10, 5), id="middle", parent="root", rotation=-15)
        .shape("rectangle", (5, 10), 24, 16, "#FF0000", id="child", parent="middle")
        .shape("rectangle", (5, 5), 6, 6, "#0000FF", id="independent", animation=animation)
    )


def embedded_png(output, kind):
    if kind == "pptx":
        with ZipFile(BytesIO(output)) as archive:
            images = [name for name in archive.namelist() if name.startswith("ppt/media/")]
            assert len(images) == 1
            data = archive.read(images[0])
    else:
        payloads = re.findall(r"data:image/png;base64,([A-Za-z0-9+/=]+)", output)
        assert len(payloads) == 1
        data = base64.b64decode(payloads[0])
    return Image.open(BytesIO(data)).convert("RGBA")


@pytest.mark.parametrize("kind", ["html", "svg", "pptx"])
def test_embedded_pixels_are_authored_still_not_time_zero_or_final(kind):
    canvas = scene()
    expected = canvas._render_to_image()
    assert expected.tobytes() != canvas.render_frame(0).tobytes()
    assert expected.tobytes() != canvas.render_frame(1).tobytes()
    actual = embedded_png(getattr(canvas, "to_" + kind)(), kind)
    assert actual.size == expected.size
    assert actual.tobytes() == expected.tobytes()
    assert canvas._ctx.motion_time is None


def test_pdf_parent_page_matches_authored_raster():
    import pypdfium2

    canvas = scene()
    expected = canvas._render_to_image().convert("RGB")
    with pypdfium2.PdfDocument(canvas.to_pdf()) as document:
        page = document[0]
        bitmap = page.render(scale=1)
        actual = bitmap.to_pil().convert("RGB")
        assert actual.size == expected.size
        assert actual.tobytes() == expected.tobytes()
        bitmap.close()
        page.close()


@pytest.mark.parametrize("target", ["html", "pptx"])
@pytest.mark.parametrize(
    "policy",
    [None, ExportPolicy(unsupported_motion="rasterize"), ExportPolicy(unsupported_motion="static")],
)
def test_entire_scene_motion_is_reported_static_even_unlinked_layers(target, policy):
    diagnostics = scene().validate_export(target, policy)
    assert diagnostics
    assert all(item.support == "fallback" and item.fallback == "static" for item in diagnostics)
    assert any(item.layer_id == "independent" for item in diagnostics)
    assert any(item.layer_id == "root" for item in diagnostics)
    assert any(item.feature == "parent" for item in diagnostics)


@pytest.mark.parametrize("kind", ["html", "svg", "pptx", "pdf"])
@pytest.mark.parametrize("deck", [False, True])
def test_export_result_reports_actual_static_document_fallback(tmp_path, kind, deck):
    if deck and kind == "svg":
        pytest.skip("SVG has no multi-page Deck output")
    source = Deck(140, 130).slide(scene()) if deck else scene()
    result = source.export(tmp_path / ("scene." + kind))
    assert result.output_format == kind
    assert result.fallback_diagnostics
    assert all(item.fallback == "static" for item in result.capability_report)
    assert all(item.support == "fallback" for item in result.capability_report)
    assert all(kind in item.message for item in result.capability_report)
    assert source.validate_export("raster")[0].support == "full"


@pytest.mark.parametrize("method", ["to_html", "to_pptx"])
@pytest.mark.parametrize("deck", [False, True])
def test_strict_convenience_policy_rejects_fallback(method, deck):
    source = Deck(140, 130).slide(scene()) if deck else scene()
    with pytest.raises(RenderingError, match="authored-static"):
        getattr(source, method)(policy=ExportPolicy(unsupported_motion="error"))


def test_per_layer_native_pptx_request_cannot_claim_editable_motion():
    with pytest.raises(RenderingError, match="authored-static"):
        scene().to_pptx(policy=ExportPolicy(pptx={"independent": "native"}))


@pytest.mark.parametrize("first_parent", [False, True])
def test_parent_deck_morph_fades_with_no_pptx_timing_or_html_layer_clock(first_parent):
    from xml.etree import ElementTree as ET

    from quickthumb._export_html import HtmlExporter

    canvas = scene()
    plain = Canvas(140, 130).shape("rectangle", (5, 5), 20, 15, "#FF0000", motion_key="match")
    canvas.layers[-1].motion_key = "match"
    first, second = (canvas, plain) if first_parent else (plain, canvas)
    deck = Deck(140, 130).slide(first).slide(second, transition=Morph())
    stage = HtmlExporter(canvas).render_stage()
    assert stage.parent_geometry and not stage.timeline and not stage.keyframes
    html = deck.to_html()
    assert 'data-qt-morph="1"' not in html
    assert all(
        item.fallback == "fade"
        for item in deck.validate_export("html")
        if item.feature == "parent_morph"
    )
    with ZipFile(BytesIO(deck.to_pptx())) as archive:
        slide = archive.read(f"ppt/slides/slide{1 if first_parent else 2}.xml")
        assert b"<p:timing" not in slide
        assert b"!!qt-morph" not in slide
        tree = ET.fromstring(slide)
        assert (
            len(tree.findall(".//{http://schemas.openxmlformats.org/presentationml/2006/main}pic"))
            == 1
        )
        assert b":morph" not in archive.read("ppt/slides/slide2.xml")
        assert b"<p:fade" in archive.read("ppt/slides/slide2.xml")


@pytest.mark.parametrize("kind", ["html", "svg", "pptx", "pdf"])
@pytest.mark.parametrize("deck", [False, True])
def test_unsupported_parent_sources_preserve_destinations(tmp_path, kind, deck):
    canvas = scene()
    canvas.layers[-2].clip = LayerClip(position=(0, 0), width=10, height=10)
    source = Deck(140, 130).slide(Canvas(140, 130)).slide(canvas) if deck else canvas
    path = tmp_path / ("existing." + kind)
    path.write_bytes(b"existing")
    with pytest.raises(RenderingError, match="clip and mask"):
        source.render(str(path))
    assert path.read_bytes() == b"existing"
    assert not (tmp_path / ("existing_01." + kind)).exists()


def test_pdf_parent_fragments_are_export_scoped_and_skip_vector_fonts(monkeypatch):
    from quickthumb._export_pdf import PdfExporter

    canvas = scene().text("frozen", font="assets/fonts/Pretendard-ExtraBold.woff2")
    exporter = PdfExporter(canvas)
    monkeypatch.setattr(exporter, "_font_key", lambda *_: pytest.fail("baked page font collection"))
    assert exporter.export_bytes().startswith(b"%PDF")
    assert not exporter._parent_fragments
    monkeypatch.setattr(
        exporter, "_draw_fragment", lambda *_: (_ for _ in ()).throw(ValueError("draw"))
    )
    with pytest.raises(ValueError, match="draw"):
        exporter.export_bytes()
    assert not exporter._parent_fragments
    assert not exporter._registered_fonts


@pytest.mark.parametrize("kind", ["html", "svg"])
def test_render_prepares_document_before_opening_destination(tmp_path, monkeypatch, kind):
    canvas = scene()
    monkeypatch.setattr(
        canvas, "to_" + kind, lambda **_: (_ for _ in ()).throw(ValueError("prepare"))
    )
    path = tmp_path / ("existing." + kind)
    path.write_bytes(b"existing")
    with pytest.raises(ValueError, match="prepare"):
        canvas.render(str(path))
    assert path.read_bytes() == b"existing"


def test_shared_model_occurrences_keep_slide_local_diagnostics():
    from quickthumb import NullLayer, ShapeLayer
    from quickthumb.models import Fade

    shared = ShapeLayer(
        type="shape",
        shape="rectangle",
        position=(0, 0),
        width=12,
        height=8,
        color="#FF0000",
        id="shared",
        animation=Fade(),
    )
    plain = Canvas(140, 130, layers=[shared])
    linked = Canvas(140, 130, layers=[shared, NullLayer(type="null", parent="shared")])
    for target, expected in [("html", "full"), ("pptx", "native")]:
        reports = Deck(140, 130).slide(plain).slide(linked).validate_export(target)
        motion = [item for item in reports if item.layer_id == "shared"]
        assert [item.support for item in motion] == [expected, "fallback"]


def test_narrated_mp4_render_policy_still_ignores_unused_morph(tmp_path, monkeypatch):
    from quickthumb import Morph

    deck = Deck(140, 130).slide(scene()).slide(Canvas(140, 130), transition=Morph())
    calls = []
    monkeypatch.setattr(deck, "render_mp4", lambda path: calls.append(path))
    path = str(tmp_path / "narrated.mp4")
    assert deck.render(path, policy=ExportPolicy(unsupported_motion="error")) == [path]
    assert calls == [path]


def test_pdf_reports_static_pages_without_claiming_morph_fade(tmp_path):
    deck = Deck(140, 130).slide(scene()).slide(Canvas(140, 130), transition=Morph())
    result = deck.export(tmp_path / "static.pdf")
    assert not any(item.feature == "parent_morph" for item in result.capability_report)


@pytest.mark.parametrize("kind", ["html", "svg", "pptx", "pdf"])
def test_unlinked_scene_never_enters_static_parent_adapter(monkeypatch, kind):
    from quickthumb import _parent_export

    def unexpected(*_):
        pytest.fail("unlinked scene entered parent fallback")

    monkeypatch.setattr(_parent_export, "static_parent_fragment", unexpected)
    canvas = Canvas(140, 130).shape("rectangle", (4, 5), 12, 10, "#FF0000")
    assert getattr(canvas, "to_" + kind)()


def test_repeated_pdf_canvas_is_prepared_once_per_document(monkeypatch):
    from quickthumb import _parent_export
    from quickthumb._export_pdf import PdfExporter

    canvas = scene()
    original = _parent_export.static_parent_fragment
    calls = []

    def capture(item):
        calls.append(item)
        return original(item)

    monkeypatch.setattr(_parent_export, "static_parent_fragment", capture)
    assert PdfExporter().export_bytes_canvases([canvas, canvas]).startswith(b"%PDF")
    assert calls == [canvas]


def test_pdf_preparation_failure_releases_prepared_fragments(tmp_path):
    from quickthumb._export_pdf import PdfExporter

    invalid = scene()
    invalid.layers[-2].clip = LayerClip(position=(0, 0), width=10, height=10)
    exporter = PdfExporter()
    path = tmp_path / "existing.pdf"
    path.write_bytes(b"existing")
    with pytest.raises(RenderingError, match="clip and mask"):
        exporter.save_canvases([scene(), invalid], path)
    assert not exporter._parent_fragments
    assert path.read_bytes() == b"existing"
