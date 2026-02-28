"""Tests for shape layer functionality"""

import json

import pytest
from inline_snapshot import snapshot
from quickthumb.errors import ValidationError
from quickthumb.models import Align, ShapeLayer


class TestShapeLayerValidation:
    """Test suite for shape layer parameter validation"""

    @pytest.mark.parametrize(
        "shape,error_pattern",
        [
            ("triangle", "shape.*rectangle.*ellipse"),
            ("circle", "shape.*rectangle.*ellipse"),
            ("polygon", "shape.*rectangle.*ellipse"),
        ],
    )
    def test_should_reject_invalid_shape_type(self, shape, error_pattern):
        """Test that unsupported shape types raise ValidationError"""
        from quickthumb import Canvas

        canvas = Canvas(400, 300)
        with pytest.raises(ValidationError, match=error_pattern):
            canvas.shape(shape=shape, position=(0, 0), width=100, height=100, color="#FF0000")

    @pytest.mark.parametrize(
        "opacity,error_pattern",
        [
            (1.5, "opacity.*0.0.*1.0"),
            (-0.5, "opacity.*0.0.*1.0"),
            (2.0, "opacity.*0.0.*1.0"),
        ],
    )
    def test_should_reject_invalid_opacity(self, opacity, error_pattern):
        """Test that opacity outside 0-1 range raises ValidationError"""
        from quickthumb import Canvas

        canvas = Canvas(400, 300)
        with pytest.raises(ValidationError, match=error_pattern):
            canvas.shape(
                shape="rectangle",
                position=(0, 0),
                width=100,
                height=100,
                color="#FF0000",
                opacity=opacity,
            )

    @pytest.mark.parametrize(
        "width,height,error_pattern",
        [
            (-100, 100, "width.*greater than 0"),
            (100, -100, "height.*greater than 0"),
            (0, 100, "width.*greater than 0"),
            (100, 0, "height.*greater than 0"),
        ],
    )
    def test_should_reject_invalid_dimensions(self, width, height, error_pattern):
        """Test that non-positive width/height raise ValidationError"""
        from quickthumb import Canvas

        canvas = Canvas(400, 300)
        with pytest.raises(ValidationError, match=error_pattern):
            canvas.shape(
                shape="rectangle",
                position=(0, 0),
                width=width,
                height=height,
                color="#FF0000",
            )

    @pytest.mark.parametrize(
        "position,error_pattern",
        [
            ((100,), "position.*must.*tuple.*two"),
            ((100, 200, 300), "position.*must.*tuple.*two"),
            (("50", "50"), "invalid percentage"),
        ],
    )
    def test_should_reject_invalid_position(self, position, error_pattern):
        """Test that invalid position format raises ValidationError"""
        from quickthumb import Canvas

        canvas = Canvas(400, 300)
        with pytest.raises(ValidationError, match=error_pattern):
            canvas.shape(
                shape="rectangle",
                position=position,
                width=100,
                height=100,
                color="#FF0000",
            )

    def test_should_reject_negative_border_radius(self):
        """Test that negative border_radius raises ValidationError"""
        from quickthumb import Canvas

        canvas = Canvas(400, 300)
        with pytest.raises(ValidationError, match="border_radius.*greater than or equal to 0"):
            canvas.shape(
                shape="rectangle",
                position=(0, 0),
                width=100,
                height=100,
                color="#FF0000",
                border_radius=-5,
            )


class TestCanvasShapeAPI:
    """Test suite for Canvas.shape() method"""

    def test_should_add_shape_layer_and_support_method_chaining(self):
        """Test that Canvas.shape() adds a shape layer and returns self for chaining"""
        from quickthumb import Canvas

        canvas = Canvas(400, 300)
        result = canvas.shape(
            shape="rectangle",
            position=(100, 75),
            width=200,
            height=150,
            color="#FF5733",
        )

        assert result is canvas
        assert len(canvas.layers) == 1
        assert canvas.layers[0] == ShapeLayer(
            type="shape",
            shape="rectangle",
            position=(100, 75),
            width=200,
            height=150,
            color="#FF5733",
        )

    def test_should_accept_percentage_position(self):
        """Test that shapes accept percentage-based positions"""
        from quickthumb import Canvas

        canvas = Canvas(400, 300)
        canvas.shape(
            shape="rectangle",
            position=("50%", "50%"),
            width=100,
            height=100,
            color="#FF0000",
        )

        layer = canvas.layers[0]
        assert isinstance(layer, ShapeLayer)
        assert layer.position == ("50%", "50%")

    def test_should_store_all_optional_params(self):
        """Test that all optional params are stored correctly on the layer"""
        from quickthumb import Canvas
        from quickthumb.models import Stroke

        canvas = Canvas(400, 300)
        canvas.shape(
            shape="ellipse",
            position=(200, 150),
            width=160,
            height=100,
            color="#3498DB",
            effects=[Stroke(width=3, color="#1A5276")],
            border_radius=0,
            opacity=0.8,
            rotation=30,
            align=("center", "middle"),
        )

        layer = canvas.layers[0]
        assert layer == snapshot(
            ShapeLayer(
                type="shape",
                shape="ellipse",
                position=(200, 150),
                width=160,
                height=100,
                color="#3498DB",
                effects=[Stroke(width=3, color="#1A5276")],
                border_radius=0,
                opacity=0.8,
                rotation=30.0,
                align=Align.CENTER,
            )
        )


class TestShapeLayerSerialization:
    """Test suite for JSON serialization/deserialization of shape layers"""

    def test_should_serialize_shape_layer_to_json(self):
        """Test that canvas with shape layer (including effects) serializes to correct JSON"""
        from quickthumb import Canvas
        from quickthumb.models import Stroke

        canvas = Canvas(400, 300)
        canvas.shape(
            shape="rectangle",
            position=(100, 75),
            width=200,
            height=150,
            color="#FF5733",
            effects=[Stroke(width=2, color="#000000")],
            border_radius=10,
            opacity=0.9,
            rotation=0,
        )

        data = json.loads(canvas.to_json())
        assert data["layers"][0] == snapshot(
            {
                "type": "shape",
                "shape": "rectangle",
                "position": [100, 75],
                "width": 200,
                "height": 150,
                "color": "#FF5733",
                "border_radius": 10,
                "opacity": 0.9,
                "rotation": 0.0,
                "align": None,
                "effects": [{"type": "stroke", "width": 2, "color": "#000000"}],
            }
        )

    def test_should_round_trip_shape_layer_through_json(self):
        """Test that shape layer survives a JSON round-trip unchanged"""
        from quickthumb import Canvas

        original = Canvas(400, 300)
        original.shape(
            shape="ellipse",
            position=("50%", "50%"),
            width=200,
            height=100,
            color="#9B59B6",
            opacity=0.75,
            align=("center", "middle"),
        )

        restored = Canvas.from_json(original.to_json())

        assert restored.layers[0] == original.layers[0]

    def test_should_deserialize_shape_layer_from_json(self):
        """Test that a shape layer can be deserialized from JSON"""
        from quickthumb import Canvas

        json_data = {
            "width": 400,
            "height": 300,
            "layers": [
                {
                    "type": "shape",
                    "shape": "rectangle",
                    "position": [100, 75],
                    "width": 200,
                    "height": 150,
                    "color": "#FF5733",
                }
            ],
        }

        canvas = Canvas.from_json(json.dumps(json_data))

        assert len(canvas.layers) == 1
        assert canvas.layers[0] == ShapeLayer(
            type="shape",
            shape="rectangle",
            position=(100, 75),
            width=200,
            height=150,
            color="#FF5733",
        )
