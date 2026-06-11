"""Tests for background layer functionality"""

import pytest
from inline_snapshot import snapshot


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

    def test_should_normalize_out_of_order_gradient_stops(self):
        """Gradient stops listed out of position order render the same as ascending stops"""
        import os
        import tempfile

        from quickthumb import Canvas, LinearGradient

        # given: the same two-stop gradient declared in ascending and descending stop order
        ascending = Canvas(200, 100).background(
            gradient=LinearGradient(angle=0, stops=[("#FF0000", 0.0), ("#0000FF", 1.0)])
        )
        descending = Canvas(200, 100).background(
            gradient=LinearGradient(angle=0, stops=[("#0000FF", 1.0), ("#FF0000", 0.0)])
        )

        # when
        with tempfile.TemporaryDirectory() as tmpdir:
            path_a = os.path.join(tmpdir, "ascending.png")
            path_b = os.path.join(tmpdir, "descending.png")
            ascending.render(path_a)
            descending.render(path_b)

            # then: byte-identical output, i.e. descending stops still produce a real gradient
            with open(path_a, "rb") as fa, open(path_b, "rb") as fb:
                assert fa.read() == fb.read()

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
        """Test that canvas with background layers can be serialized to JSON.

        Includes a tuple-color layer to verify that RGB/RGBA tuples are serialized as
        hex strings (not JSON arrays) so the output is spec-compliant and round-trippable.
        """
        # Given: Canvas with multiple background layers, including a tuple color
        import json

        from quickthumb import BlendMode, Canvas, Filter, LinearGradient

        gradient = LinearGradient(angle=45, stops=[("#FFD700", 0.0), ("#FFD70000", 1.0)])
        canvas = (
            Canvas(1920, 1080)
            .background(color="#2c3e50", effects=[Filter(blur=5, brightness=0.8)])
            .background(gradient=gradient, opacity=0.5, blend_mode=BlendMode.MULTIPLY)
            .background(color=(255, 87, 51))
            .background(color=(255, 87, 51, 200))
        )

        # When/Then: Serialized JSON matches full expected structure;
        # tuple colors appear as hex strings, not arrays.
        assert json.loads(canvas.to_json()) == snapshot(
            {
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
                        "fit": None,
                        "effects": [
                            {
                                "type": "filter",
                                "blur": 5,
                                "brightness": 0.8,
                                "contrast": 1.0,
                                "saturation": 1.0,
                            }
                        ],
                    },
                    {
                        "type": "background",
                        "color": None,
                        "gradient": {
                            "type": "linear",
                            "angle": 45.0,
                            "stops": [["#FFD700", 0.0], ["#FFD70000", 1.0]],
                        },
                        "image": None,
                        "opacity": 0.5,
                        "blend_mode": "multiply",
                        "fit": None,
                        "effects": [],
                    },
                    {
                        "type": "background",
                        "color": "#FF5733",
                        "gradient": None,
                        "image": None,
                        "opacity": 1.0,
                        "blend_mode": None,
                        "fit": None,
                        "effects": [],
                    },
                    {
                        "type": "background",
                        "color": "#FF5733C8",
                        "gradient": None,
                        "image": None,
                        "opacity": 1.0,
                        "blend_mode": None,
                        "fit": None,
                        "effects": [],
                    },
                ],
            }
        )

        # Round-trip: after from_json the tuple-color layers come back as hex strings,
        # confirming the serializer normalises them correctly.
        roundtrip = Canvas.from_json(canvas.to_json())
        assert roundtrip.layers[2].color == "#FF5733"
        assert roundtrip.layers[3].color == "#FF5733C8"

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
        from quickthumb import BackgroundLayer, Canvas

        canvas = Canvas(200, 150)

        # When: Adding background with RGB tuple color
        canvas.background(color=(255, 87, 51))

        # Then: Should create background layer with tuple color
        assert len(canvas.layers) == 1
        layer = canvas.layers[0]
        assert isinstance(layer, BackgroundLayer)
        assert layer.color == (255, 87, 51)

    def test_should_accept_tuple_rgba_color(self):
        """Test that RGBA tuple colors (R, G, B, A) are accepted"""
        # Given: Canvas
        from quickthumb import BackgroundLayer, Canvas

        canvas = Canvas(200, 150)

        # When: Adding background with RGBA tuple color
        canvas.background(color=(255, 87, 51, 200))

        # Then: Should create background layer with tuple color including alpha
        assert len(canvas.layers) == 1
        layer = canvas.layers[0]
        assert isinstance(layer, BackgroundLayer)
        assert layer.color == (255, 87, 51, 200)

    def test_should_accept_8_character_hex_color(self):
        """Test that 8-character hex colors #RRGGBBAA with alpha channel are accepted"""
        # Given: Canvas
        from quickthumb import BackgroundLayer, Canvas

        canvas = Canvas(200, 150)

        # When: Adding background with 8-character hex color including alpha
        canvas.background(color="#FF5733C8")

        # Then: Should create background layer with 8-char hex color
        assert len(canvas.layers) == 1
        layer = canvas.layers[0]
        assert isinstance(layer, BackgroundLayer)
        assert layer.color == "#FF5733C8"

    @pytest.mark.parametrize(
        "color",
        [
            (255, 87),  # too short
            (255, 87, 51, 0, 0),  # too long
            (256, 87, 51),  # channel > 255
            (-1, 87, 51),  # channel < 0
            (255, 87, 51, 256),  # alpha > 255
        ],
    )
    def test_should_raise_error_for_invalid_tuple_color(self, color):
        """ValidationError for tuple colors with wrong length or out-of-range channel values"""
        from quickthumb import Canvas
        from quickthumb.errors import ValidationError

        with pytest.raises(ValidationError, match="invalid color tuple"):
            Canvas(200, 150).background(color=color)

    def test_should_raise_error_for_invalid_fit_mode(self):
        """Test that invalid fit mode raises ValidationError"""
        # Given: Canvas and invalid fit mode string
        from quickthumb import Canvas, ValidationError

        canvas = Canvas(200, 150)

        # When: User provides invalid fit mode
        # Then: Should raise ValidationError
        with pytest.raises(ValidationError, match="fit.*cover.*contain.*fill"):
            canvas.background(image="image.jpg", fit="invalid")

    @pytest.mark.parametrize(
        "opacity, match",
        [
            (-0.1, "opacity"),
            (1.1, "opacity"),
        ],
    )
    def test_should_raise_error_for_invalid_background_opacity(self, opacity, match):
        """Test that opacity outside 0-1 range raises ValidationError on BackgroundLayer"""
        from quickthumb import Canvas, ValidationError

        canvas = Canvas(100, 100)

        with pytest.raises(ValidationError, match=match):
            canvas.background(color="#FF0000", opacity=opacity)

    @pytest.mark.parametrize(
        "kwargs, match",
        [
            ({"blur": -1}, "blur"),
            ({"contrast": 0.0}, "contrast"),
            ({"contrast": -1.0}, "contrast"),
            ({"saturation": -0.1}, "saturation"),
        ],
    )
    def test_should_raise_error_for_invalid_filter_params(self, kwargs, match):
        """Test that invalid Filter params raise ValidationError"""
        from quickthumb import Filter, ValidationError

        with pytest.raises(ValidationError, match=match):
            Filter(**kwargs)

    def test_should_add_grain_effect_to_background_layer(self):
        """Test Grain defaults contract and JSON round-trip on background layers"""
        import json

        from inline_snapshot import snapshot
        from quickthumb import Canvas, Grain

        # Defaults: monochrome=True, blend_mode="overlay", opacity=1.0
        canvas = Canvas(200, 150).background(color="#1A1A2E", effects=[Grain(intensity=0.12)])

        assert canvas.layers[0].effects[0] == snapshot(
            Grain(intensity=0.12, monochrome=True, blend_mode="overlay", opacity=1.0)
        )

        # JSON round-trip covers serialization contract
        data = json.loads(canvas.to_json())
        assert data["layers"][0]["effects"][0] == snapshot(
            {
                "type": "grain",
                "intensity": 0.12,
                "monochrome": True,
                "blend_mode": "overlay",
                "opacity": 1.0,
                "seed": None,
            }
        )
        roundtrip = Canvas.from_json(json.dumps(data))
        assert roundtrip.layers[0].effects[0] == Grain(intensity=0.12)

    @pytest.mark.parametrize(
        "kwargs, match",
        [
            ({"intensity": -0.1}, "intensity"),
            ({"intensity": 1.1}, "intensity"),
            ({"intensity": 0.5, "opacity": -0.1}, "opacity"),
            ({"intensity": 0.5, "opacity": 1.1}, "opacity"),
        ],
    )
    def test_should_raise_error_for_invalid_grain_params(self, kwargs, match):
        """Test that invalid Grain params raise ValidationError"""
        from quickthumb import Grain, ValidationError

        with pytest.raises(ValidationError, match=match):
            Grain(**kwargs)
