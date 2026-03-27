"""Tests for gradient / image-filled text (Feature 3)"""

import os
import tempfile

from quickthumb.models import LinearGradient, RadialGradient, TextFillImage, TextLayer, TextPart


class TestTextFillModels:
    """Model-level tests for TextFillImage and fill fields."""

    def test_text_fill_image_defaults(self):
        from quickthumb import FitMode

        fill = TextFillImage(path="texture.jpg")
        assert fill.type == "image"
        assert fill.path == "texture.jpg"
        assert fill.fit == FitMode.COVER

    def test_text_fill_image_custom_fit(self):
        from quickthumb import FitMode

        fill = TextFillImage(path="texture.jpg", fit="contain")
        assert fill.fit == FitMode.CONTAIN

    def test_text_layer_accepts_linear_gradient_fill(self):
        layer = TextLayer(
            type="text",
            content="GRADIENT",
            fill=LinearGradient(angle=90, stops=[("#FF0000", 0.0), ("#0000FF", 1.0)]),
        )
        assert layer.fill is not None
        assert isinstance(layer.fill, LinearGradient)
        assert layer.fill.angle == 90

    def test_text_layer_accepts_radial_gradient_fill(self):
        layer = TextLayer(
            type="text",
            content="RADIAL",
            fill=RadialGradient(stops=[("#FF0000", 0.0), ("#0000FF", 1.0)]),
        )
        assert isinstance(layer.fill, RadialGradient)

    def test_text_layer_accepts_image_fill(self):
        layer = TextLayer(
            type="text",
            content="IMAGE",
            fill=TextFillImage(path="fire.jpg"),
        )
        assert isinstance(layer.fill, TextFillImage)
        assert layer.fill.path == "fire.jpg"

    def test_text_layer_fill_defaults_to_none(self):
        layer = TextLayer(type="text", content="Plain")
        assert layer.fill is None

    def test_text_part_accepts_fill(self):
        part = TextPart(
            text="HOT",
            fill=LinearGradient(angle=45, stops=[("#FF4500", 0.0), ("#FFD700", 1.0)]),
        )
        assert isinstance(part.fill, LinearGradient)

    def test_text_part_fill_defaults_to_none(self):
        part = TextPart(text="Plain")
        assert part.fill is None

    def test_canvas_text_method_stores_fill(self):
        from quickthumb import Canvas

        fill = LinearGradient(angle=90, stops=[("#FF6B6B", 0.0), ("#4ECDC4", 1.0)])
        canvas = Canvas(400, 200).text(
            "GRADIENT", size=60, fill=fill, position=(200, 100), align="center"
        )

        assert len(canvas.layers) == 1
        layer = canvas.layers[0]
        assert isinstance(layer, TextLayer)
        assert layer.fill == fill

    def test_canvas_text_fill_and_color_coexist(self):
        """fill and color are independent fields; both can be set simultaneously."""
        from quickthumb import Canvas

        fill = LinearGradient(angle=90, stops=[("#FF0000", 0.0), ("#0000FF", 1.0)])
        canvas = Canvas(400, 200).text("TEXT", size=40, color="#FFFFFF", fill=fill, position=(0, 0))
        layer = canvas.layers[0]
        assert layer.color == "#FFFFFF"
        assert layer.fill == fill


class TestTextFillJsonSerialization:
    """JSON round-trip tests for fill."""

    def test_linear_gradient_fill_roundtrip(self):
        from quickthumb import Canvas

        fill = LinearGradient(angle=90, stops=[("#FF6B6B", 0.0), ("#4ECDC4", 1.0)])
        canvas = Canvas(400, 200).text(
            "GRADIENT", size=60, fill=fill, position=(200, 100), align="center"
        )

        json_str = canvas.to_json()
        canvas2 = Canvas.from_json(json_str)

        layer = canvas2.layers[0]
        assert isinstance(layer, TextLayer)
        assert isinstance(layer.fill, LinearGradient)
        assert layer.fill.angle == 90
        assert layer.fill.stops == [("#FF6B6B", 0.0), ("#4ECDC4", 1.0)]

    def test_radial_gradient_fill_roundtrip(self):
        from quickthumb import Canvas

        fill = RadialGradient(stops=[("#FFD700", 0.0), ("#FF000000", 1.0)])
        canvas = Canvas(400, 200).text(
            "RADIAL", size=60, fill=fill, position=(200, 100), align="center"
        )

        json_str = canvas.to_json()
        canvas2 = Canvas.from_json(json_str)

        layer = canvas2.layers[0]
        assert isinstance(layer.fill, RadialGradient)

    def test_image_fill_roundtrip(self):
        from quickthumb import Canvas

        fill = TextFillImage(path="fire.jpg", fit="cover")
        canvas = Canvas(400, 200).text(
            "FIRE", size=80, fill=fill, position=(200, 100), align="center"
        )

        json_str = canvas.to_json()
        canvas2 = Canvas.from_json(json_str)

        layer = canvas2.layers[0]
        assert isinstance(layer.fill, TextFillImage)
        assert layer.fill.path == "fire.jpg"

    def test_text_part_fill_roundtrip(self):
        from quickthumb import Canvas

        parts = [
            TextPart(
                text="HOT ",
                fill=LinearGradient(angle=45, stops=[("#FF4500", 0.0), ("#FFD700", 1.0)]),
            ),
            TextPart(text="COLD", color="#00BFFF"),
        ]
        canvas = Canvas(400, 200).text(parts, size=60, position=(200, 100), align="center")

        json_str = canvas.to_json()
        canvas2 = Canvas.from_json(json_str)

        layer = canvas2.layers[0]
        assert isinstance(layer, TextLayer)
        assert isinstance(layer.content, list)
        assert isinstance(layer.content[0].fill, LinearGradient)
        assert layer.content[1].fill is None


class TestTextFillRendering:
    """Rendering tests — verify that fill produces a valid image without errors."""

    def test_render_simple_text_with_linear_gradient_fill(self):
        from quickthumb import Canvas

        canvas = (
            Canvas(400, 200)
            .background(color="#FFFFFF")
            .text(
                "GRADIENT",
                size=60,
                fill=LinearGradient(angle=90, stops=[("#FF6B6B", 0.0), ("#4ECDC4", 1.0)]),
                position=(200, 100),
                align="center",
            )
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, "out.png")
            canvas.render(out)
            assert os.path.exists(out)
            assert os.path.getsize(out) > 0

    def test_render_simple_text_with_radial_gradient_fill(self):
        from quickthumb import Canvas

        canvas = (
            Canvas(400, 200)
            .background(color="#111111")
            .text(
                "RADIAL",
                size=60,
                fill=RadialGradient(stops=[("#FFD700", 0.0), ("#FF000000", 1.0)]),
                position=(200, 100),
                align="center",
            )
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, "out.png")
            canvas.render(out)
            assert os.path.exists(out)

    def test_render_multiline_text_with_fill(self):
        from quickthumb import Canvas

        canvas = (
            Canvas(400, 300)
            .background(color="#FFFFFF")
            .text(
                "LINE ONE\nLINE TWO",
                size=48,
                fill=LinearGradient(angle=90, stops=[("#FF0000", 0.0), ("#0000FF", 1.0)]),
                position=(200, 150),
                align="center",
            )
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, "out.png")
            canvas.render(out)
            assert os.path.exists(out)

    def test_render_text_with_fill_and_stroke(self):
        from quickthumb import Canvas, Stroke

        canvas = (
            Canvas(400, 200)
            .background(color="#FFFFFF")
            .text(
                "STROKED",
                size=60,
                fill=LinearGradient(angle=0, stops=[("#FF0000", 0.0), ("#0000FF", 1.0)]),
                effects=[Stroke(width=3, color="#000000")],
                position=(200, 100),
                align="center",
            )
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, "out.png")
            canvas.render(out)
            assert os.path.exists(out)

    def test_render_text_with_fill_and_shadow(self):
        from quickthumb import Canvas, Shadow

        canvas = (
            Canvas(400, 200)
            .background(color="#FFFFFF")
            .text(
                "SHADOW",
                size=60,
                fill=RadialGradient(stops=[("#FFD700", 0.0), ("#FF8C00", 1.0)]),
                effects=[Shadow(offset_x=4, offset_y=4, color="#00000080", blur_radius=4)],
                position=(200, 100),
                align="center",
            )
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, "out.png")
            canvas.render(out)
            assert os.path.exists(out)

    def test_render_text_with_letter_spacing_and_fill(self):
        from quickthumb import Canvas

        canvas = (
            Canvas(500, 200)
            .background(color="#FFFFFF")
            .text(
                "SPACED",
                size=50,
                fill=LinearGradient(angle=0, stops=[("#00FF00", 0.0), ("#0000FF", 1.0)]),
                letter_spacing=8,
                position=(250, 100),
                align="center",
            )
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, "out.png")
            canvas.render(out)
            assert os.path.exists(out)

    def test_render_rich_text_with_layer_fill(self):
        """Layer-level fill applied to all parts."""
        from quickthumb import Canvas

        parts = [
            TextPart(text="HOT ", weight=900),
            TextPart(text="COLD", weight=900),
        ]
        canvas = (
            Canvas(500, 200)
            .background(color="#111111")
            .text(
                parts,
                size=60,
                fill=LinearGradient(angle=90, stops=[("#FF6B6B", 0.0), ("#4ECDC4", 1.0)]),
                position=(250, 100),
                align="center",
            )
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, "out.png")
            canvas.render(out)
            assert os.path.exists(out)

    def test_render_rich_text_with_per_part_fill(self):
        """Per-part fill overrides layer-level fill for that segment."""
        from quickthumb import Canvas

        parts = [
            TextPart(
                text="HOT ",
                fill=LinearGradient(angle=45, stops=[("#FF4500", 0.0), ("#FFD700", 1.0)]),
                weight=900,
            ),
            TextPart(
                text="COLD",
                fill=LinearGradient(angle=45, stops=[("#00BFFF", 0.0), ("#8A2BE2", 1.0)]),
                weight=900,
            ),
        ]
        canvas = (
            Canvas(500, 200)
            .background(color="#111111")
            .text(parts, size=60, position=(250, 100), align="center")
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, "out.png")
            canvas.render(out)
            assert os.path.exists(out)

    def test_render_text_with_fill_wrapped(self):
        """Fill applied to wrapped (max_width) text block."""
        from quickthumb import Canvas

        canvas = (
            Canvas(400, 300)
            .background(color="#FFFFFF")
            .text(
                "Gradient filled text that wraps nicely",
                size=32,
                fill=LinearGradient(angle=90, stops=[("#FF0000", 0.0), ("#0000FF", 1.0)]),
                max_width=320,
                position=(200, 150),
                align="center",
            )
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, "out.png")
            canvas.render(out)
            assert os.path.exists(out)

    def test_render_rotated_text_with_fill(self):
        from quickthumb import Canvas

        canvas = (
            Canvas(400, 400)
            .background(color="#FFFFFF")
            .text(
                "ROTATED",
                size=50,
                fill=LinearGradient(angle=0, stops=[("#FF0000", 0.0), ("#0000FF", 1.0)]),
                rotation=45,
                position=(200, 200),
                align="center",
            )
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, "out.png")
            canvas.render(out)
            assert os.path.exists(out)

    def test_render_text_with_image_fill(self):
        import pathlib

        fixture = str(pathlib.Path(__file__).parent / "fixtures" / "sample_image.jpg")
        from quickthumb import Canvas

        canvas = (
            Canvas(400, 200)
            .background(color="#000000")
            .text(
                "TEXTURE",
                size=60,
                fill=TextFillImage(path=fixture, fit="cover"),
                position=(200, 100),
                align="center",
            )
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, "out.png")
            canvas.render(out)
            assert os.path.exists(out)
            assert os.path.getsize(out) > 0

    def test_render_text_with_per_part_letter_spacing_and_fill(self):
        """letter_spacing on a TextPart with fill should not be silently dropped."""
        from quickthumb import Canvas

        parts = [
            TextPart(
                text="HOT",
                fill=LinearGradient(angle=0, stops=[("#FF4500", 0.0), ("#FFD700", 1.0)]),
                letter_spacing=6,
            ),
        ]
        canvas = (
            Canvas(500, 200)
            .background(color="#111111")
            .text(parts, size=60, position=(250, 100), align="center")
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, "out.png")
            canvas.render(out)
            assert os.path.exists(out)

    def test_part_fill_overrides_layer_fill(self):
        """part.fill takes precedence over layer.fill for that segment."""
        from quickthumb import Canvas

        layer_fill = LinearGradient(angle=0, stops=[("#FF0000", 0.0), ("#FF0000", 1.0)])
        part_fill = LinearGradient(angle=0, stops=[("#0000FF", 0.0), ("#0000FF", 1.0)])

        parts = [
            TextPart(text="BLUE ", fill=part_fill),
            TextPart(text="RED"),
        ]
        canvas = Canvas(500, 200).text(
            parts, size=60, fill=layer_fill, position=(250, 100), align="center"
        )

        # Verify model-level resolution
        from quickthumb.canvas import Canvas as CanvasImpl

        c = CanvasImpl(500, 200)
        layer = canvas.layers[0]
        assert isinstance(layer, TextLayer)
        resolved_part0 = c._resolve_fill(layer.content[0], layer)  # type: ignore[arg-type]
        resolved_part1 = c._resolve_fill(layer.content[1], layer)  # type: ignore[arg-type]
        assert resolved_part0 == part_fill
        assert resolved_part1 == layer_fill
