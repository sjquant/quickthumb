"""Tests for SVG layer functionality"""

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import cast

import pytest
from inline_snapshot import snapshot
from PIL import Image
from quickthumb.errors import RenderingError, ValidationError
from quickthumb.models import Align, BlendMode, SvgLayer

from tests._optional import require_cairosvg

FIXTURE_SVG = str(Path(__file__).parent / "fixtures" / "sample.svg")


class TestCanvasSvgAPI:
    """Test suite for Canvas.svg() builder method"""

    def test_should_add_svg_layer_and_support_method_chaining(self):
        """Canvas.svg() stores all optional parameters on the layer and returns self for chaining"""
        from quickthumb import Canvas
        from quickthumb.models import Filter, SvgLayer

        # given
        canvas = Canvas(400, 300)

        # when: every optional parameter is provided
        result = canvas.svg(
            path=FIXTURE_SVG,
            position=(20, 30),
            width=100,
            height=80,
            opacity=0.8,
            rotation=15,
            align=("center", "middle"),
            effects=[Filter(brightness=1.2)],
            blend_mode="multiply",
        )

        # then: the full layer state is captured
        assert result is canvas
        assert len(canvas.layers) == 1
        assert canvas.layers[0] == snapshot(
            SvgLayer(
                type="svg",
                path=FIXTURE_SVG,
                position=(20, 30),
                width=100,
                height=80,
                opacity=0.8,
                rotation=15.0,
                align=Align.CENTER,
                blend_mode=BlendMode.MULTIPLY,
                effects=[Filter(brightness=1.2)],
            )
        )

    @pytest.mark.parametrize(
        "kwargs,error_pattern",
        [
            ({"width": -10}, "width"),
            ({"height": 0}, "height"),
            ({"opacity": 1.5}, "opacity"),
            ({"position": (100,)}, "position"),
        ],
    )
    def test_should_reject_invalid_svg_parameters(self, kwargs, error_pattern):
        """Invalid svg layer parameters raise ValidationError"""
        from quickthumb import Canvas

        params = {"path": FIXTURE_SVG, "position": (0, 0)}
        params.update(kwargs)

        with pytest.raises(ValidationError, match=error_pattern):
            Canvas(400, 300).svg(
                path=cast(str, params["path"]),
                position=cast(tuple[int, int], params["position"]),
                width=cast(int | None, params.get("width")),
                height=cast(int | None, params.get("height")),
                opacity=cast(float, params.get("opacity", 1.0)),
            )


class TestSvgLayerSerialization:
    """Test suite for JSON round-trip of svg layers"""

    def test_should_round_trip_svg_layer_through_json(self):
        """svg layers serialize with type discriminator and deserialize unchanged"""
        from quickthumb import Canvas

        # given
        canvas = Canvas(400, 300).svg(
            path=FIXTURE_SVG, position=("50%", "50%"), width=120, align=("center", "middle")
        )

        # when
        data = json.loads(canvas.to_json())
        restored = Canvas.from_json(canvas.to_json())

        # then
        assert data["layers"][0]["type"] == "svg"
        layer = cast(SvgLayer, restored.layers[0])
        assert layer.path == FIXTURE_SVG
        assert layer.width == 120
        assert layer.position == ("50%", "50%")
        assert layer.align == Align.CENTER


class TestSvgRendering:
    """Behavioral tests for svg rasterization (snapshots live in test_rendering.py)"""

    def test_should_rasterize_svg_onto_canvas(self):
        """An svg layer renders visible, correctly sized content onto the canvas"""
        require_cairosvg()
        from quickthumb import Canvas

        # given: a white canvas with the fixture svg placed at top-left, 50px wide
        canvas = (
            Canvas(100, 100)
            .background(color="#FFFFFF")
            .svg(path=FIXTURE_SVG, position=(0, 0), width=50)
        )

        # when
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "out.png")
            canvas.render(output_path)
            img = Image.open(output_path).convert("RGBA")

        # then: the svg body fills its 50px box (rect spans ~2.5..47.5px) and nothing outside it
        assert img.getpixel((25, 25)) != (255, 255, 255, 255)
        assert img.getpixel((45, 25)) != (255, 255, 255, 255)
        assert img.getpixel((55, 25)) == (255, 255, 255, 255)
        assert img.getpixel((75, 75)) == (255, 255, 255, 255)

    def test_should_rasterize_group_svg_child_once_per_render(self, monkeypatch, tmp_path):
        """An auto-sized svg group child is rasterized once per render pass, and still drawn"""
        cairosvg = require_cairosvg()
        from quickthumb import Canvas

        # given: cairosvg call counting at the library boundary
        calls = []
        original_svg2png = cairosvg.svg2png

        def counting_svg2png(*args, **kwargs):
            calls.append(kwargs)
            return original_svg2png(*args, **kwargs)

        monkeypatch.setattr(cairosvg, "svg2png", counting_svg2png)

        # given: a group whose svg child needs rasterization to be measured (height omitted)
        canvas = (
            Canvas(200, 200)
            .background(color="#FFFFFF")
            .group(
                children=[{"type": "svg", "path": FIXTURE_SVG, "width": 50}],
                position=(0, 0),
            )
        )

        # when
        output_path = str(tmp_path / "out.png")
        canvas.render(output_path)

        # then: a single rasterization that actually reaches the canvas
        assert len(calls) == 1
        img = Image.open(output_path).convert("RGBA")
        assert img.getpixel((25, 25)) != (255, 255, 255, 255)

        # when: rendering again — the cache must not outlive a render pass (stale-file risk)
        canvas.render(output_path)

        # then
        assert len(calls) == 2

    def test_should_pick_up_svg_file_changes_between_exports(self, tmp_path):
        """to_base64 re-rasterizes per render pass instead of serving a stale cached raster"""
        require_cairosvg()
        from quickthumb import Canvas

        # given: a canvas rendering a mutable svg file
        svg_path = tmp_path / "art.svg"
        svg_path.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40">'
            '<rect width="40" height="40" fill="red"/></svg>'
        )
        canvas = (
            Canvas(100, 100)
            .background(color="#FFFFFF")
            .svg(path=str(svg_path), position=(0, 0), width=50)
        )

        # when: exporting, changing the file on disk, and exporting again
        first = canvas.to_base64()
        svg_path.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40">'
            '<rect width="40" height="40" fill="blue"/></svg>'
        )
        second = canvas.to_base64()

        # then: the second export reflects the new artwork
        assert first != second

    def test_should_raise_for_missing_svg_file(self, tmp_path):
        """Rendering a canvas referencing a missing local svg path raises FileNotFoundError"""
        from quickthumb import Canvas

        canvas = Canvas(100, 100).svg(path="no/such/file.svg", position=(0, 0), width=50)

        with pytest.raises(FileNotFoundError, match="no/such/file.svg"):
            canvas.render(str(tmp_path / "out.png"))

    def test_should_raise_helpful_error_when_cairosvg_missing(self, monkeypatch):
        """Rendering an svg layer without cairosvg raises RenderingError with install hint"""
        from quickthumb import Canvas

        # given: cairosvg cannot be imported
        monkeypatch.setitem(sys.modules, "cairosvg", None)
        canvas = Canvas(100, 100).svg(path=FIXTURE_SVG, position=(0, 0), width=50)

        # when / then
        with (
            tempfile.TemporaryDirectory() as tmpdir,
            pytest.raises(RenderingError, match="quickthumb\\[svg\\]"),
        ):
            canvas.render(os.path.join(tmpdir, "out.png"))
