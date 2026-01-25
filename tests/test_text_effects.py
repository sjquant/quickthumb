"""Tests for text effects functionality"""

import pytest
from inline_snapshot import snapshot
from quickthumb.models import Stroke, TextLayer


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
                "size": 72,
                "color": None,
                "position": None,
                "align": None,
                "bold": False,
                "italic": False,
                "max_width": None,
                "effects": [{"type": "stroke", "width": 3, "color": "#000000"}],
                "line_height": None,
                "letter_spacing": None,
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
            ({"width": -1, "color": "#000000"}, "width.*positive"),
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
                "size": 72,
                "color": None,
                "position": None,
                "align": None,
                "bold": False,
                "italic": False,
                "max_width": None,
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
                "size": 72,
                "color": None,
                "position": None,
                "align": None,
                "bold": False,
                "italic": False,
                "max_width": None,
                "effects": [{"type": "glow", "color": "#FF0000", "radius": 10, "opacity": 0.9}],
                "line_height": None,
                "letter_spacing": None,
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
            ({"color": "#FF0000", "radius": 0}, "radius.*positive"),
            ({"color": "#FF0000", "radius": -5}, "radius.*positive"),
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
