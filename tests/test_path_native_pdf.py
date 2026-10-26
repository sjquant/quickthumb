"""Native PDF paths preserve editable curves, paint and declared bounded fallbacks."""

import builtins
import io
from typing import cast

import pytest
from quickthumb import Canvas, ExportPolicy, LinearGradient, RadialGradient
from quickthumb.errors import RenderingError

from tests._optional import require_pypdfium2


@pytest.mark.parametrize(
    "d",
    [
        "M10 50A40 40 30 1 1 90 50A40 40 30 1 1 10 50Z",
        "M10 50Q50 -20 90 50T10 50Z",
        "M10 50C10 -10 90 -10 90 50S10 110 10 50Z",
    ],
)
def test_pdf_curves_are_editable_and_keep_even_odd_holes(d, tmp_path):
    """PDF exports retain curved path objects and an unpainted interior hole."""
    pdfium = require_pypdfium2()
    # Given: a curved outer contour with a rectangular even-odd hole
    canvas = Canvas(100, 100).path(
        d + "M40 40H60V60H40Z", (0, 0), 100, 100, "#FF0000", id="curve.source"
    )
    # When: exporting natively under strict policy and opening the actual PDF
    destination = tmp_path / "curve.pdf"
    result = canvas.export(destination, policy=ExportPolicy(unsupported_motion="error"))
    document = pdfium.PdfDocument(destination)
    page = document[0]
    image = page.render(scale=1).to_pil().convert("RGB")
    # Then: editable vectors preserve paint and holes without an embedded raster
    assert [obj.type for obj in page.get_objects()] == [2]
    assert image.getpixel((50, 50)) == (255, 255, 255)
    assert image.getpixel((50, 25)) == (255, 0, 0)
    assert [(d.layer_id, d.support, d.fallback) for d in result.capability_report] == [
        ("curve.source", "native", None)
    ]


@pytest.mark.parametrize(
    "fill",
    [
        LinearGradient(angle=33, stops=[("#003366", 0), ("#42CEB7", 0.5), ("#FFFFFF", 1)]),
        RadialGradient(center=(0.25, 0.6), stops=[("#003366", 0), ("#FFFFFF", 1)]),
    ],
)
def test_pdf_gradients_follow_fixed_frame_with_independent_stroke(fill):
    """PDF shading preserves an offset stretched viewport, a hole and a separate solid stroke."""
    pdfium = require_pypdfium2()
    # Given: an anisotropic local viewBox with a frame-referenced opaque gradient
    canvas = Canvas(200, 100).path(
        "M20 30H100V110H20ZM45 55H75V85H45Z",
        (0, 0),
        200,
        100,
        None,
        view_box=(10, 20, 100, 100),
        fill=fill,
        stroke="#FF0000",
        stroke_width=3,
    )
    # When: rasterizing the actual PDF at its authored dimensions
    document = pdfium.PdfDocument(io.BytesIO(canvas.to_pdf()))
    page = document[0]
    image = page.render(scale=1).to_pil().convert("RGB")
    expected = canvas.render_frame(0).convert("RGB")
    # Then: shading remains native and interior colors follow the canonical frame gradient
    assert 3 not in [obj.type for obj in page.get_objects()]
    assert 4 in [obj.type for obj in page.get_objects()]
    for point in ((40, 20), (40, 70), (160, 80)):
        assert (
            max(
                abs(a - b)
                for a, b in zip(
                    image.getpixel(point),
                    cast(tuple[int, ...], expected.getpixel(point)),
                    strict=True,
                )
            )
            <= 5
        )
    assert image.getpixel((100, 50)) == (255, 255, 255)
    assert image.getpixel((20, 20)) == (255, 0, 0)


@pytest.mark.parametrize("cap,tip", [("butt", 255), ("round", 0), ("square", 0)])
def test_pdf_dashes_preserve_caps_joins_and_viewport_clip(cap, tip):
    """Native PDF local strokes retain their cap, corner join and fixed-frame clipping."""
    pdfium = require_pypdfium2()
    # Given: a dash crossing a corner and another segment crossing the viewport boundary
    canvas = Canvas(100, 100).path(
        "M20 60H60V20M-20 85H120",
        (0, 0),
        90,
        90,
        None,
        stroke="#000000",
        stroke_width=20,
        line_cap=cap,
        line_join="miter",
        dash_array=(60, 20),
        dash_offset=0,
    )
    # When: opening the vector PDF and rendering its actual stroked objects
    document = pdfium.PdfDocument(canvas.to_pdf())
    page = document[0]
    image = page.render(scale=1).to_pil().convert("RGB")
    # Then: cap extent, a miter tip and clipping match the declared local geometry
    assert all(obj.type == 2 for obj in page.get_objects())
    assert image.getpixel((60, 32))[0] == tip
    assert image.getpixel((67, 67)) == (0, 0, 0)
    assert image.getpixel((95, 85)) == (255, 255, 255)


@pytest.mark.parametrize(
    "kwargs,reason",
    [
        (
            {"fill": LinearGradient(angle=0, stops=[("#FF000080", 0), ("#FFFFFF", 1)])},
            "translucent",
        ),
        ({"view_box": (1e14, 1e14, 100, 100)}, "precision"),
        ({"fill": LinearGradient(angle=0, stops=[("#000000", -1), ("#FFFFFF", 1)])}, "0..1"),
    ],
)
def test_pdf_fallback_diagnostics_and_strict_prewrite_agree(kwargs, reason, tmp_path):
    """Unsupported PDF paint or numeric ranges report their source and fail before overwriting."""
    pdfium = require_pypdfium2()
    # Given: a visible path whose native paint or coordinates cannot be preserved
    origin = 1e14 if "view_box" in kwargs else 0
    canvas = Canvas(100, 100).path(
        f"M{origin} {origin}h100v100h-100Z",
        (0, 0),
        100,
        100,
        "#FF0000",
        id="fallback.source",
        **kwargs,
    )
    destination = tmp_path / "fallback.pdf"
    # When: exporting the raster fallback and then requesting strict native output
    result = canvas.export(destination)
    original = destination.read_bytes()
    with pytest.raises(RenderingError) as error:
        canvas.export(destination, policy=ExportPolicy(unsupported_motion="error"))
    # Then: actual raster content, source diagnostics and prewrite refusal remain consistent
    document = pdfium.PdfDocument(original)
    assert 3 in [obj.type for obj in document[0].get_objects()]
    assert reason in result.fallback_diagnostics[0].reason
    assert result.fallback_diagnostics[0].layer_id == "fallback.source"
    assert error.value.details[0].path == "/layers/0/d"
    assert destination.read_bytes() == original


@pytest.mark.parametrize("d", ["M20 20", "M20 20Z", "M20 20A5 5 0 0 0 20 20Z"])
def test_pdf_empty_subpaths_leave_the_page_unpainted(d):
    """Move-only and omitted-arc subpaths paint no fill or cap in the PDF."""
    pdfium = require_pypdfium2()
    # Given: a subpath with no retained drawing command
    canvas = Canvas(40, 40).path(
        d, (0, 0), 40, 40, None, stroke="#FF0000", stroke_width=10, line_cap="round"
    )
    # When: rendering the actual native PDF
    document = pdfium.PdfDocument(canvas.to_pdf())
    image = document[0].render().to_pil().convert("RGB")
    # Then: PDF's implicit degenerate caps do not introduce paint
    assert image.getextrema() == ((255, 255), (255, 255), (255, 255))


@pytest.mark.parametrize("cap", ["butt", "square"])
def test_pdf_zero_length_strokes_use_declared_canonical_fallback(cap, tmp_path):
    """Degenerate PDF strokes fall back to preserve the authored cap's actual pixels."""
    pdfium = require_pypdfium2()
    # Given: an explicit zero-length segment whose PDF cap rendering is not faithful
    canvas = Canvas(40, 40).path(
        "M20 20L20 20",
        (0, 0),
        40,
        40,
        None,
        stroke="#FF0000",
        stroke_width=10,
        line_cap=cap,
    )
    # When: exporting and opening the actual PDF
    destination = tmp_path / "cap.pdf"
    result = canvas.export(destination)
    document = pdfium.PdfDocument(destination)
    image = document[0].render().to_pil().convert("RGB")
    # Then: fallback is explicit and preserves empty butt or filled square corners
    assert "zero-length stroke" in result.fallback_diagnostics[0].reason
    expected = (255, 255, 255) if cap == "butt" else (255, 0, 0)
    assert max(abs(a - b) for a, b in zip(image.getpixel((17, 17)), expected, strict=True)) <= 3


@pytest.mark.parametrize("source", ["tiny", "zero_dash"])
def test_pdf_specific_limits_preserve_pixels_and_explain_the_route(source, tmp_path):
    """PDF decimal precision and zero dash limits use an explicit pixel-faithful fallback."""
    pdfium = require_pypdfium2()
    # Given: valid canonical geometry not faithfully representable by PDF's native route
    if source == "tiny":
        canvas = Canvas(20, 20).path(
            "M0 0H1e-8V1e-8H0Z", (0, 0), 20, 20, "#FF0000", view_box=(0, 0, 1e-8, 1e-8)
        )
    else:
        canvas = Canvas(20, 20).path(
            "M2 10H18",
            (0, 0),
            20,
            20,
            None,
            stroke="#FF0000",
            stroke_width=4,
            dash_array=(0, 4),
            line_cap="butt",
        )
    # When: exporting normally and requesting strict output against the same destination
    destination = tmp_path / "bounded.pdf"
    result = canvas.export(destination)
    original = destination.read_bytes()
    with pytest.raises(RenderingError):
        canvas.export(destination, policy=ExportPolicy(unsupported_motion="error"))
    document = pdfium.PdfDocument(original)
    image = document[0].render().to_pil().convert("RGB")
    # Then: fallback keeps a tiny full-frame fill or empty zero butt dashes and preserves output
    expected = (255, 0, 0) if source == "tiny" else (255, 255, 255)
    assert image.getpixel((10, 10)) == expected
    assert result.fallback_diagnostics
    assert destination.read_bytes() == original


@pytest.mark.parametrize("action", ["validate", "export"])
def test_missing_pdf_extra_gives_install_guidance(action, monkeypatch, tmp_path):
    """Public PDF validation and export report the optional dependency's installation command."""
    # Given: a native path in an installation without the optional PDF engine
    canvas = Canvas(20, 20).path("M0 0H20V20H0Z", (0, 0), 20, 20)
    original_import = builtins.__import__

    def without_reportlab(name, *args, **kwargs):
        if name == "reportlab" or name.startswith("reportlab."):
            raise ModuleNotFoundError("No module named 'reportlab'")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", without_reportlab)
    destination = tmp_path / "missing.pdf"
    # When: querying the actual route or exporting through the public API
    with pytest.raises(RenderingError, match=r"pip install 'quickthumb\[pdf\]'$") as error:
        if action == "validate":
            canvas.validate_export("pdf")
        else:
            canvas.export(destination)
    # Then: installation guidance is not mislabeled as a geometry fallback, and no file is created
    assert "reportlab is required for PDF export" in str(error.value)
    assert not destination.exists()
