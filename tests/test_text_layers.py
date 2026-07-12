"""Tests for text layer functionality"""

import json

import pytest
from inline_snapshot import snapshot
from PIL import Image
from quickthumb.models import Stroke, TextLayer, TextPart


class TestTextLayers:
    """Test suite for text layer operations"""

    def test_should_add_multiple_text_layers_with_styling(self):
        """Test that multiple text layers can be added with custom styling"""
        # Given: Canvas with title and subtitle text layers
        from quickthumb import Align, Canvas, Stroke, TextLayer

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
            align=Align.TOP_CENTER,
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
            align=Align.CENTER,
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

    def test_should_clip_text_layer_pixels_to_rect(self, tmp_path):
        """Text clip applies to the whole rendered text layer including backgrounds"""
        from quickthumb import Background, Canvas

        # Given: a text layer with a red text background clipped to the left side
        output = tmp_path / "text-clip.png"
        canvas = (
            Canvas(120, 80)
            .background(color="#FFFFFF")
            .text(
                "MASK",
                position=(10, 30),
                size=28,
                color="#000000",
                effects=[Background(color="#FF0000", padding=(20, 20))],
                clip={"position": (0, 0), "width": 45, "height": 80},
            )
        )

        # When: rendering the clipped text layer
        canvas.render(str(output))

        # Then: painted text-layer pixels stop at the clip boundary
        rendered = Image.open(output).convert("RGBA")
        assert rendered.getpixel((20, 30))[:3] == (255, 0, 0)
        assert rendered.getpixel((70, 30)) == (255, 255, 255, 255)

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
            "font_source": "auto",
            "font_variations": {},
            "emoji_style": "monochrome",
            "size": 84,
            "color": "#FFFFFF",
            "fill": None,
            "position": None,
            "align": "top-center",  # Now serializes as string shortcut
            "effects": [{"type": "stroke", "width": 3, "color": "#000000"}],
            "bold": True,
            "italic": False,
            "weight": None,
            "max_width": None,
            "max_height": None,
            "min_size": 1,
            "balance_lines": False,
            "line_height": 1.5,
            "letter_spacing": 2,
            "auto_scale": False,
            "rotation": 0.0,
            "opacity": 1.0,
            "animation": None,
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
        from quickthumb import Align, Canvas, Stroke, TextLayer

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
            align=Align.TOP_CENTER,
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
            "fill": None,
            "effects": [],
            "size": 80,
            "bold": True,
            "italic": None,
            "weight": None,
            "line_height": None,
            "letter_spacing": None,
            "font": "Arial",
            "font_source": None,
            "font_variations": None,
            "emoji_style": None,
        }
        assert data["layers"][0]["content"][1] == {
            "text": "World",
            "color": "#FF0000",
            "fill": None,
            "effects": [{"type": "stroke", "width": 2, "color": "#000000"}],
            "size": None,
            "bold": None,
            "italic": True,
            "weight": None,
            "line_height": 1.5,
            "letter_spacing": 2,
            "font": None,
            "font_source": None,
            "font_variations": None,
            "emoji_style": None,
        }

    def test_should_preserve_rich_part_inheritance_through_json(self):
        """Omitted rich-part settings inherit after JSON round-trip while explicit values clear"""
        from quickthumb import Canvas

        # Given: a layer default and one part with explicit clear values
        canvas = Canvas(600, 200).text(
            content=[
                TextPart(text="inherits"),
                TextPart(
                    text="clears",
                    font_source="auto",
                    font_variations={},
                    emoji_style="monochrome",
                ),
            ],
            font="assets/fonts/RobotoFlex-Variable.ttf",
            font_variations={"wdth": 25},
            emoji_style="color",
            size=40,
            position=(20, 60),
        )

        # When: the public canvas is serialized and reconstructed
        encoded = canvas.to_json()
        payload = json.loads(encoded)
        loaded = Canvas.from_json(encoded)
        parts = loaded.layers[0].content

        # Then: both model intent and public SVG output survive the round-trip
        assert payload["layers"][0]["content"][0]["font_source"] is None
        assert payload["layers"][0]["content"][1]["font_source"] == "auto"
        assert isinstance(parts, list)
        assert parts[0].font_variations is None
        assert parts[0].emoji_style is None
        assert parts[0].font_source is None
        assert parts[1].font_source == "auto"
        assert parts[1].font_variations == {}
        assert parts[1].emoji_style == "monochrome"
        svg = loaded.to_svg()
        assert svg.count("font-variation-settings=\"'wdth' 25\"") == 1
        assert svg.count('font-variant-emoji="emoji"') == 1
        assert svg.count('font-variant-emoji="text"') == 1

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


class TestAutoFit:
    """Test suite for auto-fit parameter validation"""

    def test_should_raise_error_when_auto_scale_without_bounds(self):
        """Test that auto_scale=True without width or height bounds raises ValidationError"""
        from quickthumb import Canvas, ValidationError

        canvas = Canvas(1920, 1080)

        with pytest.raises(ValidationError, match="auto_scale.*max_width or max_height"):
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


class TestTextAutoFit:
    """Test suite for box-aware text fitting and balanced wrapping"""

    def test_should_round_trip_text_layout_pipeline_fields_through_json(self):
        """Text font/layout pipeline fields validate and survive JSON serialization"""
        from quickthumb import Canvas, TextLayer

        # Given: a text layer using every W4d public layout/font field
        canvas = Canvas(640, 360).text(
            "Pipeline",
            font="Roboto",
            font_source="google",
            font_variations={"wght": 650},
            emoji_style="color",
            size=72,
            max_width=240,
            max_height="40%",
            min_size=18,
            balance_lines=True,
            auto_scale=True,
        )

        # When: the canvas round-trips through JSON
        loaded = Canvas.from_json(canvas.to_json())

        # Then: the public model fields are preserved
        assert len(loaded.layers) == 1
        assert isinstance(loaded.layers[0], TextLayer)
        assert loaded.layers[0].font_source == "google"
        assert loaded.layers[0].font_variations == {"wght": 650.0}
        assert loaded.layers[0].emoji_style == "color"
        assert loaded.layers[0].max_height == "40%"
        assert loaded.layers[0].min_size == 18
        assert loaded.layers[0].balance_lines is True
        assert loaded.layers[0].auto_scale is True

    def test_should_inspect_auto_fit_final_box_and_lines(self):
        """Inspection reports the same fitted size and balanced lines used for rendering"""
        from quickthumb import Canvas

        # Given: a headline constrained by width and height
        canvas = (
            Canvas(420, 220)
            .background(color="#FFFFFF")
            .text(
                "Alpha beta gamma delta",
                font="Roboto",
                size=48,
                color="#111111",
                position=(210, 110),
                align="center",
                max_width=210,
                max_height=78,
                min_size=18,
                balance_lines=True,
                auto_scale=True,
            )
        )

        # When: inspecting the resolved layout
        layer = canvas.inspect().layers[1]

        # Then: the fitted bbox satisfies both constraints and exposes final layout controls
        assert layer.bbox is not None
        assert layer.bbox.width <= 210
        assert layer.bbox.height <= 78
        assert layer.text is not None
        assert layer.text.auto_scaled is True
        assert layer.text.effective_font_size is not None
        assert 18 <= layer.text.effective_font_size <= 48
        assert layer.text.max_height == 78
        assert layer.text.min_size == 18
        assert layer.text.balance_lines is True
        assert layer.text.wrapped_lines == ["Alpha beta", "gamma delta"]

    def test_should_auto_scale_with_max_height_only(self, tmp_path):
        """Auto-fit accepts a height-only constraint and keeps the rendered box within it"""
        from quickthumb import Canvas

        # Given: text constrained only by max_height
        canvas = (
            Canvas(400, 160)
            .background(color="#FFFFFF")
            .text(
                "Tall headline",
                font="Roboto",
                size=72,
                color="#111111",
                position=(200, 80),
                align="center",
                max_height=32,
                min_size=18,
                auto_scale=True,
            )
        )

        # When: inspection and rendering resolve the effective text layer
        inspected = canvas.inspect().layers[1]
        output = tmp_path / "height_only.png"
        canvas.render(str(output))

        # Then: the public layout contract reports a fitting size and a real image exists
        assert inspected.bbox is not None
        assert inspected.bbox.height <= 32
        assert inspected.text is not None
        assert inspected.text.auto_scaled is True
        assert inspected.text.effective_font_size is not None
        assert inspected.text.effective_font_size < 72
        assert output.exists()
        assert output.stat().st_size > 0

    def test_should_fit_single_wrapped_line_using_multiline_line_box(self):
        """Auto-fit uses the renderer line box even when wrapping leaves one line"""
        from quickthumb import Canvas

        # Given: one line that is width-safe but too tall for the multiline renderer box
        canvas = Canvas(600, 160).text(
            "Short headline",
            font="Roboto",
            size=72,
            color="#111111",
            position=(300, 80),
            align="center",
            max_width=500,
            max_height=75,
            min_size=20,
            auto_scale=True,
        )

        # When: inspection resolves the final layout
        inspected = canvas.inspect().layers[0]

        # Then: the font is reduced for the line-height box, not only the glyph ink bounds
        assert inspected.bbox is not None
        assert inspected.bbox.height <= 75
        assert inspected.text is not None
        assert inspected.text.effective_font_size is not None
        assert inspected.text.effective_font_size < 72

    def test_should_render_emoji_with_default_monochrome_pipeline(self, tmp_path):
        """Emoji text continues rendering when the color emoji groundwork is disabled"""
        from quickthumb import Canvas

        # Given: a text layer containing emoji with default monochrome behavior
        canvas = (
            Canvas(240, 120)
            .background(color="#FFFFFF")
            .text("Launch 🚀", font="NotoSans", size=32, color="#111111", position=(10, 40))
        )

        # When: rendering the canvas
        output = tmp_path / "emoji.png"
        canvas.render(str(output))

        # Then: rendering succeeds and produces a non-empty image
        assert output.exists()
        assert output.stat().st_size > 0


class TestTextWrapping:
    """Test suite for text word-wrapping behaviour"""

    def test_should_warn_when_word_exceeds_max_width(self, tmp_path):
        """Rendering plain text with a word wider than max_width emits a UserWarning"""

        from quickthumb import Canvas

        canvas = (
            Canvas(400, 200)
            .background(color="#FFFFFF")
            .text(
                "Superlongwordthatwillneverfit",
                size=48,
                color="#000000",
                position=(200, 100),
                align="center",
                max_width=50,
            )
        )

        with pytest.warns(UserWarning, match="max_width"):
            canvas.render(str(tmp_path / "out.png"))


class TestRichTextWrapping:
    """Test suite for rich-text wrapping parity with plain text"""

    def test_should_not_insert_blank_line_before_an_overflowing_first_word(self, tmp_path):
        """Rich text whose first word exceeds max_width starts at the same row as plain text"""
        import warnings

        from PIL import Image
        from quickthumb import Canvas

        def first_ink_row(canvas, path):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")  # plain text warns about the unbreakable word
                canvas.render(str(path))
            img = Image.open(path).convert("RGB")
            for y in range(img.height):
                for x in range(img.width):
                    if img.getpixel((x, y)) != (255, 255, 255):
                        return y
            return None

        # given: the same unbreakable word as plain and as rich content
        word = "Unbreakablelongword"
        simple = (
            Canvas(400, 300)
            .background(color="#FFFFFF")
            .text(word, size=40, color="#000000", position=(10, 10), max_width=60)
        )
        rich = (
            Canvas(400, 300)
            .background(color="#FFFFFF")
            .text([{"text": word, "color": "#000000"}], size=40, position=(10, 10), max_width=60)
        )

        # when
        simple_row = first_ink_row(simple, tmp_path / "simple.png")
        rich_row = first_ink_row(rich, tmp_path / "rich.png")

        # then: rich starts within path-difference tolerance, not a full blank line (~48px) lower
        assert rich_row is not None and simple_row is not None
        assert abs(rich_row - simple_row) < 24


class TestTextRotation:
    """Test suite for text rotation functionality"""

    @pytest.mark.parametrize(
        "rotation",
        [0, 45, 90, -45, 180, 360, 720, -90, 12.5, -12.5],
    )
    def test_should_accept_various_rotation_values(self, rotation):
        """Test that rotation parameter accepts various float values"""
        from quickthumb import Canvas, TextLayer

        canvas = Canvas(1920, 1080)
        canvas.text("Test", size=48, rotation=rotation)

        assert len(canvas.layers) == 1
        assert canvas.layers[0] == TextLayer(
            type="text", content="Test", size=48, rotation=rotation
        )

    def test_should_anchor_rotated_text_with_align_when_position_omitted(self, tmp_path):
        """Rotated text with align but no position anchors at the alignment point"""
        from quickthumb import Canvas

        # given: identical rotated text, once anchored by align alone, once by the
        # explicit position that align=("center", "middle") implies
        def build(**position_kwargs):
            return (
                Canvas(400, 400)
                .background(color="#FFFFFF")
                .text(
                    "ANCHOR",
                    size=48,
                    color="#000000",
                    align=("center", "middle"),
                    rotation=45,
                    **position_kwargs,
                )
            )

        # when
        implicit_path = tmp_path / "implicit.png"
        explicit_path = tmp_path / "explicit.png"
        build().render(str(implicit_path))
        build(position=("50%", "50%")).render(str(explicit_path))

        # then: both renders are byte-identical
        assert implicit_path.read_bytes() == explicit_path.read_bytes()

    def test_should_serialize_rotation_to_json(self):
        """Test that rotation field is included in JSON serialization"""
        from quickthumb import Canvas

        canvas = Canvas(1920, 1080)
        canvas.text("Rotated", size=48, rotation=45)

        json_str = canvas.to_json()
        data = json.loads(json_str)

        assert len(data["layers"]) == 1
        assert data["layers"][0] == snapshot(
            {
                "type": "text",
                "content": "Rotated",
                "font": None,
                "font_source": "auto",
                "font_variations": {},
                "emoji_style": "monochrome",
                "size": 48,
                "color": None,
                "fill": None,
                "position": None,
                "align": None,
                "bold": False,
                "italic": False,
                "weight": None,
                "max_width": None,
                "max_height": None,
                "min_size": 1,
                "balance_lines": False,
                "effects": [],
                "line_height": None,
                "letter_spacing": None,
                "auto_scale": False,
                "rotation": 45.0,
                "opacity": 1.0,
                "animation": None,
            }
        )

    def test_should_deserialize_rotation_from_json(self):
        """Test that rotation field is correctly deserialized from JSON"""
        from quickthumb import Canvas, TextLayer

        json_data = {
            "width": 1920,
            "height": 1080,
            "layers": [
                {
                    "type": "text",
                    "content": "Rotated",
                    "size": 48,
                    "rotation": 45,
                }
            ],
        }

        canvas = Canvas.from_json(json.dumps(json_data))

        assert len(canvas.layers) == 1
        assert isinstance(canvas.layers[0], TextLayer)
        assert canvas.layers[0] == snapshot(
            TextLayer(type="text", content="Rotated", size=48, rotation=45.0)
        )


class TestTextEffects:
    """Test suite for text effects using effect classes"""

    def test_should_add_text_with_stroke_effect(self):
        """Test that text can be created with Stroke effect"""
        from quickthumb import Canvas, Stroke

        canvas = Canvas(1920, 1080)

        canvas.text("Hello", size=72, effects=[Stroke(width=3, color="#000000")])

        assert len(canvas.layers) == 1
        assert canvas.layers == [
            TextLayer(
                type="text",
                content="Hello",
                size=72,
                effects=[Stroke(width=3, color="#000000")],
            )
        ]

    def test_should_add_text_with_multiple_effects(self):
        """Test that text can have multiple stroke effects"""
        from quickthumb import Canvas, Stroke

        canvas = Canvas(1920, 1080)

        canvas.text(
            "Epic",
            size=96,
            effects=[
                Stroke(width=3, color="#000000"),
                Stroke(width=5, color="#FF0000"),
            ],
        )

        assert len(canvas.layers) == 1
        assert canvas.layers[0] == TextLayer(
            type="text",
            content="Epic",
            size=96,
            effects=[Stroke(width=3, color="#000000"), Stroke(width=5, color="#FF0000")],
        )

    def test_should_add_text_without_effects(self):
        """Test that text can be created without effects"""
        from quickthumb import Canvas

        canvas = Canvas(1920, 1080)

        canvas.text("Plain", size=72)

        assert len(canvas.layers) == 1
        assert canvas.layers[0] == TextLayer(
            type="text",
            content="Plain",
            size=72,
            effects=[],
        )

    def test_should_serialize_text_with_effects_to_json(self):
        """Test that text effects are serialized to JSON"""
        import json

        from quickthumb import Canvas, Stroke

        canvas = Canvas(1920, 1080).text(
            "Hello", size=72, effects=[Stroke(width=3, color="#000000")]
        )

        json_str = canvas.to_json()
        data = json.loads(json_str)

        assert len(data["layers"]) == 1
        assert data["layers"][0] == snapshot(
            {
                "type": "text",
                "content": "Hello",
                "font": None,
                "font_source": "auto",
                "font_variations": {},
                "emoji_style": "monochrome",
                "size": 72,
                "color": None,
                "fill": None,
                "position": None,
                "align": None,
                "bold": False,
                "italic": False,
                "weight": None,
                "max_width": None,
                "max_height": None,
                "min_size": 1,
                "balance_lines": False,
                "effects": [{"type": "stroke", "width": 3, "color": "#000000"}],
                "line_height": None,
                "letter_spacing": None,
                "auto_scale": False,
                "rotation": 0.0,
                "opacity": 1.0,
                "animation": None,
            }
        )

    def test_should_deserialize_text_with_effects_from_json(self):
        """Test that text effects are deserialized from JSON"""
        import json

        from quickthumb import Canvas

        json_data = {
            "width": 1920,
            "height": 1080,
            "layers": [
                {
                    "type": "text",
                    "content": "Hello",
                    "size": 72,
                    "effects": [{"type": "stroke", "width": 3, "color": "#000000"}],
                }
            ],
        }

        canvas = Canvas.from_json(json.dumps(json_data))

        assert len(canvas.layers) == 1
        assert canvas.layers[0] == TextLayer(
            type="text",
            content="Hello",
            size=72,
            effects=[Stroke(width=3, color="#000000")],
        )

    @pytest.mark.parametrize(
        "effect_args,error_pattern",
        [
            ({"width": -1, "color": "#000000"}, "width.*greater than 0"),
            ({"width": 3, "color": "invalid"}, "invalid hex"),
        ],
    )
    def test_should_raise_error_for_invalid_stroke(self, effect_args, error_pattern):
        """Test that invalid Stroke parameters raise ValidationError"""
        from quickthumb import Canvas, Stroke, ValidationError

        canvas = Canvas(1920, 1080)

        with pytest.raises(ValidationError, match=error_pattern):
            canvas.text("Hello", effects=[Stroke(**effect_args)])

    def test_should_add_text_with_shadow_effect(self):
        """Test that text can be created with Shadow effect"""
        from quickthumb import Canvas, Shadow

        canvas = Canvas(1920, 1080)

        canvas.text("Hello", size=72, effects=[Shadow(offset_x=5, offset_y=5, color="#000000")])

        assert len(canvas.layers) == 1
        assert canvas.layers == [
            TextLayer(
                type="text",
                content="Hello",
                size=72,
                effects=[Shadow(offset_x=5, offset_y=5, color="#000000", blur_radius=0)],
            )
        ]

    def test_should_add_text_with_multiple_shadow_effects(self):
        """Test that text can have multiple shadow effects"""
        from quickthumb import Canvas, Shadow

        canvas = Canvas(1920, 1080)

        canvas.text(
            "Epic",
            size=96,
            effects=[
                Shadow(offset_x=3, offset_y=3, color="#000000", blur_radius=2),
                Shadow(offset_x=6, offset_y=6, color="#FF0000", blur_radius=5),
            ],
        )

        assert len(canvas.layers) == 1
        assert canvas.layers[0] == TextLayer(
            type="text",
            content="Epic",
            size=96,
            effects=[
                Shadow(offset_x=3, offset_y=3, color="#000000", blur_radius=2),
                Shadow(offset_x=6, offset_y=6, color="#FF0000", blur_radius=5),
            ],
        )

    def test_should_serialize_text_with_shadow_to_json(self):
        """Test that shadow effects are serialized to JSON"""
        import json

        from quickthumb import Canvas, Shadow

        canvas = Canvas(1920, 1080).text(
            "Hello", size=72, effects=[Shadow(offset_x=5, offset_y=5, color="#000000")]
        )

        json_str = canvas.to_json()
        data = json.loads(json_str)

        assert len(data["layers"]) == 1
        assert data["layers"][0] == snapshot(
            {
                "type": "text",
                "content": "Hello",
                "font": None,
                "font_source": "auto",
                "font_variations": {},
                "emoji_style": "monochrome",
                "size": 72,
                "color": None,
                "fill": None,
                "position": None,
                "align": None,
                "bold": False,
                "italic": False,
                "weight": None,
                "max_width": None,
                "max_height": None,
                "min_size": 1,
                "balance_lines": False,
                "effects": [
                    {
                        "type": "shadow",
                        "offset_x": 5,
                        "offset_y": 5,
                        "color": "#000000",
                        "blur_radius": 0,
                    }
                ],
                "line_height": None,
                "letter_spacing": None,
                "auto_scale": False,
                "rotation": 0.0,
                "opacity": 1.0,
                "animation": None,
            }
        )

    def test_should_deserialize_text_with_shadow_from_json(self):
        """Test that shadow effects are deserialized from JSON"""
        import json

        from quickthumb import Canvas, Shadow

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
                            "type": "shadow",
                            "offset_x": 5,
                            "offset_y": 5,
                            "color": "#000000",
                            "blur_radius": 0,
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
            effects=[Shadow(offset_x=5, offset_y=5, color="#000000", blur_radius=0)],
        )

    @pytest.mark.parametrize(
        "effect_args,error_pattern",
        [
            (
                {"offset_x": 5, "offset_y": 5, "color": "invalid", "blur_radius": 0},
                "invalid hex",
            ),
            (
                {"offset_x": 5, "offset_y": 5, "color": "#000000", "blur_radius": -1},
                "blur_radius.*negative",
            ),
        ],
    )
    def test_should_raise_error_for_invalid_shadow(self, effect_args, error_pattern):
        """Test that invalid Shadow parameters raise ValidationError"""
        from quickthumb import Canvas, Shadow, ValidationError

        canvas = Canvas(1920, 1080)

        with pytest.raises(ValidationError, match=error_pattern):
            canvas.text("Hello", effects=[Shadow(**effect_args)])

    def test_should_add_text_with_glow_effect(self):
        """Test that text can be created with Glow effect"""
        from quickthumb import Canvas, Glow

        canvas = Canvas(1920, 1080)

        canvas.text("Hello", size=72, effects=[Glow(color="#FF0000", radius=10)])

        assert len(canvas.layers) == 1
        assert canvas.layers == [
            TextLayer(
                type="text",
                content="Hello",
                size=72,
                effects=[Glow(color="#FF0000", radius=10, opacity=1.0)],
            )
        ]

    def test_should_add_text_with_multiple_glow_effects(self):
        """Test that text can have multiple glow effects with different colors and radii"""
        from quickthumb import Canvas, Glow

        canvas = Canvas(1920, 1080)

        canvas.text(
            "Epic",
            size=96,
            effects=[
                Glow(color="#FF0000", radius=5, opacity=0.8),
                Glow(color="#0000FF", radius=15, opacity=0.5),
            ],
        )

        assert len(canvas.layers) == 1
        assert canvas.layers[0] == TextLayer(
            type="text",
            content="Epic",
            size=96,
            effects=[
                Glow(color="#FF0000", radius=5, opacity=0.8),
                Glow(color="#0000FF", radius=15, opacity=0.5),
            ],
        )

    def test_should_serialize_text_with_glow_to_json(self):
        """Test that glow effects are serialized to JSON"""
        import json

        from quickthumb import Canvas, Glow

        canvas = Canvas(1920, 1080).text(
            "Hello", size=72, effects=[Glow(color="#FF0000", radius=10, opacity=0.9)]
        )

        json_str = canvas.to_json()
        data = json.loads(json_str)

        assert len(data["layers"]) == 1
        assert data["layers"][0] == snapshot(
            {
                "type": "text",
                "content": "Hello",
                "font": None,
                "font_source": "auto",
                "font_variations": {},
                "emoji_style": "monochrome",
                "size": 72,
                "color": None,
                "fill": None,
                "position": None,
                "align": None,
                "bold": False,
                "italic": False,
                "weight": None,
                "max_width": None,
                "max_height": None,
                "min_size": 1,
                "balance_lines": False,
                "effects": [{"type": "glow", "color": "#FF0000", "radius": 10, "opacity": 0.9}],
                "line_height": None,
                "letter_spacing": None,
                "auto_scale": False,
                "rotation": 0.0,
                "opacity": 1.0,
                "animation": None,
            }
        )

    def test_should_deserialize_text_with_glow_from_json(self):
        """Test that glow effects are deserialized from JSON"""
        import json

        from quickthumb import Canvas, Glow

        json_data = {
            "width": 1920,
            "height": 1080,
            "layers": [
                {
                    "type": "text",
                    "content": "Hello",
                    "size": 72,
                    "effects": [{"type": "glow", "color": "#FF0000", "radius": 10, "opacity": 0.9}],
                }
            ],
        }

        canvas = Canvas.from_json(json.dumps(json_data))

        assert len(canvas.layers) == 1
        assert canvas.layers[0] == TextLayer(
            type="text",
            content="Hello",
            size=72,
            effects=[Glow(color="#FF0000", radius=10, opacity=0.9)],
        )

    @pytest.mark.parametrize(
        "effect_args,error_pattern",
        [
            ({"color": "invalid", "radius": 10}, "invalid hex"),
            ({"color": "#FF0000", "radius": 0}, "radius.*greater than 0"),
            ({"color": "#FF0000", "radius": -5}, "radius.*greater than 0"),
            ({"color": "#FF0000", "radius": 10, "opacity": -0.1}, "opacity.*0.0.*1.0"),
            ({"color": "#FF0000", "radius": 10, "opacity": 1.5}, "opacity.*0.0.*1.0"),
        ],
    )
    def test_should_raise_error_for_invalid_glow(self, effect_args, error_pattern):
        """Test that invalid Glow parameters raise ValidationError"""
        from quickthumb import Canvas, Glow, ValidationError

        canvas = Canvas(1920, 1080)

        with pytest.raises(ValidationError, match=error_pattern):
            canvas.text("Hello", effects=[Glow(**effect_args)])


class TestTextFill:
    """Validation and serialization tests for text fill (Feature 3)"""

    def test_should_serialize_linear_gradient_fill(self):
        """Linear gradient fill serializes with correct type discriminator and fields"""
        from quickthumb import Canvas, LinearGradient

        canvas = Canvas(400, 200).text(
            "GRADIENT",
            size=60,
            fill=LinearGradient(angle=45, stops=[("#FF0000", 0.0), ("#0000FF", 1.0)]),
            position=(0, 0),
        )

        data = json.loads(canvas.to_json())
        fill = data["layers"][0]["fill"]
        assert fill["type"] == "linear"
        assert fill["angle"] == 45
        assert fill["stops"] == [["#FF0000", 0.0], ["#0000FF", 1.0]]

    def test_should_serialize_radial_gradient_fill(self):
        """Radial gradient fill serializes with correct type discriminator"""
        from quickthumb import Canvas, RadialGradient

        canvas = Canvas(400, 200).text(
            "RADIAL",
            size=60,
            fill=RadialGradient(stops=[("#FFD700", 0.0), ("#FF000000", 1.0)]),
            position=(0, 0),
        )

        data = json.loads(canvas.to_json())
        fill = data["layers"][0]["fill"]
        assert fill["type"] == "radial"
        assert len(fill["stops"]) == 2

    def test_should_serialize_image_fill(self):
        """TextFillImage fill serializes with type, path, and fit"""
        from quickthumb import Canvas, TextFillImage

        canvas = Canvas(400, 200).text(
            "TEXTURE",
            size=60,
            fill=TextFillImage(path="fire.jpg", fit="contain"),
            position=(0, 0),
        )

        data = json.loads(canvas.to_json())
        fill = data["layers"][0]["fill"]
        assert fill["type"] == "image"
        assert fill["path"] == "fire.jpg"
        assert fill["fit"] == "contain"

    def test_should_serialize_null_fill_when_not_set(self):
        """fill serializes as null when not explicitly set"""
        from quickthumb import Canvas

        canvas = Canvas(400, 200).text("Plain", size=60, position=(0, 0))

        data = json.loads(canvas.to_json())
        assert data["layers"][0]["fill"] is None

    def test_should_roundtrip_fill_through_json(self):
        """Canvas with gradient fill survives a to_json/from_json round-trip"""
        from quickthumb import Canvas, LinearGradient
        from quickthumb.models import TextLayer

        fill = LinearGradient(angle=90, stops=[("#FF6B6B", 0.0), ("#4ECDC4", 1.0)])
        canvas = Canvas(400, 200).text("ROUND", size=60, fill=fill, position=(0, 0))

        canvas2 = Canvas.from_json(canvas.to_json())
        layer = canvas2.layers[0]
        assert isinstance(layer, TextLayer)
        assert isinstance(layer.fill, LinearGradient)
        assert layer.fill.angle == 90
        assert layer.fill.stops == [("#FF6B6B", 0.0), ("#4ECDC4", 1.0)]

    def test_should_serialize_text_part_fill(self):
        """TextPart fill serializes as the fill object when set, and null when not set"""
        from quickthumb import Canvas, LinearGradient, TextPart

        parts = [
            TextPart(
                text="HOT ",
                fill=LinearGradient(angle=0, stops=[("#FF4500", 0.0), ("#FFD700", 1.0)]),
            ),
            TextPart(text="COLD", color="#00BFFF"),
        ]
        canvas = Canvas(400, 200).text(parts, size=60, position=(0, 0))

        data = json.loads(canvas.to_json())
        content = data["layers"][0]["content"]
        assert content[0]["fill"]["type"] == "linear"
        assert content[1]["fill"] is None

    def test_should_raise_file_not_found_for_missing_image_fill(self):
        """Rendering with a missing TextFillImage file raises FileNotFoundError"""
        import os
        import tempfile

        from quickthumb import Canvas, TextFillImage

        canvas = Canvas(400, 200).text(
            "MISSING",
            size=60,
            fill=TextFillImage(path="nonexistent_texture.jpg"),
            position=(0, 0),
        )

        with pytest.raises(FileNotFoundError), tempfile.TemporaryDirectory() as tmpdir:
            canvas.render(os.path.join(tmpdir, "out.png"))

    def test_should_raise_file_not_found_for_missing_text_part_image_fill(self):
        """Rendering with a missing TextPart image fill raises FileNotFoundError"""
        import os
        import tempfile

        from quickthumb import Canvas, TextFillImage, TextPart

        canvas = Canvas(400, 200).text(
            [TextPart(text="X", fill=TextFillImage(path="ghost.jpg"))],
            size=60,
            position=(0, 0),
        )

        with pytest.raises(FileNotFoundError), tempfile.TemporaryDirectory() as tmpdir:
            canvas.render(os.path.join(tmpdir, "out.png"))
