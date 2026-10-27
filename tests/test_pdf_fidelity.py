"""Actual PDF bytes retain native content and carry opt-in renderer observations."""

import builtins
from io import BytesIO

import pytest
from quickthumb import Canvas, Deck, ExportPolicy, ValidationError
from quickthumb._export_pdf import PdfExporter
from quickthumb.errors import RenderingError

from tests._optional import require_pypdfium2


def policy(*, ratio: float = 0, similarity: float = 1) -> ExportPolicy:
    return ExportPolicy(
        fidelity={
            "pdf": {
                "pixel_tolerance": 0,
                "max_different_pixel_ratio": ratio,
                "min_hash_similarity": similarity,
            }
        }
    )


@pytest.mark.parametrize("kind", ["solid", "alpha", "ellipse"])
def test_pdf_reports_exact_or_caller_tolerated_pixels(tmp_path, kind):
    """Opaque and transparent pixels are exact; native ellipse edges use caller-selected limits."""
    require_pypdfium2()
    # Given: independent solid, translucent and antialiased scenes
    scene = Canvas(64, 48)
    if kind == "solid":
        scene.background(color="#123456")
    else:
        scene.shape(
            "ellipse" if kind == "ellipse" else "rectangle",
            (6, 5),
            36,
            25,
            "#42CEB7" if kind == "ellipse" else "#FF000080",
        )

    # When: comparing the actual PDF without a resizing or opaque-background adapter
    result = scene.export(tmp_path / "observed.pdf", policy=policy())
    report = result.pixel_metrics.fidelity

    # Then: the renderer context and explicit criteria explain the observed verdict
    assert report is not None
    assert report.renderer == "pdfium" and report.renderer_version and report.binding_version
    assert (
        report.page_count == 1 and report.page_size_points == (64, 48) and report.render_scale == 1
    )
    assert report.actual_width == 64 and report.actual_height == 48
    assert report.canonical_environment == scene.sample().environment
    assert report.verdict == ("out_of_policy" if kind == "ellipse" else "exact")
    assert result.fallback_diagnostics == []
    if kind == "ellipse":
        limits = policy(ratio=0.15, similarity=0.95)
        tolerant = scene.export(tmp_path / "tolerated.pdf", policy=limits).pixel_metrics.fidelity
        limits.fidelity["pdf"]["max_different_pixel_ratio"] = 1
        assert tolerant is not None and tolerant.verdict == "tolerated"
        assert tolerant.limits["max_different_pixel_ratio"] == 0.15
        assert tolerant.pixel_diff_ratio is not None and 0 < tolerant.pixel_diff_ratio <= 0.15
    else:
        assert (
            report.pixel_diff_ratio == report.mean_absolute_error == report.max_channel_delta == 0
        )


def test_pdf_retains_text_vectors_and_reports_masked_pixels(tmp_path):
    """Measured PDF retains searchable text, vector paths and one explained masked bitmap."""
    pdfium = require_pypdfium2()
    # Given: native text and a shape beside a masked green fragment
    scene = (
        Canvas(120, 60)
        .background(color="#FFFFFF")
        .text("Hi", position=(5, 5), size=16, font="assets/fonts/Roboto-Regular.ttf", id="text")
        .shape("rectangle", (5, 35), 10, 10, "#FF0000", id="vector")
        .shape(
            "rectangle",
            (70, 5),
            20,
            20,
            "#00FF00",
            id="mask",
            mask={"shape": "ellipse", "position": (70, 5), "width": 20, "height": 20},
        )
    )

    # When: exporting and reopening actual measured bytes with PDFium
    path = tmp_path / "mixed.pdf"
    result = scene.export(path, policy=policy(ratio=1, similarity=0))
    with pdfium.PdfDocument(path) as document:
        page = document[0]
        text = page.get_textpage()
        assert "Hi" in text.get_text_range()
        text.close()
        types = [item.type for item in page.get_objects()]
        assert pdfium.raw.FPDF_PAGEOBJ_TEXT in types and pdfium.raw.FPDF_PAGEOBJ_PATH in types
        assert types.count(pdfium.raw.FPDF_PAGEOBJ_IMAGE) == 1
        bitmap = page.render(scale=1, fill_color=(0, 0, 0, 0))
        assert bitmap.to_pil().getpixel((80, 15)) == (0, 255, 0, 255)
        bitmap.close()
        page.close()

    # Then: native content remains native and global measurements do not blame the masked layer
    routes = [item for item in result.capability_report if item.feature == "layer_representation"]
    assert [(item.layer_id, item.support) for item in routes] == [
        ("layer:0", "native"),
        ("text", "native"),
        ("vector", "native"),
        ("mask", "fallback"),
    ]
    (fallback,) = result.fallback_diagnostics
    assert (
        fallback.layer_id == "mask"
        and fallback.native_attempt is False
        and "mask" in fallback.reason
    )
    assert fallback.pixel_diff_ratio is None and fallback.hash_similarity is None


@pytest.mark.parametrize("pages,width", [(2, 16), (1, 15.5), (1, 8)])
def test_pdf_rejects_page_structure_without_changing_bytes(tmp_path, monkeypatch, pages, width):
    """Page count and point dimensions remain mandatory under permissive pixel limits."""
    require_pypdfium2()
    from reportlab.pdfgen.canvas import Canvas as PdfCanvas

    # Given: an exporter defect changes page geometry or adds an extra page
    buffer = BytesIO()
    document = PdfCanvas(buffer, pagesize=(width, 16))
    for _ in range(pages):
        document.setFillColorRGB(1, 1, 1)
        document.rect(0, 0, width, 16, fill=1, stroke=0)
        document.showPage()
    document.save()
    produced = buffer.getvalue()
    monkeypatch.setattr(PdfExporter, "export_bytes", lambda self: produced)

    # When: policy permits any pixel/hash error but still requires the Canvas page contract
    path = tmp_path / "changed.pdf"
    report = (
        Canvas(16, 16)
        .background(color="#FFFFFF")
        .export(path, policy=policy(ratio=1, similarity=0))
        .pixel_metrics.fidelity
    )

    # Then: no resize, page dropping or replacement representation hides the mismatch
    assert report is not None and report.verdict == "out_of_policy"
    assert report.page_count == pages and report.page_size_points == (width, 16)
    assert report.actual_width == (8 if width == 8 else 16)
    assert path.read_bytes() == produced


@pytest.mark.parametrize("failure", ["unavailable", "invalid-pdf"])
def test_pdf_observer_failure_preserves_destination(tmp_path, monkeypatch, failure):
    """Optional renderer absence and malformed PDF bytes fail before replacing the destination."""
    # Given: default PDF exports work without importing the optional observer
    scene = Canvas(16, 16).background(color="#FFFFFF")
    path = tmp_path / "existing.pdf"
    if failure == "unavailable":
        original = builtins.__import__

        def unavailable(name, *args, **kwargs):
            if name == "pypdfium2":
                raise ImportError("observer unavailable")
            return original(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", unavailable)
        assert scene.export(path).pixel_metrics.fidelity is None
    else:
        require_pypdfium2()
        monkeypatch.setattr(PdfExporter, "export_bytes", lambda self: b"broken PDF")
    path.write_bytes(b"keep")

    # When/Then: requesting observation fails honestly and leaves the caller's file intact
    with pytest.raises(RenderingError) as error:
        scene.export(path, policy=policy())
    assert error.value.code == (
        "fidelity_unavailable" if failure == "unavailable" else "fidelity_comparison_failed"
    )
    assert path.read_bytes() == b"keep"
    with pytest.raises(ValidationError, match="single Canvas"):
        Deck(16, 16).slide(scene).export(path, policy=policy())
    assert path.read_bytes() == b"keep"
