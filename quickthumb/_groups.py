from PIL import Image

from quickthumb._shapes import ShapesMixin
from quickthumb.models import Align, GroupLayer, ImageLayer, ShapeLayer, SvgLayer, TextLayer

GroupChildLayer = TextLayer | ImageLayer | ShapeLayer | SvgLayer | GroupLayer
GroupBox = tuple[int, int, int, int]


class GroupsMixin(ShapesMixin):
    def _render_group_layer(
        self, image: Image.Image, layer: GroupLayer, origin: tuple[int, int] | None = None
    ):
        placements, _ = self._layout_group(layer, origin)
        for child, position in placements:
            self._render_group_child(image, child, position)

    def _render_group_child(
        self, image: Image.Image, child: GroupChildLayer, position: tuple[int, int]
    ):
        if isinstance(child, GroupLayer):
            self._render_group_layer(image, child, origin=position)
        elif isinstance(child, TextLayer):
            placed = child.model_copy(update={"position": position, "align": None})
            self._render_text_layer(image, placed)
        elif isinstance(child, ImageLayer):
            placed = child.model_copy(update={"position": position, "align": Align.TOP_LEFT})
            self._render_image_layer(image, placed)
        elif isinstance(child, SvgLayer):
            placed = child.model_copy(update={"position": position, "align": Align.TOP_LEFT})
            self._render_svg_layer(image, placed)
        elif isinstance(child, ShapeLayer):
            placed = child.model_copy(update={"position": position, "align": None})
            self._render_shape_layer(image, placed)

    def _layout_group(
        self, layer: GroupLayer, origin: tuple[int, int] | None = None
    ) -> tuple[list[tuple[GroupChildLayer, tuple[int, int]]], GroupBox]:
        """Measure children and assign their absolute positions within the group box."""
        sizes = [self._measure_group_child(child) for child in layer.children]
        pad_top, pad_right, pad_bottom, pad_left = self._parse_padding(layer.padding)
        gap_total = layer.gap * max(0, len(sizes) - 1)

        if layer.direction == "column":
            content_w = max((w for w, _ in sizes), default=0)
            content_h = sum(h for _, h in sizes) + gap_total
        else:
            content_w = sum(w for w, _ in sizes) + gap_total
            content_h = max((h for _, h in sizes), default=0)

        group_w = content_w + pad_left + pad_right
        group_h = content_h + pad_top + pad_bottom
        group_x, group_y = (
            origin if origin is not None else self._group_anchor(layer, group_w, group_h)
        )

        placements: list[tuple[GroupChildLayer, tuple[int, int]]] = []
        cursor = 0
        for child, (child_w, child_h) in zip(layer.children, sizes, strict=True):
            if layer.direction == "column":
                cross = self._cross_axis_offset(layer.item_align, content_w - child_w)
                placements.append((child, (group_x + pad_left + cross, group_y + pad_top + cursor)))
                cursor += child_h + layer.gap
            else:
                cross = self._cross_axis_offset(layer.item_align, content_h - child_h)
                placements.append((child, (group_x + pad_left + cursor, group_y + pad_top + cross)))
                cursor += child_w + layer.gap

        return placements, (group_x, group_y, group_w, group_h)

    def _group_anchor(self, layer: GroupLayer, group_w: int, group_h: int) -> tuple[int, int]:
        """Resolve the group box's top-left corner from its position and align."""
        if layer.position is not None:
            x = self._parse_coordinate(layer.position[0], self.width)
            y = self._parse_coordinate(layer.position[1], self.height)
        elif layer.align:
            h_map = {"left": 0, "center": self.width // 2, "right": self.width}
            v_map = {"top": 0, "middle": self.height // 2, "bottom": self.height}
            x, y = h_map[layer.align.horizontal], v_map[layer.align.vertical]
        else:
            x, y = 0, 0

        if layer.align:
            x, y = self._apply_image_alignment(x, y, (group_w, group_h), layer.align)
        return x, y

    @staticmethod
    def _cross_axis_offset(item_align: str, slack: int) -> int:
        if item_align == "center":
            return slack // 2
        if item_align == "end":
            return slack
        return 0

    def _measure_group_child(self, child: GroupChildLayer) -> tuple[int, int]:
        """Return the natural rendered size of a layer, without rendering it."""
        if isinstance(child, TextLayer):
            if isinstance(child.content, list):
                return self._measure_rich_text_size(child)
            font = self._load_font(child)
            return self._measure_simple_text_size(child, font, child.content)
        if isinstance(child, ImageLayer):
            return self._measure_image_size(child)
        if isinstance(child, SvgLayer):
            if child.width and child.height:
                return child.width, child.height
            return self._rasterize_svg(child).size
        if isinstance(child, ShapeLayer):
            return child.width, child.height
        _, (_, _, group_w, group_h) = self._layout_group(child, origin=(0, 0))
        return group_w, group_h

    def _measure_image_size(self, layer: ImageLayer) -> tuple[int, int]:
        if layer.width and layer.height:
            return layer.width, layer.height

        if self._is_url(layer.path):
            img = self._load_image_from_url(layer.path)
        else:
            img = Image.open(layer.path)
        original_w, original_h = img.size

        if layer.width:
            return layer.width, int(layer.width * original_h / original_w)
        if layer.height:
            return int(layer.height * original_w / original_h), layer.height
        return original_w, original_h
