"""Tests for image layer functionality"""

import pytest
from inline_snapshot import snapshot
from quickthumb.errors import ValidationError
from quickthumb.models import Align, ImageLayer


class TestImageLayers:
    """Test suite for image layer operations"""

    @pytest.mark.parametrize(
        "opacity,error_pattern",
        [
            (1.5, "opacity.*0.0.*1.0"),
            (-0.5, "opacity.*0.0.*1.0"),
            (2.0, "opacity.*0.0.*1.0"),
        ],
    )
    def test_should_reject_invalid_opacity(self, opacity, error_pattern):
        """Test that opacity outside 0-1 range raises ValidationError with proper message"""
        # Given: Canvas and invalid opacity value
        from quickthumb import Canvas

        canvas = Canvas(1920, 1080)

        # When/Then: Creating image with invalid opacity should fail with error message
        with pytest.raises(ValidationError, match=error_pattern):
            canvas.image(path="assets/logo.png", position=(0, 0), opacity=opacity)

    @pytest.mark.parametrize(
        "width,height,error_pattern",
        [
            (-100, None, "width.*greater than 0"),
            (None, -100, "height.*greater than 0"),
            (0, None, "width.*greater than 0"),
            (None, 0, "height.*greater than 0"),
        ],
    )
    def test_should_reject_invalid_dimensions(self, width, height, error_pattern):
        """Test that invalid width/height raise ValidationError with proper message"""
        # Given: Canvas and invalid dimensions
        from quickthumb import Canvas

        canvas = Canvas(1920, 1080)

        # When/Then: Creating image with invalid dimensions should fail with error message
        with pytest.raises(ValidationError, match=error_pattern):
            canvas.image(path="assets/logo.png", position=(0, 0), width=width, height=height)

    @pytest.mark.parametrize(
        "position,error_pattern",
        [
            ((100,), "position.*must.*tuple.*two"),
            ((100, 200, 300), "position.*must.*tuple.*two"),
            (("50", "50"), "invalid percentage"),
            (("ab10%", "cd20%"), "invalid percentage"),
        ],
    )
    def test_should_reject_invalid_position(self, position, error_pattern):
        """Test that invalid position format raises ValidationError with proper message"""
        # Given: Canvas and invalid position
        from quickthumb import Canvas

        canvas = Canvas(1920, 1080)

        # When/Then: Creating image with invalid position should fail with error message
        with pytest.raises(ValidationError, match=error_pattern):
            canvas.image(path="assets/logo.png", position=position)

    @pytest.mark.parametrize(
        "align,error_pattern",
        [
            (("invalid", "left"), "invalid.*align"),
            (("top", "invalid"), "invalid.*align"),
            (("top",), "align must be a tuple of two elements"),
            (("top", "left", "extra"), "align must be a tuple of two elements"),
        ],
    )
    def test_should_reject_invalid_align(self, align, error_pattern):
        """Test that invalid align values raise ValidationError with proper message"""
        # Given: Canvas and invalid align
        from quickthumb import Canvas

        canvas = Canvas(1920, 1080)

        # When/Then: Creating image with invalid align should fail with error message
        with pytest.raises(ValidationError, match=error_pattern):
            canvas.image(path="assets/logo.png", position=(0, 0), align=align)


class TestCanvasImageAPI:
    """Test suite for Canvas.image() method"""

    def test_should_add_image_layer_to_canvas(self):
        """Test that Canvas.image() adds an image layer and supports method chaining"""
        from quickthumb import Canvas

        # Given: A canvas
        canvas = Canvas(1920, 1080)

        # When: Adding an image layer
        result = canvas.image(path="assets/logo.png", position=(50, 50))

        # Then: Should return self for method chaining and add correct layer
        assert result is canvas
        expected_layer = ImageLayer(
            type="image",
            path="assets/logo.png",
            position=(50, 50),
            width=None,
            height=None,
            opacity=1.0,
            rotation=0,
            align=Align.TOP_LEFT,
        )
        assert len(canvas.layers) == 1
        assert canvas.layers[0] == expected_layer


class TestImageLayerSerialization:
    """Test suite for JSON serialization/deserialization"""

    def test_should_serialize_image_layer_to_json(self):
        """Test that canvas with image layer can be serialized to JSON"""
        # Given: Canvas with image layer with all parameters
        from quickthumb import Canvas

        canvas = Canvas(1920, 1080)
        canvas.image(
            path="assets/logo.png",
            position=(50, 50),
            width=200,
            height=150,
            opacity=0.8,
            rotation=45,
            align=("middle", "center"),
        )

        # When: User serializes canvas to JSON
        import json

        json_str = canvas.to_json()
        data = json.loads(json_str)

        # Then: JSON should contain image layer with correct structure
        assert data["width"] == 1920
        assert data["height"] == 1080
        assert len(data["layers"]) == 1
        assert data["layers"][0] == {
            "type": "image",
            "path": "assets/logo.png",
            "position": [50, 50],
            "width": 200,
            "height": 150,
            "opacity": 0.8,
            "rotation": 45,
            "align": "center",
        }

    def test_should_deserialize_image_layer_from_json(self):
        """Test that canvas with image layer can be deserialized from JSON"""
        # Given: JSON string with image layer
        import json

        json_data = {
            "width": 1920,
            "height": 1080,
            "layers": [
                {
                    "type": "image",
                    "path": "assets/logo.png",
                    "position": [50, 50],
                    "width": 200,
                    "height": 150,
                    "opacity": 0.8,
                    "rotation": 45,
                    "align": ["middle", "center"],
                }
            ],
        }
        json_str = json.dumps(json_data)

        # When: User deserializes canvas from JSON
        from quickthumb import Canvas

        canvas = Canvas.from_json(json_str)

        # Then: Canvas should have image layer with correct properties
        assert canvas.width == 1920
        assert canvas.height == 1080
        assert len(canvas.layers) == 1
        assert canvas.layers[0] == ImageLayer(
            type="image",
            path="assets/logo.png",
            position=(50, 50),
            width=200,
            height=150,
            opacity=0.8,
            rotation=45,
            align=Align.CENTER,
        )

    def test_should_round_trip_image_layer_through_json(self):
        """Test that canvas with image layer can be serialized and deserialized"""
        from quickthumb import Canvas

        # Given: Canvas with image layer
        original = Canvas(1920, 1080)
        original.image(
            path="assets/logo.png",
            position=(50, 50),
            width=200,
            opacity=0.8,
            rotation=45,
            align=("middle", "center"),
        )

        # When: Round-tripping through JSON
        json_str = original.to_json()
        restored = Canvas.from_json(json_str)

        # Then: Restored canvas should match original
        assert restored.width == original.width
        assert restored.height == original.height
        assert len(restored.layers) == len(original.layers)
        assert restored.layers[0] == original.layers[0]

    def test_should_serialize_percentage_position_to_json(self):
        """Test that percentage positions are serialized correctly"""
        # Given: Canvas with image using percentage position
        from quickthumb import Canvas

        canvas = Canvas(1920, 1080)
        canvas.image(path="assets/logo.png", position=("50%", "25%"), width=100)

        # When: Serializing to JSON
        import json

        json_str = canvas.to_json()
        data = json.loads(json_str)

        # Then
        assert data == snapshot(
            {
                "width": 1920,
                "height": 1080,
                "layers": [
                    {
                        "type": "image",
                        "path": "assets/logo.png",
                        "position": ["50%", "25%"],
                        "width": 100,
                        "height": None,
                        "opacity": 1.0,
                        "rotation": 0.0,
                        "align": "top-left",
                    }
                ],
            }
        )

    def test_should_deserialize_percentage_position_from_json(self):
        """Test that percentage positions are deserialized correctly"""
        # Given: JSON with percentage position
        import json

        json_data = {
            "width": 1920,
            "height": 1080,
            "layers": [
                {
                    "type": "image",
                    "path": "assets/logo.png",
                    "position": ["50%", "25%"],
                    "width": 100,
                }
            ],
        }

        # When: Deserializing from JSON
        from quickthumb import Canvas

        canvas = Canvas.from_json(json.dumps(json_data))

        # Then
        assert canvas.layers[0] == snapshot(
            ImageLayer(type="image", path="assets/logo.png", position=("50%", "25%"), width=100)
        )
