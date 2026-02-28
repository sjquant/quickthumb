"""Tests for Canvas functionality"""

import json

import pytest
from inline_snapshot import snapshot


class TestCanvas:
    """Test suite for Canvas operations"""

    def test_should_create_canvas_with_explicit_dimensions(self):
        """Test that Canvas can be created with explicit width and height dimensions"""
        # Given: User wants to create a canvas with specific pixel dimensions
        width = 1920
        height = 1080

        # When: User creates a Canvas with explicit dimensions
        from quickthumb import Canvas

        canvas = Canvas(width, height)

        # Then: Canvas should be created with correct dimensions
        assert canvas.width == 1920
        assert canvas.height == 1080

    def test_should_create_canvas_from_aspect_ratio(self):
        """Test that Canvas can be created from aspect ratio and calculates correct dimensions"""
        # Given: User wants to create a 16:9 canvas with base width 1920
        ratio = "16:9"
        base_width = 1920
        expected_height = 1080  # 1920 * 9 / 16

        # When: User creates Canvas from aspect ratio
        from quickthumb import Canvas

        canvas = Canvas.from_aspect_ratio(ratio, base_width=base_width)

        # Then: Canvas dimensions should be calculated correctly
        assert canvas.width == 1920
        assert canvas.height == expected_height

    def test_should_raise_error_for_invalid_dimensions(self):
        """Test that creating canvas with zero or negative dimensions raises ValueError"""
        # Given: User attempts to create canvas with invalid dimensions
        from quickthumb import Canvas, ValidationError

        # When: User calls Canvas with zero width
        # Then: Should raise ValidationError
        with pytest.raises(ValidationError, match="width must be > 0"):
            Canvas(0, 1080)

        # When: User calls Canvas with negative height
        # Then: Should raise ValidationError
        with pytest.raises(ValidationError, match="height must be > 0"):
            Canvas(1920, -100)

    def test_should_serialize_multiple_layers_in_order(self):
        """Test that multiple layers serialize in correct order"""
        # Given: Canvas with multiple background and text layers
        from quickthumb import Canvas, LinearGradient

        gradient = LinearGradient(angle=90, stops=[("#FF0000", 0.0), ("#0000FF", 1.0)])
        canvas = (
            Canvas(1920, 1080)
            .background(color="#2c3e50")
            .background(gradient=gradient, opacity=0.5)
            .text("Title", size=84, color="#FFFFFF")
            .text("Subtitle", size=48, color="#EEEEEE")
        )

        # When: User exports to JSON
        canvas_dict = json.loads(canvas.to_json())

        # Then: All layers should be serialized in correct order
        assert canvas_dict == snapshot(
            {
                "width": 1920,
                "height": 1080,
                "layers": [
                    {
                        "type": "background",
                        "color": "#2c3e50",
                        "gradient": None,
                        "image": None,
                        "opacity": 1.0,
                        "blend_mode": None,
                        "fit": None,
                        "brightness": 1.0,
                        "blur": 0,
                        "contrast": 1.0,
                        "saturation": 1.0,
                    },
                    {
                        "type": "background",
                        "color": None,
                        "gradient": {
                            "type": "linear",
                            "angle": 90.0,
                            "stops": [["#FF0000", 0.0], ["#0000FF", 1.0]],
                        },
                        "image": None,
                        "opacity": 0.5,
                        "blend_mode": None,
                        "fit": None,
                        "brightness": 1.0,
                        "blur": 0,
                        "contrast": 1.0,
                        "saturation": 1.0,
                    },
                    {
                        "type": "text",
                        "content": "Title",
                        "font": None,
                        "size": 84,
                        "color": "#FFFFFF",
                        "position": None,
                        "align": None,
                        "bold": False,
                        "italic": False,
                        "weight": None,
                        "max_width": None,
                        "effects": [],
                        "line_height": None,
                        "letter_spacing": None,
                        "auto_scale": False,
                        "rotation": 0.0,
                        "opacity": 1.0,
                    },
                    {
                        "type": "text",
                        "content": "Subtitle",
                        "font": None,
                        "size": 48,
                        "color": "#EEEEEE",
                        "position": None,
                        "align": None,
                        "bold": False,
                        "italic": False,
                        "weight": None,
                        "max_width": None,
                        "effects": [],
                        "line_height": None,
                        "letter_spacing": None,
                        "auto_scale": False,
                        "rotation": 0.0,
                        "opacity": 1.0,
                    },
                ],
            }
        )

    def test_should_recreate_canvas_from_json(self):
        """Test that Canvas can be recreated from JSON"""
        # Given: Canvas with multiple background and text layers
        from quickthumb import Canvas, LinearGradient

        gradient = LinearGradient(angle=90, stops=[("#FF0000", 0.0), ("#0000FF", 1.0)])
        canvas = (
            Canvas(1920, 1080)
            .background(color="#2c3e50")
            .background(gradient=gradient, opacity=0.5)
            .text("Title", size=84, color="#FFFFFF")
            .text("Subtitle", size=48, color="#EEEEEE")
        )
        json_str = canvas.to_json()
        recreated = Canvas.from_json(json_str)
        assert recreated.to_json() == json_str

    def test_should_raise_error_for_invalid_json(self):
        """Test that Canvas raises error for invalid JSON"""
        # Given: Invalid JSON
        from quickthumb import Canvas, ValidationError

        # When: User calls from_json with invalid JSON
        # Then: Should raise ValidationError
        with pytest.raises(ValidationError, match="layers.*"):
            Canvas.from_json('{"width": 1920, "height": 1080, "layers": "INVALID"}')

    def test_should_base64_match_rendered_file(self):
        """Test that to_base64 output is identical to base64-encoding the rendered file"""
        import base64
        import os
        import tempfile

        from quickthumb import Canvas

        canvas = Canvas(100, 100).background(color="#FF0000")
        result = canvas.to_base64()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)
            with open(output_path, "rb") as f:
                assert result == base64.b64encode(f.read()).decode("utf-8")

    @pytest.mark.parametrize(
        "fmt, prefix",
        [
            ("PNG", "data:image/png;base64,"),
            ("JPEG", "data:image/jpeg;base64,"),
            ("WEBP", "data:image/webp;base64,"),
        ],
    )
    def test_should_prefix_data_url_with_correct_mime_type(self, fmt, prefix):
        """Test that to_data_url returns the correct MIME type prefix for each format"""
        from quickthumb import Canvas

        canvas = Canvas(100, 100).background(color="#FF0000")
        assert canvas.to_data_url(format=fmt).startswith(prefix)

    def test_should_raise_error_for_quality_with_png_in_to_base64(self):
        """Test that to_base64 raises error when quality is used with PNG format"""
        # Given: A simple canvas
        from quickthumb import Canvas
        from quickthumb.errors import RenderingError

        canvas = Canvas(100, 100).background(color="#FF0000")

        # When: User calls to_base64 with quality parameter for PNG
        # Then: Should raise RenderingError
        with pytest.raises(
            RenderingError, match="Quality parameter is only supported for JPEG and WEBP"
        ):
            canvas.to_base64(format="PNG", quality=80)

    def test_render_with_explicit_format_overrides_extension(self):
        """Test that render() format param overrides extension-based format detection"""
        import os
        import tempfile

        from PIL import Image
        from quickthumb import Canvas

        canvas = Canvas(100, 100).background(color="#FF0000")

        with tempfile.TemporaryDirectory() as tmpdir:
            # .png extension but explicit JPEG format — JPEG should win
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path, format="JPEG")

            img = Image.open(output_path)
            assert img.format == "JPEG"
