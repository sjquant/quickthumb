"""Black-box coverage for quickthumb's compact visualization layers."""

import base64
import json
from io import BytesIO

import pytest
from PIL import Image, ImageChops
from quickthumb import Canvas, ChartData, ChartStyle, ValidationError, canvas_json_schema
from quickthumb.cli import app
from typer.testing import CliRunner


def rendered_image(canvas: Canvas) -> Image.Image:
    """Return a decoded RGBA image from the public Canvas raster API."""
    data = base64.b64decode(canvas.to_base64())
    with Image.open(BytesIO(data)) as image:
        return image.convert("RGBA")


class TestVisualizationValidation:
    """Test suite for public visualization model validation."""

    @pytest.mark.parametrize("values", [[], [4.0], [2.0, 2.0, 2.0], [-3.0, -1.0, 0.0]])
    def test_should_accept_defined_edge_case_data(self, values):
        """Empty, single-point, constant, and negative data are valid chart inputs."""
        # given
        canvas = Canvas(160, 100)

        # when
        canvas.line_chart(values, position=(0, 0), width=80, height=40)

        # then
        assert isinstance(canvas.layers[0].data, ChartData)
        assert canvas.layers[0].data.values == values

    @pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf"), "1"])
    def test_should_reject_non_finite_or_non_numeric_data(self, value):
        """Chart models reject values that cannot be rendered deterministically."""
        # given
        canvas = Canvas(160, 100)

        # when / then
        with pytest.raises(ValidationError, match="chart values"):
            canvas.sparkline([value], position=(0, 0), width=80, height=40)  # type: ignore[list-item]

    def test_should_validate_shared_chart_style_and_position(self):
        """Shared style fields use the same color, opacity, and coordinate constraints."""
        # given
        canvas = Canvas(160, 100)

        # when / then
        with pytest.raises(ValidationError, match="invalid hex color"):
            canvas.bar_chart(
                [1, 2],
                position=(0, 0),
                width=80,
                height=40,
                style=ChartStyle(color="blue"),
            )
        with pytest.raises(ValidationError, match="opacity"):
            canvas.line_chart([1, 2], position=(0, 0), width=80, height=40, style={"opacity": 2.0})


class TestVisualizationRendering:
    """Test suite for deterministic chart and QR raster behavior."""

    def test_should_render_all_visualization_types_deterministically(self):
        """All four layers paint stable pixels and repeated renders are byte-identical."""

        # given
        def make_canvas() -> Canvas:
            return (
                Canvas(320, 180)
                .background(color="#FFFFFF")
                .sparkline([1, 3, 2, 5], position=(10, 10), width=80, height=28, color="#FF0000")
                .bar_chart(
                    [-2, -1, 0, 3],
                    position=(105, 10),
                    width=80,
                    height=50,
                    color="#0000FF",
                    negative_color="#00AA00",
                )
                .line_chart(
                    [-1, 0, 2],
                    position=(200, 10),
                    width=80,
                    height=50,
                    color="#7C3AED",
                    fill="#DDD6FE",
                )
                .qr_code("https://example.test", position=(10, 90), size=72)
            )

        first = make_canvas()
        second = make_canvas()

        # when
        first_png = first.to_base64()
        second_png = second.to_base64()
        image = rendered_image(first)

        # then
        assert first_png == second_png
        for box in ((10, 10, 90, 38), (105, 10, 185, 60), (200, 10, 280, 60), (10, 90, 82, 162)):
            crop = image.crop(box)
            assert any(
                crop.getpixel((x, y))[:3] != (255, 255, 255)
                for x in range(crop.width)
                for y in range(crop.height)
            )

    def test_should_leave_an_empty_chart_transparent(self):
        """An empty chart has no accidental baseline, point, or fill pixels."""
        # given
        canvas = Canvas(100, 60).sparkline([], position=(10, 10), width=60, height=30)
        expected = Image.new("RGBA", (100, 60), (0, 0, 0, 0))

        # when
        actual = rendered_image(canvas)

        # then
        assert ImageChops.difference(actual, expected).getbbox() is None

    def test_should_center_constant_line_data_and_show_bar_sign(self):
        """Constant lines center on the plot and negative bars render below zero."""
        # given
        canvas = (
            Canvas(160, 100)
            .line_chart([4, 4, 4], position=(5, 5), width=60, height=40, color="#FF0000")
            .bar_chart([-2, 2], position=(80, 5), width=60, height=70, color="#0000FF")
        )

        # when
        image = rendered_image(canvas)

        # then
        assert image.getpixel((35, 25))[0] > 200
        assert image.getpixel((95, 55))[2] > 150
        assert image.getpixel((125, 20))[2] > 150


class TestVisualizationSerialization:
    """Test suite for JSON, schema, and CLI visualization support."""

    def test_should_round_trip_all_visualization_layer_discriminators(self):
        """JSON loading and serialization preserve all four layer types and data."""
        # given
        payload = {
            "width": 240,
            "height": 160,
            "layers": [
                {
                    "type": "sparkline",
                    "data": [1, 2],
                    "position": [0, 0],
                    "width": 50,
                    "height": 20,
                },
                {
                    "type": "bar_chart",
                    "data": [-1, 2],
                    "position": [60, 0],
                    "width": 50,
                    "height": 20,
                },
                {
                    "type": "line_chart",
                    "data": [2, 3],
                    "position": [120, 0],
                    "width": 50,
                    "height": 20,
                },
                {"type": "qr_code", "data": "hello", "position": [180, 0], "size": 50},
            ],
        }

        # when
        canvas = Canvas.from_json(json.dumps(payload))
        serialized = json.loads(canvas.to_json())

        # then
        assert [layer["type"] for layer in serialized["layers"]] == [
            "sparkline",
            "bar_chart",
            "line_chart",
            "qr_code",
        ]
        assert serialized["layers"][0]["data"] == [1.0, 2.0]
        assert serialized["layers"][3]["data"] == "hello"

    def test_should_publish_visualization_schema_discriminators(self):
        """The generated schema advertises validated chart data, style, and QR contracts."""
        # given
        schema = canvas_json_schema()

        # when
        mapping = schema["properties"]["layers"]["items"]["discriminator"]["mapping"]
        definitions = schema["$defs"]

        # then
        assert set(mapping) >= {"sparkline", "bar_chart", "line_chart", "qr_code"}
        assert "ChartData" in definitions
        assert "ChartStyle" in definitions
        assert definitions["QRCodeLayer"]["properties"]["error_correction"]["enum"] == [
            "L",
            "M",
            "Q",
            "H",
        ]

    def test_should_render_visualization_json_through_cli(self, tmp_path):
        """The public render command accepts a visualization-only JSON document."""
        # given
        spec = tmp_path / "visualization.json"
        output = tmp_path / "visualization.png"
        spec.write_text(
            json.dumps(
                {
                    "width": 120,
                    "height": 100,
                    "layers": [
                        {
                            "type": "line_chart",
                            "data": [-1, 0, 1],
                            "position": [10, 10],
                            "width": 80,
                            "height": 40,
                        },
                        {"type": "qr_code", "data": "cli", "position": [10, 55], "size": 35},
                    ],
                }
            )
        )

        # when
        result = CliRunner().invoke(app, ["render", str(spec), "--output", str(output)])

        # then
        assert result.exit_code == 0, result.output
        assert output.exists()
        assert Image.open(output).size == (120, 100)


class TestVisualizationExportFallback:
    """Test suite for document exporter behavior with raster-native visualizations."""

    def test_should_preserve_visualizations_in_svg_and_html_fallbacks(self):
        """SVG and HTML exports embed the same raster layer when no native
        chart primitive exists."""
        # given
        canvas = Canvas(120, 90).line_chart([1, 3, 2], position=(10, 10), width=80, height=40)

        # when
        svg = canvas.to_svg()
        html = canvas.to_html()

        # then
        assert "data:image/png;base64," in svg
        assert "data:image/png;base64," in html

    def test_should_preserve_qr_code_in_optional_document_exports(self):
        """PDF and PPTX exports keep QR pixels through their established picture fallback."""
        # given
        canvas = Canvas(160, 120).qr_code("document", position=(20, 20), size=70)

        # when
        pdf = canvas.to_pdf()
        pptx = canvas.to_pptx()

        # then
        assert pdf.startswith(b"%PDF-")
        assert pptx.startswith(b"PK")
