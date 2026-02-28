"""Tests for outline decoration layer functionality"""

import pytest


class TestOutlineLayers:
    """Test suite for outline decoration layer operations"""

    def test_should_add_outline_with_required_parameters(self):
        """Test that outline can be added with width and color parameters"""
        # Given: Canvas with size 1920x1080
        from quickthumb import Canvas, OutlineLayer

        canvas = Canvas(1920, 1080)

        # When: User adds outline with required parameters
        canvas.outline(width=10, color="#FFFFFF")

        # Then: Canvas should have outline layer with correct properties
        assert len(canvas.layers) == 1
        assert canvas.layers[0] == OutlineLayer(
            type="outline",
            width=10,
            color="#FFFFFF",
            offset=0,
        )

    @pytest.mark.parametrize(
        "width,error_pattern",
        [
            (0, "width.*greater than 0"),
            (-5, "width.*greater than 0"),
        ],
    )
    def test_should_raise_error_for_invalid_width(self, width, error_pattern):
        """Test that invalid width values raise ValidationError"""
        # Given: Canvas and invalid width
        from quickthumb import Canvas, ValidationError

        canvas = Canvas(1920, 1080)

        # When: User provides invalid width
        # Then: Should raise ValidationError
        with pytest.raises(ValidationError, match=error_pattern):
            canvas.outline(width=width, color="#FFFFFF")

    @pytest.mark.parametrize(
        "color,error_pattern",
        [
            ("invalid", "invalid hex"),
            ("#GGGGGG", "invalid hex"),
            ("FFFFFF", "invalid hex"),
            ("#FFF", "invalid hex"),
        ],
    )
    def test_should_raise_error_for_invalid_color(self, color, error_pattern):
        """Test that invalid color format raises ValidationError"""
        # Given: Canvas and invalid color
        from quickthumb import Canvas, ValidationError

        canvas = Canvas(1920, 1080)

        # When: User provides invalid color
        # Then: Should raise ValidationError
        with pytest.raises(ValidationError, match=error_pattern):
            canvas.outline(width=5, color=color)

    @pytest.mark.parametrize(
        "offset,error_pattern",
        [
            (-1, "offset.*greater than or equal to 0"),
            (-10, "offset.*greater than or equal to 0"),
        ],
    )
    def test_should_raise_error_for_negative_offset(self, offset, error_pattern):
        """Test that negative offset values raise ValidationError"""
        # Given: Canvas and negative offset
        from quickthumb import Canvas, ValidationError

        canvas = Canvas(1920, 1080)

        # When: User provides negative offset
        # Then: Should raise ValidationError
        with pytest.raises(ValidationError, match=error_pattern):
            canvas.outline(width=5, color="#FFFFFF", offset=offset)

    def test_should_serialize_outline_layer_to_json(self):
        """Test that canvas with outline layer can be serialized to JSON"""
        # Given: Canvas with background, text, and outline layers
        from quickthumb import Canvas

        canvas = (
            Canvas(1920, 1080)
            .background(color="#2c3e50")
            .text("Python Tutorial", size=84, color="#FFFFFF")
            .outline(width=10, color="#FFFFFF", offset=5)
        )

        # When: User serializes canvas to JSON
        json_str = canvas.to_json()

        # Then: JSON should contain outline layer with correct structure
        import json

        data = json.loads(json_str)
        assert data["width"] == 1920
        assert data["height"] == 1080
        assert len(data["layers"]) == 3
        assert data["layers"][2] == {
            "type": "outline",
            "width": 10,
            "color": "#FFFFFF",
            "offset": 5,
            "opacity": 1.0,
        }

    def test_should_deserialize_outline_layer_from_json(self):
        """Test that canvas with outline layer can be deserialized from JSON"""
        # Given: JSON string with outline layer
        import json

        json_data = {
            "width": 1920,
            "height": 1080,
            "layers": [
                {
                    "type": "background",
                    "color": "#2c3e50",
                    "opacity": 1.0,
                    "blend_mode": None,
                },
                {
                    "type": "outline",
                    "width": 10,
                    "color": "#FFFFFF",
                    "offset": 5,
                },
            ],
        }
        json_str = json.dumps(json_data)

        # When: User deserializes canvas from JSON
        from quickthumb import Canvas, OutlineLayer

        canvas = Canvas.from_json(json_str)

        # Then: Canvas should have outline layer with correct properties
        assert len(canvas.layers) == 2
        assert canvas.layers[1] == OutlineLayer(
            type="outline",
            width=10,
            color="#FFFFFF",
            offset=5,
        )
