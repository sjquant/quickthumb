from typing import TYPE_CHECKING, Literal

from PIL import Image

from quickthumb._base import (
    RenderContext,
    apply_alignment,
    expanded_rotation_size,
    is_url,
    parse_coordinate,
    parse_padding,
)
from quickthumb._composition import composite_layer_with_boundary, has_layer_composition
from quickthumb._effects import EffectsEngine
from quickthumb._fonts import FontEngine
from quickthumb._images import ImageEngine
from quickthumb._shapes import ShapeEngine
from quickthumb._text import TextEngine
from quickthumb._visualizations import VisualizationEngine
from quickthumb.models import (
    Align,
    BackdropBlur,
    ChartLayer,
    GroupLayer,
    ImageLayer,
    QRCodeLayer,
    ShapeLayer,
    SvgLayer,
    TextLayer,
)

if TYPE_CHECKING:
    from quickthumb.motion import ResolvedMotionTarget

GroupChildLayer = (
    TextLayer | ImageLayer | ShapeLayer | SvgLayer | ChartLayer | QRCodeLayer | GroupLayer
)
GroupBox = tuple[int, int, int, int]
GroupPlacement = tuple[GroupChildLayer, tuple[int, int], tuple[int, int]]


class GroupEngine:
    """Auto-layout measurement and placement for group layers."""

    def __init__(
        self,
        ctx: RenderContext,
        fonts: FontEngine,
        effects: EffectsEngine,
        images: ImageEngine,
        shapes: ShapeEngine,
        text: TextEngine,
        visualizations: VisualizationEngine,
    ):
        self._ctx = ctx
        self._fonts = fonts
        self._effects = effects
        self._images = images
        self._shapes = shapes
        self._text = text
        self._visualizations = visualizations

    def render_group_layer(
        self, image: Image.Image, layer: GroupLayer, origin: tuple[int, int] | None = None
    ):
        placements, _ = self.layout_group(layer, origin)
        for child, position, size in placements:
            self._render_group_child(image, child, position, size)

    def resolve_animation_targets(
        self,
        layer: GroupLayer,
        order: Literal["document", "top_to_bottom", "left_to_right", "reverse"] = "document",
    ) -> tuple["ResolvedMotionTarget", ...]:
        """Resolve children after auto-layout without changing their placements."""
        from quickthumb.motion import resolve_targets

        placements, _ = self.layout_group(layer)
        positions = tuple(position for _, position, _ in placements)
        sizes = tuple(size for _, _, size in placements)
        return resolve_targets(placements, order=order, positions=positions, sizes=sizes)

    def _render_group_child(
        self,
        image: Image.Image,
        child: GroupChildLayer,
        position: tuple[int, int],
        size: tuple[int, int],
    ):
        if isinstance(child, GroupLayer):
            if has_layer_composition(child):
                self._render_composed_group_child(image, child, origin=position)
            else:
                self.render_group_layer(image, child, origin=position)
            return

        placed = self._place_group_child(child, position, size)
        if has_layer_composition(placed):
            self._render_composed_group_child(image, placed)
            return

        self._render_group_child_direct(image, placed)

    def _render_composed_group_child(
        self,
        image: Image.Image,
        child: GroupChildLayer,
        origin: tuple[int, int] | None = None,
    ):
        isolated = self._child_without_boundary_blend(child)
        composite_layer_with_boundary(
            self._ctx,
            self._effects,
            image,
            child,
            lambda layer_surface: self._render_group_child_boundary(
                layer_surface, isolated, origin
            ),
        )

    def _render_group_child_boundary(
        self,
        image: Image.Image,
        child: GroupChildLayer,
        origin: tuple[int, int] | None = None,
    ):
        if isinstance(child, GroupLayer):
            self.render_group_layer(image, child, origin=origin)
            return
        self._render_group_child_direct(image, child)

    @staticmethod
    def _child_without_boundary_blend(child: GroupChildLayer) -> GroupChildLayer:
        updates = {}
        if isinstance(child, (ImageLayer, SvgLayer)) and child.blend_mode is not None:
            updates["blend_mode"] = None
        effects = getattr(child, "effects", None)
        if effects is not None:
            filtered = [effect for effect in effects if not isinstance(effect, BackdropBlur)]
            if len(filtered) != len(effects):
                updates["effects"] = filtered
        if updates and isinstance(child, (ImageLayer, ShapeLayer, SvgLayer)):
            return child.model_copy(update=updates)
        return child

    def _render_group_child_direct(self, image: Image.Image, child: GroupChildLayer):
        if isinstance(child, TextLayer):
            self._text.render_text_layer(image, child)
        elif isinstance(child, ImageLayer):
            self._images.render_image_layer(image, child)
        elif isinstance(child, SvgLayer):
            self._images.render_svg_layer(image, child)
        elif isinstance(child, ShapeLayer):
            self._shapes.render_shape_layer(image, child)
        elif isinstance(child, ChartLayer):
            self._visualizations.render_chart(image, child)
        elif isinstance(child, QRCodeLayer):
            self._visualizations.render_qr_code(image, child)

    def _place_group_child(
        self,
        child: GroupChildLayer,
        position: tuple[int, int],
        size: tuple[int, int],
    ) -> GroupChildLayer:
        if isinstance(child, TextLayer):
            return self.place_text_child(child, position, size)
        if isinstance(child, (ImageLayer, SvgLayer)):
            return child.model_copy(update={"position": position, "align": Align.TOP_LEFT})
        if isinstance(child, ShapeLayer):
            return child.model_copy(update={"position": position, "align": None})
        if isinstance(child, (ChartLayer, QRCodeLayer)):
            return child.model_copy(update={"position": position, "align": Align.TOP_LEFT})
        return child

    @staticmethod
    def place_text_child(
        child: TextLayer, position: tuple[int, int], size: tuple[int, int]
    ) -> TextLayer:
        """Anchor a text child at its layout slot, keeping align for line justification.

        Alignment normally shifts the block away from its position; compensating the
        anchor by the same offset pins the block to the slot while align still
        controls how individual lines justify within it.
        """
        if not child.align:
            return child.model_copy(update={"position": position, "align": None})

        x, y = position
        w, h = size
        if child.align.horizontal == "center":
            x += w // 2
        elif child.align.horizontal == "right":
            x += w
        if child.align.vertical == "middle":
            y += h // 2
        elif child.align.vertical == "bottom":
            y += h
        return child.model_copy(update={"position": (x, y)})

    def iter_text_children(self, layer: GroupLayer, origin: tuple[int, int] | None = None):
        """Yield text children (recursively) as placed copies at their layout positions."""
        placements, _ = self.layout_group(layer, origin)
        for child, position, size in placements:
            if isinstance(child, GroupLayer):
                yield from self.iter_text_children(child, origin=position)
            elif isinstance(child, TextLayer):
                yield self.place_text_child(child, position, size)

    def layout_group(
        self, layer: GroupLayer, origin: tuple[int, int] | None = None
    ) -> tuple[list[GroupPlacement], GroupBox]:
        """Measure children and assign their absolute positions within the group box."""
        sizes = [self.measure_group_child(child) for child in layer.children]
        pad_top, pad_right, pad_bottom, pad_left = parse_padding(layer.padding)
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

        placements: list[GroupPlacement] = []
        cursor = 0
        for child, (child_w, child_h) in zip(layer.children, sizes, strict=True):
            size = (child_w, child_h)
            if layer.direction == "column":
                cross = self._cross_axis_offset(layer.item_align, content_w - child_w)
                position = (group_x + pad_left + cross, group_y + pad_top + cursor)
                cursor += child_h + layer.gap
            else:
                cross = self._cross_axis_offset(layer.item_align, content_h - child_h)
                position = (group_x + pad_left + cursor, group_y + pad_top + cross)
                cursor += child_w + layer.gap
            placements.append((child, position, size))

        return placements, (group_x, group_y, group_w, group_h)

    def _group_anchor(self, layer: GroupLayer, group_w: int, group_h: int) -> tuple[int, int]:
        """Resolve the group box's top-left corner from its position and align."""
        if layer.position is not None:
            x = parse_coordinate(layer.position[0], self._ctx.width)
            y = parse_coordinate(layer.position[1], self._ctx.height)
        elif layer.align:
            h_map = {"left": 0, "center": self._ctx.width // 2, "right": self._ctx.width}
            v_map = {"top": 0, "middle": self._ctx.height // 2, "bottom": self._ctx.height}
            x, y = h_map[layer.align.horizontal], v_map[layer.align.vertical]
        else:
            x, y = 0, 0

        if layer.align:
            x, y = apply_alignment(x, y, (group_w, group_h), layer.align)
        return x, y

    @staticmethod
    def _cross_axis_offset(item_align: str, slack: int) -> int:
        if item_align == "center":
            return slack // 2
        if item_align == "end":
            return slack
        return 0

    def measure_group_child(self, child: GroupChildLayer) -> tuple[int, int]:
        """Return the rendered size of a layer (auto-scale and rotation applied).

        Memoized per render pass: nested groups re-measure their subtree once per
        ancestor otherwise, and text/image measurement is expensive.
        """
        cached = self._ctx.measure_cache.get(id(child))
        if cached is not None and cached[0] is child:
            return cached[1]
        size = self._measure_group_child_uncached(child)
        self._ctx.measure_cache[id(child)] = (child, size)
        return size

    def _measure_group_child_uncached(self, child: GroupChildLayer) -> tuple[int, int]:
        if isinstance(child, TextLayer):
            return self._text.measure_text_rendered_size(child)
        if isinstance(child, ImageLayer):
            return expanded_rotation_size(self._measure_image_size(child), child.rotation)
        if isinstance(child, SvgLayer):
            if child.width and child.height:
                size = child.width, child.height
            else:
                size = self._images.rasterize_svg(child).size
            return expanded_rotation_size(size, child.rotation)
        if isinstance(child, ShapeLayer):
            return expanded_rotation_size((child.width, child.height), child.rotation)
        if isinstance(child, ChartLayer):
            return child.width, child.height
        if isinstance(child, QRCodeLayer):
            return child.size, child.size
        _, (_, _, group_w, group_h) = self.layout_group(child, origin=(0, 0))
        return group_w, group_h

    def _measure_image_size(self, layer: ImageLayer) -> tuple[int, int]:
        if layer.width and layer.height:
            return layer.width, layer.height

        original_size = self._ctx.image_size_cache.get(layer.path)
        if original_size is None:
            if is_url(layer.path):
                img = self._images.load_image_from_url(layer.path)
            else:
                img = Image.open(layer.path)
            original_size = img.size
            self._ctx.image_size_cache[layer.path] = original_size
        original_w, original_h = original_size

        if layer.width:
            return layer.width, int(layer.width * original_h / original_w)
        if layer.height:
            return int(layer.height * original_w / original_h), layer.height
        return original_w, original_h
