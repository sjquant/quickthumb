"""Tests for text layer functionality"""

import pytest


class TestTextLayers:
    """Test suite for text layer operations"""

    def test_should_add_multiple_text_layers_with_styling(self):
        """Test that multiple text layers can be added with custom styling"""
        # Given: Canvas with title and subtitle text layers
        from quickthumb import Canvas, Stroke, TextLayer

        canvas = Canvas(1920, 1080)

        # When: User adds multiple text layers with different styling
        canvas.text(
            "Python Tutorial",
            font="Roboto",
            size=84,
            color="#FFFFFF",
            align=("center", "top"),
            effects=[Stroke(width=3, color="#000000")],
            bold=True,
        )
        canvas.text(
            "Learn the Basics", font="Roboto", size=48, color="#EEEEEE", align=("center", "middle")
        )

        # Then: Both text layers should be stored with their properties
        assert len(canvas.layers) == 2
        assert canvas.layers[0] == TextLayer(
            type="text",
            content="Python Tutorial",
            font="Roboto",
            size=84,
            color="#FFFFFF",
            position=None,
            align=("center", "top"),
            effects=[Stroke(width=3, color="#000000")],
            bold=True,
            italic=False,
        )
        assert canvas.layers[1] == TextLayer(
            type="text",
            content="Learn the Basics",
            font="Roboto",
            size=48,
            color="#EEEEEE",
            position=None,
            align=("center", "middle"),
            effects=[],
            bold=False,
            italic=False,
        )

    def test_should_accept_position_formats(self):
        """Test that text position can be specified in pixels or percentage"""
        # Given: Canvas and text with different position formats
        from quickthumb import Canvas, TextLayer

        canvas = Canvas(1920, 1080)

        # When: User specifies position in pixels
        canvas.text("Positioned", position=(100, 200))

        # Then: Position should be stored
        assert len(canvas.layers) == 1
        assert canvas.layers[0] == TextLayer(
            type="text",
            content="Positioned",
            font=None,
            size=None,
            color=None,
            position=(100, 200),
            align=None,
            bold=False,
            italic=False,
            effects=[],
        )

        # When: User specifies position as percentage
        canvas.text("Centered", position=("50%", "50%"))

        # Then: Percentage position should be stored
        assert len(canvas.layers) == 2
        assert canvas.layers[1] == TextLayer(
            type="text",
            content="Centered",
            font=None,
            size=None,
            color=None,
            position=("50%", "50%"),
            align=None,
            bold=False,
            italic=False,
            effects=[],
        )

        # When: User specifies position with negative percentage (outside canvas)
        canvas.text("Offscreen", position=("-10%", "110%"))

        # Then: Negative percentage position should be allowed and stored
        assert len(canvas.layers) == 3
        assert canvas.layers[2] == TextLayer(
            type="text",
            content="Offscreen",
            font=None,
            size=None,
            color=None,
            position=("-10%", "110%"),
            align=None,
            bold=False,
            italic=False,
            effects=[],
        )

    @pytest.mark.parametrize(
        "color,error_pattern",
        [
            ("invalid", "invalid hex"),
            ("#GGGGGG", "invalid hex"),
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
            canvas.text("Hello", color=color)

    @pytest.mark.parametrize(
        "position,error_pattern",
        [
            ((100,), "position.*must.*tuple.*two"),
            ((100, 200, 300), "position.*must.*tuple.*two"),
            (("50", "50"), "invalid percentage"),
            (("ab10%", "cd20%"), "invalid percentage"),
        ],
    )
    def test_should_raise_error_for_invalid_position(self, position, error_pattern):
        """Test that invalid position format raises ValidationError"""
        # Given: Canvas and invalid position
        from quickthumb import Canvas, ValidationError

        canvas = Canvas(1920, 1080)

        # When: User provides invalid position
        # Then: Should raise ValidationError
        with pytest.raises(ValidationError, match=error_pattern):
            canvas.text("Hello", position=position)

    @pytest.mark.parametrize(
        "align,error_pattern",
        [
            (("invalid", "top"), "invalid.*align"),
            (("center", "invalid"), "invalid.*align"),
            (("center",), "align.*must.*tuple.*two"),
        ],
    )
    def test_should_raise_error_for_invalid_align(self, align, error_pattern):
        """Test that invalid align values raise ValidationError"""
        # Given: Canvas and invalid align
        from quickthumb import Canvas, ValidationError

        canvas = Canvas(1920, 1080)

        # When: User provides invalid align
        # Then: Should raise ValidationError
        with pytest.raises(ValidationError, match=error_pattern):
            canvas.text("Hello", align=align)

    @pytest.mark.parametrize(
        "size,error_pattern",
        [
            (-10, "size.*positive"),
            (0, "size.*positive"),
        ],
    )
    def test_should_raise_error_for_invalid_size(self, size, error_pattern):
        """Test that invalid size raises ValidationError"""
        # Given: Canvas and invalid size
        from quickthumb import Canvas, ValidationError

        canvas = Canvas(1920, 1080)

        # When: User provides invalid size
        # Then: Should raise ValidationError
        with pytest.raises(ValidationError, match=error_pattern):
            canvas.text("Hello", size=size)

    @pytest.mark.parametrize(
        "max_width,error_pattern",
        [
            (-10, "max_width.*positive"),
            (0, "max_width.*positive"),
            ("invalid", "invalid percentage"),
            ("-50%", "invalid percentage"),
        ],
    )
    def test_should_raise_error_for_invalid_max_width(self, max_width, error_pattern):
        """Test that invalid max_width raises ValidationError"""
        # Given: Canvas and invalid max_width
        from quickthumb import Canvas, ValidationError

        canvas = Canvas(1920, 1080)

        # When: User provides invalid max_width
        # Then: Should raise ValidationError
        with pytest.raises(ValidationError, match=error_pattern):
            canvas.text("Hello", max_width=max_width)

    def test_should_serialize_text_layer_to_json(self):
        """Test that canvas with text layers can be serialized to JSON"""
        # Given: Canvas with background and text layers
        from quickthumb import Canvas, Stroke

        canvas = (
            Canvas(1920, 1080)
            .background(color="#2c3e50")
            .text(
                "Python Tutorial",
                font="Roboto",
                size=84,
                color="#FFFFFF",
                align=("center", "top"),
                effects=[Stroke(width=3, color="#000000")],
                bold=True,
            )
        )

        # When: User serializes canvas to JSON
        json_str = canvas.to_json()

        # Then: JSON should contain text layer with correct structure
        import json

        data = json.loads(json_str)
        assert data["width"] == 1920
        assert data["height"] == 1080
        assert len(data["layers"]) == 2
        assert data["layers"][1] == {
            "type": "text",
            "content": "Python Tutorial",
            "font": "Roboto",
            "size": 84,
            "color": "#FFFFFF",
            "position": None,
            "align": ["center", "top"],
            "effects": [{"type": "stroke", "width": 3, "color": "#000000"}],
            "bold": True,
            "italic": False,
            "max_width": None,
        }

    def test_should_deserialize_text_layer_from_json(self):
        """Test that canvas with text layers can be deserialized from JSON"""
        # Given: JSON string with text layer
        import json

        json_data = {
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
                    "type": "text",
                    "content": "Python Tutorial",
                    "font": "Roboto",
                    "size": 84,
                    "color": "#FFFFFF",
                    "position": None,
                    "align": ["center", "top"],
                    "effects": [{"type": "stroke", "width": 3, "color": "#000000"}],
                    "bold": True,
                    "italic": False,
                },
            ],
        }
        json_str = json.dumps(json_data)

        # When: User deserializes canvas from JSON
        from quickthumb import Canvas, Stroke, TextLayer

        canvas = Canvas.from_json(json_str)

        # Then: Canvas should have text layer with correct properties
        assert len(canvas.layers) == 2
        assert canvas.layers[1] == TextLayer(
            type="text",
            content="Python Tutorial",
            font="Roboto",
            size=84,
            color="#FFFFFF",
            position=None,
            align=("center", "top"),
            effects=[Stroke(width=3, color="#000000")],
            bold=True,
            italic=False,
        )
