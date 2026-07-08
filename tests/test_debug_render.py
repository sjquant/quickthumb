"""Black-box tests for annotated debug raster rendering."""

import pytest
from inline_snapshot import external_file
from PIL import Image


class TestDebugRender:
    """Test suite for render(debug=True) output."""

    def test_snapshot_debug_render_overlay(self, tmp_path):
        """Debug rendering visually matches the expected annotated overlay."""
        from quickthumb import Canvas

        # given: a deterministic canvas with top-level and nested visible layer bboxes
        fixture = tmp_path / "sample.png"
        Image.new("RGBA", (28, 22), (24, 120, 210, 255)).save(fixture)
        canvas = (
            Canvas(240, 150)
            .background(color="#F7F4EE")
            .shape(
                shape="rectangle",
                position=(18, 20),
                width=62,
                height=42,
                color="#1D4ED8",
                border_radius=6,
            )
            .text(
                "Debug",
                size=30,
                color="#111827",
                position=(104, 24),
            )
            .image(path=str(fixture), position=(188, 24), width=28, height=22)
            .group(
                children=[
                    {
                        "type": "shape",
                        "shape": "ellipse",
                        "width": 34,
                        "height": 28,
                        "color": "#F97316",
                    },
                    {
                        "type": "text",
                        "content": "G",
                        "size": 24,
                        "color": "#0F172A",
                    },
                ],
                direction="row",
                gap=12,
                position=(24, 92),
            )
        )

        # when: rendering with debug annotations enabled
        output_path = tmp_path / "debug.png"
        canvas.render(str(output_path), debug=True)

        # then: the raster output matches the visual debug-overlay baseline
        assert output_path.read_bytes() == external_file("snapshots/debug_render_overlay.png")

    def test_should_reject_debug_render_for_document_output(self, tmp_path):
        """debug=True raises a rendering error for document output formats."""
        from quickthumb import Canvas
        from quickthumb.errors import RenderingError

        # given: a canvas rendered to a document extension
        canvas = Canvas(100, 100).background(color="#FFFFFF")

        # when: rendering with debug annotations to SVG
        # then: debug annotations are rejected because they are raster-only
        with pytest.raises(RenderingError, match="Debug render is only supported"):
            canvas.render(str(tmp_path / "output.svg"), debug=True)

    def test_should_render_deterministic_debug_overlay_for_text_shape_and_image(self, tmp_path):
        """Debug rendering overlays stable bboxes for text, shape, and image layers."""
        from quickthumb import Canvas

        # given: a canvas with visible text, shape, image, and invisible shape layers
        fixture = tmp_path / "sample.png"
        Image.new("RGBA", (20, 20), (16, 144, 96, 255)).save(fixture)
        canvas = (
            Canvas(180, 120)
            .background(color="#FFFFFF")
            .shape(shape="rectangle", position=(10, 20), width=40, height=30, color="#E8E8E8")
            .text("A", size=24, color="#111111", position=(78, 28))
            .image(path=str(fixture), position=(130, 45), width=20, height=20)
            .shape(
                shape="rectangle",
                position=(5, 5),
                width=12,
                height=12,
                color="#000000",
                opacity=0,
            )
        )
        report = canvas.inspect()

        # when: rendering normally and with debug annotations
        normal_path = tmp_path / "normal.png"
        debug_path = tmp_path / "debug.png"
        repeated_path = tmp_path / "debug-repeated.png"
        canvas.render(str(normal_path))
        canvas.render(str(debug_path), debug=True)
        canvas.render(str(repeated_path), debug=True)

        # then: debug output is deterministic and annotates only visible rendered boxes
        assert debug_path.read_bytes() == repeated_path.read_bytes()
        assert debug_path.read_bytes() != normal_path.read_bytes()

        normal = Image.open(normal_path).convert("RGBA")
        debug = Image.open(debug_path).convert("RGBA")
        for layer in report.layers[1:4]:
            box = layer.bbox
            point = (box.x + box.width - 1, box.y + box.height - 1)
            assert debug.getpixel(point) != normal.getpixel(point)

        invisible_box = report.layers[4].bbox
        invisible_point = (invisible_box.x + invisible_box.width - 1, invisible_box.y)
        assert debug.getpixel(invisible_point) == normal.getpixel(invisible_point)

    def test_should_render_debug_overlay_for_group_and_child_bboxes(self, tmp_path):
        """Debug rendering overlays group bboxes and nested child bboxes."""
        from quickthumb import Canvas

        # given: a group with text and shape children whose bboxes are inspectable
        canvas = Canvas(220, 150).group(
            children=[
                {"type": "text", "content": "Wide label", "size": 24, "color": "#111111"},
                {
                    "type": "shape",
                    "shape": "rectangle",
                    "width": 25,
                    "height": 18,
                    "color": "#DDDDDD",
                },
            ],
            position=(20, 20),
            gap=10,
        )
        group = canvas.inspect().layers[0]

        # when: rendering the group normally and with debug annotations
        normal_path = tmp_path / "group-normal.png"
        debug_path = tmp_path / "group-debug.png"
        canvas.render(str(normal_path))
        canvas.render(str(debug_path), debug=True)

        # then: the group union bbox and nested child bbox both receive overlays
        normal = Image.open(normal_path).convert("RGBA")
        debug = Image.open(debug_path).convert("RGBA")
        group_box = group.bbox
        group_point = (group_box.x + group_box.width - 1, group_box.y + group_box.height - 1)
        assert debug.getpixel(group_point) != normal.getpixel(group_point)

        child_box = group.children[1].bbox
        child_point = (child_box.x + child_box.width - 1, child_box.y)
        assert debug.getpixel(child_point) != normal.getpixel(child_point)

    def test_should_reuse_rendered_remote_image_size_for_debug_measurement(
        self, tmp_path, monkeypatch
    ):
        """Debug rendering does not fetch an unsized remote image twice."""
        from quickthumb import Canvas
        from quickthumb._images import ImageEngine

        # given: a remote image layer without explicit dimensions
        loads = 0
        source = Image.new("RGBA", (12, 8), (16, 144, 96, 255))

        def fake_load_image_from_url(self, url):
            nonlocal loads
            loads += 1
            return source.copy()

        monkeypatch.setattr(ImageEngine, "load_image_from_url", fake_load_image_from_url)
        canvas = Canvas(60, 40).image("https://example.invalid/thumb.png", position=(4, 6))

        # when: rendering with debug annotations
        canvas.render(str(tmp_path / "debug.png"), debug=True)

        # then: the already-rendered image size is reused by debug measurement
        assert loads == 1
