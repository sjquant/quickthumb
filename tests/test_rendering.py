"""Tests for rendering engine functionality"""

import os
import tempfile

import pytest
from inline_snapshot import external_file


class TestRendering:
    """Tests for rendering engine functionality with snapshots"""

    def test_snapshot_solid_background(self):
        """Snapshot test for solid color background rendering"""
        from quickthumb import Canvas

        canvas = Canvas(200, 150).background(color="#3498db")

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/solid_background.png")

    def test_snapshot_text_rendering(self):
        """Snapshot test for text rendering with styles and unicode"""
        from quickthumb import Canvas

        canvas = (
            Canvas(400, 300)
            .background(color="#FFFFFF")
            .text("Normal", size=32, color="#000000", position=(200, 50), align=("center", "top"))
            .text(
                "Bold",
                size=32,
                color="#FF0000",
                position=(200, 120),
                align=("center", "top"),
                bold=True,
            )
            .text(
                "Italic",
                size=32,
                color="#0000FF",
                position=(200, 190),
                align=("center", "top"),
                italic=True,
            )
            .text(
                "World 🌍",
                size=24,
                color="#00AA00",
                position=(200, 260),
                align=("center", "top"),
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/text_rendering.png")

    def test_snapshot_text_alignment(self):
        """Snapshot test for text alignment (left/center/right, top/middle/bottom)"""
        from quickthumb import Canvas

        canvas = (
            Canvas(400, 300)
            .background(color="#F0F0F0")
            .text("Top Left", size=16, color="#000000", position=(50, 50), align=("left", "top"))
            .text(
                "Center Middle",
                size=16,
                color="#000000",
                position=(200, 150),
                align=("center", "middle"),
            )
            .text(
                "Bottom Right",
                size=16,
                color="#000000",
                position=(350, 250),
                align=("right", "bottom"),
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/text_alignment.png")

    def test_snapshot_webp_format(self):
        """Snapshot test for WebP format output"""
        from quickthumb import Canvas

        canvas = (
            Canvas(300, 200)
            .background(color="#FF5733")
            .text(
                "WebP Test",
                size=16,
                color="#FFFFFF",
                position=(150, 100),
                align=("center", "middle"),
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.webp")
            canvas.render(output_path, quality=90)

            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/webp_format.webp")

    def test_snapshot_jpeg_format(self):
        """Snapshot test for JPEG format output (no alpha channel)"""
        from quickthumb import Canvas

        canvas = (
            Canvas(300, 200)
            .background(color="#2C3E50")
            .text(
                "JPEG Test",
                size=16,
                color="#FFFFFF",
                position=(150, 100),
                align=("center", "middle"),
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.jpg")
            canvas.render(output_path, quality=90)

            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/jpeg_format.jpg")

    def test_should_raise_error_for_unsupported_format(self):
        """Should raise RenderingError when using unsupported file format"""
        from quickthumb import Canvas
        from quickthumb.errors import RenderingError

        canvas = Canvas(100, 100).background(color="#FF0000")

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.bmp")

            with pytest.raises(RenderingError, match="Unsupported file format"):
                canvas.render(output_path)

    def test_should_raise_error_for_quality_with_png(self):
        """Should raise RenderingError when quality parameter is used with PNG format"""
        from quickthumb import Canvas
        from quickthumb.errors import RenderingError

        canvas = Canvas(100, 100).background(color="#FF0000")

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")

            with pytest.raises(
                RenderingError, match="Quality parameter is only supported for JPEG and WEBP"
            ):
                canvas.render(output_path, quality=80)

    def test_snapshot_percentage_with_alignment(self):
        """Snapshot test for percentage positioning combined with text alignment"""
        from quickthumb import Canvas

        canvas = (
            Canvas(400, 300)
            .background(color="#FAFAFA")
            .text(
                "Top Left 25%",
                size=14,
                color="#FF5722",
                position=("25%", "25%"),
                align=("left", "top"),
            )
            .text(
                "Center 50%",
                size=14,
                color="#4CAF50",
                position=("50%", "50%"),
                align=("center", "middle"),
            )
            .text(
                "Bottom Right 75%",
                size=14,
                color="#2196F3",
                position=("75%", "75%"),
                align=("right", "bottom"),
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/percentage_with_alignment.png")

    def test_snapshot_linear_gradient_with_alpha(self):
        """Snapshot test for linear gradient rendering with alpha transparency in color stops"""
        from quickthumb import Canvas
        from quickthumb.models import LinearGradient

        # Given: A linear gradient from opaque red to transparent red (with alpha)
        gradient = LinearGradient(
            type="linear", angle=0, stops=[("#FF0000FF", 0.0), ("#FF000000", 1.0)]
        )

        # When: Rendering gradient over a checkerboard pattern (to see transparency)
        canvas = (
            Canvas(400, 300)
            .background(color="#FFFFFF")
            .background(color="#2196F3", opacity=1.0)  # Blue base
            .background(gradient=gradient)
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            # Then: Should show gradient fading from red to transparent (revealing gray)
            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/linear_gradient_with_alpha.png")

    def test_snapshot_linear_gradient_horizontal(self):
        """Snapshot test for linear gradient rendering with horizontal direction (0 degrees)"""
        from quickthumb import Canvas
        from quickthumb.models import LinearGradient

        # Given: A linear gradient from red to blue at 0 degrees (horizontal)
        gradient = LinearGradient(
            type="linear", angle=0, stops=[("#FF0000", 0.0), ("#0000FF", 1.0)]
        )

        # When: Rendering the canvas with the gradient background
        canvas = Canvas(400, 300).background(gradient=gradient)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            # Then: Should match the expected gradient rendering
            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/linear_gradient_horizontal.png")

    def test_snapshot_linear_gradient_diagonal(self):
        """Snapshot test for linear gradient rendering with diagonal direction (45 degrees)"""
        from quickthumb import Canvas
        from quickthumb.models import LinearGradient

        # Given: A linear gradient at 45 degrees with three color stops
        gradient = LinearGradient(
            type="linear",
            angle=45,
            stops=[("#FF6B6B", 0.0), ("#4ECDC4", 0.5), ("#45B7D1", 1.0)],
        )

        # When: Rendering the canvas with the gradient background
        canvas = Canvas(400, 300).background(gradient=gradient)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            # Then: Should match the expected gradient rendering
            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/linear_gradient_diagonal.png")

    def test_snapshot_radial_gradient_centered(self):
        """Snapshot test for radial gradient rendering with default center position"""
        from quickthumb import Canvas
        from quickthumb.models import RadialGradient

        # Given: A radial gradient from center with default position (0.5, 0.5)
        gradient = RadialGradient(
            type="radial", stops=[("#FF0000", 0.0), ("#0000FF", 1.0)], center=(0.5, 0.5)
        )

        # When: Rendering the canvas with the radial gradient
        canvas = Canvas(400, 300).background(gradient=gradient)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            # Then: Should match the expected radial gradient rendering
            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/radial_gradient_centered.png")

    def test_snapshot_text_with_stroke(self):
        """Snapshot test for text rendering with stroke outline"""
        from quickthumb import Canvas, Stroke

        # Given: Text with a 2px black stroke around white text
        # When: Rendering text with Stroke effect
        canvas = (
            Canvas(400, 200)
            .background(color="#FFFFFF")
            .text(
                "Stroke Text",
                size=48,
                color="#FFFFFF",
                position=(200, 100),
                align=("center", "middle"),
                effects=[Stroke(width=2, color="#000000")],
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            # Then: Should show text with visible stroke outline
            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/text_with_stroke.png")

    def test_snapshot_blend_mode_multiply(self):
        """Snapshot test for multiply blend mode compositing"""
        from quickthumb import Canvas

        # Given: An image with a color layer using multiply blend mode
        # When: Layering color over image with multiply blend mode
        canvas = (
            Canvas(400, 300)
            .background(image="tests/fixtures/sample_image.jpg")
            .background(color="#FF0000", blend_mode="multiply", opacity=0.5)
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            # Then: Should show darker blended result typical of multiply mode
            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/blend_mode_multiply.png")

    def test_snapshot_blend_mode_overlay(self):
        """Snapshot test for overlay blend mode compositing"""
        from quickthumb import Canvas

        # Given: An image with a color layer using overlay blend mode
        # When: Layering color over image with overlay blend mode
        canvas = (
            Canvas(400, 300)
            .background(image="tests/fixtures/sample_image.jpg")
            .background(color="#0000FF", blend_mode="overlay", opacity=0.5)
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            # Then: Should show contrast-enhanced result typical of overlay mode
            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/blend_mode_overlay.png")

    def test_snapshot_blend_mode_screen(self):
        """Snapshot test for screen blend mode compositing"""
        from quickthumb import Canvas

        # Given: An image with a color layer using screen blend mode
        # When: Layering color over image with screen blend mode
        canvas = (
            Canvas(400, 300)
            .background(image="tests/fixtures/sample_image.jpg")
            .background(color="#FFFF00", blend_mode="screen", opacity=0.5)
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            # Then: Should show lightening effect typical of screen mode
            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/blend_mode_screen.png")

    def test_snapshot_blend_mode_darken(self):
        """Snapshot test for darken blend mode compositing"""
        from quickthumb import Canvas

        # Given: An image with a color layer using darken blend mode
        # When: Layering color over image with darken blend mode
        canvas = (
            Canvas(400, 300)
            .background(image="tests/fixtures/sample_image.jpg")
            .background(color="#333333", blend_mode="darken", opacity=0.5)
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            # Then: Should keep darker pixels typical of darken mode
            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/blend_mode_darken.png")

    def test_snapshot_blend_mode_lighten(self):
        """Snapshot test for lighten blend mode compositing"""
        from quickthumb import Canvas

        # Given: An image with a color layer using lighten blend mode
        # When: Layering color over image with lighten blend mode
        canvas = (
            Canvas(400, 300)
            .background(image="tests/fixtures/sample_image.jpg")
            .background(color="#CCCCCC", blend_mode="lighten", opacity=0.5)
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            # Then: Should keep lighter pixels typical of lighten mode
            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/blend_mode_lighten.png")

    def test_snapshot_blend_mode_normal(self):
        """Snapshot test for normal blend mode compositing"""
        from quickthumb import Canvas

        # Given: An image with a color layer using normal blend mode
        # When: Layering color over image with normal blend mode
        canvas = (
            Canvas(400, 300)
            .background(image="tests/fixtures/sample_image.jpg")
            .background(color="#00FF00", blend_mode="normal", opacity=0.5)
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            # Then: Should show standard alpha compositing typical of normal mode
            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/blend_mode_normal.png")

    def test_snapshot_image_background_basic(self):
        """Snapshot test for basic image background rendering"""
        from quickthumb import Canvas

        # Given: A canvas with an image as background
        # When: Rendering with image background parameter
        canvas = Canvas(400, 300).background(image="tests/fixtures/sample_image.jpg")

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            # Then: Should render the image as background
            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/image_background_basic.png")

    def test_snapshot_outline_basic(self):
        """Snapshot test for basic outline decoration rendering"""
        from quickthumb import Canvas

        # Given: A canvas with outline decoration
        # When: Rendering with outline layer
        canvas = Canvas(400, 300).background(color="#FFFFFF").outline(width=5, color="#FF0000")

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            # Then: Should render red outline around canvas edges
            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/outline_basic.png")

    def test_snapshot_outline_with_offset(self):
        """Snapshot test for outline decoration with inward offset"""
        from quickthumb import Canvas

        # Given: An outline with 10px offset from edges
        # When: Rendering outline with offset parameter
        canvas = (
            Canvas(400, 300)
            .background(color="#F0F0F0")
            .outline(width=3, color="#3498DB", offset=10)
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            # Then: Should render outline inset from canvas edges
            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/outline_with_offset.png")

    def test_snapshot_linear_gradient_with_opacity(self):
        """Snapshot test for linear gradient with opacity applied"""
        from quickthumb import Canvas
        from quickthumb.models import LinearGradient

        # Given: A linear gradient with opacity applied
        gradient = LinearGradient(
            type="linear", angle=90, stops=[("#FF0000", 0.0), ("#0000FF", 1.0)]
        )

        # When: Rendering gradient with 50% opacity over solid color
        canvas = (
            Canvas(400, 300).background(color="#FFFFFF").background(gradient=gradient, opacity=0.5)
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            # Then: Should show semi-transparent gradient
            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/linear_gradient_with_opacity.png")

    def test_snapshot_radial_gradient_with_opacity(self):
        """Snapshot test for radial gradient with opacity applied"""
        from quickthumb import Canvas
        from quickthumb.models import RadialGradient

        # Given: A radial gradient with opacity applied
        gradient = RadialGradient(type="radial", stops=[("#FFFF00", 0.0), ("#FF00FF", 1.0)])

        # When: Rendering gradient with 60% opacity over solid color
        canvas = (
            Canvas(400, 300).background(color="#FFFFFF").background(gradient=gradient, opacity=0.6)
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            # Then: Should show semi-transparent radial gradient
            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/radial_gradient_with_opacity.png")

    def test_snapshot_image_background_with_opacity(self):
        """Snapshot test for image background with opacity applied"""
        from quickthumb import Canvas

        # Given: An image with opacity applied
        # When: Rendering image with 50% opacity over solid color
        canvas = (
            Canvas(400, 300)
            .background(color="#FFFFFF")
            .background(image="tests/fixtures/sample_image.jpg", opacity=0.5)
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            # Then: Should show semi-transparent image
            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/image_background_with_opacity.png")

    def test_snapshot_text_bold_and_italic(self):
        """Snapshot test for text with both bold and italic applied"""
        from quickthumb import Canvas

        # Given: Text with both bold and italic styling
        # When: Rendering text with bold=True and italic=True
        canvas = (
            Canvas(400, 200)
            .background(color="#FFFFFF")
            .text(
                "Bold Italic Text",
                size=36,
                color="#000000",
                position=(200, 100),
                align=("center", "middle"),
                bold=True,
                italic=True,
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            # Then: Should render text with both bold and italic styles
            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/text_bold_and_italic.png")

    @pytest.mark.parametrize(
        "weight, weight_name",
        [
            (300, "light"),
            (900, "black"),
        ],
    )
    def test_snapshot_text_with_weight(self, weight, weight_name):
        """Snapshot test for text rendering with different font weights"""
        from quickthumb import Canvas

        # Given: Text with specific font weight
        # When: Rendering text with weight parameter
        canvas = (
            Canvas(400, 200)
            .background(color="#FFFFFF")
            .text(
                f"Weight {weight}",
                font="NotoSerif",
                size=48,
                color="#000000",
                position=(200, 100),
                align=("center", "middle"),
                weight=weight,
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            # Then: Should render text with specified font weight
            with open(output_path, "rb") as f:
                assert f.read() == external_file(f"snapshots/text_weight_{weight_name}.png")

    def test_snapshot_image_fit_cover(self):
        """Snapshot test for image background with cover fit mode"""
        from quickthumb import Canvas

        # Given: An image background with cover fit mode
        # When: Rendering image with fit="cover" (may crop)
        canvas = Canvas(400, 400).background(image="tests/fixtures/sample_image.jpg", fit="cover")

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            # Then: Should scale image to cover entire canvas while preserving aspect ratio
            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/image_fit_cover.png")

    def test_snapshot_image_fit_contain(self):
        """Snapshot test for image background with contain fit mode"""
        from quickthumb import Canvas

        # Given: An image background with contain fit mode
        # When: Rendering image with fit="contain" (may have empty space)
        canvas = Canvas(400, 400).background(image="tests/fixtures/sample_image.jpg", fit="contain")

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            # Then: Should scale image to fit within canvas while preserving aspect ratio
            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/image_fit_contain.png")

    def test_snapshot_image_fit_fill(self):
        """Snapshot test for image background with fill fit mode"""
        from quickthumb import Canvas

        # Given: An image background with fill fit mode
        canvas = Canvas(400, 400).background(image="tests/fixtures/sample_image.jpg", fit="fill")

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            # Then: Should stretch image to fill entire canvas exactly
            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/image_fit_fill.png")

    def test_should_handle_unknown_font_name_gracefully(self):
        """Test that invalid font name falls back to default font gracefully"""
        from quickthumb import Canvas

        # Given: User specifies a non-existent font name
        # When: Rendering with unknown font name
        canvas = (
            Canvas(400, 200)
            .background(color="#FFFFFF")
            .text("Hello", font="NonExistentFont123", size=48, color="#000000")
        )

        # Then: Should fall back to default font without crashing
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)
            assert os.path.exists(output_path)
            assert os.path.getsize(output_path) > 0

    @pytest.mark.parametrize(
        "font_family, style_name, style_attrs",
        [
            ("Roboto", "bold", {"bold": True}),
            ("Roboto", "italic", {"italic": True}),
            ("Roboto", "bold_italic", {"bold": True, "italic": True}),
        ],
    )
    def test_should_support_styled_named_fonts(self, font_family, style_name, style_attrs):
        """Test that styled variants work with named fonts (e.g., Roboto Bold)"""
        from quickthumb import Canvas

        snapshot_name = f"{font_family.lower().replace(' ', '_')}_{style_name}.png"

        # Given: User wants to use a named font with a specific style
        canvas = (
            Canvas(400, 200)
            .background(color="#FFFFFF")
            .text(
                f"{font_family} {style_name}",
                font=font_family,
                size=36,
                color="#000000",
                **style_attrs,
            )
        )

        # When: Rendering with font name and style flags
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            # Then: Should render with the styled variant successfully
            with open(output_path, "rb") as f:
                assert f.read() == external_file(f"snapshots/{snapshot_name}")

    @pytest.mark.parametrize(
        "brightness, direction",
        [
            (1.5, "increase"),
            (0.5, "decrease"),
        ],
    )
    def test_snapshot_image_brightness(self, brightness, direction):
        """Snapshot test for image background with brightness adjustment"""
        from quickthumb import Canvas

        canvas = Canvas(400, 300).background(
            image="tests/fixtures/sample_image.jpg", brightness=brightness
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            with open(output_path, "rb") as f:
                assert f.read() == external_file(f"snapshots/image_brightness_{direction}.png")

    @pytest.mark.parametrize(
        "brightness, direction",
        [
            (1.5, "increase"),
            (0.5, "decrease"),
        ],
    )
    def test_snapshot_solid_color_brightness(self, brightness, direction):
        """Snapshot test for solid color background with brightness adjustment"""
        from quickthumb import Canvas

        canvas = Canvas(400, 300).background(color="#3498db", brightness=brightness)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            with open(output_path, "rb") as f:
                assert f.read() == external_file(
                    f"snapshots/solid_color_brightness_{direction}.png"
                )

    @pytest.mark.parametrize(
        "brightness, direction",
        [
            (1.5, "increase"),
            (0.7, "decrease"),
        ],
    )
    def test_snapshot_linear_gradient_brightness(self, brightness, direction):
        """Snapshot test for linear gradient with brightness adjustment"""
        from quickthumb import Canvas
        from quickthumb.models import LinearGradient

        gradient = LinearGradient(
            type="linear", angle=45, stops=[("#FF6B6B", 0.0), ("#4ECDC4", 1.0)]
        )

        canvas = Canvas(400, 300).background(gradient=gradient, brightness=brightness)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            with open(output_path, "rb") as f:
                assert f.read() == external_file(
                    f"snapshots/linear_gradient_brightness_{direction}.png"
                )

    @pytest.mark.parametrize(
        "brightness, direction",
        [
            (1.3, "increase"),
            (0.6, "decrease"),
        ],
    )
    def test_snapshot_radial_gradient_brightness(self, brightness, direction):
        """Snapshot test for radial gradient with brightness adjustment"""
        from quickthumb import Canvas
        from quickthumb.models import RadialGradient

        gradient = RadialGradient(
            type="radial", stops=[("#FF0000", 0.0), ("#0000FF", 1.0)], center=(0.5, 0.5)
        )

        canvas = Canvas(400, 300).background(gradient=gradient, brightness=brightness)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            with open(output_path, "rb") as f:
                assert f.read() == external_file(
                    f"snapshots/radial_gradient_brightness_{direction}.png"
                )

    @pytest.mark.parametrize(
        "alignment, position_x, max_width, snapshot_suffix",
        [
            ("center", 200, 300, "center_aligned"),
            ("left", 50, 300, "left_aligned"),
            ("right", 350, 300, "right_aligned"),
            ("center", 200, "50%", "center_aligned_percentage"),
        ],
    )
    def test_snapshot_text_wrapping(self, alignment, position_x, max_width, snapshot_suffix):
        """Snapshot test for text word wrapping with different alignments"""
        from quickthumb import Canvas

        canvas = (
            Canvas(400, 300)
            .background(color="#FFFFFF")
            .text(
                "This is a very long text that should wrap to multiple lines when rendered",
                size=24,
                color="#000000",
                position=(position_x, 150),
                align=(alignment, "middle"),
                max_width=max_width,
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            with open(output_path, "rb") as f:
                assert f.read() == external_file(f"snapshots/text_wrapping_{snapshot_suffix}.png")

    def test_snapshot_text_no_wrapping(self):
        """Snapshot test for long text without max_width (no wrapping)"""
        from quickthumb import Canvas

        canvas = (
            Canvas(400, 300)
            .background(color="#FFFFFF")
            .text(
                "This is a very long text that should not wrap",
                size=24,
                color="#000000",
                position=(200, 150),
                align=("center", "middle"),
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/text_no_wrapping.png")

    def test_snapshot_text_with_basic_shadow(self):
        """Snapshot test for text rendering with basic shadow effect"""
        from quickthumb import Canvas, Shadow

        canvas = (
            Canvas(400, 200)
            .background(color="#FFFFFF")
            .text(
                "Shadow Text",
                size=48,
                color="#000000",
                position=(200, 100),
                align=("center", "middle"),
                effects=[Shadow(offset_x=5, offset_y=5, color="#CCCCCC")],
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/text_with_basic_shadow.png")

    def test_snapshot_text_with_blurred_shadow(self):
        """Snapshot test for text rendering with blurred shadow effect"""
        from quickthumb import Canvas, Shadow

        canvas = (
            Canvas(400, 200)
            .background(color="#FFFFFF")
            .text(
                "Blurred Shadow",
                size=48,
                color="#000000",
                position=(200, 100),
                align=("center", "middle"),
                effects=[Shadow(offset_x=8, offset_y=8, color="#FF0000", blur_radius=10)],
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/text_with_blurred_shadow.png")

    def test_snapshot_text_with_glow(self):
        """Snapshot test for text rendering with glow effect"""
        from quickthumb import Canvas, Glow

        canvas = (
            Canvas(400, 200)
            .background(color="#000000")
            .text(
                "Glow Text",
                size=48,
                color="#FFFFFF",
                position=(200, 100),
                align=("center", "middle"),
                effects=[Glow(color="#C81414", radius=15, opacity=0.8)],
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/text_with_glow.png")

    def test_snapshot_text_with_multiple_glows(self):
        """Snapshot test for text rendering with multiple layered glow effects"""
        from quickthumb import Canvas, Glow

        canvas = (
            Canvas(400, 200)
            .background(color="#1a1a1a")
            .text(
                "Multi Glow",
                size=48,
                color="#FFFFFF",
                position=(200, 100),
                align=("center", "middle"),
                effects=[
                    Glow(color="#FF0000", radius=5, opacity=1.0),
                    Glow(color="#0000FF", radius=20, opacity=0.6),
                ],
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/text_with_multiple_glows.png")

    def test_snapshot_text_with_line_height(self):
        """Snapshot test for text rendering with custom line_height spacing"""
        from quickthumb import Canvas

        # Given: Multi-line text with custom line_height
        # When: Rendering text with line_height parameter
        canvas = (
            Canvas(400, 300)
            .background(color="#FFFFFF")
            .text(
                "This is a long text that wraps to multiple lines for testing line height",
                size=24,
                color="#000000",
                position=(200, 150),
                align=("center", "middle"),
                max_width=300,
                line_height=1.8,
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            # Then: Should show increased spacing between lines
            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/text_with_line_height.png")

    def test_snapshot_text_with_letter_spacing(self):
        """Snapshot test for text rendering with custom letter_spacing"""
        from quickthumb import Canvas

        # Given: Text with custom letter_spacing
        # When: Rendering text with letter_spacing parameter
        canvas = (
            Canvas(400, 200)
            .background(color="#FFFFFF")
            .text(
                "LETTER SPACING",
                size=32,
                color="#000000",
                position=(200, 100),
                align=("center", "middle"),
                letter_spacing=5,
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            # Then: Should show increased spacing between characters
            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/text_with_letter_spacing.png")

    def test_snapshot_rich_text_different_colors(self):
        """Snapshot test for rich text with different colors per part"""
        from quickthumb import Canvas, TextPart

        # Given: Rich text with different colored parts
        # When: Rendering text with multiple TextPart objects with different colors
        canvas = (
            Canvas(400, 200)
            .background(color="#FFFFFF")
            .text(
                content=[
                    TextPart(text="Hello "),
                    TextPart(text="Beautiful ", color="#00FF00"),
                    TextPart(text="World", color="#0000FF"),
                ],
                size=36,
                position=(200, 100),
                align=("center", "middle"),
                color="#FF0000",
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            # Then: Should show text with different colors for each part
            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/rich_text_different_colors.png")

    def test_snapshot_rich_text_with_effects(self):
        """Snapshot test for rich text with part-specific effects"""
        from quickthumb import Canvas, Stroke, TextPart

        # Given: Rich text with part-specific stroke effects
        # When: Rendering text where one part has a stroke effect
        canvas = (
            Canvas(400, 200)
            .background(color="#FFFFFF")
            .text(
                content=[
                    TextPart(text="Normal ", color="#000000"),
                    TextPart(
                        text="Outlined",
                        color="#FF0000",
                        effects=[Stroke(width=2, color="#000000")],
                    ),
                ],
                size=36,
                position=(200, 100),
                align=("center", "middle"),
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            # Then: Should show part-specific stroke effect on second part only
            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/rich_text_with_effects.png")

    def test_snapshot_rich_text_mixed_styles(self):
        """Snapshot test for rich text with both parent and part effects"""
        from quickthumb import Canvas, Stroke, TextPart

        # Given: Rich text with parent effects and additional part-specific effects
        # When: Rendering text with both types of effects
        canvas = (
            Canvas(400, 200)
            .background(color="#FFFFFF")
            .text(
                content=[
                    TextPart(text="Parent ", color="#FFFFFF"),
                    TextPart(
                        text="Both",
                        color="#FF0000",
                        effects=[Stroke(width=1, color="#0000FF")],
                    ),
                    TextPart(text=" Parent", color="#FFFFFF"),
                ],
                size=36,
                position=(200, 100),
                align=("center", "middle"),
                effects=[Stroke(width=3, color="#000000")],
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            # Then: Should show parent effects on all parts plus additional effects on middle part
            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/rich_text_mixed_styles.png")

    def test_snapshot_rich_text_alignment(self):
        """Snapshot test verifying rich text positioning with center/middle alignment"""
        from quickthumb import Canvas, TextPart

        # Given: Rich text with TextPart objects using center/middle alignment
        # When: Rendering rich text at the same position as regular text would be
        canvas = (
            Canvas(400, 300)
            .background(color="#F0F0F0")
            .text(
                content=[
                    TextPart(text="Rich\n", color="#FF0000"),
                    TextPart(text="Text\n", color="#00FF00"),
                    TextPart(text="Alignment", color="#0000FF"),
                ],
                size=32,
                position=(200, 150),
                align=("center", "middle"),
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            # Then: Should be properly centered at the specified position
            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/rich_text_alignment.png")

    def test_snapshot_rich_text_advanced_styles(self):
        """Snapshot test for rich text with advanced styling options (size, bold, etc.)"""
        from quickthumb import Canvas, TextPart

        # Given: Rich text with mixed sizes, bold, italic, line height, letter spacing
        # When: Rendering with TextParts using these options
        canvas = (
            Canvas(400, 300)
            .background(color="#FFFFFF")
            .text(
                content=[
                    TextPart(text="Big Bold\n", size=48, bold=True, color="#000000"),
                    TextPart(text="Small Italic\n", size=24, italic=True, color="#555555"),
                    TextPart(
                        text="Spaced Out",
                        size=32,
                        letter_spacing=10,
                        color="#FF0000",
                        line_height=2.0,
                    ),
                ],
                position=(200, 150),
                align=("center", "middle"),
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            # Then: Should show varied text styles in one block
            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/rich_text_advanced_styles.png")

    def test_snapshot_rich_text_mixed_fonts(self):
        """Snapshot test for rich text with different fonts per part"""
        from quickthumb import Canvas, TextPart

        # Given: Rich text with mixed fonts
        # When: Rendering with TextParts using different fonts
        canvas = (
            Canvas(400, 200)
            .background(color="#FFFFFF")
            .text(
                content=[
                    TextPart(text="Roboto ", font="Roboto", size=32, color="#000000"),
                    TextPart(text="NotoSerif ", font="NotoSerif", size=32, color="#000000"),
                    TextPart(text="Mixed", font="Roboto", size=32, color="#000000", bold=True),
                ],
                position=(200, 100),
                align=("center", "middle"),
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            # Then: Should show text with different fonts
            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/rich_text_mixed_fonts.png")

    def test_snapshot_url_image_background_basic(self):
        """Snapshot test for URL-based image background rendering"""
        from quickthumb import Canvas

        # Given: A canvas with a URL image as background
        # When: Rendering with URL image parameter
        canvas = Canvas(400, 300).background(image="https://httpbin.org/image/png")

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            # Then: Should render the URL image as background
            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/url_image_background_basic.png")

    def test_snapshot_webfont_basic_rendering(self):
        """Snapshot test for loading and rendering text with a web font from URL"""
        from quickthumb import Canvas

        # Given: A canvas with text using a distinctive script font (Pacifico) from URL
        # When: Rendering text with font parameter pointing to a URL
        canvas = (
            Canvas(400, 200)
            .background(color="#FFFFFF")
            .text(
                "Web Font Test",
                font="https://fonts.gstatic.com/s/pacifico/v22/FwZY7-Qmy14u9lezJ-6H6MmBp0u-.woff2",
                size=48,
                color="#FF1493",
                position=("50%", "50%"),
                align=("center", "middle"),
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            # Then: Should render text with the web font loaded from URL
            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/webfont_basic_rendering.png")

    def test_should_raise_error_for_invalid_webfont_url(self):
        """Should raise RenderingError when web font URL is invalid or unreachable"""
        from quickthumb import Canvas
        from quickthumb.errors import RenderingError

        # Given: A canvas with text using an invalid font URL
        # When: Rendering text with unreachable or invalid font URL
        canvas = (
            Canvas(400, 200)
            .background(color="#FFFFFF")
            .text(
                "Test",
                font="https://invalid-domain-that-does-not-exist-12345.com/font.woff2",
                size=36,
                color="#000000",
            )
        )

        # Then: Should raise RenderingError during render
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            with pytest.raises(RenderingError):
                canvas.render(output_path)

    def test_should_warn_when_using_bold_italic_with_webfont(self):
        """Should warn when bold/italic flags are used with webfont URLs"""
        import warnings

        from quickthumb import Canvas

        # Given: A canvas with text using webfont URL with bold flag
        canvas = (
            Canvas(400, 200)
            .background(color="#FFFFFF")
            .text(
                "Test",
                font="https://fonts.gstatic.com/s/pacifico/v22/FwZY7-Qmy14u9lezJ-6H6MmBp0u-.woff2",
                size=36,
                color="#000000",
                bold=True,
            )
        )

        # When: Rendering with bold flag
        # Then: Should issue a UserWarning
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                canvas.render(output_path)

                assert len(w) == 1
                assert issubclass(w[0].category, UserWarning)
                assert "Bold/italic/weight flags are ignored for webfont URLs" in str(w[0].message)

    def test_snapshot_text_with_background_basic(self):
        """Snapshot test for text rendering with basic background effect"""
        from quickthumb import Background, Canvas

        canvas = (
            Canvas(400, 200)
            .background(color="#FFFFFF")
            .text(
                "FEATURED",
                size=64,
                color="#FFFFFF",
                position=(200, 100),
                align=("center", "middle"),
                effects=[Background(color="#FF5722", padding=20, border_radius=12)],
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/text_with_background_basic.png")

    def test_snapshot_text_with_background_and_effects(self):
        """Snapshot test for text with background combined with stroke and shadow"""
        from quickthumb import Background, Canvas, Shadow, Stroke

        canvas = (
            Canvas(400, 200)
            .background(color="#F0F0F0")
            .text(
                "LABEL",
                size=48,
                color="#FFFFFF",
                position=(200, 100),
                align=("center", "middle"),
                effects=[
                    Background(color="#E74C3C", padding=(10, 20), border_radius=8, opacity=0.9),
                    Stroke(width=2, color="#000000"),
                    Shadow(offset_x=2, offset_y=2, color="#00000080", blur_radius=2),
                ],
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/text_with_background_and_effects.png")

    def test_snapshot_rich_text_with_background(self):
        """Snapshot test for rich text with part-specific background effects"""
        from quickthumb import Background, Canvas, TextPart

        canvas = (
            Canvas(600, 200)
            .background(color="#FFFFFF")
            .text(
                [
                    TextPart(
                        text="URGENT",
                        bold=True,
                        color="#FFFFFF",
                        effects=[Background(color="#E74C3C", padding=10, border_radius=5)],
                    ),
                    TextPart(text=" NOTICE", color="#000000"),
                ],
                size=48,
                position=(300, 100),
                align=("center", "middle"),
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/rich_text_with_background.png")
