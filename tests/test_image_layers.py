"""Tests for image layer functionality"""

import builtins
import json
import sys
from unittest.mock import patch

import pytest
from inline_snapshot import snapshot
from PIL import Image
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
            (("invalid", "top"), "invalid.*align"),
            (("left", "invalid"), "invalid.*align"),
            (("left",), "align must be a tuple of two elements"),
            (("left", "top", "extra"), "align must be a tuple of two elements"),
            # Old VH order ("top", "left") is now rejected: "top" is not a valid horizontal
            (("top", "left"), "invalid.*align"),
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
            rotation=0.0,
            align=Align.TOP_LEFT,
        )
        assert len(canvas.layers) == 1
        assert canvas.layers[0] == expected_layer


class TestImageLayerBackgroundRemoval:
    """Test suite for image layer background removal"""

    def test_should_raise_import_error_when_rembg_not_installed(self):
        """Test that ImportError with helpful message is raised when rembg is missing"""
        from quickthumb import Canvas

        # Given: A canvas instance and rembg not installed
        canvas = Canvas(200, 200)
        img = Image.new("RGBA", (100, 100), (255, 0, 0, 255))

        # When/Then: Calling _remove_background should raise ImportError
        # Mock is justified here: impossible to test "library not installed" with real code
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "rembg":
                raise ImportError("No module named 'rembg'")
            return original_import(name, *args, **kwargs)

        saved = sys.modules.pop("rembg", None)
        try:
            with (
                patch.object(builtins, "__import__", side_effect=mock_import),
                pytest.raises(ImportError, match="rembg is required.*pip install quickthumb"),
            ):
                canvas._remove_background(img)
        finally:
            if saved is not None:
                sys.modules["rembg"] = saved


class TestImageLayerBorderRadius:
    """Test suite for image layer border_radius (rounded corners)"""

    def test_should_accept_border_radius_on_image_layer(self):
        """Test that Canvas.image() accepts border_radius and stores it in the layer"""
        from quickthumb import Canvas

        canvas = Canvas(400, 300)
        result = canvas.image(path="assets/logo.png", position=(0, 0), width=200, border_radius=20)

        assert result is canvas
        assert canvas.layers[0] == snapshot(
            ImageLayer(
                type="image",
                path="assets/logo.png",
                position=(0, 0),
                width=200,
                border_radius=20,
            )
        )

    def test_should_reject_negative_border_radius(self):
        """Test that negative border_radius raises ValidationError"""
        from quickthumb import Canvas

        canvas = Canvas(400, 300)

        with pytest.raises(ValidationError, match="border_radius.*greater than or equal to 0"):
            canvas.image(path="assets/logo.png", position=(0, 0), border_radius=-1)


class TestImageLayerSerialization:
    """Test suite for JSON serialization/deserialization"""

    def test_should_round_trip_remove_background_through_json(self):
        """Test that remove_background survives JSON round-trip"""
        from quickthumb import Canvas

        # Given: Canvas with remove_background=True
        original = Canvas(1920, 1080)
        original.image(path="logo.png", position=(0, 0), remove_background=True)

        # When: Round-tripping through JSON
        restored = Canvas.from_json(original.to_json())

        # Then: remove_background should be preserved
        assert restored.layers[0] == original.layers[0]

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
            align=("center", "middle"),
        )

        # When: User serializes canvas to JSON

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
            "rotation": 45.0,
            "remove_background": False,
            "align": "center",
            "border_radius": 0,
            "effects": [],
        }

    def test_should_deserialize_image_layer_from_json(self):
        """Test that canvas with image layer can be deserialized from JSON"""
        # Given: JSON string with image layer

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
                    "align": ["center", "middle"],
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
            align=("center", "middle"),
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
                        "remove_background": False,
                        "align": "top-left",
                        "border_radius": 0,
                        "effects": [],
                    }
                ],
            }
        )

    def test_should_serialize_image_with_effects_to_json(self):
        """Test that image layer with effects serializes the effects field correctly"""
        import json

        from quickthumb import Canvas, Shadow

        canvas = Canvas(400, 300)
        canvas.image(
            path="assets/logo.png",
            position=(50, 50),
            width=200,
            effects=[Shadow(offset_x=5, offset_y=5, color="#000000", blur_radius=10)],
        )

        data = json.loads(canvas.to_json())

        assert data == snapshot(
            {
                "width": 400,
                "height": 300,
                "layers": [
                    {
                        "type": "image",
                        "path": "assets/logo.png",
                        "position": [50, 50],
                        "width": 200,
                        "height": None,
                        "opacity": 1.0,
                        "rotation": 0.0,
                        "remove_background": False,
                        "align": "top-left",
                        "border_radius": 0,
                        "effects": [
                            {
                                "type": "shadow",
                                "offset_x": 5,
                                "offset_y": 5,
                                "color": "#000000",
                                "blur_radius": 10,
                            }
                        ],
                    }
                ],
            }
        )

    def test_should_deserialize_image_with_effects_from_json(self):
        """Test that image layer with effects deserializes correctly"""
        import json

        from quickthumb import Canvas, Shadow
        from quickthumb.models import ImageLayer

        json_data = {
            "width": 400,
            "height": 300,
            "layers": [
                {
                    "type": "image",
                    "path": "assets/logo.png",
                    "position": [50, 50],
                    "width": 200,
                    "effects": [
                        {
                            "type": "shadow",
                            "offset_x": 5,
                            "offset_y": 5,
                            "color": "#000000",
                            "blur_radius": 10,
                        }
                    ],
                }
            ],
        }

        canvas = Canvas.from_json(json.dumps(json_data))

        assert canvas.layers[0] == snapshot(
            ImageLayer(
                type="image",
                path="assets/logo.png",
                position=(50, 50),
                width=200,
                effects=[Shadow(offset_x=5, offset_y=5, color="#000000", blur_radius=10)],
            )
        )

    def test_should_deserialize_percentage_position_from_json(self):
        """Test that percentage positions are deserialized correctly"""
        # Given: JSON with percentage position

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
