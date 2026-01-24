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
