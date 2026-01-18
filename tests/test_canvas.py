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
                    },
                    {
                        "type": "text",
                        "content": "Title",
                        "font": None,
                        "size": 84,
                        "color": "#FFFFFF",
                        "position": None,
                        "align": None,
                        "stroke": None,
                        "bold": False,
                        "italic": False,
                    },
                    {
                        "type": "text",
                        "content": "Subtitle",
                        "font": None,
                        "size": 48,
                        "color": "#EEEEEE",
                        "position": None,
                        "align": None,
                        "stroke": None,
                        "bold": False,
                        "italic": False,
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
