"""Tests for canvas inspection reports (canvas.inspect())."""

from pathlib import Path

from PIL import Image

FIXTURE_SVG = str(Path(__file__).parent / "fixtures" / "sample.svg")


class TestInspectCanvas:
    """Test suite for deterministic canvas layout inspection."""

    def test_should_report_shape_order_identity_and_bbox(self):
        """A shape report includes stable identity, order, type, visibility, and bbox."""
        from quickthumb import Canvas, CanvasInspection, InspectionBBox, LayerInspection

        # given: a background and one positioned shape
        canvas = (
            Canvas(200, 100)
            .background(color="#FFFFFF")
            .shape(shape="rectangle", position=(10, 20), width=30, height=40, color="#FF0000")
        )

        # when
        report = canvas.inspect()

        # then
        assert report == CanvasInspection(
            width=200,
            height=100,
            layers=[
                LayerInspection(
                    id="layer:0",
                    index=0,
                    order=0,
                    z_order=0,
                    type="background",
                    visible=True,
                ),
                LayerInspection(
                    id="layer:1",
                    index=1,
                    order=1,
                    z_order=1,
                    type="shape",
                    visible=True,
                    bbox=InspectionBBox(x=10, y=20, width=30, height=40),
                ),
            ],
        )

    def test_should_report_text_layout_metadata(self):
        """Text reports include wrapped lines and effective font size from measurement."""
        from quickthumb import Canvas, TextInspection

        # given: text with explicit line breaks and a declared font size
        canvas = Canvas(300, 200).text(
            "First line\nSecond line",
            size=32,
            color="#000000",
            position=(10, 20),
        )

        # when
        text = canvas.inspect().layers[0].text

        # then
        assert text == TextInspection(
            wrapped_lines=["First line", "Second line"],
            effective_font_size=32,
            effective_font_sizes=[32],
        )

    def test_should_report_auto_scaled_text_effective_font_size(self):
        """Auto-scaled text reports the reduced effective size used for measurement."""
        from quickthumb import Canvas, TextInspection

        # given: large text constrained to a narrow width
        canvas = Canvas(400, 300).text(
            "WORDS WRAP HERE",
            size=80,
            color="#000000",
            position=(10, 10),
            max_width=150,
            auto_scale=True,
        )

        # when
        text = canvas.inspect().layers[0].text

        # then
        assert text == TextInspection(
            wrapped_lines=["WORDS", "WRAP", "HERE"],
            effective_font_size=41,
            effective_font_sizes=[41],
            max_width=150,
            auto_scaled=True,
        )

    def test_should_report_auto_scaled_rich_text_effective_font_sizes(self):
        """Auto-scaled rich text reports per-part effective font sizes and lines."""
        from quickthumb import Canvas, TextInspection

        # given: rich text parts with different declared sizes constrained to a narrow width
        canvas = Canvas(400, 300).text(
            [
                {"text": "ALPHA ", "size": 80, "color": "#000000"},
                {"text": "BETA", "size": 40, "color": "#111111"},
            ],
            position=(10, 10),
            max_width=180,
            auto_scale=True,
        )

        # when
        text = canvas.inspect().layers[0].text

        # then
        assert text == TextInspection(
            wrapped_lines=["ALPHA BETA"],
            effective_font_size=17,
            effective_font_sizes=[17, 35],
            max_width=180,
            auto_scaled=True,
        )

    def test_should_report_image_and_svg_bounds(self, tmp_path):
        """Image and SVG reports expose measured final bboxes."""
        from quickthumb import Canvas, InspectionBBox, LayerInspection

        # given: an image with inferred height and an SVG with explicit dimensions
        fixture = tmp_path / "sample.png"
        Image.new("RGBA", (80, 40), (0, 255, 0, 255)).save(fixture)
        canvas = (
            Canvas(300, 200)
            .image(path=str(fixture), position=(20, 30), width=60)
            .svg(path=FIXTURE_SVG, position=(100, 40), width=50, height=25)
        )

        # when
        report = canvas.inspect()

        # then
        image, svg = report.layers
        assert image == LayerInspection(
            id="layer:0",
            index=0,
            order=0,
            z_order=0,
            type="image",
            visible=True,
            bbox=InspectionBBox(x=20, y=30, width=60, height=30),
        )
        assert svg == LayerInspection(
            id="layer:1",
            index=1,
            order=1,
            z_order=1,
            type="svg",
            visible=True,
            bbox=InspectionBBox(x=100, y=40, width=50, height=25),
        )

    def test_should_report_group_children_with_stable_ids(self):
        """Group reports include child layout reports with stable path-based IDs."""
        from quickthumb import Canvas, InspectionBBox, LayerInspection, TextInspection

        # given: a group containing a text child and a shape child
        canvas = Canvas(300, 200).group(
            children=[
                {"type": "text", "content": "Label", "size": 20, "color": "#000000"},
                {
                    "type": "shape",
                    "shape": "rectangle",
                    "width": 30,
                    "height": 20,
                    "color": "#FF0000",
                },
            ],
            position=(15, 25),
            gap=5,
        )

        # when
        group = canvas.inspect().layers[0]

        # then: text glyph width differs by platform font rasterizer, but layout stays stable
        text_bbox = group.children[0].bbox
        text_width = text_bbox.width
        text_height = text_bbox.height
        assert text_width in {49, 50, 52}
        assert text_height in {15, 17}
        shape_y = 25 + text_height + 5
        assert group == LayerInspection(
            id="layer:0",
            index=0,
            order=0,
            z_order=0,
            type="group",
            visible=True,
            bbox=InspectionBBox(x=15, y=25, width=text_width, height=text_height + 25),
            children=[
                LayerInspection(
                    id="layer:0:0",
                    index=0,
                    order=0,
                    z_order=0,
                    type="text",
                    visible=True,
                    bbox=InspectionBBox(x=15, y=25, width=text_width, height=text_height),
                    text=TextInspection(
                        wrapped_lines=["Label"],
                        effective_font_size=20,
                        effective_font_sizes=[20],
                    ),
                ),
                LayerInspection(
                    id="layer:0:1",
                    index=1,
                    order=1,
                    z_order=1,
                    type="shape",
                    visible=True,
                    bbox=InspectionBBox(x=15, y=shape_y, width=30, height=20),
                ),
            ],
        )

    def test_should_report_custom_layers(self):
        """Custom layer reports include public identity and no measured geometry."""
        from quickthumb import Canvas, LayerInspection

        # given: a named custom layer
        canvas = Canvas(100, 100).custom(lambda _image: None, name="noop")

        # when
        layer = canvas.inspect().layers[0]

        # then
        assert layer == LayerInspection(
            id="layer:0",
            index=0,
            order=0,
            z_order=0,
            type="custom",
            name="noop",
            visible=True,
        )

    def test_should_report_invisible_layers_without_filtering_them(self):
        """Invisible layers stay in the report with visibility set to false."""
        from quickthumb import Canvas, InspectionBBox, LayerInspection

        # given: a transparent shape that still has measurable geometry
        canvas = Canvas(100, 100).shape(
            shape="rectangle",
            position=(70, 80),
            width=20,
            height=10,
            color="#FF0000",
            opacity=0,
        )

        # when
        layer = canvas.inspect().layers[0]

        # then
        assert layer == LayerInspection(
            id="layer:0",
            index=0,
            order=0,
            z_order=0,
            type="shape",
            visible=False,
            bbox=InspectionBBox(x=70, y=80, width=20, height=10),
        )
