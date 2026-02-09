"""Tests for text layer functionality"""

import json

import pytest
from inline_snapshot import snapshot
from quickthumb.models import Stroke, TextLayer, TextPart


class TestTextLayers:
    """Test suite for text layer operations"""

    def test_should_add_multiple_text_layers_with_styling(self):
        """Test that multiple text layers can be added with custom styling"""
        # Given: Canvas with title and subtitle text layers
        from quickthumb import Canvas, Stroke, TextAlign, TextLayer

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
            align=TextAlign.TOP_CENTER,
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
            align=TextAlign.CENTER,
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
            (-10, "size.*greater than 0"),
            (0, "size.*greater than 0"),
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
            "align": "top-center",  # Now serializes as string shortcut
            "effects": [{"type": "stroke", "width": 3, "color": "#000000"}],
            "bold": True,
            "italic": False,
            "weight": None,
            "max_width": None,
            "line_height": 1.5,
            "letter_spacing": 2,
            "auto_scale": False,
        }

    def test_should_deserialize_text_layer_from_json(self):
        """Test that canvas with text layers can be deserialized from JSON"""
        # Given: JSON string with text layer

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
        from quickthumb import Canvas, Stroke, TextAlign, TextLayer

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
            align=TextAlign.TOP_CENTER,
            effects=[Stroke(width=3, color="#000000")],
            bold=True,
            italic=False,
            line_height=1.5,
            letter_spacing=2,
        )

    @pytest.mark.parametrize(
        "line_height,error_pattern",
        [
            (0, "line_height.*greater than 0"),
            (-1, "line_height.*greater than 0"),
            (-1.5, "line_height.*greater than 0"),
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
        with pytest.raises(ValidationError, match="size.*greater than 0"):
            TextPart(text="test", size=0)

        # When/Then: User provides invalid line_height
        with pytest.raises(ValidationError, match="line_height.*greater than 0"):
            TextPart(text="test", line_height=-1.0)

    def test_should_serialize_rich_text_to_json_correctly(self):
        """Test that canvas with rich text serializes to JSON correctly"""
        # Given: Canvas with rich text content

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
            "weight": None,
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
            "weight": None,
            "line_height": 1.5,
            "letter_spacing": 2,
            "font": None,
        }

    def test_should_deserialize_rich_text_from_json_correctly(self):
        """Test that canvas with rich text can be deserialized from JSON"""
        # Given: JSON string with rich text content

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


class TestTextBackgroundEffect:
    """Test suite for text background effect using Background effect class"""

    def test_should_add_text_with_background_effect(self):
        """Test that background effect can be added to text"""
        from quickthumb import Background, Canvas, TextLayer

        canvas = Canvas(1920, 1080)
        canvas.text(
            "Label",
            size=48,
            effects=[
                Background(color="#00FF00", padding=(15, 30, 15, 30), border_radius=8, opacity=0.8)
            ],
        )

        assert len(canvas.layers) == 1
        assert canvas.layers[0] == TextLayer(
            type="text",
            content="Label",
            size=48,
            effects=[
                Background(color="#00FF00", padding=(15, 30, 15, 30), border_radius=8, opacity=0.8)
            ],
        )

    def test_should_serialize_text_with_background_to_json(self):
        """Test that background effects are serialized to JSON"""

        from quickthumb import Background, Canvas

        canvas = Canvas(1920, 1080).text(
            "Hello",
            size=72,
            effects=[Background(color="#FF0000", padding=(10, 20, 10, 20), border_radius=8)],
        )

        json_str = canvas.to_json()
        data = json.loads(json_str)

        assert len(data["layers"]) == 1
        assert data["layers"][0]["effects"][0] == {
            "type": "background",
            "color": "#FF0000",
            "padding": [10, 20, 10, 20],
            "border_radius": 8,
            "opacity": 1.0,
        }

    def test_should_deserialize_text_with_background_from_json(self):
        """Test that background effects are deserialized from JSON"""

        from quickthumb import Background, Canvas, TextLayer

        json_data = {
            "width": 1920,
            "height": 1080,
            "layers": [
                {
                    "type": "text",
                    "content": "Hello",
                    "size": 72,
                    "effects": [
                        {
                            "type": "background",
                            "color": "#FF0000",
                            "padding": [10, 20, 10, 20],
                            "border_radius": 8,
                            "opacity": 0.9,
                        }
                    ],
                }
            ],
        }

        canvas = Canvas.from_json(json.dumps(json_data))

        assert len(canvas.layers) == 1
        assert canvas.layers[0] == TextLayer(
            type="text",
            content="Hello",
            size=72,
            effects=[
                Background(color="#FF0000", padding=(10, 20, 10, 20), border_radius=8, opacity=0.9)
            ],
        )

    @pytest.mark.parametrize(
        "effect_args,error_pattern",
        [
            ({"color": "invalid"}, "invalid hex"),
            ({"color": "#FF0000", "padding": -5}, "padding.*negative"),
            ({"color": "#FF0000", "padding": (10, -5, 10, 5)}, "padding.*negative"),
            ({"color": "#FF0000", "padding": (10, 20, 30)}, "padding"),
            ({"color": "#FF0000", "border_radius": -1}, "border_radius.*negative"),
            ({"color": "#FF0000", "opacity": -0.1}, "opacity.*0.0.*1.0"),
            ({"color": "#FF0000", "opacity": 1.5}, "opacity.*0.0.*1.0"),
        ],
    )
    def test_should_raise_error_for_invalid_background(self, effect_args, error_pattern):
        """Test that invalid Background parameters raise ValidationError"""
        from quickthumb import Background, Canvas, ValidationError

        canvas = Canvas(1920, 1080)

        with pytest.raises(ValidationError, match=error_pattern):
            canvas.text("Hello", effects=[Background(**effect_args)])


class TestTextLayerFontWeight:
    """Test suite for font weight parameter in text layers"""

    def test_should_use_numeric_weight_parameter(self):
        """Test that text layer accepts numeric weight parameter"""
        from quickthumb import Canvas, TextLayer

        canvas = Canvas(1920, 1080)

        canvas.text("Bold Text", font="NotoSerif", size=72, weight=700)

        assert len(canvas.layers) == 1
        assert canvas.layers[0] == TextLayer(
            type="text",
            content="Bold Text",
            font="NotoSerif",
            size=72,
            weight=700,
        )

    def test_should_use_named_weight_parameter(self):
        """Test that text layer accepts named weight parameter"""
        from quickthumb import Canvas, TextLayer

        canvas = Canvas(1920, 1080)

        canvas.text("Medium Text", font="NotoSerif", size=72, weight="medium")

        assert len(canvas.layers) == 1
        assert canvas.layers[0] == TextLayer(
            type="text",
            content="Medium Text",
            font="NotoSerif",
            size=72,
            weight="medium",
        )

    def test_should_render_with_numeric_weight(self, tmp_path):
        """Test that canvas renders correctly with numeric weight"""
        from quickthumb import Canvas

        canvas = Canvas(400, 200)
        canvas.background(color="#FFFFFF")
        canvas.text(
            "Heavy",
            font="NotoSerif",
            size=72,
            color="#000000",
            weight=900,
            align=("center", "middle"),
        )

        output_path = tmp_path / "weight_numeric.png"
        canvas.render(str(output_path))

        assert output_path.exists()
        assert output_path.stat().st_size > 0

    def test_should_render_with_named_weight(self, tmp_path):
        """Test that canvas renders correctly with named weight"""
        from quickthumb import Canvas

        canvas = Canvas(400, 200)
        canvas.background(color="#FFFFFF")
        canvas.text(
            "Thin",
            font="NotoSerif",
            size=72,
            color="#000000",
            weight="thin",
            align=("center", "middle"),
        )

        output_path = tmp_path / "weight_named.png"
        canvas.render(str(output_path))

        assert output_path.exists()
        assert output_path.stat().st_size > 0

    def test_should_raise_error_when_both_weight_and_bold_in_text_layer(self):
        """Test that ValidationError is raised when both weight and bold are specified"""
        from quickthumb import Canvas, ValidationError

        canvas = Canvas(400, 200)

        with pytest.raises(ValidationError, match="cannot specify both.*weight.*bold"):
            canvas.text("Test", font="NotoSerif", size=72, weight=700, bold=True)

    def test_should_raise_error_when_both_weight_and_bold_in_text_part(self):
        """Test that ValidationError is raised when both weight and bold in TextPart"""
        from quickthumb import Canvas, TextPart, ValidationError

        canvas = Canvas(400, 200)

        with pytest.raises(ValidationError, match="cannot specify both.*weight.*bold"):
            canvas.text(
                content=[TextPart(text="Test", weight=700, bold=True)],
                font="NotoSerif",
                size=72,
            )


class TestAutoScale:
    """Test suite for auto_scale parameter validation"""

    def test_should_raise_error_when_auto_scale_without_max_width(self):
        """Test that auto_scale=True without max_width raises ValidationError"""
        from quickthumb import Canvas, ValidationError

        canvas = Canvas(1920, 1080)

        with pytest.raises(ValidationError, match="auto_scale.*max_width"):
            canvas.text("Hello", auto_scale=True)

    def test_should_accept_auto_scale_with_max_width(self):
        """Test that auto_scale=True with max_width works and stores correctly"""
        from quickthumb import Canvas, TextLayer

        canvas = Canvas(1920, 1080)
        canvas.text("Hello", auto_scale=True, max_width=500)

        assert len(canvas.layers) == 1
        assert isinstance(canvas.layers[0], TextLayer)
        assert canvas.layers[0].auto_scale is True
        assert canvas.layers[0].max_width == 500

    def test_should_serialize_auto_scale_to_json(self):
        """Test that auto_scale field is included in JSON serialization"""
        from quickthumb import Canvas

        canvas = Canvas(1920, 1080)
        canvas.text("Hello", auto_scale=True, max_width=500, size=48)

        json_str = canvas.to_json()
        data = json.loads(json_str)

        assert len(data["layers"]) == 1
        assert data["layers"][0]["auto_scale"] is True

    def test_should_deserialize_auto_scale_from_json(self):
        """Test that auto_scale field is correctly deserialized from JSON"""
        from quickthumb import Canvas, TextLayer

        json_data = {
            "width": 1920,
            "height": 1080,
            "layers": [
                {
                    "type": "text",
                    "content": "Hello",
                    "auto_scale": True,
                    "max_width": 500,
                    "size": 48,
                }
            ],
        }

        canvas = Canvas.from_json(json.dumps(json_data))

        assert len(canvas.layers) == 1
        assert isinstance(canvas.layers[0], TextLayer)
        assert canvas.layers[0].auto_scale is True
        assert canvas.layers[0].max_width == 500

    def test_should_not_scale_when_text_fits(self, tmp_path):
        """Test that short text at size 48 with wide max_width stays at size 48"""
        from quickthumb import Canvas

        # Given: Short text that fits within max_width
        canvas_with_auto = Canvas(800, 400)
        canvas_with_auto.background(color="#FFFFFF")
        canvas_with_auto.text(
            "Short",
            size=48,
            color="#000000",
            position=("50%", "50%"),
            align="center",
            max_width=600,
            auto_scale=True,
        )

        canvas_without_auto = Canvas(800, 400)
        canvas_without_auto.background(color="#FFFFFF")
        canvas_without_auto.text(
            "Short",
            size=48,
            color="#000000",
            position=("50%", "50%"),
            align="center",
            max_width=600,
            auto_scale=False,
        )

        # When: Rendering both canvases
        output_with = tmp_path / "with_auto.png"
        output_without = tmp_path / "without_auto.png"
        canvas_with_auto.render(str(output_with))
        canvas_without_auto.render(str(output_without))

        # Then: Both should produce identical output
        assert output_with.read_bytes() == output_without.read_bytes()

    def test_should_reduce_size_when_text_exceeds_max_width(self, tmp_path):
        """Test that long text auto-scales to fit within max_width"""
        from quickthumb import Canvas

        # Given: Long text that exceeds max_width at original size
        canvas_with_auto = Canvas(800, 400)
        canvas_with_auto.background(color="#FFFFFF")
        canvas_with_auto.text(
            "This is a very long title that definitely exceeds the max width",
            size=72,
            color="#000000",
            position=("50%", "50%"),
            align="center",
            max_width=300,
            auto_scale=True,
        )

        canvas_without_auto = Canvas(800, 400)
        canvas_without_auto.background(color="#FFFFFF")
        canvas_without_auto.text(
            "This is a very long title that definitely exceeds the max width",
            size=72,
            color="#000000",
            position=("50%", "50%"),
            align="center",
            max_width=300,
            auto_scale=False,
        )

        # When: Rendering both canvases
        output_with = tmp_path / "with_auto_scaled.png"
        output_without = tmp_path / "without_auto_scaled.png"
        canvas_with_auto.render(str(output_with))
        canvas_without_auto.render(str(output_without))

        # Then: Auto-scaled version should be different (text scaled down)
        assert output_with.read_bytes() != output_without.read_bytes()

    def test_should_auto_scale_wrapped_text(self, tmp_path):
        """Test that auto_scale works with wrapped text"""
        from quickthumb import Canvas

        # Given: Multi-word text with max_width that causes wrapping
        canvas = Canvas(800, 400)
        canvas.background(color="#FFFFFF")
        canvas.text(
            "This is a long sentence that should wrap",
            size=60,
            color="#000000",
            position=("50%", "50%"),
            align="center",
            max_width=200,
            auto_scale=True,
        )

        # When: Rendering the canvas
        output = tmp_path / "auto_scale_wrapped.png"
        canvas.render(str(output))

        # Then: Should render without error
        assert output.exists()
        assert output.stat().st_size > 0

    def test_should_auto_scale_rich_text_proportionally(self, tmp_path):
        """Test that rich text auto-scales all parts proportionally"""
        from quickthumb import Canvas, TextPart

        # Given: Rich text with multiple parts of different sizes
        canvas = Canvas(800, 400)
        canvas.background(color="#FFFFFF")
        canvas.text(
            content=[
                TextPart(text="Big ", size=80, color="#FF0000"),
                TextPart(text="Medium ", size=50, color="#00FF00"),
                TextPart(text="Small", size=30, color="#0000FF"),
            ],
            position=("50%", "50%"),
            align="center",
            max_width=200,
            auto_scale=True,
        )

        # When: Rendering the canvas
        output = tmp_path / "auto_scale_rich.png"
        canvas.render(str(output))

        # Then: Should render without error
        assert output.exists()
        assert output.stat().st_size > 0

    def test_should_not_scale_rich_text_when_fits(self, tmp_path):
        """Test that short rich text that fits renders identically with or without auto_scale"""
        from quickthumb import Canvas, TextPart

        # Given: Short rich text that fits within max_width
        canvas_with_auto = Canvas(800, 400)
        canvas_with_auto.background(color="#FFFFFF")
        canvas_with_auto.text(
            content=[
                TextPart(text="A ", size=40, color="#FF0000"),
                TextPart(text="B", size=40, color="#00FF00"),
            ],
            position=("50%", "50%"),
            align="center",
            max_width=600,
            auto_scale=True,
        )

        canvas_without_auto = Canvas(800, 400)
        canvas_without_auto.background(color="#FFFFFF")
        canvas_without_auto.text(
            content=[
                TextPart(text="A ", size=40, color="#FF0000"),
                TextPart(text="B", size=40, color="#00FF00"),
            ],
            position=("50%", "50%"),
            align="center",
            max_width=600,
            auto_scale=False,
        )

        # When: Rendering both canvases
        output_with = tmp_path / "rich_with_auto.png"
        output_without = tmp_path / "rich_without_auto.png"
        canvas_with_auto.render(str(output_with))
        canvas_without_auto.render(str(output_without))

        # Then: Both should produce identical output
        assert output_with.read_bytes() == output_without.read_bytes()


class TestTextAlign:
    """Test suite for TextAlign enum and text alignment validation"""

    @pytest.mark.parametrize(
        "shortcut,expected_member",
        [
            ("center", "CENTER"),
            ("top-left", "TOP_LEFT"),
            ("top-center", "TOP_CENTER"),
            ("top-right", "TOP_RIGHT"),
            ("left", "LEFT"),
            ("right", "RIGHT"),
            ("bottom-left", "BOTTOM_LEFT"),
            ("bottom-center", "BOTTOM_CENTER"),
            ("bottom-right", "BOTTOM_RIGHT"),
        ],
    )
    def test_should_accept_string_shortcut_in_text_layer(self, shortcut, expected_member):
        """Test that string shortcuts are accepted and converted to TextAlign"""
        # Given: Canvas and a string shortcut for alignment
        from quickthumb import Canvas, TextAlign
        from quickthumb.models import TextLayer

        canvas = Canvas(1920, 1080)

        # When: User provides a string shortcut as align
        canvas.text("Hello", align=shortcut)

        # Then: Should be converted to the corresponding TextAlign enum
        layer = canvas.layers[0]
        assert isinstance(layer, TextLayer)
        assert layer.align == TextAlign[expected_member]

    @pytest.mark.parametrize(
        "align_tuple,expected_member",
        [
            (("center", "middle"), "CENTER"),
            (("left", "top"), "TOP_LEFT"),
            (("center", "top"), "TOP_CENTER"),
            (("right", "top"), "TOP_RIGHT"),
            (("left", "middle"), "LEFT"),
            (("right", "middle"), "RIGHT"),
            (("left", "bottom"), "BOTTOM_LEFT"),
            (("center", "bottom"), "BOTTOM_CENTER"),
            (("right", "bottom"), "BOTTOM_RIGHT"),
        ],
    )
    def test_should_accept_tuple_for_backward_compatibility(self, align_tuple, expected_member):
        """Test that tuple format is accepted and converted to TextAlign"""
        # Given: Canvas and a tuple for alignment
        from quickthumb import Canvas, TextAlign
        from quickthumb.models import TextLayer

        canvas = Canvas(1920, 1080)

        # When: User provides a tuple as align
        canvas.text("Hello", align=align_tuple)

        # Then: Should be converted to the corresponding TextAlign enum
        layer = canvas.layers[0]
        assert isinstance(layer, TextLayer)
        assert layer.align == TextAlign[expected_member]

    def test_should_accept_enum_value_directly(self):
        """Test that TextAlign enum values are accepted directly"""
        # Given: Canvas and a TextAlign enum value
        from quickthumb import Canvas, TextAlign
        from quickthumb.models import TextLayer

        canvas = Canvas(1920, 1080)

        # When: User provides a TextAlign enum as align
        canvas.text("Hello", align=TextAlign.CENTER)

        # Then: Should store the enum value as-is
        layer = canvas.layers[0]
        assert isinstance(layer, TextLayer)
        assert layer.align == TextAlign.CENTER

    def test_should_reject_invalid_string_shortcut(self):
        """Test that invalid string shortcuts are rejected"""
        # Given: Canvas and an invalid string shortcut
        from quickthumb import Canvas, ValidationError

        canvas = Canvas(1920, 1080)

        # When: User provides invalid string shortcut
        # Then: Should raise ValidationError
        with pytest.raises(ValidationError, match="unsupported.*textalign"):
            canvas.text("Hello", align="middle-left")

    def test_should_reject_invalid_tuple_horizontal(self):
        """Test that invalid horizontal value in tuple is rejected"""
        # Given: Canvas and a tuple with invalid horizontal value
        from quickthumb import Canvas, ValidationError

        canvas = Canvas(1920, 1080)

        # When: User provides invalid horizontal value
        # Then: Should raise ValidationError
        with pytest.raises(ValidationError, match="invalid.*align"):
            canvas.text("Hello", align=("diagonal", "top"))

    def test_should_reject_invalid_tuple_vertical(self):
        """Test that invalid vertical value in tuple is rejected"""
        # Given: Canvas and a tuple with invalid vertical value
        from quickthumb import Canvas, ValidationError

        canvas = Canvas(1920, 1080)

        # When: User provides invalid vertical value
        # Then: Should raise ValidationError
        with pytest.raises(ValidationError, match="invalid.*align"):
            canvas.text("Hello", align=("center", "diagonal"))

    def test_should_reject_tuple_with_wrong_length(self):
        """Test that tuples with wrong number of elements are rejected"""
        # Given: Canvas and tuples with wrong length
        from quickthumb import Canvas, ValidationError

        canvas = Canvas(1920, 1080)

        # When: User provides a 1-element tuple
        # Then: Should raise ValidationError
        with pytest.raises(ValidationError, match="align.*must.*tuple.*two"):
            canvas.text("Hello", align=("center",))  # type: ignore[arg-type]

        # When: User provides a 3-element tuple
        # Then: Should raise ValidationError
        with pytest.raises(ValidationError, match="align.*must.*tuple.*two"):
            canvas.text("Hello", align=("center", "middle", "extra"))  # type: ignore[arg-type]

    def test_should_serialize_to_string_shortcut_in_json(self):
        """Test that TextAlign serializes as string shortcut in JSON"""
        # Given: Canvas with a TextAlign enum value
        from quickthumb import Canvas, TextAlign

        canvas = Canvas(1920, 1080)
        canvas.text("Hello", align=TextAlign.TOP_LEFT)

        # When: User serializes canvas to JSON
        data = json.loads(canvas.to_json())

        # Then: align should be serialized as a string shortcut
        assert data["layers"][0]["align"] == "top-left"

    def test_should_deserialize_string_shortcut_from_json(self):
        """Test that string shortcut in JSON deserializes to TextAlign"""
        # Given: JSON with a string shortcut for align
        from quickthumb import Canvas, TextAlign
        from quickthumb.models import TextLayer

        json_data = {
            "width": 1920,
            "height": 1080,
            "layers": [{"type": "text", "content": "Hello", "align": "center"}],
        }

        # When: User deserializes canvas from JSON
        canvas = Canvas.from_json(json.dumps(json_data))

        # Then: align should be deserialized to TextAlign enum
        layer = canvas.layers[0]
        assert isinstance(layer, TextLayer)
        assert layer.align == TextAlign.CENTER

    def test_should_deserialize_tuple_format_from_json(self):
        """Test that old tuple format in JSON deserializes to TextAlign"""
        # Given: JSON with old tuple format for align
        from quickthumb import Canvas, TextAlign
        from quickthumb.models import TextLayer

        json_data = {
            "width": 1920,
            "height": 1080,
            "layers": [{"type": "text", "content": "Hello", "align": ["center", "middle"]}],
        }

        # When: User deserializes canvas from JSON
        canvas = Canvas.from_json(json.dumps(json_data))

        # Then: align should be deserialized to TextAlign enum
        layer = canvas.layers[0]
        assert isinstance(layer, TextLayer)
        assert layer.align == TextAlign.CENTER
