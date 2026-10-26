"""Filled SVG paths share static raster, JSON, and document inspection contracts."""

import json
from typing import cast

import jsonschema
import pytest
from PIL import Image
from quickthumb import Canvas, Deck, ExportPolicy, PathLayer, canvas_json_schema
from quickthumb.errors import RenderingError, ValidationError


@pytest.mark.parametrize(
    "d",
    ["M5 5H25V20H5Z", "m5,5 20,0v15h-20z", "M5 5L25 5 25 20 5 20", "M5 5C5 5 25 5 25 5V20H5Z"],
)
def test_path_roundtrip_and_viewport(d, tmp_path):
    """A path retains its fixed viewport and pixels through schema, JSON, Deck and PNG."""
    # Given: local SVG coordinates mapped into a positioned fixed-size frame
    canvas = Canvas(60, 50).path(
        d, (10, 12), 40, 30, "#FF0000", view_box=(5, 5, 20, 15), id="badge"
    )

    # When: the same document is observed through JSON, Deck, and a PNG export
    encoded = canvas.to_json()
    jsonschema.validate(json.loads(encoded), canvas_json_schema())
    restored = Canvas.from_json(encoded)
    capture = restored.sample()
    result = Deck(slides=[restored]).export(tmp_path / "path.png")

    # Then: the frame and identity remain stable, with the same actual filled pixels
    assert isinstance(restored.layers[0], PathLayer)
    layer = restored.inspect().layers[0]
    assert layer.id == "badge" and layer.type == "path"
    assert layer.bbox is not None
    assert (layer.bbox.x, layer.bbox.y, layer.bbox.width, layer.bbox.height) == (10, 12, 40, 30)
    frame = capture.frames[0].to_image()
    assert frame.getpixel((20, 20)) == (255, 0, 0, 255)
    assert frame.getpixel((0, 0)) == (0, 0, 0, 0)
    with Image.open(result.written_paths[0]) as image:
        assert image.convert("RGBA").tobytes() == frame.tobytes()


@pytest.mark.parametrize(
    "d",
    [
        "M2 2H46V46H2Z M10 10H38V38H10Z",
        "M24 2L37 44 3 18 45 18 11 44Z",
    ],
)
def test_even_odd_fill_and_antialiasing(d):
    """Same-direction contours and a self-intersecting star retain their even-odd holes."""
    # Given: a path whose central region has two crossings
    canvas = Canvas(48, 48).path(d, (0, 0), 48, 48, "#42CEB7")

    # When: its alpha is rendered at the public frame boundary
    alpha = canvas.render_frame(0).getchannel("A")

    # Then: the hole is transparent, outer ink is opaque, and edges are antialiased
    assert alpha.getpixel((24, 24)) == 0
    assert alpha.getpixel((24, 5)) == 255
    assert any(0 < value < 255 for value in alpha.tobytes())


@pytest.mark.parametrize(
    "d,view_box,height",
    [
        ("M-1e9 -1e9H1e9V1e9H-1e9Z", None, 10),
        ("M0 0H1e308V1e308H0Z", (0, 0, 1e308, 1e308), 20),
        ("M-5e307 -5e307H5e307V5e307H-5e307Z", (-5e307, -5e307, 1e308, 1e308), 20),
    ],
)
def test_viewport_clips_large_paths_and_off_canvas_frames(d, view_box, height):
    """Large SVG coordinates paint only the viewport's visible canvas intersection."""
    # Given: large SVG coordinates and a partly off-canvas viewport
    canvas = Canvas(40, 30).path(d, (-5, 4), 20, height, "#FF0000", view_box=view_box)

    # When: rendering the frame
    image = canvas.render_frame(0)

    # Then: only the intersection of the viewport and canvas is painted
    assert image.getpixel((0, 4)) == image.getpixel((14, 3 + height)) == (255, 0, 0, 255)
    assert image.getpixel((15, 8)) == image.getpixel((5, 4 + height)) == (0, 0, 0, 0)


@pytest.mark.parametrize(
    "d",
    [
        "M0 0C1 2 3 4",
        "M0 0A1 1 0 0 0 3 4",
        "M0 0Q1 2",
        "M0 0L",
        "M,,0 0",
        "L1 2",
        "M0 0H1e999",
    ],
)
def test_invalid_path_does_not_enter_document(d):
    """Malformed or unsupported SVG commands fail before a layer enters the document."""
    # Given: an otherwise empty document
    canvas = Canvas(20, 20)

    # When: authoring an unrenderable path
    with pytest.raises(ValidationError):
        canvas.path(d, (0, 0), 20, 20)

    # Then: no incomplete layer remains to fail during a later export
    assert canvas.layers == []


@pytest.mark.parametrize(
    "format,dependency", [("svg", None), ("html", "jinja2"), ("pdf", "reportlab"), ("pptx", "pptx")]
)
def test_document_raster_fallback_is_reported_and_strict_policy_preserves_output(
    format, dependency, tmp_path
):
    """Document exports report a path raster fallback and reject strict requests before writing."""
    if dependency:
        pytest.importorskip(dependency)
    # Given: a real filled path and its successful document export
    canvas = Canvas(100, 100).path("M0 0H20V20H0Z", (5, 5), 20, 20, "#FF0000", id="badge")
    destination = tmp_path / f"path.{format}"
    result = canvas.export(destination)
    original = destination.read_bytes()

    # When: the same output is requested without permitting fallback
    with pytest.raises(RenderingError) as error:
        canvas.export(destination, policy=ExportPolicy(unsupported_motion="error"))

    # Then: the real fallback and structured refusal agree, and the file is preserved
    assert original and destination.read_bytes() == original
    assert error.value.code == "unsupported_capability"
    assert error.value.details[0].path == "/layers/0/d"
    assert [(item.feature, item.target, item.fallback) for item in result.capability_report] == [
        ("path", format, "rasterize")
    ]
    assert result.fallback_diagnostics[0].layer_id == "badge"


@pytest.mark.parametrize(
    "d,explicit",
    [
        (
            "M0 50C15 0 35 0 50 50S85 100 100 50L100 100H0Z",
            "M0 50C15 0 35 0 50 50C65 100 85 100 100 50L100 100H0Z",
        ),
        (
            "m0 50c15 -50 35 -50 50 0s35 50 50 0l0 50h-100z",
            "M0 50C15 0 35 0 50 50C65 100 85 100 100 50L100 100H0Z",
        ),
        ("M0 50Q25 0 50 50T100 50L100 100H0Z", "M0 50Q25 0 50 50Q75 100 100 50L100 100H0Z"),
        ("m0 50q25 -50 50 0t50 0v50h-100z", "M0 50Q25 0 50 50Q75 100 100 50L100 100H0Z"),
        (
            "M0 50C5 0 10 0 20 50L30 50S70 0 100 50L100 100H0Z",
            "M0 50C5 0 10 0 20 50L30 50C30 50 70 0 100 50L100 100H0Z",
        ),
        ("M0 50C5 0 10 0 20 50T100 50L100 100H0Z", "M0 50C5 0 10 0 20 50Q20 50 100 50L100 100H0Z"),
    ],
)
def test_smooth_curves_match_explicit_controls(d, explicit):
    """Relative and smooth curves paint the same pixels as explicit SVG control points."""
    # Given: equivalent paths, including smooth controls reset by another command family
    compact = Canvas(100, 100).path(d, (0, 0), 100, 100, "#42CEB7")
    expanded = Canvas(100, 100).path(explicit, (0, 0), 100, 100, "#42CEB7")

    # When: rendering the actual filled paths
    image = compact.render_frame(0)
    reference = expanded.render_frame(0)

    # Then: command shorthand does not change geometry or raster output
    assert image.tobytes() == reference.tobytes()


@pytest.mark.parametrize("size,x,inside,outside", [(400, 25, 310, 300), (1600, 50, 1410, 1400)])
def test_curve_precision_follows_mapped_frame_size(size, x, inside, outside):
    """A quadratic's mapped boundary retains subpixel precision at large static frame sizes."""
    # Given: y=100-4x+0.04x² in local coordinates, enlarged through its viewBox
    canvas = Canvas(size, size).path(
        "M0 100Q50 -100 100 100Z", (0, 0), size, size, "#42CEB7", view_box=(0, 0, 100, 100)
    )

    # When: rasterizing at each target resolution
    alpha = canvas.render_frame(0).getchannel("A")

    # Then: coverage follows the analytic boundary, allowing a small antialiasing halo
    assert cast(int, alpha.getpixel((x, inside))) >= 250
    assert cast(int, alpha.getpixel((x, outside))) <= 5


def test_large_finite_curve_coordinates_map_without_overflow():
    """A huge local cubic maps to finite, correctly painted viewport pixels."""
    # Given: a cubic occupying a 20-pixel viewport despite large source coordinates
    canvas = Canvas(20, 20).path(
        "M0 0C1e308 0 1e308 1e308 0 1e308Z",
        (0, 0),
        20,
        20,
        "#42CEB7",
        view_box=(0, 0, 1e308, 1e308),
    )

    # When: rendering the mapped curve
    alpha = canvas.render_frame(0).getchannel("A")

    # Then: its convex side is filled while the region beyond the curve is empty
    assert alpha.getpixel((5, 10)) == 255
    assert alpha.getpixel((19, 10)) == 0


def test_excessive_curve_plan_preserves_existing_output(tmp_path):
    """An unrepresentably large curve fails with an actionable limit before replacing a file."""
    # Given: valid finite coordinates whose mapped curvature exceeds the bounded plan
    canvas = Canvas(20, 20).path("M0 0C1e308 0 0 1e308 20 20Z", (0, 0), 20, 20)
    destination = tmp_path / "path.png"
    destination.write_bytes(b"existing")

    # When: an export cannot reach the required curve precision within its work budget
    with pytest.raises(RenderingError) as error:
        canvas.export(destination)

    # Then: precision is not silently truncated and the existing output is untouched
    assert error.value.code == "path_subdivision_limit"
    assert "simplify d" in str(error.value)
    assert destination.read_bytes() == b"existing"
