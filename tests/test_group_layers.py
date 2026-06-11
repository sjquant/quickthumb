"""Tests for group layer (auto-layout) functionality"""

import json
import os
import tempfile

import pytest
from inline_snapshot import snapshot
from PIL import Image
from quickthumb.errors import ValidationError

WHITE = (255, 255, 255, 255)
RED = {"type": "shape", "shape": "rectangle", "width": 50, "height": 20, "color": "#FF0000"}
BLUE = {"type": "shape", "shape": "rectangle", "width": 30, "height": 40, "color": "#0000FF"}


def render_pixels(canvas):
    """Render a canvas to RGBA pixels for probing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, "out.png")
        canvas.render(output_path)
        return Image.open(output_path).convert("RGBA")


class TestCanvasGroupAPI:
    """Test suite for Canvas.group() builder method"""

    def test_should_add_group_layer_and_support_method_chaining(self):
        """Canvas.group() adds a group layer with children and returns self for chaining"""
        from quickthumb import Canvas

        # given
        canvas = Canvas(400, 300)

        # when: children are given as a dict and as a layer model instance
        from quickthumb import TextLayer

        result = canvas.group(
            children=[RED, TextLayer(type="text", content="caption", size=20)],
            direction="row",
            gap=12,
            padding=8,
            position=(10, 10),
        )

        # then
        assert result is canvas
        assert len(canvas.layers) == 1
        layer = canvas.layers[0]
        assert layer.type == "group"
        assert layer.direction == "row"
        assert layer.gap == 12
        assert len(layer.children) == 2
        assert layer.children[0].shape == "rectangle"
        assert layer.children[1].content == "caption"

    def test_should_round_trip_group_layer_through_json(self):
        """Group layers (including nested groups) survive a JSON round-trip"""
        from quickthumb import Canvas

        # given: a group containing a text child and a nested row group
        canvas = Canvas(400, 300).group(
            children=[
                {"type": "text", "content": "Title", "size": 40, "color": "#FFFFFF"},
                {"type": "group", "direction": "row", "gap": 4, "children": [RED, BLUE]},
            ],
            direction="column",
            gap=16,
            position=("8%", "50%"),
            align=("left", "middle"),
        )

        # when
        data = json.loads(canvas.to_json())
        restored = Canvas.from_json(canvas.to_json())

        # then: wire format and restored models both preserve the structure
        assert data["layers"][0] == snapshot(
            {
                "type": "group",
                "direction": "column",
                "gap": 16,
                "padding": 0,
                "position": ["8%", "50%"],
                "align": "left",
                "item_align": "start",
                "children": [
                    {
                        "type": "text",
                        "content": "Title",
                        "font": None,
                        "size": 40,
                        "color": "#FFFFFF",
                        "fill": None,
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
                        "type": "group",
                        "direction": "row",
                        "gap": 4,
                        "padding": 0,
                        "position": None,
                        "align": None,
                        "item_align": "start",
                        "children": [
                            {
                                "type": "shape",
                                "shape": "rectangle",
                                "position": [0, 0],
                                "width": 50,
                                "height": 20,
                                "color": "#FF0000",
                                "border_radius": 0,
                                "opacity": 1.0,
                                "rotation": 0.0,
                                "align": None,
                                "points": None,
                                "star_points": 5,
                                "inner_radius": 0.5,
                                "effects": [],
                            },
                            {
                                "type": "shape",
                                "shape": "rectangle",
                                "position": [0, 0],
                                "width": 30,
                                "height": 40,
                                "color": "#0000FF",
                                "border_radius": 0,
                                "opacity": 1.0,
                                "rotation": 0.0,
                                "align": None,
                                "points": None,
                                "star_points": 5,
                                "inner_radius": 0.5,
                                "effects": [],
                            },
                        ],
                    },
                ],
            }
        )
        assert data["layers"][0]["children"][1]["type"] == "group"
        layer = restored.layers[0]
        assert layer.direction == "column"
        assert layer.gap == 16
        assert layer.children[0].content == "Title"
        assert layer.children[1].children[1].color == "#0000FF"

    @pytest.mark.parametrize(
        "overrides,error_pattern",
        [
            ({"children": []}, "children"),
            ({"direction": "diagonal"}, "direction"),
            ({"gap": -4}, "gap"),
            ({"item_align": "middle"}, "item_align"),
            ({"children": [{"type": "background", "color": "#000000"}]}, "background"),
            ({"children": [{"type": "outline", "width": 2, "color": "#000000"}]}, "outline"),
            ({"children": [dict(RED, position=5)]}, "must not set position"),
        ],
    )
    def test_should_reject_invalid_group_parameters(self, overrides, error_pattern):
        """Invalid group parameters and unsupported child types raise ValidationError via JSON"""
        from quickthumb import Canvas

        layer = {"type": "group", "children": [RED], **overrides}
        spec = json.dumps({"width": 400, "height": 300, "layers": [layer]})

        with pytest.raises(ValidationError, match=error_pattern):
            Canvas.from_json(spec)

    def test_should_reject_children_with_explicit_position(self):
        """Children must not set position — the group assigns positions"""
        from quickthumb import Canvas

        child = dict(RED, position=(50, 50))
        with pytest.raises(ValidationError, match="position"):
            Canvas(400, 300).group(children=[child])


class TestGroupLayout:
    """Black-box layout behavior verified by probing rendered pixels"""

    def test_should_stack_children_in_a_column_with_gap(self):
        """Column groups stack children top-to-bottom separated by gap"""
        from quickthumb import Canvas

        # given: a column group at (10, 10) with a 10px gap between a red and a blue box
        canvas = (
            Canvas(200, 200)
            .background(color="#FFFFFF")
            .group(children=[RED, BLUE], direction="column", gap=10, position=(10, 10))
        )

        # when
        img = render_pixels(canvas)

        # then: red spans y 10..29, the gap leaves white at y 30..39, blue spans y 40..79
        assert img.getpixel((12, 12)) == (255, 0, 0, 255)
        assert img.getpixel((12, 27)) == (255, 0, 0, 255)
        assert img.getpixel((12, 34)) == WHITE
        assert img.getpixel((12, 45)) == (0, 0, 255, 255)
        assert img.getpixel((45, 45)) == WHITE  # blue is only 30px wide

    def test_should_stack_children_in_a_row_with_gap(self):
        """Row groups place children left-to-right separated by gap"""
        from quickthumb import Canvas

        # given: a row group at (10, 10) with a 5px gap
        canvas = (
            Canvas(200, 200)
            .background(color="#FFFFFF")
            .group(children=[RED, BLUE], direction="row", gap=5, position=(10, 10))
        )

        # when
        img = render_pixels(canvas)

        # then: red spans x 10..59, gap leaves white at x 60..64, blue spans x 65..94
        assert img.getpixel((12, 12)) == (255, 0, 0, 255)
        assert img.getpixel((62, 12)) == WHITE
        assert img.getpixel((70, 12)) == (0, 0, 255, 255)

    def test_should_align_children_on_the_cross_axis(self):
        """item_align centers or end-aligns children within the group's cross axis"""
        from quickthumb import Canvas

        # given: a column group where blue (30px) is centered within red's 50px width
        canvas = (
            Canvas(200, 200)
            .background(color="#FFFFFF")
            .group(
                children=[RED, BLUE],
                direction="column",
                gap=0,
                position=(10, 10),
                item_align="center",
            )
        )

        # when
        img = render_pixels(canvas)

        # then: blue is offset by (50-30)//2 = 10px, spanning x 20..49
        assert img.getpixel((15, 45)) == WHITE
        assert img.getpixel((25, 45)) == (0, 0, 255, 255)
        assert img.getpixel((45, 45)) == (0, 0, 255, 255)
        assert img.getpixel((55, 45)) == WHITE

    def test_should_end_align_children_on_the_cross_axis(self):
        """item_align="end" pushes narrower children to the cross-axis end"""
        from quickthumb import Canvas

        # given: a column group where blue (30px) is end-aligned within red's 50px width
        canvas = (
            Canvas(200, 200)
            .background(color="#FFFFFF")
            .group(
                children=[RED, BLUE],
                direction="column",
                gap=0,
                position=(10, 10),
                item_align="end",
            )
        )

        # when
        img = render_pixels(canvas)

        # then: blue is offset by 50-30 = 20px, spanning x 30..59
        assert img.getpixel((25, 45)) == WHITE
        assert img.getpixel((35, 45)) == (0, 0, 255, 255)
        assert img.getpixel((55, 45)) == (0, 0, 255, 255)

    def test_should_measure_image_children_with_intrinsic_aspect_ratio(self, tmp_path):
        """An image child with only width set is measured using its intrinsic aspect ratio"""
        from quickthumb import Canvas

        # given: a 40x20 green image scaled to width 20 (height must become 10 by aspect)
        fixture = tmp_path / "green.png"
        Image.new("RGBA", (40, 20), (0, 255, 0, 255)).save(fixture)
        canvas = (
            Canvas(100, 100)
            .background(color="#FFFFFF")
            .group(
                children=[
                    {"type": "image", "path": str(fixture), "width": 20},
                    BLUE,
                ],
                direction="column",
                position=(0, 0),
            )
        )

        # when
        img = render_pixels(canvas)

        # then: blue starts at y=10, immediately under the 20x10 image
        assert img.getpixel((5, 5)) == (0, 255, 0, 255)
        assert img.getpixel((5, 15)) == (0, 0, 255, 255)
        assert img.getpixel((25, 5)) == WHITE

    @pytest.mark.parametrize(
        "padding,origin",
        [
            (4, (4, 4)),  # uniform
            ((5, 8), (8, 5)),  # (vertical, horizontal)
            ((1, 2, 3, 4), (4, 1)),  # (top, right, bottom, left)
        ],
    )
    def test_should_apply_padding_inside_the_group_box(self, padding, origin):
        """All padding forms offset the child from the group anchor with the right side order"""
        from quickthumb import Canvas

        # given: padding around a single red box anchored at (0, 0)
        canvas = (
            Canvas(100, 100)
            .background(color="#FFFFFF")
            .group(children=[RED], padding=padding, position=(0, 0))
        )

        # when
        img = render_pixels(canvas)

        # then: the box's top-left corner lands exactly at (left, top)
        x0, y0 = origin
        assert img.getpixel((x0 + 2, y0 + 2)) == (255, 0, 0, 255)
        if x0 > 0:
            assert img.getpixel((x0 - 1, y0 + 2)) == WHITE
        if y0 > 0:
            assert img.getpixel((x0 + 2, y0 - 1)) == WHITE

    def test_should_anchor_group_box_with_align(self):
        """align anchors the whole group box relative to its position"""
        from quickthumb import Canvas

        # given: a single 50x20 red box centered on the canvas midpoint
        canvas = (
            Canvas(200, 200)
            .background(color="#FFFFFF")
            .group(
                children=[RED],
                position=("50%", "50%"),
                align=("center", "middle"),
            )
        )

        # when
        img = render_pixels(canvas)

        # then: the box spans x 75..124, y 90..109 (centered on both axes)
        assert img.getpixel((100, 100)) == (255, 0, 0, 255)
        assert img.getpixel((78, 100)) == (255, 0, 0, 255)
        assert img.getpixel((100, 92)) == (255, 0, 0, 255)
        assert img.getpixel((70, 100)) == WHITE
        assert img.getpixel((100, 85)) == WHITE
        assert img.getpixel((100, 115)) == WHITE

    def test_should_layout_nested_groups(self):
        """A group child is measured as a unit and laid out recursively"""
        from quickthumb import Canvas

        green = {
            "type": "shape",
            "shape": "rectangle",
            "width": 20,
            "height": 20,
            "color": "#00FF00",
        }
        red = {"type": "shape", "shape": "rectangle", "width": 20, "height": 20, "color": "#FF0000"}
        blue = {
            "type": "shape",
            "shape": "rectangle",
            "width": 20,
            "height": 20,
            "color": "#0000FF",
        }

        # given: a column [green, row[red, blue]] anchored at the origin with no gaps
        canvas = (
            Canvas(100, 100)
            .background(color="#FFFFFF")
            .group(
                children=[
                    green,
                    {"type": "group", "direction": "row", "children": [red, blue]},
                ],
                direction="column",
                position=(0, 0),
            )
        )

        # when
        img = render_pixels(canvas)

        # then: green at (0..19, 0..19); the nested row renders red then blue at y 20..39
        assert img.getpixel((10, 10)) == (0, 255, 0, 255)
        assert img.getpixel((10, 30)) == (255, 0, 0, 255)
        assert img.getpixel((30, 30)) == (0, 0, 255, 255)
        assert img.getpixel((50, 30)) == WHITE
