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
            ("circle", "shape.*rectangle.*pill"),
            ("hexagon", "shape.*rectangle.*pill"),
            ("squircle", "shape.*rectangle.*pill"),
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
                "points": None,
                "star_points": 5,
                "inner_radius": 0.5,
                "effects": [{"type": "stroke", "width": 2, "color": "#000000"}],
                "animation": None,
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


class TestShapePrimitives:
    """Test suite for pill, triangle, star, and polygon shape primitives"""

    @pytest.mark.parametrize("shape", ["pill", "triangle", "star"])
    def test_should_round_trip_new_primitives_through_json(self, shape):
        """pill/triangle/star shapes serialize and deserialize preserving the shape type"""
        from quickthumb import Canvas

        # given: a canvas with one of the new primitives
        canvas = Canvas(400, 300).shape(
            shape=shape, position=(20, 30), width=120, height=80, color="#3366FF"
        )

        # when: round-tripped through JSON
        restored = Canvas.from_json(canvas.to_json())

        # then: the shape type and geometry survive
        layer = restored.layers[0]
        assert layer.shape == shape
        assert (layer.width, layer.height) == (120, 80)

    def test_should_round_trip_star_parameters_through_json(self):
        """Non-default star_points and inner_radius survive the JSON round-trip"""
        from quickthumb import Canvas

        # given: a star with non-default parameters (and the minimum spike count accepted)
        canvas = (
            Canvas(400, 300)
            .shape(
                shape="star",
                position=(0, 0),
                width=100,
                height=100,
                color="#FFD700",
                star_points=7,
                inner_radius=0.4,
            )
            .shape(
                shape="star",
                position=(120, 0),
                width=100,
                height=100,
                color="#FFD700",
                star_points=3,
            )
        )

        # when
        restored = Canvas.from_json(canvas.to_json())

        # then: parameters are stored, serialized, and restored
        assert restored.layers[0].star_points == 7
        assert restored.layers[0].inner_radius == 0.4
        assert restored.layers[1].star_points == 3

    def test_should_round_trip_polygon_points_through_json(self):
        """Polygon shapes preserve their normalized points across JSON round-trip"""
        from quickthumb import Canvas

        # given: a polygon with explicit normalized points (a right arrow)
        points = [
            (0.0, 0.25),
            (0.6, 0.25),
            (0.6, 0.0),
            (1.0, 0.5),
            (0.6, 1.0),
            (0.6, 0.75),
            (0.0, 0.75),
        ]
        canvas = Canvas(400, 300).shape(
            shape="polygon",
            position=(10, 10),
            width=200,
            height=100,
            color="#FF8800",
            points=points,
        )

        # when
        serialized = json.loads(canvas.to_json())
        restored = Canvas.from_json(canvas.to_json())

        # then: the wire format keeps points as [x, y] pairs and the round-trip preserves them
        assert serialized["layers"][0]["points"] == [list(p) for p in points]
        assert restored.layers[0].shape == "polygon"
        assert [tuple(p) for p in restored.layers[0].points] == points

    @pytest.mark.parametrize(
        "points,error_pattern",
        [
            (None, "points"),  # polygon requires points
            ([(0.0, 0.0), (1.0, 1.0)], "points"),  # fewer than 3 points
            ([(0.0, 0.0), (1.5, 0.0), (1.0, 1.0)], "points"),  # coordinate out of 0..1
            ([(0.0, 0.0), (-0.1, 0.0), (1.0, 1.0)], "points"),  # negative coordinate
        ],
    )
    def test_should_reject_invalid_polygon_points(self, points, error_pattern):
        """Polygon points are required, with at least 3 entries and coordinates in 0..1"""
        from quickthumb import Canvas

        canvas = Canvas(400, 300)
        with pytest.raises(ValidationError, match=error_pattern):
            canvas.shape(
                shape="polygon",
                position=(0, 0),
                width=100,
                height=100,
                color="#FF0000",
                points=points,
            )

    def test_should_reject_points_on_non_polygon_shapes(self):
        """Providing points for a non-polygon shape raises ValidationError"""
        from quickthumb import Canvas

        canvas = Canvas(400, 300)
        with pytest.raises(ValidationError, match="points"):
            canvas.shape(
                shape="rectangle",
                position=(0, 0),
                width=100,
                height=100,
                color="#FF0000",
                points=[(0.0, 0.0), (1.0, 0.0), (1.0, 1.0)],
            )

    @pytest.mark.parametrize(
        "kwargs,error_pattern",
        [
            ({"star_points": 2}, "star_points"),
            ({"inner_radius": 0.0}, "inner_radius"),
            ({"inner_radius": 1.0}, "inner_radius"),
        ],
    )
    def test_should_reject_invalid_star_parameters(self, kwargs, error_pattern):
        """Star shapes require star_points >= 3 and inner_radius strictly between 0 and 1"""
        from quickthumb import Canvas

        canvas = Canvas(400, 300)
        with pytest.raises(ValidationError, match=error_pattern):
            canvas.shape(
                shape="star",
                position=(0, 0),
                width=100,
                height=100,
                color="#FF0000",
                **kwargs,
            )
