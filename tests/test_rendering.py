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
