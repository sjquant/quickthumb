"""Tests for PPTX export (Canvas.to_pptx and rendering to .pptx files)"""

from io import BytesIO
from pathlib import Path
from typing import Any

import pytest
from PIL import Image, ImageChops, ImageFilter
from quickthumb import (
    AnimationSpec,
    Canvas,
    Deck,
    ExportPolicy,
    Fade,
    KeyframeSpec,
    LinearGradient,
    Morph,
    PositionTrack,
    ShapeLayer,
    TextPart,
    TimingSpec,
    Wipe,
)
from quickthumb.errors import RenderingError
from quickthumb.models import Background, Glow, RadialGradient, Shadow, Stroke, TextLayer

from tests._helpers import pixel_channel

pptx = pytest.importorskip("pptx")

from pptx import Presentation  # noqa: E402
from pptx.enum.shapes import MSO_SHAPE, MSO_SHAPE_TYPE  # noqa: E402
from pptx.oxml.ns import qn  # noqa: E402
from pptx.presentation import Presentation as PresentationDocument  # noqa: E402
from pptx.util import Emu  # noqa: E402

EMU_PER_PX = 9525
FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_IMAGE = str(FIXTURES_DIR / "sample_image.jpg")


def timing_of(canvas: Canvas):
    return open_pptx(canvas).slides[0]._element.find(qn("p:timing"))


def open_pptx(canvas: Canvas) -> PresentationDocument:
    return Presentation(BytesIO(canvas.to_pptx()))


def slide_of(canvas: Canvas):
    return open_pptx(canvas).slides[0]


@pytest.mark.parametrize("rotation,spacing", [(0, 0), (23, 3)])
def test_glow_keeps_exact_canonical_halo_and_editable_foreground(tmp_path, rotation, spacing):
    """Glow pixels survive import as an explicit underlay while outlined text remains editable."""
    # Given: outlined text with a halo, including rotation and tracking
    common: dict[str, Any] = {
        "position": (110, 70),
        "font": "assets/fonts/NotoSans-Regular.ttf",
        "size": 22,
        "align": "center",
        "rotation": rotation,
        "letter_spacing": spacing,
    }
    text = Canvas(240, 160).text(
        "Glow",
        **common,
        effects=[Glow(color="#FFD166", radius=5, opacity=0), Stroke(width=2, color="#7C3AED")],
    )
    scene = Canvas(240, 160).text(
        "Glow",
        **common,
        id="title",
        effects=[Glow(color="#FFD166", radius=5, opacity=0.8), Stroke(width=2, color="#7C3AED")],
    )

    # When: inspecting the real exported presentation and its public capability report
    path = tmp_path / "halo.pptx"
    result = scene.export(path)
    picture, backing, foreground = Presentation(path).slides[0].shapes
    underlay = Image.new("RGBA", (240, 160))
    underlay.alpha_composite(
        Image.open(BytesIO(picture.image.blob)),
        (picture.left // EMU_PER_PX, picture.top // EMU_PER_PX),
    )
    # Rotation interpolates the complete canonical foreground/halo together. Exclude
    # its two-pixel antialias boundary when checking the isolated halo's exact bytes.
    outside_ink = (
        text.sample()
        .frames[0]
        .to_image()
        .getchannel("A")
        .filter(ImageFilter.MaxFilter(5))
        .point(lambda a: 255 * (a == 0))
    )
    difference = ImageChops.difference(underlay, scene.sample().frames[0].to_image())

    # Then: embed the canonical halo once, retain native outline/fill, and report partial support
    assert all(
        ImageChops.multiply(channel, outside_ink).getbbox() is None
        for channel in difference.split()
    )
    assert backing.text == foreground.text == "Glow"
    assert foreground.rotation == pytest.approx(rotation % 360)
    assert not foreground._element.findall(".//" + qn("a:glow"))
    assert foreground.text_frame.paragraphs[0].runs[0]._r.rPr.get("spc", "0") == str(spacing * 75)
    (glow,) = [item for item in scene.validate_export("pptx") if item.feature == "glow"]
    assert (glow.support, glow.fallback) == ("partial", "rasterize")
    (route,) = [item for item in result.capability_report if item.feature == "layer_representation"]
    assert (route.support, route.fallback) == ("partial", "rasterize")
    assert "re-export" in route.message


@pytest.mark.parametrize(
    "policy", [ExportPolicy(unsupported_motion="error"), ExportPolicy(pptx={"title": "native"})]
)
def test_glow_native_only_policy_rejects_before_replacing_output(tmp_path, policy):
    """Native-only or strict exports reject fixed glow pixels before changing a destination."""
    # Given: a pre-existing output and a glow that needs a fixed raster underlay
    path = tmp_path / "existing.pptx"
    path.write_bytes(b"keep")
    scene = Canvas(240, 160).text("Glow", id="title", effects=[Glow(color="#FFD166", radius=5)])

    # When / Then: both preflight and execution refuse a silent native-only approximation
    with pytest.raises(RenderingError, match="fixed canonical PNG"):
        scene.validate_export("pptx", policy)
    with pytest.raises(RenderingError, match="fixed canonical PNG"):
        scene.export(path, policy=policy)
    with pytest.raises(RenderingError, match="fixed canonical PNG"):
        scene.to_pptx(policy=policy)
    with pytest.raises(RenderingError, match="fixed canonical PNG"):
        Deck().slide(scene).to_pptx(policy=policy)
    assert path.read_bytes() == b"keep"


def test_rich_text_glow_reports_complete_pixel_fallback(tmp_path):
    """Interleaved rich-run glow uses the canonical composite instead of reordering effects."""
    # Given: different glow effects interleaved with rich text runs
    scene = Canvas(240, 160).text(
        [TextPart(text="Rich ", effects=[Glow(color="#FFD166", radius=5)]), TextPart(text="glow")],
        position=(20, 50),
        size=22,
    )

    # When: reopening the actual exported file
    path = tmp_path / "rich.pptx"
    result = scene.export(path)
    (picture,) = Presentation(path).slides[0].shapes

    # Then: flattening is limited to this unsupported layer and reported explicitly
    assert picture.shape_type == MSO_SHAPE_TYPE.PICTURE
    assert "rich-text glow" in result.fallback_diagnostics[0].reason


def test_native_only_policy_rejects_translucent_stroke_without_glow(tmp_path):
    """A stroke-only composite cannot silently become a picture under a native-only policy."""
    # Given: translucent geometry whose outside stroke cannot be split into opaque copies
    scene = Canvas(240, 160).shape(
        "triangle",
        (40, 30),
        60,
        60,
        "#FF000080",
        effects=[Stroke(width=4, color="#FFFFFF")],
        id="triangle",
    )
    policy = ExportPolicy(pptx={"triangle": "native"})

    # When / Then: every public entrypoint rejects the fallback before writing
    with pytest.raises(RenderingError, match="canonical PNG composite"):
        scene.validate_export("pptx", policy)
    with pytest.raises(RenderingError, match="canonical PNG composite"):
        scene.export(tmp_path / "native.pptx", policy=policy)
    with pytest.raises(RenderingError, match="canonical PNG composite"):
        scene.to_pptx(policy=policy)
    with pytest.raises(RenderingError, match="canonical PNG composite"):
        Deck().slide(scene).to_pptx(policy=policy)
    assert not (tmp_path / "native.pptx").exists()


@pytest.mark.parametrize(
    "parts,fill,expected_shapes,expected_diagnostics",
    [
        (
            [TextPart(text="Override", color="#FFFFFF")],
            None,
            [MSO_SHAPE_TYPE.TEXT_BOX, MSO_SHAPE_TYPE.TEXT_BOX],
            [],
        ),
        (
            [
                TextPart(
                    text="Override",
                    fill=LinearGradient(angle=0, stops=[("#FF0000", 0), ("#FFFF00", 1)]),
                )
            ],
            LinearGradient(angle=0, stops=[("#FF000080", 0), ("#FFFF00", 1)]),
            [MSO_SHAPE_TYPE.TEXT_BOX, MSO_SHAPE_TYPE.TEXT_BOX],
            [],
        ),
        (
            [TextPart(text="Override", color="#FFFFFF"), TextPart(text=" Inherit")],
            None,
            [MSO_SHAPE_TYPE.PICTURE],
            ["fallback"],
        ),
        (
            [TextPart(text="Override", color="#FFFFFF")],
            LinearGradient(angle=0, stops=[("#FF000080", 0), ("#FFFF00", 1)]),
            [MSO_SHAPE_TYPE.PICTURE],
            ["fallback"],
        ),
    ],
)
def test_rich_text_editability_uses_inherited_paint(
    tmp_path, parts, fill, expected_shapes, expected_diagnostics
):
    """Rich text stays editable when every active paint is opaque; inherited alpha uses pixels."""
    # Given: rich parts that override or inherit a translucent parent paint
    scene = Canvas(400, 160).text(
        parts,
        position=(20, 30),
        size=24,
        font="assets/fonts/NotoSans-Regular.ttf",
        color="#00000080",
        fill=fill,
        effects=[Stroke(width=2, color="#FFFF00")],
    )

    # When: opening the public export and inspecting its compatibility report
    path = tmp_path / "inheritance.pptx"
    scene.export(path)
    shapes = Presentation(path).slides[0].shapes

    # Then: unused parent paint cannot remove editability or hide inherited transparency
    assert [shape.shape_type for shape in shapes] == expected_shapes
    assert [item.support for item in scene.validate_export("pptx")] == expected_diagnostics


def test_animated_glow_and_multiple_strokes_target_every_emitted_object():
    """A glow underlay, ordered native strokes and foreground share their layer's entrance."""
    # Given: animated text with two outside outlines and a fixed canonical halo
    scene = Canvas(240, 160).text(
        "Glow",
        position=(30, 40),
        size=28,
        effects=[
            Glow(color="#FFD166", radius=5),
            Stroke(width=4, color="#FF0000"),
            Stroke(width=2, color="#00FF00"),
        ],
        animation=Fade(),
    )

    # When: reading all targets in the actual presentation's animation tree
    slide = slide_of(scene)
    ids = {str(shape.shape_id) for shape in slide.shapes}
    timing = slide._element.find(qn("p:timing"))
    targets = {target.get("spid") for target in timing.iter(qn("p:spTgt"))}
    first, second = list(slide.shapes)[1:3]

    # Then: no backing remains visible before its foreground, and authored stroke order is retained
    assert len(ids) == 4 and ids == targets
    assert first.text_frame.paragraphs[0].runs[0]._r.rPr.find(qn("a:ln")).get("w") == str(
        8 * EMU_PER_PX
    )
    assert second.text_frame.paragraphs[0].runs[0]._r.rPr.find(qn("a:ln")).get("w") == str(
        4 * EMU_PER_PX
    )


@pytest.mark.parametrize(
    "scene",
    [
        Canvas(240, 160).shape(
            "triangle",
            (40, 30),
            60,
            60,
            "#FF0000",
            effects=[
                Stroke(width=3, color="#FFFF00"),
                Shadow(offset_x=4, offset_y=4, color="#000000"),
            ],
        ),
        Canvas(240, 160).text(
            "Stroke",
            position=(40, 30),
            size=24,
            effects=[
                Stroke(width=3, color="#FFFF00"),
                Shadow(offset_x=4, offset_y=4, color="#000000"),
            ],
        ),
    ],
)
def test_shadow_is_painted_before_outside_stroke(scene):
    """Opaque shadows cannot darken the outside border painted after them."""
    # Given: opaque geometry or text with an outside outline overlapping its shadow
    # When: reopening the emitted shadow source, outside border and foreground
    shadow, backing, foreground = slide_of(scene).shapes

    # Then: the shadow belongs only to the earlier source, preserving canonical paint order
    assert shadow._element.find(".//" + qn("a:outerShdw")) is not None
    assert backing._element.find(".//" + qn("a:outerShdw")) is None
    assert foreground._element.find(".//" + qn("a:outerShdw")) is None


@pytest.mark.parametrize(
    "source",
    [
        Canvas(240, 160).shape("triangle", (40, 30), 60, 60, "#FF0000", motion_key="hero"),
        Canvas(240, 160).text(
            "Hero",
            position=(40, 30),
            size=24,
            motion_key="hero",
            effects=[Background(color="#7C3AED", padding=4)],
        ),
    ],
)
@pytest.mark.parametrize(
    "effects",
    [
        [Stroke(width=3, color="#FFFF00")],
        [Glow(color="#FFD166", radius=5)],
        [Glow(color="#FFD166", radius=5), Stroke(width=3, color="#FFFF00")],
        [Shadow(offset_x=4, offset_y=4, color="#000000"), Stroke(width=3, color="#FFFF00")],
    ],
)
def test_effect_copies_keep_foreground_morph_identity_stable(source, effects):
    """Adding effect underlays never forces Morph to match a foreground to its new border."""
    # Given: the same keyed foreground gaining effects on the next slide
    target = Canvas.from_json(source.to_json())
    layer = target.layers[0]
    assert isinstance(layer, (ShapeLayer, TextLayer))
    layer.effects.extend(effects)

    # When: opening a real Morph presentation
    document = Presentation(BytesIO(Deck(slides=[source, target], transition=Morph()).to_pptx()))
    before = document.slides[0].shapes
    after = document.slides[1].shapes

    # Then: existing foreground/background identities survive, and effect roles stay distinct
    assert before[-1].name == after[-1].name
    assert len({shape.name for shape in after}) == len(after)
    assert all(shape.name.startswith(("!!qt-morph-hero-", "!!qt-effect-hero-")) for shape in after)
    assert sum(shape.name.startswith("!!qt-effect-") for shape in after) == len(after) - len(before)


def test_effect_morph_names_cannot_collide_with_an_authored_foreground_key():
    """Effect identities occupy a separate namespace from arbitrary authored motion keys."""
    # Given: a valid authored key that resembles another layer's generated stroke suffix
    scene = (
        Canvas(240, 160)
        .shape(
            "triangle",
            (40, 30),
            60,
            60,
            "#FF0000",
            motion_key="logo",
            effects=[Stroke(width=3, color="#FFFF00")],
        )
        .shape("rectangle", (130, 30), 30, 30, "#FF0000", motion_key="logo-effect-stroke")
    )

    # When: reading names from the emitted slide
    names = [shape.name for shape in slide_of(scene).shapes]

    # Then: the effect cannot force-match either layer's foreground
    assert len(set(names)) == len(names) == 3
    assert names == [
        "!!qt-effect-logo-stroke-0",
        "!!qt-morph-logo-0",
        "!!qt-morph-logo-effect-stroke-0",
    ]


def test_interleaved_glow_shadow_reports_its_canonical_composite(tmp_path):
    """Mixed shadow/halo ordering is kept exact with a bounded, reported layer fallback."""
    # Given: opaque text mixing two effect types whose stacking differs between viewers
    scene = Canvas(240, 160).text(
        "Glow",
        position=(40, 30),
        size=24,
        effects=[Shadow(offset_x=3, offset_y=3, color="#000000"), Glow(color="#FFD166", radius=5)],
    )

    # When: exporting and checking preflight as well as the actual route
    path = tmp_path / "mixed.pptx"
    result = scene.export(path)
    (picture,) = Presentation(path).slides[0].shapes
    (diagnostic,) = scene.validate_export("pptx")

    # Then: only this layer is flattened, without claiming live editable glow
    assert picture.shape_type == MSO_SHAPE_TYPE.PICTURE
    assert diagnostic.support == "fallback"
    assert "Interleaved glow and shadow" in result.fallback_diagnostics[0].reason


def test_export_preserves_editable_objects_and_exact_mask_payload(tmp_path):
    """PPTX receipts match editable text and geometry plus an exact positioned PNG mask."""
    # Given: an opaque document mixing text, an autoshape and a masked source
    mask = {"shape": "ellipse", "position": (100, 30), "width": 20, "height": 20}
    source = Canvas(160, 120).shape("rectangle", (100, 30), 20, 20, "#00FF00", mask=mask)
    scene = (
        Canvas(160, 120)
        .background(color="#FFFFFF")
        .text(
            "Editable", position=(5, 5), size=16, font="assets/fonts/Roboto-Regular.ttf", id="text"
        )
        .shape("rectangle", (5, 50), 20, 20, "#FF0000", id="vector")
        .shape("rectangle", (100, 30), 20, 20, "#00FF00", mask=mask, id="mask")
    )
    original = scene.to_json()

    # When: reopening the actual file produced by the recommended export boundary
    path = tmp_path / "mixed.pptx"
    result = scene.export(path)
    document = Presentation(path)
    slide = document.slides[0]

    # Then: native objects remain editable OOXML and the fragment retains canonical RGBA/geometry
    (box,) = [shape for shape in slide.shapes if shape.shape_type == MSO_SHAPE_TYPE.TEXT_BOX]
    assert box.text == "Editable"
    assert (
        len([shape for shape in slide.shapes if shape.shape_type == MSO_SHAPE_TYPE.AUTO_SHAPE]) == 2
    )
    (picture,) = [shape for shape in slide.shapes if shape.shape_type == MSO_SHAPE_TYPE.PICTURE]
    expected = source.sample().frames[0].to_image().crop((100, 30, 120, 50))
    encoded = BytesIO()
    expected.save(encoded, format="PNG")
    assert picture.image.blob == encoded.getvalue()
    assert (picture.left, picture.top, picture.width, picture.height) == tuple(
        value * EMU_PER_PX for value in (100, 30, 20, 20)
    )
    assert (document.slide_width, document.slide_height) == (160 * EMU_PER_PX, 120 * EMU_PER_PX)
    routes = [item for item in result.capability_report if item.feature == "layer_representation"]
    assert [(item.layer_id, item.support) for item in routes] == [
        ("layer:0", "native"),
        ("text", "native"),
        ("vector", "native"),
        ("mask", "fallback"),
    ]
    assert all(item.slide_index is None for item in routes)
    (fallback,) = result.fallback_diagnostics
    assert (
        fallback.layer_id == "mask"
        and fallback.native_attempt is False
        and "mask" in fallback.reason
    )
    assert result.pixel_metrics.fidelity is None and scene.to_json() == original


@pytest.mark.parametrize("composite", ["group", "prefix", "parent"])
def test_deck_routes_keep_occurrences_and_atomic_membership(tmp_path, composite):
    """Deck PPTX routes distinguish reused objects and identify atomic raster composites."""
    # Given: repeated native occurrences followed by one grouped, backdrop or parent composite
    shared = ShapeLayer(
        type="shape", shape="rectangle", position=(0, 0), width=10, height=10, color="#FF0000"
    )
    first = Canvas(160, 120, layers=[shared, shared])
    second = Canvas(160, 120)
    if composite == "group":
        second.group(
            [
                {
                    "type": "shape",
                    "shape": "rectangle",
                    "width": 20,
                    "height": 20,
                    "color": "#00FF00",
                }
            ],
            id="group",
            position=(0, 0),
            mask={"shape": "ellipse", "position": (0, 0), "width": 20, "height": 20},
        )
        members = ["group", "layer:0:0"]
    elif composite == "prefix":
        from quickthumb import BackdropBlur

        second.shape("rectangle", (0, 0), 20, 20, "#FF0000", id="backdrop").shape(
            "rectangle", (0, 0), 20, 20, "#FFFFFF80", effects=[BackdropBlur(radius=2)], id="blur"
        )
        members = ["backdrop", "blur"]
    else:
        second.null(id="controller").shape(
            "rectangle", (0, 0), 20, 20, "#00FF00", parent="controller", id="child"
        )
        members = ["controller", "child"]

    # When: exporting one presentation through the shared result contract
    path = tmp_path / "composites.pptx"
    result = Deck(160, 120).slide(first).slide(second).export(path)
    document = Presentation(path)

    # Then: source-local IDs and slide indices match real native objects and one PNG composite
    routes = [item for item in result.capability_report if item.feature == "layer_representation"]
    assert [(item.slide_index, item.layer_id, item.support) for item in routes[:2]] == [
        (0, "layer:0", "native"),
        (0, "layer:1", "native"),
    ]
    assert len(document.slides[0].shapes) == 2
    assert len(routes) == 3 and routes[2].slide_index == 1
    assert routes[2].layer_ids == members and routes[2].fallback == "rasterize"
    assert routes[2].native_attempt is False
    (picture,) = document.slides[1].shapes
    assert picture.shape_type == MSO_SHAPE_TYPE.PICTURE
    actual = Image.open(BytesIO(picture.image.blob)).convert("RGBA")
    expected = second.sample().frames[0].to_image()
    assert (
        actual.tobytes()
        == (expected if composite == "parent" else expected.crop(expected.getbbox())).tobytes()
    )
    assert first.layers[0] is first.layers[1] is shared and shared.id is None


@pytest.mark.parametrize("deck", [False, True])
def test_pptx_build_failure_preserves_file(tmp_path, deck):
    """PPTX preparation failure cannot replace an existing Canvas or Deck file."""

    # Given: an admitted custom layer fails during actual raster capture
    def fail_capture(image):
        raise RenderingError("task capture failed")

    broken = Canvas(160, 120).custom(fail_capture)
    source = Deck(160, 120).slide(Canvas(160, 120)).slide(broken) if deck else broken
    path = tmp_path / "preserved.pptx"
    path.write_bytes(b"keep")

    # When/Then: the producer fails before opening the presentation destination
    with pytest.raises(RenderingError, match="task capture failed"):
        source.export(path)
    assert path.read_bytes() == b"keep"


class TestPptxDocument:
    """Test suite for presentation-level output"""

    def test_should_size_slide_to_canvas_pixels(self):
        """The slide adopts the canvas dimensions at 96 dpi"""
        # given
        canvas = Canvas(1280, 720).background(color="#000000")

        # when
        presentation = open_pptx(canvas)

        # then
        assert presentation.slide_width == Emu(1280 * EMU_PER_PX)
        assert presentation.slide_height == Emu(720 * EMU_PER_PX)
        assert len(presentation.slides) == 1

    def test_should_render_pptx_file_from_extension(self, tmp_path):
        """render() writes a PowerPoint file when the output path ends in .pptx"""
        # given
        canvas = Canvas(400, 300).background(color="#FF0000")
        output = tmp_path / "deck.pptx"

        # when
        canvas.render(str(output))

        # then
        assert len(Presentation(str(output)).slides) == 1

    def test_should_raise_rendering_error_for_pptx_canvas_below_slide_minimum(self):
        """PPTX export reports a quickthumb error for canvases below PowerPoint limits"""
        # given
        canvas = Canvas(120, 80)

        # when / then
        with pytest.raises(RenderingError, match="PPTX export supports canvas dimensions"):
            canvas.to_pptx()


class TestPptxBackgroundsAndOutline:
    """Test suite for background and outline layers"""

    def test_should_emit_solid_background_as_full_bleed_rectangle(self):
        """A solid background becomes a full-slide rectangle with the fill color"""
        # given
        canvas = Canvas(400, 300).background(color="#FF8800")

        # when
        slide = slide_of(canvas)

        # then
        shape = slide.shapes[0]
        assert shape.shape_type == MSO_SHAPE_TYPE.AUTO_SHAPE
        assert shape.width == Emu(400 * EMU_PER_PX)
        assert str(shape.fill.fore_color.rgb) == "FF8800"

    def test_should_emit_linear_gradient_background_as_gradient_fill(self):
        """Linear gradient backgrounds use a native gradient fill"""
        # given
        from pptx.enum.dml import MSO_FILL

        canvas = Canvas(400, 300).background(
            gradient=LinearGradient(angle=90, stops=[("#000000", 0.0), ("#FFFFFF", 1.0)])
        )

        # when
        slide = slide_of(canvas)

        # then
        assert slide.shapes[0].fill.type == MSO_FILL.GRADIENT

    def test_should_emit_outline_as_bordered_rectangle(self):
        """Outline layers become an unfilled rectangle with a matching line"""
        # given
        from pptx.enum.dml import MSO_FILL

        canvas = Canvas(400, 300).outline(width=6, color="#FFFFFF", offset=10)

        # when
        slide = slide_of(canvas)

        # then
        shape = slide.shapes[0]
        assert shape.fill.type == MSO_FILL.BACKGROUND
        assert shape.line.width == Emu(6 * EMU_PER_PX)
        assert str(shape.line.color.rgb) == "FFFFFF"


class TestPptxShapes:
    """Test suite for shape layer mapping"""

    def test_should_map_shape_primitives_to_autoshapes(self):
        """Rectangle, pill, star, and triangle map to the matching autoshapes"""
        # given
        canvas = (
            Canvas(800, 600)
            .shape(
                shape="rectangle",
                position=(10, 10),
                width=100,
                height=60,
                color="#FF0000",
                border_radius=12,
            )
            .shape(shape="pill", position=(150, 10), width=100, height=40, color="#00FF00")
            .shape(
                shape="star",
                position=(300, 10),
                width=80,
                height=80,
                color="#0000FF",
                star_points=5,
            )
            .shape(shape="triangle", position=(420, 10), width=80, height=80, color="#FFFF00")
        )

        # when
        shapes = list(slide_of(canvas).shapes)

        # then
        assert shapes[0].auto_shape_type == MSO_SHAPE.ROUNDED_RECTANGLE
        assert shapes[1].auto_shape_type == MSO_SHAPE.ROUNDED_RECTANGLE
        assert shapes[1].adjustments[0] == pytest.approx(0.5, abs=0.01)
        assert shapes[2].auto_shape_type == MSO_SHAPE.STAR_5_POINT
        assert shapes[3].auto_shape_type == MSO_SHAPE.ISOSCELES_TRIANGLE

    def test_should_emit_polygon_as_freeform(self):
        """Custom polygons become freeform shapes"""
        # given
        canvas = Canvas(400, 300).shape(
            shape="polygon",
            position=(50, 50),
            width=120,
            height=120,
            color="#14B8A6",
            points=[(0.5, 0.0), (1.0, 1.0), (0.0, 1.0)],
        )

        # when
        shape = slide_of(canvas).shapes[0]

        # then
        assert shape.shape_type == MSO_SHAPE_TYPE.FREEFORM
        assert str(shape.fill.fore_color.rgb) == "14B8A6"

    def test_should_fall_back_to_picture_for_masked_shape(self):
        """Masked shapes are emitted as pictures so PPTX preserves the mask boundary"""
        # given
        canvas = Canvas(400, 300).shape(
            shape="rectangle",
            position=(10, 10),
            width=120,
            height=120,
            color="#FF0000",
            mask={"shape": "ellipse", "position": (10, 10), "width": 120, "height": 120},
        )

        # when
        shape = slide_of(canvas).shapes[0]

        # then
        assert shape.shape_type == MSO_SHAPE_TYPE.PICTURE
        embedded = Image.open(BytesIO(shape.image.blob)).convert("RGBA")
        assert embedded.getpixel((embedded.width // 2, embedded.height // 2)) == (255, 0, 0, 255)
        assert pixel_channel(embedded, (0, 0), 3) == 0

    def test_should_apply_rotation_and_stroke_to_shapes(self):
        """Outside strokes use a doubled centered backing behind the rotated editable fill."""
        # given
        canvas = Canvas(400, 300).shape(
            shape="rectangle",
            position=(100, 100),
            width=100,
            height=60,
            color="#FFFFFF",
            rotation=15,
            effects=[Stroke(width=3, color="#FF00FF")],
        )

        # when
        backing, shape = slide_of(canvas).shapes

        # then
        assert shape.rotation == pytest.approx(15)
        assert backing.rotation == pytest.approx(15)
        assert backing.line.width == Emu(6 * EMU_PER_PX)
        assert str(backing.line.color.rgb) == "FF00FF"
        assert backing._element.find(".//" + qn("a:miter")).get("lim") == "400000"
        assert shape._element.find(".//" + qn("a:ln") + "/" + qn("a:noFill")) is not None
        assert (backing.left, backing.top, backing.width, backing.height) == (
            shape.left,
            shape.top,
            shape.width,
            shape.height,
        )

    def test_should_apply_shape_opacity_to_stroke_and_effects(self, tmp_path):
        """Translucent shape effects preserve canonical compositing with a reported fallback."""
        # given
        canvas = Canvas(400, 300).shape(
            shape="rectangle",
            position=(100, 100),
            width=100,
            height=60,
            color="#FFFFFF",
            opacity=0.25,
            effects=[
                Stroke(width=3, color="#FF00FF"),
                Glow(color="#00FFFF", radius=4),
                Shadow(offset_x=4, offset_y=4, color="#000000", blur_radius=2),
            ],
        )

        # when
        path = tmp_path / "translucent-shape.pptx"
        result = canvas.export(path)
        (picture,) = Presentation(path).slides[0].shapes
        actual = Image.new("RGBA", (400, 300))
        actual.alpha_composite(
            Image.open(BytesIO(picture.image.blob)),
            (picture.left // EMU_PER_PX, picture.top // EMU_PER_PX),
        )

        # then
        assert actual.tobytes() == canvas.sample().frames[0].to_image().tobytes()
        assert "Translucent" in result.fallback_diagnostics[0].reason


class TestPptxText:
    """Test suite for text layer export"""

    def test_badge_uses_a_font_line_box_inside_its_background(self):
        """Editable badge text retains its canonical baseline and symmetric background padding."""
        # Given: a centered badge whose visible ink is shorter than its font's line box
        canvas = Canvas(240, 120).text(
            "badge",
            position=(120, 60),
            font="assets/fonts/NotoSans-Regular.ttf",
            size=20,
            align="center",
            effects=[Background(color="#7C3AED", padding=8)],
        )

        # When: reopening the editable shapes in the actual presentation
        background, text = slide_of(canvas).shapes

        # Then: the native frame includes font ascent/descent instead of starting at ink top
        assert (background.top, background.height) == (45 * EMU_PER_PX, 36 * EMU_PER_PX)
        assert (text.top, text.height) == (46 * EMU_PER_PX, 28 * EMU_PER_PX)
        assert text.left - background.left == 8 * EMU_PER_PX
        assert background.width - text.width == 16 * EMU_PER_PX
        assert text.text == "badge"
        assert text.text_frame.paragraphs[0].alignment == pptx.enum.text.PP_ALIGN.CENTER
        assert text.text_frame.margin_top == text.text_frame.margin_bottom == 0

    @pytest.mark.parametrize("spacing", [-5334, 5334])
    def test_tracking_outside_native_range_uses_reported_pixels(self, tmp_path, spacing):
        """Out-of-range PowerPoint tracking preserves pixels with a fallback diagnostic."""
        # Given: one visible glyph with tracking that cannot fit in DrawingML
        canvas = Canvas(120, 120).text("A", position=(20, 20), size=20, letter_spacing=spacing)

        # When: exporting through the public file boundary
        path = tmp_path / "tracking.pptx"
        result = canvas.export(path)
        (picture,) = Presentation(path).slides[0].shapes

        # Then: the result is an explicitly reported pixel fallback, not invalid native text
        assert picture.shape_type == MSO_SHAPE_TYPE.PICTURE
        (fallback,) = result.fallback_diagnostics
        assert "tracking" in fallback.reason
        assert fallback.native_attempt is False

    def test_should_emit_editable_textbox_with_font_properties(self):
        """Text layers become text boxes with size, weight, color, and font name"""
        # given
        canvas = Canvas(800, 400).text(
            content="Editable headline",
            font="Roboto",
            size=48,
            bold=True,
            color="#FFCC00",
            position=(60, 80),
        )

        # when
        slide = slide_of(canvas)

        # then
        boxes = [s for s in slide.shapes if s.shape_type == MSO_SHAPE_TYPE.TEXT_BOX]
        assert len(boxes) == 1
        run = boxes[0].text_frame.paragraphs[0].runs[0]
        assert run.text == "Editable headline"
        assert run.font.size.pt == pytest.approx(48 * 0.75)
        assert run.font.bold is True
        assert str(run.font.color.rgb) == "FFCC00"
        assert run.font.name == "Roboto"

    def test_should_emit_wrapped_text_as_one_paragraph_per_line(self):
        """max_width wrapping becomes explicit paragraphs matching the PNG layout"""
        # given
        canvas = Canvas(400, 300).text(
            content="several words that will certainly wrap around",
            font="Roboto",
            size=40,
            color="#FFFFFF",
            position=(20, 20),
            max_width=300,
            letter_spacing=3,
        )

        # when
        box = slide_of(canvas).shapes[0]

        # then
        paragraphs = box.text_frame.paragraphs
        assert len(paragraphs) > 1
        rejoined = " ".join(p.runs[0].text for p in paragraphs)
        assert rejoined == "several words that will certainly wrap around"
        assert {p.runs[0]._r.rPr.get("spc") for p in paragraphs} == {"225"}

    def test_should_emit_rich_parts_as_styled_runs(self):
        """Rich content keeps per-part styling within a single paragraph"""
        # given
        canvas = Canvas(600, 200).text(
            content=[
                TextPart(text="Big ", color="#FF0000", size=48, bold=True, letter_spacing=2),
                TextPart(text="small", color="#00FF00", size=24, italic=True, letter_spacing=-1),
            ],
            font="Roboto",
            position=(40, 60),
        )

        # when
        box = slide_of(canvas).shapes[0]

        # then
        runs = box.text_frame.paragraphs[0].runs
        assert [run.text for run in runs] == ["Big ", "small"]
        assert runs[0].font.size.pt == pytest.approx(36)
        assert runs[0].font.bold is True
        assert runs[1].font.italic is True
        assert str(runs[1].font.color.rgb) == "00FF00"
        assert [run._r.rPr.get("spc") for run in runs] == ["150", "-75"]

    def test_should_rasterize_text_with_unsupported_font_semantics(self, tmp_path):
        """Variable-font and color-emoji runs fall back to a pixel-exact picture"""
        # given: text semantics that DrawingML cannot preserve
        canvas = Canvas(600, 200).text(
            "Variable 🚀",
            font="assets/fonts/RobotoFlex-Variable.ttf",
            font_variations={"wdth": 25},
            emoji_style="color",
            size=40,
            color="#FFFFFF",
            position=(40, 60),
        )

        # when: exporting to PPTX
        result = canvas.export(tmp_path / "font-semantics.pptx")
        shape = Presentation(tmp_path / "font-semantics.pptx").slides[0].shapes[0]

        # then: the exporter uses the raster fallback for unsupported semantics
        assert shape.shape_type == MSO_SHAPE_TYPE.PICTURE
        (fallback,) = result.fallback_diagnostics
        assert fallback.layer_id == "layer:0" and fallback.native_attempt is False
        assert "font" in fallback.reason

    @pytest.mark.parametrize("color", ["#000000", "#00000000"])
    def test_should_emit_valid_drawingml_for_gradient_plus_stroke_run(self, tmp_path, color):
        """An opaque gradient stays editable regardless of the color it replaces."""
        # given a gradient-filled headline that also has a stroke effect
        from pptx.oxml.ns import qn

        canvas = Canvas(600, 200).text(
            content="GRAD",
            font="Roboto",
            size=48,
            bold=True,
            position=(40, 60),
            color=color,
            id="title",
            fill=LinearGradient(angle=0, stops=[("#F59E0B", 0.0), ("#EF4444", 1.0)]),
            effects=[Stroke(width=3, color="#7C3AED")],
        )

        # when the exported deck is reopened
        path = tmp_path / "gradient.pptx"
        canvas.export(path, policy=ExportPolicy(pptx={"title": "native"}))
        backing, foreground = Presentation(path).slides[0].shapes
        backing_rpr = backing.text_frame.paragraphs[0].runs[0]._r.find(qn("a:rPr"))
        rpr = foreground.text_frame.paragraphs[0].runs[0]._r.find(qn("a:rPr"))

        # then: backing strokes stay outside, without replacing the editable gradient fill
        assert backing.text == foreground.text == "GRAD"
        assert backing_rpr.find(qn("a:ln")).get("w") == str(6 * EMU_PER_PX)
        assert backing_rpr.find(qn("a:ln") + "/" + qn("a:round")) is not None
        assert rpr.find(qn("a:ln")) is None
        assert rpr.find(qn("a:gradFill")) is not None
        tags = [child.tag.split("}")[-1] for child in rpr]
        assert tags.index("gradFill") < tags.index("latin")

    def test_should_rotate_textbox_for_rotated_text(self):
        """Rotation carries over to the text box"""
        # given
        canvas = Canvas(600, 200).text(
            content="tilted",
            font="Roboto",
            size=30,
            color="#FFFFFF",
            position=(300, 100),
            align="center",
            rotation=-20,
        )

        # when
        box = slide_of(canvas).shapes[0]

        # then PowerPoint stores rotation as a positive clockwise angle
        assert box.rotation == pytest.approx(340)

    def test_should_apply_text_opacity_to_background_and_effects(self, tmp_path):
        """Translucent text effects preserve the canonical alpha composite in a reported PNG."""
        # given
        canvas = Canvas(600, 200).text(
            content="badge",
            font="Roboto",
            size=32,
            color="#FFFFFF",
            position=(40, 60),
            opacity=0.25,
            effects=[
                Background(color="#FF0000", padding=8),
                Stroke(width=2, color="#00FF00"),
                Glow(color="#00FFFF", radius=4),
                Shadow(offset_x=2, offset_y=2, color="#000000", blur_radius=2),
            ],
        )

        # when
        path = tmp_path / "translucent-text.pptx"
        result = canvas.export(path)
        (picture,) = Presentation(path).slides[0].shapes
        actual = Image.new("RGBA", (600, 200))
        actual.alpha_composite(
            Image.open(BytesIO(picture.image.blob)),
            (picture.left // EMU_PER_PX, picture.top // EMU_PER_PX),
        )

        # then
        assert actual.tobytes() == canvas.sample().frames[0].to_image().tobytes()
        assert "Translucent" in result.fallback_diagnostics[0].reason

    def test_should_rasterize_radial_gradient_text_fill(self):
        """Radial text fills fall back to a picture instead of a flat solid color"""
        # given
        canvas = Canvas(600, 200).text(
            content="RADIAL",
            font="Roboto",
            size=48,
            position=(40, 60),
            fill=RadialGradient(stops=[("#FFFFFF", 0.0), ("#000000", 1.0)]),
        )

        # when
        shape = slide_of(canvas).shapes[0]

        # then
        assert shape.shape_type == MSO_SHAPE_TYPE.PICTURE


class TestPptxEmbeddedLayers:
    """Test suite for layers exported as pictures"""

    def test_should_embed_image_layer_as_picture(self):
        """Image layers become positioned pictures"""
        # given
        canvas = Canvas(400, 300).image(path=SAMPLE_IMAGE, position=(50, 50), width=120)

        # when
        shapes = list(slide_of(canvas).shapes)

        # then
        assert shapes[0].shape_type == MSO_SHAPE_TYPE.PICTURE
        assert shapes[0].left == Emu(50 * EMU_PER_PX)
        assert shapes[0].width == Emu(120 * EMU_PER_PX)

    def test_should_flatten_blend_mode_stack_into_single_picture(self):
        """Blend modes collapse everything beneath them into one picture"""
        # given
        canvas = (
            Canvas(400, 300)
            .background(color="#888888")
            .image(path=SAMPLE_IMAGE, position=(0, 0), width=200, blend_mode="multiply")
            .shape(shape="rectangle", position=(10, 10), width=50, height=50, color="#FF0000")
        )

        # when
        shapes = list(slide_of(canvas).shapes)

        # then
        assert [s.shape_type for s in shapes] == [
            MSO_SHAPE_TYPE.PICTURE,
            MSO_SHAPE_TYPE.AUTO_SHAPE,
        ]


class TestPptxElementAnimations:
    """Test suite for per-layer animations emitted as a <p:timing> tree."""

    def test_should_not_emit_timing_without_animations(self):
        """A slide with no animated layers produces no <p:timing> element"""
        # given
        canvas = Canvas(400, 300).background(color="#000000").text("Hi", size=40, position=(10, 10))

        # when
        timing = timing_of(canvas)

        # then
        assert timing is None

    def test_should_emit_entrance_animation_targeting_the_shape(self):
        """An animated shape gets a clickEffect targeting its shape id"""
        # given
        canvas = Canvas(400, 300).shape(
            shape="rectangle",
            position=(10, 10),
            width=80,
            height=40,
            color="#FF0000",
            animation=Fade(),
        )
        document = open_pptx(canvas)
        shape = document.slides[0].shapes[0]

        # when
        timing = document.slides[0]._element.find(qn("p:timing"))
        targets = {t.get("spid") for t in timing.iter(qn("p:spTgt"))}
        node_types = [c.get("nodeType") for c in timing.iter(qn("p:cTn")) if c.get("nodeType")]

        # then
        assert str(shape.shape_id) in targets
        assert "mainSeq" in node_types
        assert "clickEffect" in node_types
        assert [e.get("filter") for e in timing.iter(qn("p:animEffect"))] == ["fade"]

    def test_should_keep_entrance_animation_targets_visible_in_static_pptx(self):
        """Entrance targets remain visible in the editable deck while timing targets them"""
        # given
        canvas = (
            Canvas(400, 300)
            .shape(
                shape="rectangle",
                position=(10, 10),
                width=80,
                height=40,
                color="#FF0000",
                animation=Fade(),
            )
            .shape(
                shape="ellipse",
                position=(120, 10),
                width=80,
                height=40,
                color="#00FF00",
                animation=Fade(trigger="after_previous"),
            )
        )
        document = open_pptx(canvas)

        # when
        timing = document.slides[0]._element.find(qn("p:timing"))
        animated = {t.get("spid") for t in timing.iter(qn("p:spTgt"))}
        hidden = {
            str(shape.shape_id)
            for shape in document.slides[0].shapes
            if shape._element.xpath('.//*[local-name()="cNvPr"]')[0].get("hidden") == "1"
        }
        visibility = [value.get("val") for value in timing.iter(qn("p:strVal"))]

        # then
        assert len(animated) == 2
        assert hidden == set()
        assert "hidden" in visibility
        assert "visible" in visibility

    def test_should_apply_initial_visibility_after_animation_defaults(self):
        """Initial entrance hiding wins over eager animation default values"""
        # given
        canvas = (
            Canvas(400, 300)
            .shape(
                shape="rectangle",
                position=(10, 10),
                width=80,
                height=40,
                color="#FF0000",
                animation=Fade(),
            )
            .shape(
                shape="ellipse",
                position=(120, 10),
                width=80,
                height=40,
                color="#00FF00",
                animation=Fade(trigger="after_previous"),
            )
        )

        # when
        timing = timing_of(canvas)
        tm_root = next(c for c in timing.iter(qn("p:cTn")) if c.get("nodeType") == "tmRoot")
        children = list(tm_root.find(qn("p:childTnLst")))
        final_values = [value.get("val") for value in children[-1].iter(qn("p:strVal"))]

        # then
        assert children[0].tag == qn("p:seq")
        assert final_values == ["hidden", "hidden"]

    def test_should_map_wipe_direction_to_animation_filter(self):
        """A directional wipe animation encodes the direction in its filter"""
        # given
        canvas = Canvas(400, 300).text(
            "Slide in",
            size=40,
            position=(10, 10),
            animation=Wipe(direction="right"),
        )

        # when
        timing = timing_of(canvas)

        # then
        assert [e.get("filter") for e in timing.iter(qn("p:animEffect"))] == ["wipe(right)"]

    def test_should_animate_a_canonical_spec_with_the_effect_powerpoint_has(self):
        """Given canonical motion, when exported, then it plays as its nearest preset."""
        # Given: two layers whose canonical presets each have a PowerPoint equivalent
        canvas = (
            Canvas(400, 300)
            .text(
                "Headline",
                size=40,
                position=(10, 10),
                animation=AnimationSpec.rise(from_="bottom", duration=0.4),
            )
            .shape(
                shape="rectangle",
                position=(10, 100),
                width=200,
                height=20,
                color="#147CE5",
                animation=AnimationSpec.bar_grow(duration=0.4, trigger="after_previous"),
            )
        )

        # When: the slide's animation timing is read back
        timing = timing_of(canvas)

        # Then: the rise reveals upward and the growing bar reveals left to right
        assert [e.get("filter") for e in timing.iter(qn("p:animEffect"))] == [
            "wipe(up)",
            "wipe(right)",
        ]

    def test_custom_easing_preset_exports_with_a_named_powerpoint_fallback(self):
        """A custom-eased fade remains a PowerPoint fade with a declared easing fallback."""
        from quickthumb import CubicBezierEasing

        # Given: a fade whose custom clock has no native PowerPoint representation.
        canvas = Canvas(160, 120).shape(
            "rectangle",
            (10, 10),
            20,
            20,
            "#FFFFFF",
            animation=AnimationSpec.fade(easing=CubicBezierEasing(points=(0.5, 0, 0.5, 1))),
        )

        # When: PowerPoint export lowers the preset.
        document = open_pptx(canvas)

        # Then: the shape and timing survive and capability inspection explains the approximation.
        assert len(document.slides[0].shapes) == 1
        assert document.slides[0]._element.find(qn("p:timing")) is not None
        assert any(
            item.feature == "easing" and item.fallback is not None
            for item in canvas.validate_export("pptx")
        )

    def test_should_export_canonical_motion_powerpoint_cannot_express_as_a_still_layer(self):
        """Given a keyframed timeline, when exported, then the layer ships unanimated."""
        # Given: a playhead driven by a position track, which has no PPTX preset
        canvas = Canvas(400, 300).shape(
            shape="rectangle",
            position=(10, 100),
            width=4,
            height=40,
            color="#FFFFFF",
            animation=AnimationSpec.timeline(
                PositionTrack(
                    keyframes=[
                        KeyframeSpec(time=0.0, value=(0.0, 0.0)),
                        KeyframeSpec(time=2.0, value=(300.0, 0.0)),
                    ]
                ),
                timing=TimingSpec(start=0.0, duration=2.0),
                easing="linear",
            ),
        )

        # When: the deck is exported
        document = open_pptx(canvas)

        # Then: the shape is present and the slide carries no timing tree at all
        assert len(document.slides[0].shapes) == 1
        assert document.slides[0]._element.find(qn("p:timing")) is None

    def test_should_play_a_list_of_animations_on_one_layer_in_order(self):
        """A layer can carry several animations that target the same shape in order"""
        # given an entrance fade followed by an exit wipe on the same text layer
        canvas = Canvas(400, 300).text(
            "Hi",
            size=40,
            position=(10, 10),
            animation=[Fade(), Wipe(animate="exit", direction="down", trigger="after_previous")],
        )
        document = open_pptx(canvas)
        shape_id = str(document.slides[0].shapes[0].shape_id)

        # when
        timing = document.slides[0]._element.find(qn("p:timing"))
        filters = [e.get("filter") for e in timing.iter(qn("p:animEffect"))]
        node_types = [c.get("nodeType") for c in timing.iter(qn("p:cTn")) if c.get("nodeType")]
        targets = {t.get("spid") for t in timing.iter(qn("p:spTgt"))}

        # then both effects run, in order, against the one shape
        assert filters == ["fade", "wipe(down)"]
        assert "clickEffect" in node_types and "afterEffect" in node_types
        assert targets == {shape_id}

    def test_should_encode_effect_specific_options(self):
        """Each effect class emits its own filter options (orientation, spokes)"""
        # given a blinds and a wheel animation with effect-specific kwargs
        from quickthumb import Blinds, Wheel

        canvas = (
            Canvas(400, 300)
            .shape(
                shape="rectangle",
                position=(10, 10),
                width=60,
                height=60,
                color="#FF0000",
                animation=Blinds(orientation="vertical"),
            )
            .shape(
                shape="ellipse",
                position=(90, 10),
                width=60,
                height=60,
                color="#00FF00",
                animation=Wheel(spokes=4, trigger="after_previous"),
            )
        )

        # when
        filters = [e.get("filter") for e in timing_of(canvas).iter(qn("p:animEffect"))]

        # then
        assert filters == ["blinds(vertical)", "wheel(4)"]

    def test_should_group_with_previous_into_one_click(self):
        """with_previous shares a click group; on_click starts a new one"""
        # given
        canvas = (
            Canvas(400, 300)
            .shape(
                shape="rectangle",
                position=(10, 10),
                width=40,
                height=40,
                color="#FF0000",
                animation=Fade(trigger="on_click"),
            )
            .shape(
                shape="ellipse",
                position=(60, 10),
                width=40,
                height=40,
                color="#00FF00",
                animation=Fade(trigger="with_previous"),
            )
            .shape(
                shape="pill",
                position=(110, 10),
                width=40,
                height=40,
                color="#0000FF",
                animation=Fade(trigger="on_click"),
            )
        )

        # when
        timing = timing_of(canvas)
        main_seq = next(c for c in timing.iter(qn("p:cTn")) if c.get("nodeType") == "mainSeq")
        click_groups = main_seq.find(qn("p:childTnLst")).findall(qn("p:par"))
        node_types = [c.get("nodeType") for c in timing.iter(qn("p:cTn")) if c.get("nodeType")]

        # then
        assert len(click_groups) == 2  # two clicks: [fade+fade], [fade]
        assert node_types.count("clickEffect") == 2
        assert node_types.count("withEffect") == 1

    def test_should_chain_after_previous_in_the_current_click_group(self):
        """after_previous waits for the prior effect in the current click group"""
        # given
        canvas = (
            Canvas(400, 300)
            .text(
                "First",
                size=40,
                position=(10, 10),
                animation=Fade(trigger="on_click"),
            )
            .text(
                "Second",
                size=40,
                position=(10, 80),
                animation=Fade(trigger="after_previous"),
            )
        )

        # when
        timing = timing_of(canvas)
        main_seq = next(c for c in timing.iter(qn("p:cTn")) if c.get("nodeType") == "mainSeq")
        click_groups = main_seq.find(qn("p:childTnLst")).findall(qn("p:par"))
        node_types = [c.get("nodeType") for c in timing.iter(qn("p:cTn")) if c.get("nodeType")]

        # then
        assert len(click_groups) == 1
        assert node_types.count("clickEffect") == 1
        assert "afterEffect" in node_types

    def test_should_emit_exit_animation_hiding_the_shape(self):
        """An exit animation plays out and pins visibility to hidden"""
        # given
        canvas = Canvas(400, 300).shape(
            shape="rectangle",
            position=(10, 10),
            width=80,
            height=40,
            color="#FF0000",
            animation=Fade(animate="exit"),
        )

        # when
        timing = timing_of(canvas)
        effect = next(c for c in timing.iter(qn("p:cTn")) if c.get("presetClass"))
        visibility = [v.get("val") for v in timing.iter(qn("p:strVal"))]

        # then
        assert effect.get("presetClass") == "exit"
        assert "hidden" in visibility

    def test_should_animate_all_shapes_a_text_layer_produces(self):
        """A text layer with a background fill animates the box and its background together"""
        # given
        canvas = Canvas(400, 300).text(
            "Boxed",
            size=40,
            position=(10, 10),
            effects=[Background(color="#222222", padding=8)],
            animation=Fade(),
        )
        document = open_pptx(canvas)

        # when
        timing = document.slides[0]._element.find(qn("p:timing"))
        animated = {t.get("spid") for t in timing.iter(qn("p:spTgt"))}
        all_ids = {str(s.shape_id) for s in document.slides[0].shapes}

        # then: every shape the layer produced is animated (background + text box)
        assert len(animated) >= 2
        assert animated <= all_ids

    def test_should_animate_a_group_on_one_click(self):
        """A group animation plays across all its children on one click"""
        # given
        canvas = Canvas(1280, 720).group(
            children=[
                {"type": "text", "content": "Agenda", "size": 90, "color": "#FFFFFF"},
                {"type": "shape", "shape": "pill", "width": 200, "height": 40, "color": "#B8FF00"},
            ],
            position=("50%", "50%"),
            align="center",
            animation=Fade(trigger="on_click"),
        )

        # when
        document = open_pptx(canvas)
        timing = document.slides[0]._element.find(qn("p:timing"))
        main_seq = next(c for c in timing.iter(qn("p:cTn")) if c.get("nodeType") == "mainSeq")
        click_groups = main_seq.find(qn("p:childTnLst")).findall(qn("p:par"))
        node_types = [c.get("nodeType") for c in timing.iter(qn("p:cTn")) if c.get("nodeType")]
        animated = {t.get("spid") for t in timing.iter(qn("p:spTgt"))}
        hidden = {
            str(shape.shape_id)
            for shape in document.slides[0].shapes
            if shape._element.xpath('.//*[local-name()="cNvPr"]')[0].get("hidden") == "1"
        }
        visibility = [value.get("val") for value in timing.iter(qn("p:strVal"))]

        # then: one click drives parallel effects that target both children
        assert len(click_groups) == 1
        assert node_types.count("clickEffect") == 1
        assert node_types.count("withEffect") == 1
        assert len(animated) == 2
        assert hidden == set()
        assert "hidden" in visibility

    def test_should_expand_after_previous_group_targets_as_parallel_effects(self):
        """A multi-shape after_previous group imports as hidden builds in Keynote"""
        # given
        canvas = (
            Canvas(1280, 720)
            .text(
                "First",
                size=60,
                color="#FFFFFF",
                animation=Fade(trigger="on_click"),
            )
            .group(
                children=[
                    {"type": "text", "content": "A", "size": 40, "color": "#FFFFFF"},
                    {"type": "text", "content": "B", "size": 40, "color": "#FFFFFF"},
                    {"type": "text", "content": "C", "size": 40, "color": "#FFFFFF"},
                ],
                position=("50%", "50%"),
                align="center",
                animation=Fade(trigger="after_previous"),
            )
        )

        # when
        timing = timing_of(canvas)
        main_seq = next(c for c in timing.iter(qn("p:cTn")) if c.get("nodeType") == "mainSeq")
        click_groups = main_seq.find(qn("p:childTnLst")).findall(qn("p:par"))
        node_types = [c.get("nodeType") for c in timing.iter(qn("p:cTn")) if c.get("nodeType")]

        # then
        assert len(click_groups) == 1
        assert node_types.count("clickEffect") == 1
        assert node_types.count("afterEffect") == 1
        assert node_types.count("withEffect") == 2

    def test_group_animation_should_take_precedence_over_child_animations(self):
        """A group animation drives all children as one effect, ignoring child ones"""
        # given a group animation plus a conflicting child animation
        canvas = Canvas(1280, 720).group(
            children=[
                {"type": "text", "content": "A", "size": 60, "color": "#FFFFFF"},
                {
                    "type": "shape",
                    "shape": "pill",
                    "width": 120,
                    "height": 40,
                    "color": "#B8FF00",
                    "animation": {"effect": "wipe", "trigger": "on_click"},
                },
            ],
            position=("50%", "50%"),
            align="center",
            animation=Fade(trigger="on_click"),
        )

        # when
        timing = timing_of(canvas)
        main_seq = next(c for c in timing.iter(qn("p:cTn")) if c.get("nodeType") == "mainSeq")
        click_groups = main_seq.find(qn("p:childTnLst")).findall(qn("p:par"))
        filters = [e.get("filter") for e in timing.iter(qn("p:animEffect"))]

        # then: one click, both children fade (the child's own wipe is overridden)
        assert len(click_groups) == 1
        assert filters == ["fade", "fade"]

    def test_should_reproduce_animation_through_json_round_trip(self):
        """Animations survive to_json/from_json and still emit timing"""
        # given
        canvas = Canvas(400, 300).text(
            "Hi", size=40, position=(10, 10), animation=Wipe(direction="up")
        )

        # when
        restored = Canvas.from_json(canvas.to_json())
        timing = timing_of(restored)

        # then
        assert timing is not None
        assert [e.get("filter") for e in timing.iter(qn("p:animEffect"))] == ["wipe(up)"]
