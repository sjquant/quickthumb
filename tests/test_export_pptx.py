"""Tests for PPTX export (Canvas.to_pptx and rendering to .pptx files)"""

from io import BytesIO
from pathlib import Path

import pytest
from quickthumb import Canvas, LinearGradient, TextPart
from quickthumb.models import Stroke

pptx = pytest.importorskip("pptx")

from pptx import Presentation  # noqa: E402
from pptx.enum.shapes import MSO_SHAPE, MSO_SHAPE_TYPE  # noqa: E402
from pptx.util import Emu  # noqa: E402

EMU_PER_PX = 9525
FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_IMAGE = str(FIXTURES_DIR / "sample_image.jpg")


def open_pptx(canvas: Canvas) -> Presentation:
    return Presentation(BytesIO(canvas.to_pptx()))


def slide_of(canvas: Canvas):
    return open_pptx(canvas).slides[0]


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

    def test_should_apply_rotation_and_stroke_to_shapes(self):
        """Rotation maps to shape.rotation and stroke effects to the shape line"""
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
        shape = slide_of(canvas).shapes[0]

        # then
        assert shape.rotation == pytest.approx(15)
        assert shape.line.width == Emu(3 * EMU_PER_PX)
        assert str(shape.line.color.rgb) == "FF00FF"


class TestPptxText:
    """Test suite for text layer export"""

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
        )

        # when
        box = slide_of(canvas).shapes[0]

        # then
        paragraphs = box.text_frame.paragraphs
        assert len(paragraphs) > 1
        rejoined = " ".join(p.runs[0].text for p in paragraphs)
        assert rejoined == "several words that will certainly wrap around"

    def test_should_emit_rich_parts_as_styled_runs(self):
        """Rich content keeps per-part styling within a single paragraph"""
        # given
        canvas = Canvas(600, 200).text(
            content=[
                TextPart(text="Big ", color="#FF0000", size=48, bold=True),
                TextPart(text="small", color="#00FF00", size=24, italic=True),
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

    def test_should_emit_valid_drawingml_for_gradient_plus_stroke_run(self):
        """A run with both a gradient fill and a stroke keeps valid rPr child order"""
        # given a gradient-filled headline that also has a stroke effect
        from pptx.oxml.ns import qn

        canvas = Canvas(600, 200).text(
            content="GRAD",
            font="Roboto",
            size=48,
            bold=True,
            position=(40, 60),
            fill=LinearGradient(angle=0, stops=[("#F59E0B", 0.0), ("#EF4444", 1.0)]),
            effects=[Stroke(width=3, color="#7C3AED")],
        )

        # when the exported deck is reopened
        run = slide_of(canvas).shapes[0].text_frame.paragraphs[0].runs[0]
        rpr = run._r.find(qn("a:rPr"))
        tags = [child.tag.split("}")[-1] for child in rpr]

        # then DrawingML requires line, then fill, then latin within rPr
        assert tags.index("ln") < tags.index("gradFill") < tags.index("latin")

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
