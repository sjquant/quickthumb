"""Tests for background layer functionality"""

import pytest


class TestBackgroundLayers:
    """Test suite for background layer operations"""

    def test_should_add_solid_color_background(self):
        """Test that solid color background can be added with multiple color formats"""
        # Given: Canvas with size 1920x1080
        from quickthumb import BackgroundLayer, Canvas

        canvas = Canvas(1920, 1080)

        # When: User adds solid color backgrounds with different formats
        canvas.background(color="#3498db")  # Hex string

        # Then: Canvas should have background layer with correct color value
        assert len(canvas.layers) >= 1
        assert canvas.layers[0] == BackgroundLayer(
            type="background",
            color="#3498db",
            gradient=None,
            image=None,
            opacity=1.0,
            blend_mode=None,
        )

    def test_should_accept_multiple_color_formats(self):
        """Test that RGB/RGBA tuples and hex strings are all accepted"""
        # Given: Canvas and different color formats
        from quickthumb import BackgroundLayer, Canvas

        canvas = Canvas(1920, 1080)

        # When: User provides RGB tuple
        canvas.background(color=(255, 87, 51))

        # Then: Should accept RGB tuple with exact color value
        assert len(canvas.layers) == 1
        assert canvas.layers[0] == BackgroundLayer(
            type="background",
            color=(255, 87, 51),
            gradient=None,
            image=None,
            opacity=1.0,
            blend_mode=None,
        )

        # When: User provides RGBA tuple
        canvas.background(color=(255, 87, 51, 200))

        # Then: Should accept RGBA tuple with exact color value
        assert len(canvas.layers) == 2
        assert canvas.layers[1] == BackgroundLayer(
            type="background",
            color=(255, 87, 51, 200),
            gradient=None,
            image=None,
            opacity=1.0,
            blend_mode=None,
        )

    def test_should_composite_multiple_background_layers_with_blend_modes(self):
        """Test that multiple background layers can be composited with blend modes"""
        # Given: Canvas with three different background layers
        from quickthumb import BackgroundLayer, BlendMode, Canvas, LinearGradient

        canvas = Canvas(1920, 1080)

        # When: User adds multiple background layers with blend modes
        canvas.background(color="#FF5733")
        gradient = LinearGradient(angle=45, stops=[("#FFD700", 0.0), ("#FFD70000", 1.0)])
        canvas.background(
            gradient=gradient,
            opacity=0.5,
            blend_mode=BlendMode.MULTIPLY,
        )
        canvas.background(image="texture.jpg", opacity=0.3, blend_mode=BlendMode.OVERLAY)

        # Then: First layer should have color data
        assert len(canvas.layers) == 3
        assert canvas.layers[0] == BackgroundLayer(
            type="background",
            color="#FF5733",
            gradient=None,
            image=None,
            opacity=1.0,
            blend_mode=None,
        )

        # Then: Second layer should have gradient data with correct configuration
        assert canvas.layers[1] == BackgroundLayer(
            type="background",
            color=None,
            gradient=gradient,
            image=None,
            opacity=0.5,
            blend_mode=BlendMode.MULTIPLY,
        )

        # Then: Third layer should have image data with correct path
        assert canvas.layers[2] == BackgroundLayer(
            type="background",
            color=None,
            gradient=None,
            image="texture.jpg",
            opacity=0.3,
            blend_mode=BlendMode.OVERLAY,
        )

    def test_should_raise_error_for_invalid_color(self):
        """Test that invalid color format raises ValidationError"""
        # Given: Canvas and invalid colors
        from quickthumb import Canvas, ValidationError

        canvas = Canvas(1920, 1080)

        # When: User provides invalid hex color
        # Then: Should raise ValidationError
        with pytest.raises(ValidationError, match="invalid hex"):
            canvas.background(color="invalid")

        # When: User provides hex with invalid characters
        # Then: Should raise ValidationError
        with pytest.raises(ValidationError, match="invalid hex"):
            canvas.background(color="#GGGGGG")

    def test_should_raise_error_for_unsupported_blend_mode(self):
        """Test that unsupported blend mode raises ValidationError"""
        # Given: Canvas and invalid blend mode string
        from quickthumb import Canvas, ValidationError

        canvas = Canvas(1920, 1080)

        # When: User provides unsupported blend mode
        # Then: Should raise ValidationError
        with pytest.raises(ValidationError, match="blend_mode.*multiply.*overlay.*screen"):
            canvas.background(color="#FF0000", blend_mode="invalid")

    def test_should_defer_file_not_found_error_until_render(self):
        """Test that missing image file raises error at render time, not at background() call"""
        # Given: Canvas with non-existent image background
        from quickthumb import BackgroundLayer, Canvas

        canvas = Canvas(1920, 1080)

        # When: User adds background with missing image (lazy evaluation)
        canvas.background(image="nonexistent.jpg")

        # Then: background() should not raise error and image path should be stored
        assert len(canvas.layers) == 1
        assert canvas.layers[0] == BackgroundLayer(
            type="background",
            color=None,
            gradient=None,
            image="nonexistent.jpg",
            opacity=1.0,
            blend_mode=None,
        )

        # When: User calls render
        # Then: Should raise FileNotFoundError
        with pytest.raises(FileNotFoundError, match="nonexistent.jpg"):
            canvas.render("output.png")

    def test_should_add_radial_gradient_background_with_default_center(self):
        """Test that radial gradient can be added with default center position (0.5, 0.5)"""
        # Given: Canvas and RadialGradient with default center
        from quickthumb import BackgroundLayer, Canvas, RadialGradient

        canvas = Canvas(1920, 1080)
        gradient = RadialGradient(stops=[("#FF5733", 0.0), ("#3498db", 1.0)])

        # When: User adds radial gradient background
        canvas.background(gradient=gradient)

        # Then: Canvas should have background layer with radial gradient and default center
        assert len(canvas.layers) == 1
        assert canvas.layers[0] == BackgroundLayer(
            type="background",
            color=None,
            gradient=gradient,
            image=None,
            opacity=1.0,
            blend_mode=None,
        )
        assert gradient.center == (0.5, 0.5)

    def test_should_add_radial_gradient_background_with_custom_center(self):
        """Test that radial gradient can be added with custom center position"""
        # Given: Canvas and RadialGradient with custom center
        from quickthumb import BackgroundLayer, Canvas, RadialGradient

        canvas = Canvas(1920, 1080)
        gradient = RadialGradient(stops=[("#FF5733", 0.0), ("#3498db", 1.0)], center=(0.3, 0.7))

        # When: User adds radial gradient background
        canvas.background(gradient=gradient)

        # Then: Canvas should have background layer with radial gradient and custom center
        assert len(canvas.layers) == 1
        assert canvas.layers[0] == BackgroundLayer(
            type="background",
            color=None,
            gradient=gradient,
            image=None,
            opacity=1.0,
            blend_mode=None,
        )
        assert gradient.center == (0.3, 0.7)

    def test_should_serialize_background_layer_to_json(self):
        """Test that canvas with background layers can be serialized to JSON"""
        # Given: Canvas with multiple background layers
        from quickthumb import BlendMode, Canvas, LinearGradient

        gradient = LinearGradient(angle=45, stops=[("#FFD700", 0.0), ("#FFD70000", 1.0)])
        canvas = (
            Canvas(1920, 1080)
            .background(color="#2c3e50")
            .background(gradient=gradient, opacity=0.5, blend_mode=BlendMode.MULTIPLY)
        )

        # When: User serializes canvas to JSON
        json_str = canvas.to_json()

        # Then: JSON should contain background layers with correct structure
        import json

        data = json.loads(json_str)
        assert data["width"] == 1920
        assert data["height"] == 1080
        assert len(data["layers"]) == 2
        assert data["layers"][0] == {
            "type": "background",
            "color": "#2c3e50",
            "gradient": None,
            "image": None,
            "opacity": 1.0,
            "blend_mode": None,
            "fit": None,
            "brightness": 1.0,
        }
        assert data["layers"][1] == {
            "type": "background",
            "color": None,
            "gradient": {
                "type": "linear",
                "angle": 45,
                "stops": [["#FFD700", 0.0], ["#FFD70000", 1.0]],
            },
            "image": None,
            "opacity": 0.5,
            "blend_mode": "multiply",
            "fit": None,
            "brightness": 1.0,
        }

    def test_should_deserialize_background_layer_from_json(self):
        """Test that canvas with background layers can be deserialized from JSON"""
        # Given: JSON string with background layers
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
                    "type": "background",
                    "color": None,
                    "gradient": {
                        "type": "linear",
                        "angle": 45,
                        "stops": [["#FFD700", 0.0], ["#FFD70000", 1.0]],
                    },
                    "image": None,
                    "opacity": 0.5,
                    "blend_mode": "multiply",
                },
            ],
        }
        json_str = json.dumps(json_data)

        # When: User deserializes canvas from JSON
        from quickthumb import BackgroundLayer, BlendMode, Canvas, LinearGradient

        canvas = Canvas.from_json(json_str)

        # Then: Canvas should have background layers with correct properties
        assert len(canvas.layers) == 2
        assert canvas.layers[0] == BackgroundLayer(
            type="background",
            color="#2c3e50",
            gradient=None,
            image=None,
            opacity=1.0,
            blend_mode=None,
        )
        gradient = LinearGradient(angle=45, stops=[("#FFD700", 0.0), ("#FFD70000", 1.0)])
        assert canvas.layers[1] == BackgroundLayer(
            type="background",
            color=None,
            gradient=gradient,
            image=None,
            opacity=0.5,
            blend_mode=BlendMode.MULTIPLY,
        )

    def test_should_accept_tuple_rgb_color(self):
        """Test that RGB tuple colors (R, G, B) are accepted"""
        # Given: Canvas
        from quickthumb import Canvas

        canvas = Canvas(200, 150)

        # When: Adding background with RGB tuple color
        canvas.background(color=(255, 87, 51))

        # Then: Should create background layer with tuple color
        assert len(canvas.layers) == 1
        assert canvas.layers[0].color == (255, 87, 51)

    def test_should_accept_tuple_rgba_color(self):
        """Test that RGBA tuple colors (R, G, B, A) are accepted"""
        # Given: Canvas
        from quickthumb import Canvas

        canvas = Canvas(200, 150)

        # When: Adding background with RGBA tuple color
        canvas.background(color=(255, 87, 51, 200))

        # Then: Should create background layer with tuple color including alpha
        assert len(canvas.layers) == 1
        assert canvas.layers[0].color == (255, 87, 51, 200)

    def test_should_accept_8_character_hex_color(self):
        """Test that 8-character hex colors #RRGGBBAA with alpha channel are accepted"""
        # Given: Canvas
        from quickthumb import Canvas

        canvas = Canvas(200, 150)

        # When: Adding background with 8-character hex color including alpha
        canvas.background(color="#FF5733C8")

        # Then: Should create background layer with 8-char hex color
        assert len(canvas.layers) == 1
        assert canvas.layers[0].color == "#FF5733C8"

    def test_should_raise_error_for_invalid_tuple_color_length(self):
        """Should raise ValidationError for tuple colors with invalid length"""
        # Given: Canvas
        from quickthumb import Canvas
        from quickthumb.errors import ValidationError

        canvas = Canvas(200, 150)

        # When: Adding background with invalid tuple color (wrong length)
        # Then: Should raise ValidationError
        with pytest.raises(ValidationError, match="invalid color tuple"):
            canvas.background(color=(255, 87))

    def test_should_raise_error_for_invalid_fit_mode(self):
        """Test that invalid fit mode raises ValidationError"""
        # Given: Canvas and invalid fit mode string
        from quickthumb import Canvas, ValidationError

        canvas = Canvas(200, 150)

        # When: User provides invalid fit mode
        # Then: Should raise ValidationError
        with pytest.raises(ValidationError, match="fit.*cover.*contain.*fill"):
            canvas.background(image="image.jpg", fit="invalid")
