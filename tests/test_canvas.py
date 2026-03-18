"""Tests for Canvas functionality"""

import json

import pytest
from inline_snapshot import snapshot


class TestCanvas:
    """Test suite for Canvas operations"""

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

    def test_should_serialize_multiple_layers_in_order(self):
        """Test that multiple layers serialize in correct order"""
        # Given: Canvas with multiple background and text layers
        from quickthumb import Canvas, LinearGradient

        gradient = LinearGradient(angle=90, stops=[("#FF0000", 0.0), ("#0000FF", 1.0)])
        canvas = (
            Canvas(1920, 1080)
            .background(color="#2c3e50")
            .background(gradient=gradient, opacity=0.5)
            .text("Title", size=84, color="#FFFFFF")
            .text("Subtitle", size=48, color="#EEEEEE")
        )

        # When: User exports to JSON
        canvas_dict = json.loads(canvas.to_json())

        # Then: All layers should be serialized in correct order
        assert canvas_dict == snapshot(
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
                        "effects": [],
                    },
                    {
                        "type": "background",
                        "color": None,
                        "gradient": {
                            "type": "linear",
                            "angle": 90.0,
                            "stops": [["#FF0000", 0.0], ["#0000FF", 1.0]],
                        },
                        "image": None,
                        "opacity": 0.5,
                        "blend_mode": None,
                        "fit": None,
                        "effects": [],
                    },
                    {
                        "type": "text",
                        "content": "Title",
                        "font": None,
                        "size": 84,
                        "color": "#FFFFFF",
                        "position": None,
                        "align": None,
                        "bold": False,
                        "italic": False,
                        "weight": None,
                        "max_width": None,
                        "effects": [],
                        "line_height": None,
                        "letter_spacing": None,
                        "auto_scale": False,
                        "rotation": 0.0,
                        "opacity": 1.0,
                    },
                    {
                        "type": "text",
                        "content": "Subtitle",
                        "font": None,
                        "size": 48,
                        "color": "#EEEEEE",
                        "position": None,
                        "align": None,
                        "bold": False,
                        "italic": False,
                        "weight": None,
                        "max_width": None,
                        "effects": [],
                        "line_height": None,
                        "letter_spacing": None,
                        "auto_scale": False,
                        "rotation": 0.0,
                        "opacity": 1.0,
                    },
                ],
            }
        )

    def test_should_recreate_canvas_from_json(self):
        """Test that Canvas can be recreated from JSON"""
        # Given: Canvas with multiple background and text layers
        from quickthumb import Canvas, LinearGradient

        gradient = LinearGradient(angle=90, stops=[("#FF0000", 0.0), ("#0000FF", 1.0)])
        canvas = (
            Canvas(1920, 1080)
            .background(color="#2c3e50")
            .background(gradient=gradient, opacity=0.5)
            .text("Title", size=84, color="#FFFFFF")
            .text("Subtitle", size=48, color="#EEEEEE")
        )
        json_str = canvas.to_json()
        recreated = Canvas.from_json(json_str)
        assert recreated.to_json() == json_str

    @pytest.mark.parametrize(
        "json_str, match",
        [
            (
                '{"width": 1920, "height": 1080, "layers": "INVALID"}',
                "layers.*",
            ),
            (
                json.dumps(
                    {
                        "width": 100,
                        "height": 100,
                        "layers": [{"type": "custom", "name": "no_such_fn_xyz"}],
                    }
                ),
                "no_such_fn_xyz",
            ),
        ],
    )
    def test_should_raise_error_for_invalid_json(self, json_str, match):
        """Canvas.from_json raises ValidationError for malformed or unresolvable JSON"""
        from quickthumb import Canvas, ValidationError

        with pytest.raises(ValidationError, match=match):
            Canvas.from_json(json_str)

    def test_should_base64_match_rendered_file(self):
        """Test that to_base64 output is identical to base64-encoding the rendered file"""
        import base64
        import os
        import tempfile

        from quickthumb import Canvas

        canvas = Canvas(100, 100).background(color="#FF0000")
        result = canvas.to_base64()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path)
            with open(output_path, "rb") as f:
                assert result == base64.b64encode(f.read()).decode("utf-8")

    @pytest.mark.parametrize(
        "fmt, prefix",
        [
            ("PNG", "data:image/png;base64,"),
            ("JPEG", "data:image/jpeg;base64,"),
            ("WEBP", "data:image/webp;base64,"),
        ],
    )
    def test_should_prefix_data_url_with_correct_mime_type(self, fmt, prefix):
        """Test that to_data_url returns the correct MIME type prefix for each format"""
        from quickthumb import Canvas

        canvas = Canvas(100, 100).background(color="#FF0000")
        assert canvas.to_data_url(format=fmt).startswith(prefix)

    def test_should_raise_error_for_quality_with_png_in_to_base64(self):
        """Test that to_base64 raises error when quality is used with PNG format"""
        # Given: A simple canvas
        from quickthumb import Canvas
        from quickthumb.errors import RenderingError

        canvas = Canvas(100, 100).background(color="#FF0000")

        # When: User calls to_base64 with quality parameter for PNG
        # Then: Should raise RenderingError
        with pytest.raises(
            RenderingError, match="Quality parameter is only supported for JPEG and WEBP"
        ):
            canvas.to_base64(format="PNG", quality=80)

    def test_render_with_explicit_format_overrides_extension(self):
        """Test that render() format param overrides extension-based format detection"""
        import os
        import tempfile

        from PIL import Image
        from quickthumb import Canvas

        canvas = Canvas(100, 100).background(color="#FF0000")

        with tempfile.TemporaryDirectory() as tmpdir:
            # .png extension but explicit JPEG format — JPEG should win
            output_path = os.path.join(tmpdir, "output.png")
            canvas.render(output_path, format="JPEG")

            img = Image.open(output_path)
            assert img.format == "JPEG"

    def test_should_reject_serializing_unnamed_custom_layer(self):
        """to_json() raises ValidationError for unnamed custom layers"""
        from quickthumb import Canvas, ValidationError

        canvas = Canvas(100, 100).background(color="#FFFFFF").custom(lambda image: image)

        with pytest.raises(ValidationError, match="Custom layers cannot be serialized"):
            canvas.to_json()

    def test_should_reject_serializing_custom_layer_with_non_serializable_kwargs(self):
        """to_json() raises ValidationError when custom layer kwargs are not JSON-serializable"""
        from quickthumb import Canvas, ValidationError

        canvas = (
            Canvas(100, 100)
            .background(color="#FFFFFF")
            .custom(lambda image: image, name="fn", kwargs={"obj": object()})
        )

        with pytest.raises(ValidationError, match="kwargs.*not JSON-serializable"):
            canvas.to_json()

    def test_should_round_trip_named_custom_layer(self):
        """Named custom layers serialize to JSON and deserialize back via the registry"""
        import os
        import tempfile

        from inline_snapshot import snapshot
        from PIL import Image
        from quickthumb import Canvas

        calls: list[dict] = []

        def draw_dot(image: Image.Image, *, color: str = "red", size: int = 10) -> None:
            calls.append({"color": color, "size": size})

        Canvas.register_layer_fn("draw_dot", draw_dot)
        try:
            canvas = (
                Canvas(100, 100)
                .background(color="#FFFFFF")
                .custom(draw_dot, name="draw_dot")
                .custom(draw_dot, name="draw_dot", kwargs={"color": "blue", "size": 20})
            )

            json_str = canvas.to_json()
            assert json.loads(json_str) == snapshot(
                {
                    "width": 100,
                    "height": 100,
                    "layers": [
                        {
                            "type": "background",
                            "color": "#FFFFFF",
                            "gradient": None,
                            "image": None,
                            "opacity": 1.0,
                            "blend_mode": None,
                            "fit": None,
                            "effects": [],
                        },
                        {"type": "custom", "name": "draw_dot", "kwargs": {}},
                        {
                            "type": "custom",
                            "name": "draw_dot",
                            "kwargs": {"color": "blue", "size": 20},
                        },
                    ],
                }
            )

            recreated = Canvas.from_json(json_str)
            with tempfile.TemporaryDirectory() as tmpdir:
                recreated.render(os.path.join(tmpdir, "out.png"))
            assert calls == [{"color": "red", "size": 10}, {"color": "blue", "size": 20}]
        finally:
            Canvas.unregister_layer_fn("draw_dot")

    def test_should_raise_error_deserializing_unregistered_custom_layer(self):
        """Deserializing a custom layer whose name is not in the registry raises ValidationError"""
        from quickthumb import Canvas, ValidationError

        json_str = json.dumps(
            {
                "width": 100,
                "height": 100,
                "layers": [{"type": "custom", "name": "no_such_fn_xyz"}],
            }
        )
        with pytest.raises(ValidationError, match="no_such_fn_xyz"):
            Canvas.from_json(json_str)

    def test_should_raise_rendering_error_when_custom_callback_fails(self):
        """Exceptions inside custom callback should be wrapped as RenderingError"""
        import os
        import tempfile

        from quickthumb import Canvas
        from quickthumb.errors import RenderingError

        def bad_custom(_image):
            raise RuntimeError("boom")

        canvas = Canvas(100, 100).background(color="#FFFFFF").custom(bad_custom)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            with pytest.raises(RenderingError, match="Custom layer callback failed: boom"):
                canvas.render(output_path)

    def test_should_raise_error_when_custom_callback_returns_non_image(self):
        """custom callback should return PIL.Image.Image or None"""
        import os
        import tempfile

        from quickthumb import Canvas
        from quickthumb.errors import RenderingError

        canvas = Canvas(100, 100).background(color="#FFFFFF").custom(lambda _image: "not-image")

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            with pytest.raises(
                RenderingError, match="Custom layer callback must return PIL.Image.Image or None"
            ):
                canvas.render(output_path)

    def test_should_use_font_cache_dir_env_var_when_downloading_font(self, monkeypatch):
        """_download_and_cache_font uses QUICKTHUMB_FONT_CACHE_DIR when set"""
        import os
        import tempfile
        from unittest.mock import MagicMock, patch

        from quickthumb import Canvas

        canvas = Canvas(100, 100)

        with tempfile.TemporaryDirectory() as tmpdir:
            monkeypatch.setenv("QUICKTHUMB_FONT_CACHE_DIR", tmpdir)

            fake_font_data = b"fake font data"
            mock_response = MagicMock()
            mock_response.__enter__ = lambda s: s
            mock_response.__exit__ = MagicMock(return_value=False)
            mock_response.read.return_value = fake_font_data

            with patch("quickthumb.canvas.urlopen", return_value=mock_response):
                result = canvas._download_and_cache_font("https://example.com/font.ttf")

            assert result.startswith(tmpdir)
            assert os.path.exists(result)

    def test_should_default_to_tmp_when_font_cache_dir_not_set(self, monkeypatch):
        """_download_and_cache_font defaults to /tmp when QUICKTHUMB_FONT_CACHE_DIR is unset"""
        from unittest.mock import MagicMock, patch

        from quickthumb import Canvas

        canvas = Canvas(100, 100)
        monkeypatch.delenv("QUICKTHUMB_FONT_CACHE_DIR", raising=False)

        fake_font_data = b"fake font data"
        mock_response = MagicMock()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_response.read.return_value = fake_font_data

        with patch("quickthumb.canvas.urlopen", return_value=mock_response):
            result = canvas._download_and_cache_font("https://example.com/font2.ttf")

        assert result.startswith("/tmp")

    def test_should_create_font_cache_dir_if_not_exists(self, monkeypatch):
        """_download_and_cache_font creates QUICKTHUMB_FONT_CACHE_DIR if it does not exist"""
        import os
        import tempfile
        from unittest.mock import MagicMock, patch

        from quickthumb import Canvas

        canvas = Canvas(100, 100)

        with tempfile.TemporaryDirectory() as base:
            new_dir = os.path.join(base, "nested", "cache")
            monkeypatch.setenv("QUICKTHUMB_FONT_CACHE_DIR", new_dir)

            fake_font_data = b"fake font data"
            mock_response = MagicMock()
            mock_response.__enter__ = lambda s: s
            mock_response.__exit__ = MagicMock(return_value=False)
            mock_response.read.return_value = fake_font_data

            # Given: cache dir does not exist yet
            assert not os.path.exists(new_dir)

            # When: downloading a font
            with patch("quickthumb.canvas.urlopen", return_value=mock_response):
                result = canvas._download_and_cache_font("https://example.com/font3.ttf")

            # Then: the directory is created and the font is written there
            assert os.path.exists(new_dir)
            assert result.startswith(new_dir)

    def test_should_raise_error_when_custom_callback_returns_different_size(self):
        """custom callback should preserve canvas dimensions when returning an image"""
        import os
        import tempfile

        from PIL import Image
        from quickthumb import Canvas
        from quickthumb.errors import RenderingError

        canvas = (
            Canvas(100, 100)
            .background(color="#FFFFFF")
            .custom(lambda _image: Image.new("RGBA", (10, 10), (0, 0, 0, 0)))
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output.png")
            with pytest.raises(
                RenderingError,
                match="Custom layer callback returned an image with different size",
            ):
                canvas.render(output_path)
