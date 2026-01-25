"""Tests for text layer functionality"""

import pytest
from inline_snapshot import snapshot
from quickthumb.models import Stroke, TextLayer, TextPart


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
                line_height=1.5,
                letter_spacing=2,
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
            "line_height": 1.5,
            "letter_spacing": 2,
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
                    "line_height": 1.5,
                    "letter_spacing": 2,
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
            line_height=1.5,
            letter_spacing=2,
        )

    @pytest.mark.parametrize(
        "line_height,error_pattern",
        [
            (0, "line_height.*positive"),
            (-1, "line_height.*positive"),
            (-1.5, "line_height.*positive"),
        ],
    )
    def test_should_raise_error_for_invalid_line_height(self, line_height, error_pattern):
        """Test that non-positive line_height raises ValidationError"""
        # Given: Canvas and invalid line_height
        from quickthumb import Canvas, ValidationError

        canvas = Canvas(1920, 1080)

        # When: User provides non-positive line_height
        # Then: Should raise ValidationError
        with pytest.raises(ValidationError, match=error_pattern):
            canvas.text("Hello", line_height=line_height)


class TestRichText:
    """Test suite for rich text (TextPart) functionality"""

    def test_should_accept_list_of_text_parts_with_styles(self):
        """Test that TextPart objects accept advanced styling options"""
        from quickthumb import Canvas, TextPart

        parts = [
            TextPart(text="Big Bold ", size=100, bold=True, font="Arial"),
            TextPart(text="Small Italic", size=20, italic=True),
            TextPart(text="\nSpaced", letter_spacing=10, line_height=2.0),
        ]

        canvas = Canvas(1920, 1080)
        canvas.text(content=parts, size=72)  # Default size

        from quickthumb import TextLayer

        assert len(canvas.layers) == 1
        assert isinstance(canvas.layers[0], TextLayer)
        assert canvas.layers[0].content == parts

    def test_should_validate_text_part_fields(self):
        """Test validation for TextPart styling fields"""
        from quickthumb import TextPart, ValidationError

        # When/Then: User provides invalid size
        with pytest.raises(ValidationError, match="size.*positive"):
            TextPart(text="test", size=0)

        # When/Then: User provides invalid line_height
        with pytest.raises(ValidationError, match="line_height.*positive"):
            TextPart(text="test", line_height=-1.0)

    def test_should_serialize_rich_text_to_json_correctly(self):
        """Test that canvas with rich text serializes to JSON correctly"""
        # Given: Canvas with rich text content
        import json

        from quickthumb import Canvas, Stroke, TextPart

        canvas = Canvas(1920, 1080).text(
            content=[
                TextPart(text="Hello ", color="#FFFFFF", bold=True, size=80, font="Arial"),
                TextPart(
                    text="World",
                    color="#FF0000",
                    italic=True,
                    line_height=1.5,
                    letter_spacing=2,
                    effects=[Stroke(width=2, color="#000000")],
                ),
            ],
            size=72,
            effects=[Stroke(width=1, color="#000000")],
        )

        # When: User serializes canvas to JSON
        json_str = canvas.to_json()

        # Then: JSON should contain TextPart array with correct structure
        data = json.loads(json_str)
        assert len(data["layers"]) == 1
        assert data["layers"][0]["type"] == "text"
        assert isinstance(data["layers"][0]["content"], list)
        assert len(data["layers"][0]["content"]) == 2
        assert data["layers"][0]["content"][0] == {
            "text": "Hello ",
            "color": "#FFFFFF",
            "effects": [],
            "size": 80,
            "bold": True,
            "italic": None,
            "line_height": None,
            "letter_spacing": None,
            "font": "Arial",
        }
        assert data["layers"][0]["content"][1] == {
            "text": "World",
            "color": "#FF0000",
            "effects": [{"type": "stroke", "width": 2, "color": "#000000"}],
            "size": None,
            "bold": None,
            "italic": True,
            "line_height": 1.5,
            "letter_spacing": 2,
            "font": None,
        }

    def test_should_deserialize_rich_text_from_json_correctly(self):
        """Test that canvas with rich text can be deserialized from JSON"""
        # Given: JSON string with rich text content
        import json

        from quickthumb import Canvas

        json_data = {
            "width": 1920,
            "height": 1080,
            "layers": [
                {
                    "type": "text",
                    "content": [
                        {
                            "text": "Hello ",
                            "color": "#FFFFFF",
                            "effects": [],
                            "bold": True,
                            "size": 80,
                            "font": "Arial",
                        },
                        {
                            "text": "World",
                            "color": "#FF0000",
                            "effects": [{"type": "stroke", "width": 2, "color": "#000000"}],
                            "italic": True,
                            "line_height": 1.5,
                            "letter_spacing": 2,
                            "font": None,
                        },
                    ],
                    "size": 72,
                    "color": None,
                    "effects": [{"type": "stroke", "width": 1, "color": "#000000"}],
                }
            ],
        }
        json_str = json.dumps(json_data)

        # When: User deserializes canvas from JSON
        canvas = Canvas.from_json(json_str)

        # Then: Canvas should recreate the rich text structure
        assert len(canvas.layers) == 1
        assert canvas.layers[0] == snapshot(
            TextLayer(
                type="text",
                content=[
                    TextPart(text="Hello ", color="#FFFFFF", size=80, bold=True, font="Arial"),
                    TextPart(
                        text="World",
                        color="#FF0000",
                        effects=[Stroke(width=2, color="#000000")],
                        italic=True,
                        line_height=1.5,
                        letter_spacing=2,
                    ),
                ],
                size=72,
                effects=[Stroke(width=1, color="#000000")],
            )
        )

    def test_should_handle_empty_text_part_list(self):
        """Test that empty TextPart list raises ValidationError"""
        # Given: Canvas and empty TextPart list
        from quickthumb import Canvas, ValidationError

        canvas = Canvas(1920, 1080)

        # When: User provides empty TextPart list
        # Then: Should raise ValidationError
        with pytest.raises(ValidationError, match="content.*empty"):
            canvas.text(content=[], size=72)
