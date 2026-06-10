"""Tests for rendering engine functionality"""

import os
import tempfile

import pytest
from inline_snapshot import external_file
from quickthumb.models import Align


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

    def test_snapshot_text_and_outline_with_opacity(self):
        """Snapshot test for semi-transparent text and outline layers"""
        from quickthumb import Canvas

        canvas = (
            Canvas(400, 300)
            .background(color="#3498DB")
            .text("Hello", size=48, color="#FFFFFF", align=("center", "middle"), opacity=0.5)
            .outline(width=10, color="#FF0000", opacity=0.5)
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/text_and_outline_with_opacity.png")

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

    @pytest.mark.parametrize(
        "fit,snapshot_name",
        [
            ("cover", "image_overlay_fit_cover.png"),
            ("contain", "image_overlay_fit_contain.png"),
            ("fill", "image_overlay_fit_fill.png"),
        ],
    )
    def test_snapshot_image_overlay_fit_modes(self, fit, snapshot_name):
        """Snapshot test for image overlay fit modes in a clearly visible framed target box"""
        from quickthumb import Canvas

        canvas = (
            Canvas(460, 320)
            .background(color="#E2E8F0")
            # Dark outer frame to make the target box edges obvious in snapshots.
            .shape(
                shape="rectangle",
                position=(230, 180),
                width=300,
                height=150,
                color="#1F2937",
                align=("center", "middle"),
            )
            # White inner target box where fit mode is applied.
            .shape(
                shape="rectangle",
                position=(230, 180),
                width=286,
                height=136,
                color="#FFFFFF",
                align=("center", "middle"),
            )
            .image(
                path="tests/fixtures/tobias-rademacher-wnF27F85ZKw-unsplash.jpg",
                position=(230, 180),
                width=286,
                height=136,
                fit=fit,
                align=("center", "middle"),
            )
            .text(
                f"fit={fit}",
                size=28,
                color="#111827",
                position=(230, 44),
                align=("center", "middle"),
                bold=True,
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            with open(output_path, "rb") as f:
                assert f.read() == external_file(f"snapshots/{snapshot_name}")

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
        from quickthumb import Canvas, Filter

        canvas = Canvas(400, 300).background(
            image="tests/fixtures/sample_image.jpg", effects=[Filter(brightness=brightness)]
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
        from quickthumb import Canvas, Filter

        canvas = Canvas(400, 300).background(
            color="#3498db", effects=[Filter(brightness=brightness)]
        )

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
        from quickthumb import Canvas, Filter
        from quickthumb.models import LinearGradient

        gradient = LinearGradient(
            type="linear", angle=45, stops=[("#FF6B6B", 0.0), ("#4ECDC4", 1.0)]
        )

        canvas = Canvas(400, 300).background(
            gradient=gradient, effects=[Filter(brightness=brightness)]
        )

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
        from quickthumb import Canvas, Filter
        from quickthumb.models import RadialGradient

        gradient = RadialGradient(
            type="radial", stops=[("#FF0000", 0.0), ("#0000FF", 1.0)], center=(0.5, 0.5)
        )

        canvas = Canvas(400, 300).background(
            gradient=gradient, effects=[Filter(brightness=brightness)]
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            with open(output_path, "rb") as f:
                assert f.read() == external_file(
                    f"snapshots/radial_gradient_brightness_{direction}.png"
                )

    _WRAP_TEXT = "This is a very long text that should wrap to multiple lines when rendered"

    @pytest.mark.parametrize(
        "content, alignment, position_x, max_width, snapshot_suffix",
        [
            (_WRAP_TEXT, "center", 200, 300, "center_aligned"),
            (_WRAP_TEXT, "left", 50, 300, "left_aligned"),
            (_WRAP_TEXT, "right", 350, 300, "right_aligned"),
            (_WRAP_TEXT, "center", 200, "50%", "center_aligned_percentage"),
            (
                "Superlongwordthatwillneverfit and then some normal words",
                "center",
                200,
                80,
                "long_word_overflow",
            ),
        ],
    )
    def test_snapshot_text_wrapping(
        self, content, alignment, position_x, max_width, snapshot_suffix
    ):
        """Snapshot test for text word wrapping with different alignments and overflow"""
        import warnings

        from quickthumb import Canvas

        canvas = (
            Canvas(400, 300)
            .background(color="#FFFFFF")
            .text(
                content,
                size=24,
                color="#000000",
                position=(position_x, 150),
                align=(alignment, "middle"),
                max_width=max_width,
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            with warnings.catch_warnings(record=True):
                warnings.simplefilter("always")
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

    def test_snapshot_text_with_letter_spacing_shadow(self):
        """Snapshot test for letter-spaced text with shadow effect"""
        from quickthumb import Canvas, Shadow

        canvas = (
            Canvas(400, 200)
            .background(color="#FFFFFF")
            .text(
                "ARE YOU",
                size=48,
                color="#fbbf24",
                position=(200, 100),
                align=("center", "middle"),
                letter_spacing=2,
                effects=[Shadow(offset_x=5, offset_y=5, color="#000000", blur_radius=0)],
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/text_with_letter_spacing_shadow.png")

    def test_snapshot_text_with_letter_spacing_glow(self):
        """Snapshot test for letter-spaced text with glow effect"""
        from quickthumb import Canvas, Glow

        canvas = (
            Canvas(400, 200)
            .background(color="#1a1a1a")
            .text(
                "ARE YOU",
                size=48,
                color="#fbbf24",
                position=(200, 100),
                align=("center", "middle"),
                letter_spacing=2,
                effects=[Glow(color="#FF0000", radius=10, opacity=0.8)],
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/text_with_letter_spacing_glow.png")

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

    def test_snapshot_multiline_text_with_shadow(self):
        """Snapshot test for multiline text with shadow effect"""
        from quickthumb import Canvas, Shadow

        canvas = (
            Canvas(400, 200)
            .background(color="#FFFFFF")
            .text(
                "Line 1\nLine 2\nLine 3",
                size=32,
                color="#000000",
                position=(200, 100),
                align=("center", "middle"),
                effects=[Shadow(offset_x=4, offset_y=4, color="#888888", blur_radius=3)],
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/multiline_text_with_shadow.png")

    def test_snapshot_multiline_text_with_glow(self):
        """Snapshot test for multiline text with glow effect"""
        from quickthumb import Canvas, Glow

        canvas = (
            Canvas(400, 200)
            .background(color="#1a1a1a")
            .text(
                "Line 1\nLine 2\nLine 3",
                size=32,
                color="#FFFFFF",
                position=(200, 100),
                align=("center", "middle"),
                effects=[Glow(color="#FF0000", radius=10, opacity=0.8)],
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/multiline_text_with_glow.png")

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
                align=Align.CENTER,
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

    def test_snapshot_multiline_text_with_background(self):
        """Snapshot test for multiline text with a background effect"""
        from quickthumb import Background, Canvas

        canvas = (
            Canvas(420, 260)
            .background(color="#0B1020")
            .text(
                "JSON in.\nCover out.",
                font="Roboto",
                size=58,
                color="#F8FAFC",
                position=(40, 100),
                align=("left", "top"),
                line_height=1.1,
                effects=[Background(color="#0F2746D9", padding=(20, 24), border_radius=18)],
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/multiline_text_with_background.png")

    def test_snapshot_explicit_newlines_preserved_with_max_width(self):
        """Snapshot test that explicit newlines survive additional wrapping constraints"""
        from quickthumb import Background, Canvas

        canvas = (
            Canvas(420, 260)
            .background(color="#0B1020")
            .text(
                "JSON in.\nCover out.",
                font="Roboto",
                size=40,
                color="#F8FAFC",
                position=(40, 48),
                align=("left", "top"),
                max_width=220,
                line_height=1.1,
                effects=[Background(color="#0F2746D9", padding=(20, 24), border_radius=18)],
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            with open(output_path, "rb") as f:
                assert f.read() == external_file(
                    "snapshots/explicit_newlines_preserved_with_max_width.png"
                )

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

    def test_snapshot_auto_scale_simple_text(self):
        """Snapshot test for auto-scaled simple text"""
        from quickthumb import Canvas

        canvas = (
            Canvas(400, 200)
            .background(color="#FFFFFF")
            .text(
                "This is a long text that should be auto-scaled to fit",
                size=48,
                color="#000000",
                position=(200, 100),
                align=Align.CENTER,
                max_width=100,
                auto_scale=True,
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/auto_scale_simple_text.png")

    def test_snapshot_auto_scale_rich_text(self):
        """Snapshot test for auto-scaled rich text"""
        from quickthumb import Canvas, TextPart

        canvas = (
            Canvas(400, 200)
            .background(color="#FFFFFF")
            .text(
                content=[
                    TextPart(text="Big ", size=60, color="#FF0000", bold=True),
                    TextPart(text="Medium ", size=40, color="#00FF00"),
                    TextPart(text="Small", size=30, color="#0000FF"),
                ],
                position=(200, 100),
                align=Align.CENTER,
                max_width=150,
                auto_scale=True,
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/auto_scale_rich_text.png")

    def test_snapshot_rich_text_wrapping(self):
        """Snapshot test for rich text word-wrapping with list[TextPart] and max_width"""
        from quickthumb import Canvas, TextPart

        canvas = (
            Canvas(400, 300)
            .background(color="#FFFFFF")
            .text(
                content=[
                    TextPart(text="Breaking news: ", color="#CC0000", bold=True),
                    TextPart(
                        text="a long story that should wrap across multiple lines", color="#111111"
                    ),
                ],
                size=24,
                position=(200, 150),
                align=("center", "middle"),
                max_width=300,
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/rich_text_wrapping.png")

    def test_snapshot_image_basic(self):
        """Snapshot test for basic image layer rendering"""
        from quickthumb import Canvas

        # Given: Canvas with image overlay at specific position
        canvas = (
            Canvas(400, 300)
            .background(color="#F0F0F0")
            .image(path="tests/fixtures/sample_image.jpg", position=(50, 50), width=200)
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            # Then: Should render image at specified position
            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/image_basic.png")

    def test_snapshot_image_with_opacity(self):
        """Snapshot test for image layer with opacity"""
        from quickthumb import Canvas

        # Given: Canvas with semi-transparent image overlay
        canvas = (
            Canvas(400, 300)
            .background(color="#FFFFFF")
            .image(
                path="tests/fixtures/ivana-cajina-_7LbC5J-jw4-unsplash.jpg",
                position=(50, 50),
                width=200,
                opacity=0.5,
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            # Then: Should render semi-transparent image
            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/image_with_opacity.png")

    def test_snapshot_image_with_rotation(self):
        """Snapshot test for image layer with rotation"""
        from quickthumb import Canvas

        # Given: Canvas with rotated image overlay
        canvas = (
            Canvas(400, 300)
            .background(color="#F0F0F0")
            .image(
                path="tests/fixtures/tobias-rademacher-wnF27F85ZKw-unsplash.jpg",
                position=(200, 150),
                width=150,
                rotation=45,
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            # Then: Should render rotated image
            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/image_with_rotation.png")

    def test_snapshot_image_percentage_position(self):
        """Snapshot test for image layer with percentage positioning"""
        from quickthumb import Canvas

        # Given: Canvas with image at percentage position
        canvas = (
            Canvas(400, 300)
            .background(color="#FFFFFF")
            .image(
                path="tests/fixtures/sample_image.jpg",
                position=("50%", "50%"),
                width=100,
                align=("center", "middle"),
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            # Then: Should render image at center
            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/image_percentage_position.png")

    def test_snapshot_multiple_images(self):
        """Snapshot test for multiple layered images"""
        from quickthumb import Canvas

        # Given: Canvas with multiple image layers
        canvas = (
            Canvas(400, 300)
            .background(color="#2C3E50")
            .image(
                path="tests/fixtures/ivana-cajina-_7LbC5J-jw4-unsplash.jpg",
                position=(50, 50),
                width=150,
                opacity=0.8,
            )
            .image(
                path="tests/fixtures/tobias-rademacher-wnF27F85ZKw-unsplash.jpg",
                position=(200, 100),
                width=120,
                opacity=0.6,
                rotation=15,
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            # Then: Should render multiple images in correct layer order
            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/multiple_images.png")

    def test_snapshot_image_with_text_overlay(self):
        """Snapshot test for image layer combined with text"""
        from quickthumb import Canvas

        # Given: Canvas with image and text layers combined
        canvas = (
            Canvas(400, 300)
            .background(color="#FFFFFF")
            .image(
                path="tests/fixtures/ivana-cajina-_7LbC5J-jw4-unsplash.jpg",
                position=(50, 50),
                width=300,
            )
            .text(
                "OVERLAY TEXT",
                size=48,
                color="#FFFFFF",
                position=(200, 150),
                align=("center", "middle"),
                bold=True,
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            # Then: Should render image with text on top
            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/image_with_text_overlay.png")

    @pytest.mark.parametrize(
        "blend_mode,snapshot_name",
        [
            (None, "image_on_background_image.png"),
            ("multiply", "image_blend_mode_multiply.png"),
            ("overlay", "image_blend_mode_overlay.png"),
            ("screen", "image_blend_mode_screen.png"),
            ("darken", "image_blend_mode_darken.png"),
            ("lighten", "image_blend_mode_lighten.png"),
            ("normal", "image_blend_mode_normal.png"),
        ],
    )
    def test_snapshot_image_on_background_image(self, blend_mode, snapshot_name):
        """Snapshot test for image layer compositing on top of a background image"""
        from quickthumb import Canvas

        # Given: Canvas with background image and overlay image layer
        canvas = (
            Canvas(400, 300)
            .background(image="tests/fixtures/sample_image.jpg")
            .image(
                path="tests/fixtures/tobias-rademacher-wnF27F85ZKw-unsplash.jpg",
                position=(250, 150),
                width=120,
                opacity=0.9,
                blend_mode=blend_mode,
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            # Then: Should render overlay image with requested blend mode
            with open(output_path, "rb") as f:
                assert f.read() == external_file(f"snapshots/{snapshot_name}")

    def test_snapshot_text_rotation_basic(self):
        """Snapshot test for basic text rotation at 45 degrees"""
        from quickthumb import Canvas

        # Given: Text rotated 45 degrees
        canvas = (
            Canvas(400, 400)
            .background(color="#FFFFFF")
            .text(
                "Rotated 45°",
                size=48,
                color="#000000",
                position=(200, 200),
                align="center",
                rotation=45,
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            # Then: Should render text rotated 45 degrees
            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/text_rotation_basic.png")

    def test_snapshot_text_rotation_with_effects(self):
        """Snapshot test for rotated text with stroke and shadow effects"""
        from quickthumb import Canvas, Shadow, Stroke

        # Given: Rotated text with multiple effects
        canvas = (
            Canvas(400, 400)
            .background(color="#F0F0F0")
            .text(
                "ROTATED",
                size=56,
                color="#FF5722",
                position=(200, 200),
                align="center",
                rotation=-30,
                effects=[
                    Stroke(width=3, color="#FFFFFF"),
                    Shadow(offset_x=4, offset_y=4, color="#00000080", blur_radius=2),
                ],
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            # Then: Should render rotated text with effects properly applied
            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/text_rotation_with_effects.png")

    def test_snapshot_text_rotation_centered(self):
        """Snapshot test for multiple text rotations with center alignment"""
        from quickthumb import Canvas

        # Given: Multiple texts at different rotation angles, all center-aligned
        canvas = (
            Canvas(400, 400)
            .background(color="#FFFFFF")
            .text(
                "0°",
                size=32,
                color="#000000",
                position=(200, 200),
                align="center",
                rotation=0,
            )
            .text(
                "45°",
                size=32,
                color="#FF0000",
                position=(200, 200),
                align="center",
                rotation=45,
            )
            .text(
                "90°",
                size=32,
                color="#00FF00",
                position=(200, 200),
                align="center",
                rotation=90,
            )
            .text(
                "135°",
                size=32,
                color="#0000FF",
                position=(200, 200),
                align="center",
                rotation=135,
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            # Then: Should render multiple rotated texts creating a circular pattern
            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/text_rotation_centered.png")

    def test_snapshot_image_with_remove_background(self):
        """Snapshot test for image layer with real rembg background removal"""
        from quickthumb import Canvas

        # Given: Canvas with image overlay using real background removal
        canvas = (
            Canvas(400, 300)
            .background(image="tests/fixtures/sample_image.jpg")
            .image(
                path="tests/fixtures/tobias-rademacher-wnF27F85ZKw-unsplash.jpg",
                position=("50%", "50%"),
                width=200,
                align=("center", "middle"),
                remove_background=True,
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            # Then: Should render image with background removed, revealing blue canvas behind
            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/image_with_remove_background.png")

    def test_snapshot_shape_rectangle_basic(self):
        """Snapshot test for basic rectangle shape layer"""
        from quickthumb import Canvas

        # Given: Canvas with a basic filled rectangle
        canvas = (
            Canvas(400, 300)
            .background(color="#FFFFFF")
            .shape(shape="rectangle", position=(100, 75), width=200, height=150, color="#FF5733")
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            # Then: Should render a solid orange rectangle at the specified position
            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/shape_rectangle_basic.png")

    def test_snapshot_shape_ellipse_basic(self):
        """Snapshot test for basic ellipse shape layer"""
        from quickthumb import Canvas

        # Given: Canvas with a basic filled ellipse
        canvas = (
            Canvas(400, 300)
            .background(color="#F0F0F0")
            .shape(
                shape="ellipse",
                position=(200, 150),
                width=200,
                height=120,
                color="#3498DB",
                align=("center", "middle"),
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            # Then: Should render a blue ellipse centered at the specified position
            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/shape_ellipse_basic.png")

    def test_snapshot_shape_with_effects(self):
        """Snapshot test for shape layer with stroke, shadow, and glow effects.

        Covers both a rectangle and an ellipse to verify that blurred shadows
        follow the actual shape outline rather than the rectangular bounding box.
        """
        from quickthumb import Canvas, Glow, Shadow, Stroke

        canvas = (
            Canvas(400, 400)
            .background(color="#1a1a2e")
            .shape(
                shape="rectangle",
                position=("50%", "27%"),
                width=200,
                height=120,
                color="#2ECC71",
                align=("center", "middle"),
                effects=[
                    Shadow(offset_x=6, offset_y=6, color="#000000", blur_radius=8),
                    Glow(color="#2ECC71", radius=12, opacity=0.8),
                    Stroke(width=4, color="#1A8A4A"),
                ],
            )
            .shape(
                shape="ellipse",
                position=("50%", "73%"),
                width=160,
                height=160,
                color="#3B82F6",
                align=("center", "middle"),
                effects=[
                    Shadow(offset_x=0, offset_y=0, color="#000000", blur_radius=14),
                ],
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/shape_with_effects.png")

    def test_snapshot_shape_rectangle_with_border_radius(self):
        """Snapshot test for rectangle with rounded corners"""
        from quickthumb import Canvas

        # Given: Canvas with a rounded rectangle
        canvas = (
            Canvas(400, 300)
            .background(color="#FFFFFF")
            .shape(
                shape="rectangle",
                position=(100, 75),
                width=200,
                height=150,
                color="#9B59B6",
                border_radius=20,
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            # Then: Should render a purple rectangle with rounded corners
            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/shape_rectangle_with_border_radius.png")

    def test_snapshot_shape_with_opacity(self):
        """Snapshot test for shape layer with opacity"""
        from quickthumb import Canvas

        # Given: Canvas with a semi-transparent shape over a colored background
        canvas = (
            Canvas(400, 300)
            .background(image="tests/fixtures/sample_image.jpg")
            .shape(
                shape="rectangle",
                position=(100, 75),
                width=200,
                height=150,
                color="#E74C3C",
                opacity=0.5,
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            # Then: Should render a semi-transparent red rectangle over blue background
            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/shape_with_opacity.png")

    def test_snapshot_shape_with_rotation(self):
        """Snapshot test for shape layer with rotation"""
        from quickthumb import Canvas

        # Given: Canvas with a rotated rectangle
        canvas = (
            Canvas(400, 300)
            .background(color="#FFFFFF")
            .shape(
                shape="rectangle",
                position=(200, 150),
                width=200,
                height=80,
                color="#E67E22",
                align=("center", "middle"),
                rotation=45,
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            # Then: Should render an orange rectangle rotated 45 degrees
            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/shape_with_rotation.png")

    @pytest.mark.parametrize(
        "blur, suffix",
        [
            (5, "soft"),
            (15, "heavy"),
        ],
    )
    def test_snapshot_background_blur(self, blur, suffix):
        """Snapshot test for background blur filter effect"""
        from quickthumb import Canvas, Filter

        canvas = Canvas(400, 300).background(
            image="tests/fixtures/sample_image.jpg",
            effects=[Filter(blur=blur)],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            with open(output_path, "rb") as f:
                assert f.read() == external_file(f"snapshots/background_blur_{suffix}.png")

    @pytest.mark.parametrize(
        "saturation, suffix",
        [
            (0.0, "grayscale"),
            (2.0, "vivid"),
        ],
    )
    def test_snapshot_background_saturation(self, saturation, suffix):
        """Snapshot test for background saturation filter effect"""
        from quickthumb import Canvas, Filter

        canvas = Canvas(400, 300).background(
            image="tests/fixtures/sample_image.jpg",
            effects=[Filter(saturation=saturation)],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            with open(output_path, "rb") as f:
                assert f.read() == external_file(f"snapshots/background_saturation_{suffix}.png")

    @pytest.mark.parametrize(
        "contrast, suffix",
        [
            (0.5, "low"),
            (2.0, "high"),
        ],
    )
    def test_snapshot_background_contrast(self, contrast, suffix):
        """Snapshot test for background contrast filter effect"""
        from quickthumb import Canvas, Filter

        canvas = Canvas(400, 300).background(
            image="tests/fixtures/sample_image.jpg",
            effects=[Filter(contrast=contrast)],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            with open(output_path, "rb") as f:
                assert f.read() == external_file(f"snapshots/background_contrast_{suffix}.png")

    def test_snapshot_background_combined_filters(self):
        """Snapshot test for background with blur, contrast, and saturation combined"""
        from quickthumb import Canvas, Filter

        canvas = Canvas(400, 300).background(
            image="tests/fixtures/sample_image.jpg",
            effects=[Filter(blur=5, contrast=1.5, saturation=0.5)],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/background_combined_filters.png")

    def test_snapshot_image_with_drop_shadow(self):
        """Snapshot test for image layer with drop shadow cast from image alpha shape"""
        from quickthumb import Canvas, Shadow

        canvas = (
            Canvas(400, 300)
            .background(color="#F0F0F0")
            .image(
                path="tests/fixtures/sample_image.jpg",
                position=("50%", "50%"),
                width=200,
                align=("center", "middle"),
                effects=[Shadow(offset_x=8, offset_y=8, color="#000000", blur_radius=10)],
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/image_with_drop_shadow.png")

    def test_snapshot_image_with_border_radius(self):
        """Snapshot test for image layer with rounded corners via border_radius"""
        from quickthumb import Canvas

        # Given: Canvas with image overlay clipped to rounded rectangle
        canvas = (
            Canvas(400, 300)
            .background(color="#F0F0F0")
            .image(
                path="tests/fixtures/sample_image.jpg",
                position=(100, 75),
                width=200,
                border_radius=30,
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            # Then: Should render image clipped to a rounded rectangle
            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/image_with_border_radius.png")

    def test_snapshot_image_with_stroke(self):
        """Snapshot test for image layer with stroke effect (border around alpha shape)"""
        from quickthumb import Canvas, Stroke

        canvas = (
            Canvas(400, 300)
            .background(color="#F0F0F0")
            .image(
                path="tests/fixtures/sample_image.jpg",
                position=("50%", "50%"),
                width=200,
                align=("center", "middle"),
                effects=[Stroke(width=10, color="#C81414")],
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/image_with_stroke.png")

    def test_snapshot_image_with_glow(self):
        """Snapshot test for image layer with glow effect (blurred halo around alpha shape)"""
        from quickthumb import Canvas, Glow

        canvas = (
            Canvas(400, 300)
            .background(color="#1a1a2e")
            .image(
                path="tests/fixtures/sample_image.jpg",
                position=("50%", "50%"),
                width=200,
                align=("center", "middle"),
                effects=[Glow(color="#00BFFF", radius=15, opacity=0.9)],
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/image_with_glow.png")

    def test_snapshot_background_filter_effect(self):
        """Snapshot test for background with Filter effect (blur + brightness + contrast)"""
        from quickthumb import Canvas, Filter

        canvas = Canvas(200, 150).background(
            image="tests/fixtures/sample_image.jpg",
            effects=[Filter(blur=3, brightness=0.6, contrast=1.4, saturation=0.5)],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/background_filter_effect.png")

    def test_snapshot_image_filter_effect(self):
        """Snapshot test for image layer with Filter effect"""
        from quickthumb import Canvas, Filter

        canvas = (
            Canvas(400, 300)
            .background(color="#222222")
            .image(
                path="tests/fixtures/sample_image.jpg",
                position=("50%", "50%"),
                width=200,
                align=("center", "middle"),
                effects=[Filter(blur=2, brightness=0.7, saturation=0.3)],
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/image_filter_effect.png")

    def test_snapshot_custom_layer_with_kwargs(self):
        """Snapshot test for custom layer where kwargs control visual output"""
        from PIL import ImageDraw
        from quickthumb import Canvas

        def draw_colored_bar(image, *, color: str = "#000000", height: int = 40) -> None:
            draw = ImageDraw.Draw(image)
            draw.rectangle((0, 0, image.width, height), fill=color)

        Canvas.register_layer_fn("draw_colored_bar", draw_colored_bar)
        try:
            canvas = (
                Canvas(200, 150)
                .background(color="#FFFFFF")
                .custom(
                    draw_colored_bar,
                    name="draw_colored_bar",
                    kwargs={"color": "#E74C3C", "height": 50},
                )
            )

            with tempfile.TemporaryDirectory() as tmpdir:
                output_path = os.path.join(tmpdir, "output.png")
                canvas.render(output_path)

                with open(output_path, "rb") as f:
                    assert f.read() == external_file("snapshots/custom_layer_with_kwargs.png")
        finally:
            Canvas.unregister_layer_fn("draw_colored_bar")

    def test_snapshot_custom_canvas_layer(self):
        """Snapshot test for realistic user customization via canvas.custom(fn)"""
        from PIL import Image, ImageDraw, ImageFont
        from quickthumb import Canvas

        def draw_custom_card(image):
            draw = ImageDraw.Draw(image, "RGBA")
            draw.rounded_rectangle((16, 16, 384, 112), radius=18, fill=(17, 24, 39, 196))

            with Image.open("tests/fixtures/sample_image.jpg") as avatar_source:
                avatar = avatar_source.convert("RGBA").resize((72, 72), Image.Resampling.LANCZOS)
            avatar_mask = Image.new("L", avatar.size, 0)
            ImageDraw.Draw(avatar_mask).ellipse((0, 0, 71, 71), fill=255)
            avatar.putalpha(avatar_mask)
            image.alpha_composite(avatar, (28, 28))

            title_font = ImageFont.truetype("assets/fonts/Roboto-Bold.ttf", 30)
            subtitle_font = ImageFont.truetype("assets/fonts/Roboto-Regular.ttf", 18)
            draw.text((116, 34), "MY STYLE", font=title_font, fill="#F8FAFC")
            draw.text((116, 72), "custom thumbnail", font=subtitle_font, fill="#FFD166")

        canvas = (
            Canvas(400, 300)
            .background(
                image="tests/fixtures/tobias-rademacher-wnF27F85ZKw-unsplash.jpg",
                fit="cover",
            )
            .custom(draw_custom_card)
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/custom_canvas_layer.png")

    def test_snapshot_text_with_linear_gradient_fill(self):
        """Snapshot test for text rendered with a linear gradient fill"""
        from quickthumb import Canvas, LinearGradient

        canvas = (
            Canvas(400, 200)
            .background(color="#111111")
            .text(
                "GRADIENT",
                size=72,
                fill=LinearGradient(angle=90, stops=[("#FF6B6B", 0.0), ("#4ECDC4", 1.0)]),
                position=(200, 100),
                align=("center", "middle"),
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/text_with_linear_gradient_fill.png")

    def test_snapshot_text_with_radial_gradient_fill(self):
        """Snapshot test for text rendered with a radial gradient fill"""
        from quickthumb import Canvas, RadialGradient

        canvas = (
            Canvas(400, 200)
            .background(color="#111111")
            .text(
                "RADIAL",
                size=72,
                fill=RadialGradient(stops=[("#FFD700", 0.0), ("#FF000000", 1.0)]),
                position=(200, 100),
                align=("center", "middle"),
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/text_with_radial_gradient_fill.png")

    def test_snapshot_text_with_image_fill(self):
        """Snapshot test for text rendered with an image fill (TextFillImage)"""
        from quickthumb import Canvas, TextFillImage

        canvas = (
            Canvas(400, 200)
            .background(color="#111111")
            .text(
                "TEXTURE",
                size=72,
                fill=TextFillImage(path="tests/fixtures/sample_image.jpg", fit="cover"),
                position=(200, 100),
                align=("center", "middle"),
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/text_with_image_fill.png")

    def test_snapshot_text_fill_with_stroke(self):
        """Snapshot test for gradient-filled text with a stroke effect"""
        from quickthumb import Canvas, LinearGradient, Stroke

        canvas = (
            Canvas(400, 200)
            .background(color="#111111")
            .text(
                "STROKE",
                size=72,
                fill=LinearGradient(angle=0, stops=[("#B8FF00", 0.0), ("#00CFFF", 1.0)]),
                position=(200, 100),
                align=("center", "middle"),
                effects=[Stroke(width=3, color="#000000")],
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/text_fill_with_stroke.png")

    def test_snapshot_text_fill_with_letter_spacing(self):
        """Snapshot test for gradient-filled text with letter spacing"""
        from quickthumb import Canvas, LinearGradient

        canvas = (
            Canvas(400, 200)
            .background(color="#111111")
            .text(
                "SPACED",
                size=60,
                fill=LinearGradient(angle=0, stops=[("#FF4500", 0.0), ("#FFD700", 1.0)]),
                letter_spacing=8,
                position=(200, 100),
                align=("center", "middle"),
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/text_fill_with_letter_spacing.png")

    def test_snapshot_multiline_text_with_fill(self):
        """Snapshot test for multiline text with a gradient fill spanning the full block"""
        from quickthumb import Canvas, LinearGradient

        canvas = (
            Canvas(400, 250)
            .background(color="#111111")
            .text(
                "TOP LINE\nBOTTOM LINE",
                size=52,
                fill=LinearGradient(angle=180, stops=[("#FF6B6B", 0.0), ("#4ECDC4", 1.0)]),
                position=(200, 125),
                align=("center", "middle"),
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/multiline_text_with_fill.png")

    def test_snapshot_rich_text_with_per_part_fill(self):
        """Snapshot test for rich text where individual TextParts have different fills"""
        from quickthumb import Canvas, LinearGradient, TextPart

        canvas = (
            Canvas(400, 200)
            .background(color="#111111")
            .text(
                content=[
                    TextPart(
                        text="HOT ",
                        fill=LinearGradient(angle=0, stops=[("#FF4500", 0.0), ("#FFD700", 1.0)]),
                        weight=900,
                    ),
                    TextPart(
                        text="COLD",
                        fill=LinearGradient(angle=0, stops=[("#00BFFF", 0.0), ("#8A2BE2", 1.0)]),
                        weight=900,
                    ),
                ],
                size=60,
                position=(200, 100),
                align=("center", "middle"),
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/rich_text_with_per_part_fill.png")

    def test_snapshot_grain_effect_on_background(self):
        """Snapshot test for Grain as a per-layer effect on a background layer"""
        from quickthumb import Canvas, Grain

        canvas = Canvas(200, 150).background(
            color="#2C3E50", effects=[Grain(intensity=0.2, monochrome=True, seed=42)]
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/grain_effect_on_background.png")


class TestWebfontCache:
    """Integration tests for webfont downloading and caching behaviour."""

    def test_should_cache_webfont_in_font_cache_dir(self, monkeypatch):
        """Font downloaded from URL is written into QUICKTHUMB_FONT_CACHE_DIR"""
        import hashlib
        from unittest.mock import MagicMock, patch

        from quickthumb import Canvas

        with open("assets/fonts/Roboto-Regular.ttf", "rb") as f:
            real_font_data = f.read()

        with tempfile.TemporaryDirectory() as cache_dir:
            # Given: QUICKTHUMB_FONT_CACHE_DIR points to an empty directory
            monkeypatch.setenv("QUICKTHUMB_FONT_CACHE_DIR", cache_dir)

            mock_response = MagicMock()
            mock_response.__enter__ = lambda s: s
            mock_response.__exit__ = MagicMock(return_value=False)
            mock_response.read.return_value = real_font_data

            canvas = (
                Canvas(200, 100)
                .background(color="#FFFFFF")
                .text("Hello", font="https://example.com/Roboto.ttf", size=24, color="#000000")
            )

            with tempfile.TemporaryDirectory() as out_dir:
                output_path = os.path.join(out_dir, "output.png")

                # When: rendering with a webfont URL
                with patch("quickthumb._fonts.urlopen", return_value=mock_response):
                    canvas.render(output_path)

            # Then: a cached font file is written to the specified cache directory
            url_hash = hashlib.md5(b"https://example.com/Roboto.ttf").hexdigest()
            cached_file = os.path.join(cache_dir, f"quickthumb_font_{url_hash}.ttf")
            assert os.path.exists(cached_file)

    def test_should_use_tmp_as_default_font_cache_dir(self, monkeypatch):
        """Font is cached in /tmp when QUICKTHUMB_FONT_CACHE_DIR is not set"""
        import hashlib
        from unittest.mock import MagicMock, patch

        from quickthumb import Canvas

        with open("assets/fonts/Roboto-Regular.ttf", "rb") as f:
            real_font_data = f.read()

        # Given: QUICKTHUMB_FONT_CACHE_DIR is not set
        monkeypatch.delenv("QUICKTHUMB_FONT_CACHE_DIR", raising=False)

        mock_response = MagicMock()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_response.read.return_value = real_font_data

        canvas = (
            Canvas(200, 100)
            .background(color="#FFFFFF")
            .text("Hello", font="https://example.com/RobotoDefault.ttf", size=24, color="#000000")
        )

        with tempfile.TemporaryDirectory() as out_dir:
            output_path = os.path.join(out_dir, "output.png")

            # When: rendering with a webfont URL
            with patch("quickthumb._fonts.urlopen", return_value=mock_response):
                canvas.render(output_path)

        # Then: the cached file is written under /tmp
        url_hash = hashlib.md5(b"https://example.com/RobotoDefault.ttf").hexdigest()
        cached_file = os.path.join(tempfile.gettempdir(), f"quickthumb_font_{url_hash}.ttf")
        assert os.path.exists(cached_file)

    def test_should_create_nested_font_cache_dir_if_not_exists(self, monkeypatch):
        """Font cache directory is created automatically if it does not exist"""
        from unittest.mock import MagicMock, patch

        from quickthumb import Canvas

        with open("assets/fonts/Roboto-Regular.ttf", "rb") as f:
            real_font_data = f.read()

        with tempfile.TemporaryDirectory() as base:
            new_cache_dir = os.path.join(base, "nested", "font_cache")

            # Given: the cache directory does not yet exist
            assert not os.path.exists(new_cache_dir)
            monkeypatch.setenv("QUICKTHUMB_FONT_CACHE_DIR", new_cache_dir)

            mock_response = MagicMock()
            mock_response.__enter__ = lambda s: s
            mock_response.__exit__ = MagicMock(return_value=False)
            mock_response.read.return_value = real_font_data

            canvas = (
                Canvas(200, 100)
                .background(color="#FFFFFF")
                .text("Hello", font="https://example.com/RobotoNested.ttf", size=24, color="#000000")
            )

            with tempfile.TemporaryDirectory() as out_dir:
                output_path = os.path.join(out_dir, "output.png")

                # When: rendering with a webfont URL
                with patch("quickthumb._fonts.urlopen", return_value=mock_response):
                    canvas.render(output_path)

            # Then: the nested cache directory is created and the font is written there
            assert os.path.exists(new_cache_dir)

    def test_should_raise_error_when_webfont_response_is_not_a_valid_font(self, monkeypatch):
        """Rendering raises RenderingError when a webfont URL returns non-font content"""
        from unittest.mock import MagicMock, patch

        from quickthumb import Canvas
        from quickthumb.errors import RenderingError

        with tempfile.TemporaryDirectory() as cache_dir:
            # Given: a webfont URL that returns HTML instead of a font
            monkeypatch.setenv("QUICKTHUMB_FONT_CACHE_DIR", cache_dir)

            mock_response = MagicMock()
            mock_response.__enter__ = lambda s: s
            mock_response.__exit__ = MagicMock(return_value=False)
            mock_response.read.return_value = b"<html><body>404 Not Found</body></html>"

            canvas = (
                Canvas(200, 100)
                .background(color="#FFFFFF")
                .text("Hello", font="https://example.com/notfont.ttf", size=24, color="#000000")
            )

            with tempfile.TemporaryDirectory() as out_dir:
                output_path = os.path.join(out_dir, "output.png")

                # When: rendering
                with patch("quickthumb._fonts.urlopen", return_value=mock_response):
                    # Then: a RenderingError is raised
                    with pytest.raises(RenderingError, match="not a valid font"):
                        canvas.render(output_path)

    def test_should_not_write_cache_file_when_webfont_response_is_invalid(self, monkeypatch):
        """No cache file is written when the downloaded content is not a valid font"""
        from unittest.mock import MagicMock, patch

        from quickthumb import Canvas
        from quickthumb.errors import RenderingError

        with tempfile.TemporaryDirectory() as cache_dir:
            # Given: a webfont URL that returns garbage bytes
            monkeypatch.setenv("QUICKTHUMB_FONT_CACHE_DIR", cache_dir)

            mock_response = MagicMock()
            mock_response.__enter__ = lambda s: s
            mock_response.__exit__ = MagicMock(return_value=False)
            mock_response.read.return_value = b"this is not a font"

            canvas = (
                Canvas(200, 100)
                .background(color="#FFFFFF")
                .text("Hello", font="https://example.com/garbage.ttf", size=24, color="#000000")
            )

            with tempfile.TemporaryDirectory() as out_dir:
                output_path = os.path.join(out_dir, "output.png")

                # When: rendering fails due to invalid font content
                with patch("quickthumb._fonts.urlopen", return_value=mock_response):
                    with pytest.raises(RenderingError):
                        canvas.render(output_path)

            # Then: no font file is left in the cache directory
            assert os.listdir(cache_dir) == []

    def test_should_redownload_webfont_when_cached_file_is_invalid(self, monkeypatch):
        """A stale invalid cache file is purged and the font is re-downloaded on next render"""
        import hashlib
        from unittest.mock import MagicMock, patch

        from quickthumb import Canvas

        with open("assets/fonts/Roboto-Regular.ttf", "rb") as f:
            real_font_data = f.read()

        with tempfile.TemporaryDirectory() as cache_dir:
            font_url = "https://example.com/RobotoStale.ttf"
            url_hash = hashlib.md5(font_url.encode()).hexdigest()
            stale_path = os.path.join(cache_dir, f"quickthumb_font_{url_hash}.ttf")

            # Given: a stale cache file with invalid content from a previous (pre-fix) run
            monkeypatch.setenv("QUICKTHUMB_FONT_CACHE_DIR", cache_dir)
            with open(stale_path, "wb") as f:
                f.write(b"<html>stale garbage</html>")

            mock_response = MagicMock()
            mock_response.__enter__ = lambda s: s
            mock_response.__exit__ = MagicMock(return_value=False)
            mock_response.read.return_value = real_font_data

            canvas = (
                Canvas(200, 100)
                .background(color="#FFFFFF")
                .text("Hello", font=font_url, size=24, color="#000000")
            )

            with tempfile.TemporaryDirectory() as out_dir:
                output_path = os.path.join(out_dir, "output.png")

                # When: rendering with the stale cache present
                with patch("quickthumb._fonts.urlopen", return_value=mock_response) as mock_open:
                    canvas.render(output_path)

                # Then: the font was re-downloaded and the cache file now contains valid data
                mock_open.assert_called_once()
            with open(stale_path, "rb") as f:
                assert f.read() == real_font_data


class TestShapePrimitiveRendering:
    """Snapshot tests for pill, triangle, star, and polygon shape primitives"""

    def test_snapshot_new_shape_primitives(self):
        """Snapshot test rendering all new shape primitives on one canvas"""
        from quickthumb import Canvas

        canvas = (
            Canvas(400, 300)
            .background(color="#1A1A2E")
            .shape(shape="pill", position=(20, 20), width=160, height=60, color="#E94560")
            .shape(shape="triangle", position=(220, 20), width=120, height=100, color="#0F3460")
            .shape(
                shape="star",
                position=(20, 120),
                width=140,
                height=140,
                color="#FFD700",
                star_points=5,
                inner_radius=0.5,
            )
            .shape(
                shape="polygon",
                position=(200, 140),
                width=160,
                height=100,
                color="#53BF9D",
                points=[
                    (0.0, 0.25),
                    (0.6, 0.25),
                    (0.6, 0.0),
                    (1.0, 0.5),
                    (0.6, 1.0),
                    (0.6, 0.75),
                    (0.0, 0.75),
                ],
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/shape_primitives.png")

    def test_snapshot_star_with_rotation_and_effects(self):
        """Snapshot test for a rotated star with stroke and shadow effects"""
        from quickthumb import Canvas
        from quickthumb.models import Shadow, Stroke

        canvas = (
            Canvas(300, 300)
            .background(color="#FFFFFF")
            .shape(
                shape="star",
                position=(150, 150),
                width=180,
                height=180,
                color="#FFD700",
                star_points=6,
                inner_radius=0.35,
                rotation=20,
                align=("center", "middle"),
                effects=[
                    Stroke(width=4, color="#B8860B"),
                    Shadow(offset_x=6, offset_y=6, color="#00000088", blur_radius=8),
                ],
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/star_rotated_effects.png")


class TestSvgLayerRendering:
    """Snapshot tests for svg layer rasterization"""

    def test_snapshot_svg_layer(self):
        """Snapshot test for an svg layer scaled and centered on the canvas"""
        pytest.importorskip("cairosvg")
        from quickthumb import Canvas

        fixture = os.path.join(os.path.dirname(__file__), "fixtures", "sample.svg")
        canvas = (
            Canvas(300, 200)
            .background(color="#F5F5F5")
            .svg(path=fixture, position=("50%", "50%"), width=120, align=("center", "middle"))
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)

            with open(output_path, "rb") as f:
                assert f.read() == external_file("snapshots/svg_layer.png")
