"""Path gradients share shape paint semantics while keeping a fixed, clipped frame."""

import json
import xml.etree.ElementTree as ET
from typing import cast

import jsonschema
import pytest
from PIL import Image, ImageChops
from quickthumb import Canvas, LinearGradient, RadialGradient, canvas_json_schema


@pytest.mark.parametrize("color", [None, "#FF000000"])
def test_gradient_replaces_flat_color_and_retains_alpha_through_holes(color, tmp_path):
    """A path's gradient replaces its flat color and multiplies stop alpha by even-odd coverage."""
    # Given: a gradient with transparent stops, an even-odd hole, and an independent solid stroke
    canvas = Canvas(100, 100).path(
        "M10 10H90V90H10ZM35 35H65V65H35Z",
        (0, 0),
        100,
        100,
        color,
        fill=LinearGradient(angle=90, stops=[("#0000FF00", 0), ("#0000FFFF", 1)]),
        stroke="#FF0000",
        stroke_width=4,
    )
    encoded = canvas.to_json()
    jsonschema.validate(json.loads(encoded), canvas_json_schema())

    # When: restoring the actual public document and exporting its RGBA pixels
    restored = Canvas.from_json(encoded)
    destination = tmp_path / "gradient.png"
    restored.export(destination)
    with Image.open(destination) as image:
        actual = image.convert("RGBA")

    # Then: fill alpha ramps, the hole stays empty, and solid stroke is painted above the gradient
    alpha = actual.getchannel("A")
    assert 30 < cast(int, alpha.getpixel((20, 20))) < cast(int, alpha.getpixel((20, 80))) < 240
    assert actual.getpixel((50, 50)) == (0, 0, 0, 0)
    assert actual.getpixel((10, 50)) == pytest.approx((255, 0, 0, 255), abs=2)
    assert actual.convert("RGB").getpixel((20, 80)) == (0, 0, 255)
    assert actual.tobytes() == restored.sample().frames[0].to_image().tobytes()


@pytest.mark.parametrize(
    "fill",
    [
        LinearGradient(angle=0, stops=[("#000000", 0), ("#FFFFFF", 1)]),
        LinearGradient(angle=33, stops=[("#000000", 0), ("#FFFFFF", 1)]),
        RadialGradient(center=(0.25, 0.5), stops=[("#000000", 0), ("#FFFFFF", 1)]),
    ],
)
def test_gradient_uses_fixed_frame_after_anisotropic_viewbox_mapping(fill):
    """Path gradients match the fixed-frame shape field instead of fitting paint bounds."""
    # Given: an offset local viewBox mapping a partial path into a stretched frame
    path = Canvas(200, 100).path(
        "M0 20H60V50H0Z",
        (0, 0),
        200,
        100,
        None,
        view_box=(-20, 10, 100, 50),
        fill=fill,
    )
    reference = Canvas(200, 100).shape("rectangle", (0, 0), 200, 100, "#FF0000", fill=fill)

    # When: sampling an interior rectangle from the path and the existing shape gradient
    actual = path.render_frame(0)
    expected = reference.render_frame(0)
    difference = ImageChops.difference(
        actual.crop((45, 25, 155, 75)), expected.crop((45, 25, 155, 75))
    )

    # Then: colors agree within raster sampling precision and the unpainted frame stays transparent
    assert max(cast(int, band.getextrema()[1]) for band in difference.split()) <= 2
    assert actual.getpixel((20, 50)) == (0, 0, 0, 0)


@pytest.mark.parametrize(
    "fill",
    [
        LinearGradient(angle=33, stops=[("#00336680", 0), ("#42CEB7FF", 0.4), ("#FFFFFF00", 1)]),
        RadialGradient(
            center=(0.2, 0.7), stops=[("#00336680", 0), ("#42CEB7FF", 0.4), ("#FFFFFF00", 1)]
        ),
    ],
)
def test_clipping_crops_gradient_without_restarting_its_field(fill):
    """Clipping a gradient path retains its frame coordinates and transparent-stop colors."""
    # Given: the same path painted in full and offset partly outside a smaller canvas
    full = Canvas(180, 120).path("M20 10H160V110H20Z", (0, 0), 180, 120, None, fill=fill)
    clipped = Canvas(70, 70).path("M20 10H160V110H20Z", (-50, -30), 180, 120, None, fill=fill)

    # When: comparing the visible path with the corresponding area of the full render
    expected = full.render_frame(0).crop((50, 30, 120, 100))
    actual = clipped.render_frame(0)
    difference = ImageChops.difference(actual, expected)

    # Then: clipping does not shift, stretch or reset the color/alpha field
    assert max(cast(int, band.getextrema()[1]) for band in difference.split()) <= 1


def test_svg_native_fill_preserves_gradient_stops(tmp_path):
    """SVG emits a path gradient rather than substituting flat color or a raster image."""
    # Given: a gradient path with a visibly different flat color
    canvas = Canvas(80, 60).path(
        "M5 5H75V55H5Z",
        (0, 0),
        80,
        60,
        "#FF0000",
        fill=LinearGradient(angle=90, stops=[("#000000", 0), ("#FFFFFF", 1)]),
    )

    # When: exporting native SVG output
    destination = tmp_path / "path.svg"
    result = canvas.export(destination)
    root = ET.parse(destination)

    # Then: the gradient and path remain vectors and the report declares native support
    assert root.find(".//{http://www.w3.org/2000/svg}path") is not None
    assert root.find(".//{http://www.w3.org/2000/svg}image") is None
    assert [
        stop.get("stop-color") for stop in root.findall(".//{http://www.w3.org/2000/svg}stop")
    ] == ["#000000", "#FFFFFF"]
    assert [(item.feature, item.support) for item in result.capability_report] == [
        ("path", "native"),
        ("layer_representation", "native"),
    ]


@pytest.mark.parametrize(
    "fill,low,high",
    [
        (LinearGradient(angle=0, stops=[("#000000", 0), ("#FFFFFF", 1)]), 0, 60),
        (RadialGradient(stops=[("#000000", 0), ("#FFFFFF", 1)]), 150, 220),
    ],
)
def test_large_frame_gradient_allocates_only_visible_region(fill, low, high, monkeypatch):
    """A huge path frame paints a small visible gradient without allocating a full-frame ramp."""
    # Given: a small visible canvas inside a million-pixel path frame and an allocation guard
    original_new, original_resize = Image.new, Image.Image.resize

    def new(mode, size, *args, **kwargs):
        assert size[0] * size[1] <= 1_000_000
        return original_new(mode, size, *args, **kwargs)

    def resize(image, size, *args, **kwargs):
        assert size[0] * size[1] <= 1_000_000
        return original_resize(image, size, *args, **kwargs)

    monkeypatch.setattr(Image, "new", new)
    monkeypatch.setattr(Image.Image, "resize", resize)
    canvas = Canvas(32, 32).path(
        "M0 0H1000000V1000000H0Z",
        (0, 0),
        1_000_000,
        1_000_000,
        None,
        fill=fill,
    )

    # When: rendering only the visible intersection of the path frame
    image = canvas.render_frame(0)

    # Then: real opaque gradient pixels are produced within the bounded allocation budget
    assert image.size == (32, 32)
    assert image.getchannel("A").getpixel((16, 16)) == 255
    assert low < cast(int, image.getchannel("R").getpixel((16, 16))) < high
