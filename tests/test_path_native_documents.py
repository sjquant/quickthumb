"""Native path documents preserve paint, viewport, identities and bounded fallbacks."""

import io
import re
import xml.etree.ElementTree as ET
from typing import cast

import pytest
from PIL import Image
from quickthumb import Canvas, Deck, ExportPolicy, LinearGradient, RadialGradient
from quickthumb.errors import RenderingError

from tests._optional import require_cairosvg

NS = "{http://www.w3.org/2000/svg}"


@pytest.mark.parametrize("format", ["svg", "html"])
@pytest.mark.parametrize(
    "fill",
    [
        LinearGradient(
            angle=33,
            stops=[("#00336680", 0.123456), ("#42CEB7FF", 0.456789), ("#FFFFFF20", 0.923456)],
        ),
        RadialGradient(
            center=(0.25, 0.6), stops=[("#00336680", 0), ("#42CEB7FF", 0.5), ("#FFFFFF20", 1)]
        ),
    ],
)
def test_native_paths_keep_frame_gradient_alpha_and_holes(format, fill, tmp_path):
    """Native SVG and HTML retain frame gradients through an offset, stretched viewport."""
    cairo = require_cairosvg()
    # Given: a local even-odd ring with an independent solid stroke and a source identity
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
        id="ring.source",
        motion_key="shared.key",
    )

    # When: exporting with strict policy and rasterizing the actual native SVG content
    result = canvas.export(
        tmp_path / f"path.{format}", policy=ExportPolicy(unsupported_motion="error")
    )
    text = (tmp_path / f"path.{format}").read_text()
    svg = re.findall(r"<svg\b[^>]*data-qt-source-id=[^>]*>.*?</svg>", text, flags=re.S)[0]
    root = ET.fromstring(svg)
    actual = Image.open(io.BytesIO(cairo.svg2png(bytestring=svg.encode()))).convert("RGBA")
    expected = canvas.render_frame(0)

    # Then: native paths retain interior color and alpha within sampling precision
    assert root.find(f".//{NS}path") is not None and root.find(f".//{NS}image") is None
    assert any(node.get("data-qt-source-id") == "ring.source" for node in root.iter(f"{NS}svg"))
    for point in ((40, 20), (40, 70), (160, 80)):
        a = cast(tuple[int, ...], actual.getpixel(point))
        b = cast(tuple[int, ...], expected.getpixel(point))
        assert max(abs(x - y) for x, y in zip(a, b, strict=True)) <= 5
    assert actual.getpixel((100, 50)) == (0, 0, 0, 0)
    assert [(d.support, d.fallback) for d in result.capability_report] == [("native", None)]
    assert not result.fallback_diagnostics


@pytest.mark.parametrize("join,corner", [("miter", 255), ("bevel", 0), ("round", 0)])
def test_native_dash_crosses_corner_with_selected_join(join, corner):
    """Native dashes preserve their local join across a corner and leave the following gap clear."""
    cairo = require_cairosvg()
    # Given: a dash crossing the bend with precise local stroke controls
    canvas = Canvas(90, 90).path(
        "M20 60H60V20",
        (0, 0),
        90,
        90,
        None,
        stroke="#42CEB7",
        stroke_width=20,
        line_join=join,
        line_cap="butt",
        miter_limit=4,
        dash_array=(60, 20),
        dash_offset=0,
    )

    # When: rendering the emitted native path with Cairo
    svg = canvas.to_svg()
    image = Image.open(io.BytesIO(cairo.svg2png(bytestring=svg.encode()))).convert("RGBA")
    path = ET.fromstring(svg).find(f".//{NS}path")

    # Then: geometry follows the chosen join, and cap/dash properties remain explicit vectors
    assert path is not None
    assert path.get("stroke-linejoin") == join and path.get("stroke-linecap") == "butt"
    assert path.get("stroke-dasharray") == "60 20"
    assert abs(cast(int, image.getchannel("A").getpixel((68, 68))) - corner) <= 5
    assert image.getpixel((60, 25)) == (0, 0, 0, 0)


def test_native_viewport_clips_paint_to_its_frame():
    """A native path clips distant geometry to its partially off-canvas fixed viewport."""
    cairo = require_cairosvg()
    # Given: a large filled path inside a partly off-canvas twenty-pixel viewport
    canvas = Canvas(40, 30).path("M-10000 -10000H10000V10000H-10000Z", (-5, 4), 20, 20, "#FF0000")

    # When: rendering the actual native document
    image = Image.open(io.BytesIO(cairo.svg2png(bytestring=canvas.to_svg().encode()))).convert(
        "RGBA"
    )

    # Then: only the visible viewport intersection is painted
    assert image.getpixel((0, 4)) == image.getpixel((14, 23)) == (255, 0, 0, 255)
    assert image.getpixel((15, 8)) == image.getpixel((5, 24)) == (0, 0, 0, 0)


def test_html_deck_namespaces_native_gradient_ids(tmp_path):
    """HTML slides retain independent native gradients and shared motion identity."""
    # Given: two slides reusing authored source/motion IDs with different gradient colors
    slides = [
        Canvas(100, 100).path(
            "M10 10H90V90H10Z",
            (0, 0),
            100,
            100,
            None,
            fill=LinearGradient(angle=0, stops=[(color, 0), ("#FFFFFF", 1)]),
            id="same",
            motion_key="match.key",
        )
        for color in ("#FF0000", "#0000FF")
    ]

    # When: exporting both native path fragments in one HTML document
    destination = tmp_path / "deck.html"
    Deck(slides=slides).export(destination)
    text = destination.read_text()
    roots = [
        ET.fromstring(svg)
        for svg in re.findall(r"<svg\b[^>]*data-qt-source-id=[^>]*>.*?</svg>", text, flags=re.S)
    ]

    # Then: each gradient reference resolves in its own fragment without cross-slide ID collisions
    assert len(roots) == 2 and text.count('data-qt-motion-key="match.key"') == 2
    ids = [root.findall(f".//{NS}linearGradient")[0].get("id") for root in roots]
    assert len(set(ids)) == 2
    assert [root.findall(f".//{NS}stop")[0].get("stop-color") for root in roots] == [
        "#FF0000",
        "#0000FF",
    ]
    assert [root.findall(f".//{NS}path")[0].get("fill") for root in roots] == [
        f"url(#{value})" for value in ids
    ]


@pytest.mark.parametrize("format", ["svg", "html"])
@pytest.mark.parametrize("source", ["translated", "huge", "gradient"])
def test_native_limits_report_actual_raster_route_and_preserve_strict_output(
    format, source, tmp_path
):
    """Numeric extremes and unsupported stops use declared raster fallback and strict refusal."""
    # Given: valid canonical geometry beyond native SVG precision or stop interpolation bounds
    o = 10**14
    d = f"M{o + 5} {o + 50}A45 45 0 0 1 {o + 95} {o + 50}A45 45 0 0 1 {o + 5} {o + 50}Z"
    options = {
        "translated": (d, (o, o, 100, 100), None),
        "huge": ("M0 0H1e308V1e308H0Z", (0, 0, 1e308, 1e308), None),
        "gradient": (
            "M0 0H100V100H0Z",
            None,
            LinearGradient(angle=0, stops=[("#000000", -1), ("#FFFFFF", 1)]),
        ),
    }
    data, view_box, fill = options[source]
    canvas = Canvas(100, 100).path(
        data, (0, 0), 100, 100, "#42CEB7", view_box=view_box, fill=fill, id="bounded"
    )

    # When: exporting with fallback and then requesting strict native output
    destination = tmp_path / f"limited.{format}"
    result = canvas.export(destination)
    original = destination.read_bytes()
    with pytest.raises(RenderingError) as error:
        canvas.export(destination, policy=ExportPolicy(unsupported_motion="error"))

    # Then: content, diagnostics and strict policy agree on the actual rasterized source layer
    assert b"data:image/png;base64," in original
    assert result.fallback_diagnostics[0].layer_id == "bounded"
    assert "native SVG" in result.fallback_diagnostics[0].reason
    assert (
        error.value.code == "unsupported_capability"
        and error.value.details[0].path == "/layers/0/d"
    )
    assert destination.read_bytes() == original


@pytest.mark.parametrize(
    "cap,axis,corner", [("butt", 0, 0), ("round", 255, 0), ("square", 255, 255)]
)
def test_native_caps_scale_in_local_units(cap, axis, corner):
    """Native endpoint caps retain their local shape under anisotropic viewport scaling."""
    cairo = require_cairosvg()
    # Given: a local stroke stretched twice as far horizontally
    canvas = Canvas(160, 60).path(
        "M20 30H60",
        (0, 0),
        160,
        60,
        None,
        view_box=(0, 0, 80, 60),
        stroke="#42CEB7",
        stroke_width=20,
        line_cap=cap,
    )

    # When: rendering the actual native viewport
    image = Image.open(io.BytesIO(cairo.svg2png(bytestring=canvas.to_svg().encode()))).convert(
        "RGBA"
    )
    alpha = image.getchannel("A")

    # Then: both cap extension and square corners scale with the local geometry
    assert abs(cast(int, alpha.getpixel((24, 30))) - axis) <= 5
    assert abs(cast(int, alpha.getpixel((22, 21))) - corner) <= 5


@pytest.mark.parametrize("offset,seam", [(10, 255), (40, 0)])
def test_native_closed_dash_seam_preserves_join_and_gap(offset, seam):
    """Native closed-path dashes join painted runs across the seam and preserve an offset gap."""
    cairo = require_cairosvg()
    # Given: a closed square with its seam inside an on interval or an off interval
    canvas = Canvas(80, 80).path(
        "M20 20H60V60H20Z",
        (0, 0),
        80,
        80,
        None,
        stroke="#42CEB7",
        stroke_width=8,
        line_join="miter",
        line_cap="butt",
        dash_array=(30, 20),
        dash_offset=offset,
    )

    # When: drawing the native SVG stroke
    alpha = (
        Image.open(io.BytesIO(cairo.svg2png(bytestring=canvas.to_svg().encode())))
        .convert("RGBA")
        .getchannel("A")
    )

    # Then: the seam's outer miter is painted only when both adjacent runs are on
    assert abs(cast(int, alpha.getpixel((17, 17))) - seam) <= 5


@pytest.mark.parametrize("cap", ["round", "square"])
@pytest.mark.parametrize(
    "d,emitted,alpha",
    [
        ("M20 20A5 5 0 0 0 20 20Z", "M20 20", 0),
        ("M20 20Z", "M20 20", 0),
        ("M10 20L30 20Z", "M10 20 L30 20 Z", 255),
    ],
)
def test_native_empty_subpaths_omit_closepath_but_keep_explicit_lines(cap, d, emitted, alpha):
    """Empty native subpaths omit closepath while explicit lines retain their native stroke."""
    cairo = require_cairosvg()
    # Given: an empty subpath or an explicit nonempty line control
    canvas = Canvas(40, 40).path(
        d,
        (0, 0),
        40,
        40,
        None,
        stroke="#42CEB7",
        stroke_width=10,
        line_cap=cap,
    )

    # When: rendering the actual native document
    svg = canvas.to_svg()
    image = Image.open(io.BytesIO(cairo.svg2png(bytestring=svg.encode()))).convert("RGBA")

    # Then: emitted commands prevent phantom caps without suppressing the nonempty line
    path = ET.fromstring(svg).find(f".//{NS}path")
    assert path is not None and path.get("d") == emitted
    assert image.getchannel("A").getpixel((20, 20)) == alpha
    assert canvas.render_frame(0).getchannel("A").getpixel((20, 20)) == alpha


@pytest.mark.parametrize("cap", ["round", "square"])
def test_native_explicit_zero_length_line_keeps_its_drawing_command(cap):
    """Explicit zero-length lines retain SVG drawing commands and canonical cap dots."""
    # Given: an explicit zero-length line that must not be treated as an empty moveto
    canvas = Canvas(40, 40).path(
        "M20 20L20 20Z", (0, 0), 40, 40, None, stroke="#42CEB7", stroke_width=10, line_cap=cap
    )

    # When: emitting its native SVG data
    path = ET.fromstring(canvas.to_svg()).find(f".//{NS}path")

    # Then: zero-length drawing remains explicit and its canonical cap remains painted
    assert path is not None and path.get("d") == "M20 20 L20 20 Z"
    assert canvas.render_frame(0).getchannel("A").getpixel((20, 20)) == 255
