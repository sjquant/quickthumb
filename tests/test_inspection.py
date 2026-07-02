"""Tests for canvas inspection reports (canvas.inspect())."""

from pathlib import Path

from PIL import Image

FIXTURE_SVG = str(Path(__file__).parent / "fixtures" / "sample.svg")


class TestInspectCanvas:
    """Test suite for deterministic canvas layout inspection."""

    def test_should_report_shape_order_identity_and_bbox(self):
        """A shape report includes stable identity, order, type, visibility, and bbox."""
        from quickthumb import Canvas

        # given: a background and one positioned shape
        canvas = (
            Canvas(200, 100)
            .background(color="#FFFFFF")
            .shape(shape="rectangle", position=(10, 20), width=30, height=40, color="#FF0000")
        )

        # when
        report = canvas.inspect()

        # then
        assert report.width == 200
        assert report.height == 100
        assert [layer.id for layer in report.layers] == ["layer:0", "layer:1"]
        assert [layer.order for layer in report.layers] == [0, 1]
        assert [layer.z_order for layer in report.layers] == [0, 1]
        assert report.layers[0].type == "background"
        assert report.layers[0].bbox is None
        assert report.layers[1].type == "shape"
        assert report.layers[1].visible is True
        assert report.layers[1].bbox.model_dump() == {
            "x": 10,
            "y": 20,
            "width": 30,
            "height": 40,
        }

    def test_should_report_text_layout_metadata(self):
        """Text reports include wrapped lines and effective font size from measurement."""
        from quickthumb import Canvas

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
        assert text is not None
        assert text.wrapped_lines == ["First line", "Second line"]
        assert text.effective_font_size == 32
        assert text.effective_font_sizes == [32]
        assert text.auto_scaled is False

    def test_should_report_auto_scaled_text_effective_font_size(self):
        """Auto-scaled text reports the reduced effective size used for measurement."""
        from quickthumb import Canvas

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
        assert text is not None
        assert text.auto_scaled is True
        assert text.max_width == 150
        assert text.effective_font_size is not None
        assert text.effective_font_size < 80
        assert text.wrapped_lines

    def test_should_report_image_and_svg_bounds(self, tmp_path):
        """Image and SVG reports expose measured final bboxes."""
        from quickthumb import Canvas

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
        assert image.type == "image"
        assert image.bbox.model_dump() == {"x": 20, "y": 30, "width": 60, "height": 30}
        assert svg.type == "svg"
        assert svg.bbox.model_dump() == {"x": 100, "y": 40, "width": 50, "height": 25}

    def test_should_report_group_children_with_stable_ids(self):
        """Group reports include child layout reports with stable path-based IDs."""
        from quickthumb import Canvas

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

        # then
        assert group.type == "group"
        assert group.id == "layer:0"
        assert group.bbox is not None
        assert [child.id for child in group.children] == ["layer:0:0", "layer:0:1"]
        assert [child.type for child in group.children] == ["text", "shape"]
        assert group.children[0].text is not None
        assert group.children[0].text.wrapped_lines == ["Label"]

    def test_should_report_invisible_layers_without_filtering_them(self):
        """Invisible layers stay in the report with visibility set to false."""
        from quickthumb import Canvas

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
        assert layer.visible is False
        assert layer.bbox.model_dump() == {"x": 70, "y": 80, "width": 20, "height": 10}
