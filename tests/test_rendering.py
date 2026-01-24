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
        from quickthumb import Canvas

        # Given: Text with a 2px black stroke around white text
        # When: Rendering text with stroke parameter
        canvas = (
            Canvas(400, 200)
            .background(color="#FFFFFF")
            .text(
                "Stroke Text",
                size=48,
                color="#FFFFFF",
                position=(200, 100),
                align=("center", "middle"),
                stroke=(2, "#000000"),
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
        """Test that invalid font name raises ValidationError with helpful message"""
        from quickthumb import Canvas
        from quickthumb.errors import RenderingError

        # Given: User specifies a non-existent font name
        # When: Rendering with unknown font name
        canvas = (
            Canvas(400, 200)
            .background(color="#FFFFFF")
            .text("Hello", font="NonExistentFont123", size=48, color="#000000")
        )

        # Then: Should raise ValidationError during render
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            with pytest.raises(RenderingError):
                canvas.render(output_path)

    @pytest.mark.parametrize(
        "font_family, style_name, style_attrs",
        [
            ("Arial", "bold", {"bold": True}),
            ("Arial", "italic", {"italic": True}),
            ("Arial", "bold_italic", {"bold": True, "italic": True}),
            ("Times New Roman", "bold", {"bold": True}),
            ("Times New Roman", "italic", {"italic": True}),
            ("Times New Roman", "bold_italic", {"bold": True, "italic": True}),
        ],
    )
    def test_should_support_styled_named_fonts(self, font_family, style_name, style_attrs):
        """Test that styled variants work with named fonts (e.g., Arial Bold)"""
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
