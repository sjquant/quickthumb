"""Tests for Canvas creation methods"""

import pytest


class TestCanvasCreation:
    """Test suite for Canvas creation"""

    def test_should_create_canvas_with_explicit_dimensions(self):
        """Test that Canvas can be created with explicit width and height dimensions"""
        # Given: User wants to create a canvas with specific pixel dimensions
        width = 1920
        height = 1080

        # When: User creates a Canvas with explicit dimensions
        from quickthumb import Canvas

        canvas = Canvas(width, height)

        # Then: Canvas should be created with correct dimensions
        assert canvas.width == 1920
        assert canvas.height == 1080

    def test_should_create_canvas_from_aspect_ratio(self):
        """Test that Canvas can be created from aspect ratio and calculates correct dimensions"""
        # Given: User wants to create a 16:9 canvas with base width 1920
        ratio = "16:9"
        base_width = 1920
        expected_height = 1080  # 1920 * 9 / 16

        # When: User creates Canvas from aspect ratio
        from quickthumb import Canvas

        canvas = Canvas.from_aspect_ratio(ratio, base_width=base_width)

        # Then: Canvas dimensions should be calculated correctly
        assert canvas.width == 1920
        assert canvas.height == expected_height

    def test_should_raise_error_for_invalid_dimensions(self):
        """Test that creating canvas with zero or negative dimensions raises ValueError"""
        # Given: User attempts to create canvas with invalid dimensions
        from quickthumb import Canvas, ValidationError

        # When: User calls Canvas with zero width
        # Then: Should raise ValidationError
        with pytest.raises(ValidationError, match="width must be > 0"):
            Canvas(0, 1080)

        # When: User calls Canvas with negative height
        # Then: Should raise ValidationError
        with pytest.raises(ValidationError, match="height must be > 0"):
            Canvas(1920, -100)
