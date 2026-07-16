"""Black-box tests for annotated debug raster rendering."""

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image, ImageChops, ImageStat


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

        # then: the raster output visually matches the debug-overlay baseline
        actual = Image.open(output_path).convert("RGBA")
        snapshot_path = Path(__file__).parent / "snapshots" / "debug_render_overlay.png"
        expected = Image.open(snapshot_path).convert("RGBA")
        diff = ImageChops.difference(actual, expected)
        diff_bytes = diff.tobytes()
        changed_pixels = sum(
            any(diff_bytes[index : index + 4]) for index in range(0, len(diff_bytes), 4)
        )
        mean_channel_delta = sum(ImageStat.Stat(diff).mean[:3]) / 3
        assert actual.size == expected.size
        assert changed_pixels / (actual.width * actual.height) < 0.08
        assert mean_channel_delta < 3

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
            assert box is not None
            point = (box.x + box.width - 1, box.y + box.height - 1)
            assert debug.getpixel(point) != normal.getpixel(point)

        invisible_box = report.layers[4].bbox
        assert invisible_box is not None
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
        assert group_box is not None
        group_point = (group_box.x + group_box.width - 1, group_box.y + group_box.height - 1)
        assert debug.getpixel(group_point) != normal.getpixel(group_point)

        child_box = group.children[1].bbox
        assert child_box is not None
        child_point = (child_box.x + child_box.width - 1, child_box.y)
        assert debug.getpixel(child_point) != normal.getpixel(child_point)

    def test_should_request_remote_image_once_for_debug_measurement(self, tmp_path):
        """Debug rendering reuses the rendered remote image size."""
        from quickthumb import Canvas

        # given: a remote image layer without explicit dimensions
        source = Image.new("RGBA", (12, 8), (16, 144, 96, 255))
        buffer = BytesIO()
        source.save(buffer, format="PNG")
        png_bytes = buffer.getvalue()
        requests = 0

        class ImageHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                nonlocal requests
                requests += 1
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Content-Length", str(len(png_bytes)))
                self.end_headers()
                self.wfile.write(png_bytes)

            def log_message(self, format, *args):
                return

        server = ThreadingHTTPServer(("127.0.0.1", 0), ImageHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        url = f"http://127.0.0.1:{server.server_port}/thumb.png"
        canvas = Canvas(60, 40).image(url, position=(4, 6))

        # when: rendering with debug annotations
        try:
            canvas.render(str(tmp_path / "debug.png"), debug=True)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

        # then: the already-rendered image size is reused by debug measurement
        assert requests == 1
