"""Tests for background layer functionality"""

import pytest


class TestBackgroundLayers:
    """Test suite for background layer operations"""

    def test_should_add_solid_color_background(self):
        """Test that solid color background can be added with multiple color formats"""
        # Given: Canvas with size 1920x1080
        from quickthumb import Canvas

        canvas = Canvas(1920, 1080)

        # When: User adds solid color backgrounds with different formats
        canvas.background(color="#3498db")  # Hex string

        # Then: Canvas should have background layer
        assert len(canvas.layers) >= 1
        assert canvas.layers[0]["type"] == "background"

    def test_should_accept_multiple_color_formats(self):
        """Test that RGB/RGBA tuples and hex strings are all accepted"""
        # Given: Canvas and different color formats
        from quickthumb import Canvas

        canvas = Canvas(1920, 1080)

        # When: User provides RGB tuple
        canvas.background(color=(255, 87, 51))

        # Then: Should accept RGB tuple
        assert len(canvas.layers) == 1

        # When: User provides RGBA tuple
        canvas.background(color=(255, 87, 51, 200))

        # Then: Should accept RGBA tuple
        assert len(canvas.layers) == 2

    def test_should_composite_multiple_background_layers_with_blend_modes(self):
        """Test that multiple background layers can be composited with blend modes"""
        # Given: Canvas with three different background layers
        from quickthumb import BlendMode, Canvas, LinearGradient

        canvas = Canvas(1920, 1080)

        # When: User adds multiple background layers with blend modes
        canvas.background(color="#FF5733")
        canvas.background(
            gradient=LinearGradient(45, [("#FFD700", 0.0), ("#FFD70000", 1.0)]),
            opacity=0.5,
            blend_mode=BlendMode.MULTIPLY,
        )
        canvas.background(image="texture.jpg", opacity=0.3, blend_mode=BlendMode.OVERLAY)

        # Then: All background layers should be stored in order with blend modes
        assert len(canvas.layers) == 3
        assert canvas.layers[1]["blend_mode"] == BlendMode.MULTIPLY
        assert canvas.layers[1]["opacity"] == 0.5
        assert canvas.layers[2]["blend_mode"] == BlendMode.OVERLAY

    def test_should_raise_error_for_invalid_color(self):
        """Test that invalid color format raises BackgroundValidationError"""
        # Given: Canvas and invalid colors
        from quickthumb import BackgroundValidationError, Canvas

        canvas = Canvas(1920, 1080)

        # When: User provides invalid hex color
        # Then: Should raise BackgroundValidationError
        with pytest.raises(BackgroundValidationError, match="invalid hex"):
            canvas.background(color="invalid")

        # When: User provides hex with invalid characters
        # Then: Should raise BackgroundValidationError
        with pytest.raises(BackgroundValidationError, match="invalid hex"):
            canvas.background(color="#GGGGGG")

    def test_should_raise_error_for_unsupported_blend_mode(self):
        """Test that unsupported blend mode raises BackgroundValidationError"""
        # Given: Canvas and invalid blend mode string
        from quickthumb import BackgroundValidationError, Canvas

        canvas = Canvas(1920, 1080)

        # When: User provides unsupported blend mode
        # Then: Should raise BackgroundValidationError
        with pytest.raises(BackgroundValidationError, match="unsupported blend mode"):
            canvas.background(color="#FF0000", blend_mode="invalid")

    def test_should_defer_file_not_found_error_until_render(self):
        """Test that missing image file raises error at render time, not at background() call"""
        # Given: Canvas with non-existent image background
        from quickthumb import Canvas

        canvas = Canvas(1920, 1080)

        # When: User adds background with missing image (lazy evaluation)
        canvas.background(image="nonexistent.jpg")

        # Then: background() should not raise error
        assert len(canvas.layers) == 1

        # When: User calls render
        # Then: Should raise FileNotFoundError
        with pytest.raises(FileNotFoundError, match="nonexistent.jpg"):
            canvas.render("output.png")
