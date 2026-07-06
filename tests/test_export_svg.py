"""Tests for SVG export (Canvas.to_svg and rendering to .svg files)"""

import base64
import builtins
import xml.etree.ElementTree as ET
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image
from quickthumb import Canvas, LinearGradient, RadialGradient, TextPart
from quickthumb.errors import RenderingError
from quickthumb.models import Background, Glow, Grain, Shadow, Stroke, TextFillImage

from tests._optional import require_cairosvg

SVG_NS = "{http://www.w3.org/2000/svg}"
XLINK_NS = "{http://www.w3.org/1999/xlink}"
FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_IMAGE = str(FIXTURES_DIR / "sample_image.jpg")
SAMPLE_SVG = str(FIXTURES_DIR / "sample.svg")


def parse_svg(svg: str) -> ET.Element:
    return ET.fromstring(svg)


def find_all(root: ET.Element, tag: str) -> list[ET.Element]:
    return list(root.iter(f"{SVG_NS}{tag}"))


def require_attr(element: ET.Element, name: str) -> str:
    value = element.get(name)
    assert value is not None
    return value


def png_image_from_svg_href(href: str) -> Image.Image:
    prefix = "data:image/png;base64,"
    assert href.startswith(prefix)
    return Image.open(BytesIO(base64.b64decode(href.removeprefix(prefix)))).convert("RGBA")


class TestSvgDocument:
    """Test suite for overall SVG document structure"""

    def test_should_emit_svg_document_with_canvas_dimensions(self):
        """Exported SVG declares the canvas size and a matching viewBox"""
        # given
        canvas = Canvas(640, 360).background(color="#112233")

        # when
        root = parse_svg(canvas.to_svg())

        # then
        assert root.tag == f"{SVG_NS}svg"
        assert root.get("width") == "640"
        assert root.get("height") == "360"
        assert root.get("viewBox") == "0 0 640 360"

    def test_should_render_svg_file_from_extension(self, tmp_path):
        """render() writes an SVG document when the output path ends in .svg"""
        # given
        canvas = Canvas(200, 100).background(color="#FF0000")
        output = tmp_path / "out.svg"

        # when
        canvas.render(str(output))

        # then
        content = output.read_text()
        assert content.startswith("<svg")
        assert parse_svg(content) is not None

    def test_should_reject_quality_for_svg_output(self, tmp_path):
        """Quality only applies to JPEG/WEBP, so .svg output raises RenderingError"""
        # given
        canvas = Canvas(200, 100).background(color="#FF0000")

        # when / then
        with pytest.raises(RenderingError, match="[Qq]uality"):
            canvas.render(str(tmp_path / "out.svg"), quality=80)


class TestSvgBackgrounds:
    """Test suite for background layer export"""

    def test_should_emit_solid_color_background_as_rect(self):
        """A solid background becomes a full-canvas rect with the hex fill"""
        # given
        canvas = Canvas(400, 300).background(color="#FF8800")

        # when
        root = parse_svg(canvas.to_svg())

        # then
        rects = find_all(root, "rect")
        assert len(rects) == 1
        assert rects[0].get("fill") == "#FF8800"
        assert rects[0].get("width") == "400"
        assert rects[0].get("height") == "300"

    def test_should_apply_alpha_and_opacity_to_background_color(self):
        """8-digit hex alpha combines with layer opacity into fill-opacity"""
        # given an 0x80 alpha (~0.502) and 0.5 layer opacity
        canvas = Canvas(400, 300).background(color="#FF000080", opacity=0.5)

        # when
        root = parse_svg(canvas.to_svg())

        # then
        fill_opacity_attr = find_all(root, "rect")[0].get("fill-opacity")
        assert fill_opacity_attr is not None
        fill_opacity = float(fill_opacity_attr)
        assert fill_opacity == pytest.approx(0.25, abs=0.01)

    def test_should_emit_linear_gradient_with_stops(self):
        """Linear gradients become defs with userSpaceOnUse stops along the angle"""
        # given a left-to-right gradient
        canvas = Canvas(400, 300).background(
            gradient=LinearGradient(angle=0, stops=[("#000000", 0.0), ("#FFFFFF", 1.0)])
        )

        # when
        root = parse_svg(canvas.to_svg())

        # then
        gradients = find_all(root, "linearGradient")
        assert len(gradients) == 1
        stops = find_all(gradients[0], "stop")
        assert [s.get("stop-color") for s in stops] == ["#000000", "#FFFFFF"]
        # angle 0 runs along +x through the canvas center
        y1 = gradients[0].get("y1")
        y2 = gradients[0].get("y2")
        x1 = gradients[0].get("x1")
        x2 = gradients[0].get("x2")
        assert y1 is not None
        assert y2 is not None
        assert x1 is not None
        assert x2 is not None
        assert float(y1) == float(y2)
        assert float(x1) < float(x2)
        rect = find_all(root, "rect")[0]
        assert rect.get("fill") == f"url(#{gradients[0].get('id')})"

    def test_should_emit_radial_gradient_centered_on_focus(self):
        """Radial gradients keep the configured center point"""
        # given
        canvas = Canvas(400, 200).background(
            gradient=RadialGradient(stops=[("#FFFFFF", 0.0), ("#000000", 1.0)], center=(0.25, 0.5))
        )

        # when
        root = parse_svg(canvas.to_svg())

        # then
        gradients = find_all(root, "radialGradient")
        assert len(gradients) == 1
        cx = gradients[0].get("cx")
        cy = gradients[0].get("cy")
        radius = gradients[0].get("r")
        assert cx is not None
        assert cy is not None
        assert radius is not None
        assert float(cx) == pytest.approx(100)
        assert float(cy) == pytest.approx(100)
        assert float(radius) > 0

    def test_should_fall_back_to_raster_for_background_effects(self):
        """Backgrounds with grain cannot be vectorized and embed a PNG instead"""
        # given
        canvas = Canvas(200, 100).background(
            color="#336699", effects=[Grain(intensity=0.4, seed=7)]
        )

        # when
        root = parse_svg(canvas.to_svg())

        # then
        images = find_all(root, "image")
        assert len(images) == 1
        assert (
            images[0]
            .get("{http://www.w3.org/1999/xlink}href", images[0].get("href", ""))
            .startswith("data:image/png;base64,")
        )
        assert not find_all(root, "rect")


class TestSvgShapesAndOutline:
    """Test suite for shape and outline layer export"""

    def test_should_emit_rounded_rectangle_shape(self):
        """Rectangle shapes keep position, size, and border radius"""
        # given
        canvas = Canvas(400, 300).shape(
            shape="rectangle",
            position=(40, 50),
            width=120,
            height=80,
            color="#22C55E",
            border_radius=12,
        )

        # when
        root = parse_svg(canvas.to_svg())

        # then
        rect = find_all(root, "rect")[0]
        assert rect.get("x") == "40"
        assert rect.get("y") == "50"
        assert rect.get("rx") == "12"
        assert rect.get("fill") == "#22C55E"

    def test_should_fall_back_to_raster_for_masked_shape(self):
        """Masked shapes are embedded as PNG fragments so SVG export preserves the mask"""
        # given
        canvas = Canvas(80, 80).shape(
            shape="rectangle",
            position=(10, 10),
            width=60,
            height=60,
            color="#FF0000",
            mask={"shape": "ellipse", "position": (10, 10), "width": 60, "height": 60},
        )

        # when
        root = parse_svg(canvas.to_svg())

        # then
        images = find_all(root, "image")
        assert len(images) == 1
        assert not find_all(root, "rect")
        embedded = png_image_from_svg_href(require_attr(images[0], f"{XLINK_NS}href"))
        assert embedded.getpixel((embedded.width // 2, embedded.height // 2)) == (255, 0, 0, 255)
        assert embedded.getpixel((0, 0))[3] == 0

    def test_should_emit_star_as_polygon_with_expected_points(self):
        """A star becomes a polygon with two points per spike"""
        # given
        canvas = Canvas(400, 300).shape(
            shape="star",
            position=(50, 50),
            width=100,
            height=100,
            color="#FACC15",
            star_points=6,
        )

        # when
        root = parse_svg(canvas.to_svg())

        # then
        polygons = find_all(root, "polygon")
        assert len(polygons) == 1
        assert len(require_attr(polygons[0], "points").split()) == 12

    def test_should_rotate_shapes_with_transform(self):
        """Rotation becomes a rotate() transform around the shape center"""
        # given
        canvas = Canvas(400, 300).shape(
            shape="ellipse",
            position=(100, 100),
            width=80,
            height=40,
            color="#3B82F6",
            rotation=30,
        )

        # when
        svg = canvas.to_svg()

        # then
        ellipse = find_all(parse_svg(svg), "ellipse")[0]
        assert "rotate(30" in require_attr(ellipse, "transform")

    def test_should_emit_stroke_effect_as_backing_shape(self):
        """A stroke effect paints a doubled-width outline shape behind the fill"""
        # given
        canvas = Canvas(400, 300).shape(
            shape="rectangle",
            position=(40, 40),
            width=100,
            height=60,
            color="#FFFFFF",
            effects=[Stroke(width=4, color="#FF0000")],
        )

        # when
        root = parse_svg(canvas.to_svg())

        # then
        rects = find_all(root, "rect")
        assert len(rects) == 2
        stroke_rect, fill_rect = rects
        assert stroke_rect.get("stroke") == "#FF0000"
        assert stroke_rect.get("stroke-width") == "8"
        assert fill_rect.get("fill") == "#FFFFFF"

    def test_should_preserve_alpha_in_shape_stroke_effect(self):
        """8-digit hex colors keep alpha when exported as SVG shape effects"""
        # given
        canvas = Canvas(400, 300).shape(
            shape="rectangle",
            position=(40, 40),
            width=100,
            height=60,
            color="#FFFFFF",
            effects=[Stroke(width=4, color="#FF000080")],
        )

        # when
        root = parse_svg(canvas.to_svg())

        # then
        stroke_rect = find_all(root, "rect")[0]
        assert stroke_rect.get("fill") == "#FF0000"
        assert float(require_attr(stroke_rect, "fill-opacity")) == pytest.approx(0.5, abs=0.01)
        assert float(require_attr(stroke_rect, "stroke-opacity")) == pytest.approx(0.5, abs=0.01)

    def test_should_emit_shadow_with_blur_filter(self):
        """A blurred shadow becomes an offset duplicate with a Gaussian filter"""
        # given
        canvas = Canvas(400, 300).shape(
            shape="ellipse",
            position=(100, 100),
            width=80,
            height=80,
            color="#FFFFFF",
            effects=[Shadow(offset_x=6, offset_y=8, color="#000000", blur_radius=5)],
        )

        # when
        root = parse_svg(canvas.to_svg())

        # then
        blurs = find_all(root, "feGaussianBlur")
        assert len(blurs) == 1
        assert blurs[0].get("stdDeviation") == "5"
        shadow = find_all(root, "ellipse")[0]
        assert "translate(6 8)" in require_attr(shadow, "transform")
        assert shadow.get("fill") == "#000000"

    def test_should_emit_outline_as_stroked_rect(self):
        """Outline layers become a non-filled rect stroked at the band center"""
        # given
        canvas = Canvas(400, 300).outline(width=6, color="#FFFFFF", offset=10)

        # when
        root = parse_svg(canvas.to_svg())

        # then
        rect = find_all(root, "rect")[0]
        assert rect.get("fill") == "none"
        assert rect.get("stroke") == "#FFFFFF"
        assert rect.get("stroke-width") == "6"
        assert float(require_attr(rect, "x")) == pytest.approx(13)
        assert float(require_attr(rect, "width")) == pytest.approx(400 - 2 * 10 - 6)


class TestSvgText:
    """Test suite for text layer export"""

    def test_should_emit_text_with_font_attributes(self):
        """Simple text keeps content, size, family, and color"""
        # given
        canvas = Canvas(600, 200).text(
            content="Hello SVG",
            font="Roboto",
            size=48,
            bold=True,
            color="#FFCC00",
            position=(50, 60),
        )

        # when
        root = parse_svg(canvas.to_svg())

        # then
        texts = find_all(root, "text")
        assert len(texts) == 1
        text = texts[0]
        assert text.text == "Hello SVG"
        assert text.get("font-size") == "48px"
        assert "Roboto" in require_attr(text, "font-family")
        assert text.get("font-weight") == "700"
        assert text.get("fill") == "#FFCC00"
        assert float(require_attr(text, "x")) >= 50

    def test_should_wrap_text_into_one_element_per_line(self):
        """max_width wrapping emits one positioned text element per line"""
        # given
        canvas = Canvas(400, 300).text(
            content="several words that will certainly wrap around",
            font="Roboto",
            size=40,
            color="#FFFFFF",
            position=(20, 20),
            max_width=300,
        )

        # when
        root = parse_svg(canvas.to_svg())

        # then
        texts = find_all(root, "text")
        assert len(texts) > 1
        joined = " ".join(t.text for t in texts)
        assert joined == "several words that will certainly wrap around"
        ys = [float(require_attr(t, "y")) for t in texts]
        assert ys == sorted(ys)

    def test_should_emit_letter_spaced_text_with_per_character_positions(self):
        """Letter spacing produces an explicit x position per character"""
        # given
        canvas = Canvas(600, 200).text(
            content="SPACED",
            font="Roboto",
            size=40,
            color="#FFFFFF",
            position=(30, 60),
            letter_spacing=10,
        )

        # when
        root = parse_svg(canvas.to_svg())

        # then
        text = find_all(root, "text")[0]
        positions = require_attr(text, "x").split()
        assert len(positions) == len("SPACED")
        assert [float(p) for p in positions] == sorted(float(p) for p in positions)

    def test_should_emit_rich_text_parts_as_separate_runs(self):
        """Rich content keeps per-part color, size, and style"""
        # given
        canvas = Canvas(600, 200).text(
            content=[
                TextPart(text="Bold ", color="#FF0000", size=40, bold=True),
                TextPart(text="italic", color="#00FF00", size=24, italic=True),
            ],
            font="Roboto",
            position=(40, 60),
        )

        # when
        root = parse_svg(canvas.to_svg())

        # then
        texts = find_all(root, "text")
        assert [t.text for t in texts] == ["Bold ", "italic"]
        assert texts[0].get("fill") == "#FF0000"
        assert texts[0].get("font-weight") == "700"
        assert texts[1].get("fill") == "#00FF00"
        assert texts[1].get("font-style") == "italic"
        assert texts[1].get("font-size") == "24px"

    def test_should_emit_gradient_text_fill(self):
        """Gradient glyph fills reference a gradient def spanning the text block"""
        # given
        canvas = Canvas(600, 200).text(
            content="GRADIENT",
            font="Roboto",
            size=48,
            position=(40, 60),
            fill=LinearGradient(angle=0, stops=[("#F59E0B", 0.0), ("#EF4444", 1.0)]),
        )

        # when
        root = parse_svg(canvas.to_svg())

        # then
        text = find_all(root, "text")[0]
        assert require_attr(text, "fill").startswith("url(#")
        assert len(find_all(root, "linearGradient")) == 1

    def test_should_emit_text_effects_as_layered_duplicates(self):
        """Stroke, shadow, and glow each add a backing copy of the text"""
        # given
        canvas = Canvas(600, 200).text(
            content="FX",
            font="Roboto",
            size=60,
            color="#FFFFFF",
            position=(40, 60),
            effects=[
                Glow(color="#00FFFF", radius=6),
                Shadow(offset_x=4, offset_y=4, color="#000000", blur_radius=2),
                Stroke(width=3, color="#FF00FF"),
            ],
        )

        # when
        root = parse_svg(canvas.to_svg())

        # then glow + shadow + stroke + fill = four copies, blurs for glow and shadow
        texts = find_all(root, "text")
        assert len(texts) == 4
        assert len(find_all(root, "feGaussianBlur")) == 2
        stroke_copies = [t for t in texts if t.get("stroke") == "#FF00FF"]
        assert stroke_copies and stroke_copies[0].get("stroke-width") == "6"

    def test_should_emit_background_effect_as_padded_rect(self):
        """A Background text effect draws a padded box behind the text"""
        # given
        canvas = Canvas(600, 200).text(
            content="BADGE",
            font="Roboto",
            size=30,
            color="#FFFFFF",
            position=(40, 60),
            effects=[Background(color="#7C3AED", padding=10, border_radius=6)],
        )

        # when
        root = parse_svg(canvas.to_svg())

        # then
        rects = find_all(root, "rect")
        assert len(rects) == 1
        assert rects[0].get("fill") == "#7C3AED"
        assert rects[0].get("rx") == "6"

    def test_should_wrap_rotated_text_in_rotation_transform(self):
        """Rotation and opacity wrap the whole text block in a transformed group"""
        # given
        canvas = Canvas(600, 200).text(
            content="tilted",
            font="Roboto",
            size=30,
            color="#FFFFFF",
            position=(300, 100),
            align="center",
            rotation=-20,
            opacity=0.8,
        )

        # when
        root = parse_svg(canvas.to_svg())

        # then
        groups = [g for g in find_all(root, "g") if g.get("transform")]
        assert groups and "rotate(-20" in require_attr(groups[0], "transform")
        assert float(require_attr(groups[0], "opacity")) == pytest.approx(0.8)

    def test_should_fall_back_to_raster_for_image_glyph_fill(self):
        """Image-textured glyphs cannot be vectorized and embed a PNG"""
        # given
        canvas = Canvas(600, 200).text(
            content="TEXTURE",
            font="Roboto",
            size=60,
            position=(40, 60),
            fill=TextFillImage(path=SAMPLE_IMAGE),
        )

        # when
        root = parse_svg(canvas.to_svg())

        # then
        assert not find_all(root, "text")
        assert len(find_all(root, "image")) == 1


class TestSvgEmbeddedLayers:
    """Test suite for layers exported as embedded content"""

    def test_should_embed_image_layer_as_png_fragment(self):
        """Image layers embed the composited pixels as a base64 PNG"""
        # given
        canvas = Canvas(400, 300).image(path=SAMPLE_IMAGE, position=(50, 50), width=120)

        # when
        root = parse_svg(canvas.to_svg())

        # then
        image = find_all(root, "image")[0]
        assert image.get("{http://www.w3.org/1999/xlink}href").startswith("data:image/png;base64,")
        assert int(image.get("x")) == 50
        assert int(image.get("width")) == 120

    def test_should_embed_svg_layer_as_vector_data_url(self):
        """Plain SVG overlays stay vector via an svg+xml data URL"""
        # given
        canvas = Canvas(400, 300).svg(path=SAMPLE_SVG, position=(30, 40), width=100)

        # when
        root = parse_svg(canvas.to_svg())

        # then
        image = find_all(root, "image")[0]
        assert image.get("{http://www.w3.org/1999/xlink}href").startswith(
            "data:image/svg+xml;base64,"
        )

    def test_should_embed_svg_layer_without_rasterizer_available(self, monkeypatch):
        """Plain SVG overlays do not require CairoSVG when exported to SVG"""
        # given
        original_import = builtins.__import__

        def block_cairosvg(name, *args, **kwargs):
            if name.startswith(("cairosvg", "cairocffi")):
                raise OSError("native cairo unavailable")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", block_cairosvg)
        canvas = Canvas(400, 300).svg(path=SAMPLE_SVG, position=(30, 40), width=100)

        # when
        root = parse_svg(canvas.to_svg())

        # then
        image = find_all(root, "image")[0]
        assert image.get("{http://www.w3.org/1999/xlink}href").startswith(
            "data:image/svg+xml;base64,"
        )
        assert image.get("width") == "100"

    def test_should_flatten_blend_mode_stack_into_single_raster(self):
        """Blend modes depend on the backdrop, so the stack collapses to one PNG"""
        # given a background and a multiplied image above it
        canvas = (
            Canvas(400, 300)
            .background(color="#888888")
            .image(path=SAMPLE_IMAGE, position=(0, 0), width=200, blend_mode="multiply")
            .shape(shape="rectangle", position=(10, 10), width=50, height=50, color="#FF0000")
        )

        # when
        root = parse_svg(canvas.to_svg())

        # then the blended prefix is one image and the shape above stays native
        assert len(find_all(root, "image")) == 1
        assert len(find_all(root, "rect")) == 1

    def test_should_export_group_children_natively(self):
        """Auto-layout group children are exported as positioned native elements"""
        # given
        canvas = Canvas(600, 400).group(
            children=[
                {
                    "type": "text",
                    "content": "Grouped",
                    "font": "Roboto",
                    "size": 30,
                    "color": "#FFFFFF",
                },
                {
                    "type": "shape",
                    "shape": "rectangle",
                    "width": 80,
                    "height": 40,
                    "color": "#22C55E",
                },
            ],
            direction="column",
            gap=12,
            position=(60, 80),
        )

        # when
        root = parse_svg(canvas.to_svg())

        # then
        assert find_all(root, "text")[0].text == "Grouped"
        rect = find_all(root, "rect")[0]
        assert float(require_attr(rect, "x")) == pytest.approx(60)
        assert not find_all(root, "image")

    def test_should_fall_back_to_raster_for_nested_masked_group(self):
        """Nested composed groups survive exporter flattening as masked PNG fragments"""
        # given
        canvas = Canvas(100, 50).group(
            children=[
                {
                    "type": "group",
                    "direction": "row",
                    "mask": {"position": (0, 0), "width": 50, "height": 50},
                    "children": [
                        {
                            "type": "shape",
                            "shape": "rectangle",
                            "width": 50,
                            "height": 50,
                            "color": "#FF0000",
                        },
                        {
                            "type": "shape",
                            "shape": "rectangle",
                            "width": 50,
                            "height": 50,
                            "color": "#0000FF",
                        },
                    ],
                }
            ]
        )

        # when
        root = parse_svg(canvas.to_svg())

        # then
        images = find_all(root, "image")
        assert len(images) == 1
        assert not find_all(root, "rect")
        embedded = png_image_from_svg_href(require_attr(images[0], f"{XLINK_NS}href"))
        assert embedded.size == (50, 50)
        assert embedded.getpixel((25, 25)) == (255, 0, 0, 255)


class TestSvgFontEmbedding:
    """Test suite for the embed_fonts option"""

    def test_should_embed_used_fonts_as_font_face_when_enabled(self):
        """embed_fonts=True inlines the used font files as @font-face data URLs"""
        # given
        canvas = Canvas(400, 200).text(
            content="embedded", font="Roboto", size=30, color="#FFFFFF", position=(20, 20)
        )

        # when
        svg = canvas.to_svg(embed_fonts=True)

        # then
        assert "@font-face" in svg
        assert "data:font/ttf;base64," in svg
        assert "font-family:'Roboto'" in svg

    def test_should_not_embed_fonts_by_default(self):
        """to_svg() leaves fonts as references unless embedding is requested"""
        # given
        canvas = Canvas(400, 200).text(
            content="plain", font="Roboto", size=30, color="#FFFFFF", position=(20, 20)
        )

        # when / then
        assert "@font-face" not in canvas.to_svg()


class TestSvgPixelFidelity:
    """Test suite comparing SVG output against the raster pipeline"""

    def test_should_match_raster_render_for_vector_only_canvas(self, tmp_path):
        """Rasterizing the exported SVG reproduces the PNG render for vector layers"""
        # given a canvas using only natively exportable, font-free layers
        cairosvg = require_cairosvg()
        from PIL import Image, ImageChops

        canvas = (
            Canvas(640, 360)
            .background(
                gradient=LinearGradient(
                    angle=35, stops=[("#0F172A", 0.0), ("#7C3AED", 0.6), ("#F472B6", 1.0)]
                )
            )
            .background(
                gradient=RadialGradient(
                    stops=[("#FFFFFF40", 0.0), ("#00000000", 0.7)], center=(0.3, 0.4)
                )
            )
            .shape(
                shape="rectangle",
                position=(40, 40),
                width=160,
                height=90,
                color="#22C55E",
                border_radius=18,
            )
            .shape(shape="ellipse", position=(260, 40), width=120, height=90, color="#F59E0BCC")
            .shape(
                shape="pill", position=(420, 40), width=160, height=60, color="#3B82F6", rotation=20
            )
            .shape(
                shape="star",
                position=(80, 200),
                width=110,
                height=110,
                color="#FACC15",
                star_points=5,
                inner_radius=0.5,
            )
            .shape(
                shape="triangle",
                position=(260, 200),
                width=110,
                height=100,
                color="#EF4444",
                opacity=0.8,
            )
            .outline(width=6, color="#FFFFFF", offset=10, opacity=0.9)
        )

        # when both pipelines render the same spec
        raster_path = tmp_path / "raster.png"
        canvas.render(str(raster_path))
        raster = Image.open(raster_path).convert("RGB")
        svg_png = cairosvg.svg2png(bytestring=canvas.to_svg().encode())
        vector = Image.open(BytesIO(svg_png)).convert("RGB")

        # then the outputs differ only by anti-aliasing noise
        diff = ImageChops.difference(raster, vector).convert("L")
        histogram = diff.histogram()
        total = sum(histogram)
        mean = sum(i * count for i, count in enumerate(histogram)) / total
        assert mean < 5.0

    def test_should_match_raster_render_for_aligned_and_percentage_text(self, tmp_path):
        """Right/bottom alignment and percentage positions land where the PNG render does"""
        # given text anchored by percentage positions and varied alignment
        cairosvg = require_cairosvg()
        from PIL import Image, ImageChops

        canvas = (
            Canvas(480, 240)
            .background(color="#101826")
            .text(
                content="right edge",
                font="Roboto",
                size=32,
                color="#FFFFFF",
                position=("100%", "25%"),
                align="right",
            )
            .text(
                content="bottom center",
                font="Roboto",
                size=32,
                color="#FFD166",
                position=("50%", "100%"),
                align="bottom-center",
            )
            .text(
                content="SPACED",
                font="Roboto",
                size=28,
                color="#9AE6B4",
                position=("50%", "55%"),
                align="center",
                letter_spacing=8,
            )
        )

        # when both pipelines render the same spec
        raster_path = tmp_path / "aligned.png"
        canvas.render(str(raster_path))
        raster = Image.open(raster_path).convert("RGB")
        svg_png = cairosvg.svg2png(bytestring=canvas.to_svg().encode())
        vector = Image.open(BytesIO(svg_png)).convert("RGB")

        # then alignment and percentage anchoring agree to within anti-aliasing noise
        diff = ImageChops.difference(raster, vector).convert("L")
        histogram = diff.histogram()
        total = sum(histogram)
        mean = sum(i * count for i, count in enumerate(histogram)) / total
        assert mean < 5.0
