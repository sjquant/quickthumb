from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, cast

from quickthumb._base import RenderContext, apply_alignment, parse_coordinate
from quickthumb._composition import composition_bounds
from quickthumb._groups import GroupEngine
from quickthumb._text import TextEngine
from quickthumb.models import (
    Align,
    ChartLayer,
    GroupLayer,
    ImageLayer,
    QRCodeLayer,
    ShapeLayer,
    SvgLayer,
    TextLayer,
)

if TYPE_CHECKING:
    from quickthumb.canvas import Canvas

MEASURABLE_LAYER_TYPES = frozenset(
    {
        "text",
        "shape",
        "image",
        "svg",
        "group",
        "chart",
        "qr_code",
    }
)


def measure_layers(canvas: "Canvas") -> list["LayerMeasurement"]:
    """Measure a canvas's renderable layers into the stable internal contract."""
    engine = LayerMeasurementEngine(canvas._ctx, canvas._groups, canvas._text)
    return engine.measure_layers(canvas.layers)


def layer_id_for(layer: object, index: int, path: tuple[int, ...]) -> str:
    """Return the stable public identifier shared by inspection and diagnostics."""
    explicit_id = getattr(layer, "id", None)
    if explicit_id:
        return str(explicit_id)
    if len(path) == 1:
        return f"layer:{index}"
    child_path = ".".join(str(part) for part in path[1:])
    return f"layer:{index}:{child_path}"


@dataclass(frozen=True)
class BBox:
    """Canvas-space rectangle occupied by a measured layer."""

    x: int
    y: int
    width: int
    height: int

    @property
    def right(self) -> int:
        return self.x + self.width

    @property
    def bottom(self) -> int:
        return self.y + self.height

    @property
    def area(self) -> int:
        if self.is_empty:
            return 0
        return self.width * self.height

    @property
    def is_empty(self) -> bool:
        return self.width <= 0 or self.height <= 0

    @classmethod
    def from_points(cls, left: int, top: int, right: int, bottom: int) -> "BBox":
        return cls(left, top, right - left, bottom - top)

    @classmethod
    def union(cls, boxes: Iterable["BBox"]) -> "BBox | None":
        non_empty = [box for box in boxes if not box.is_empty]
        if not non_empty:
            return None
        return cls.from_points(
            min(box.x for box in non_empty),
            min(box.y for box in non_empty),
            max(box.right for box in non_empty),
            max(box.bottom for box in non_empty),
        )

    def as_tuple(self) -> tuple[int, int, int, int]:
        return self.x, self.y, self.width, self.height

    def is_fully_outside(self, canvas_width: int, canvas_height: int) -> bool:
        return (
            self.right <= 0 or self.bottom <= 0 or self.x >= canvas_width or self.y >= canvas_height
        )

    def is_partially_outside(self, canvas_width: int, canvas_height: int) -> bool:
        return self.x < 0 or self.y < 0 or self.right > canvas_width or self.bottom > canvas_height

    def clamped_to(self, canvas_width: int, canvas_height: int) -> "BBox | None":
        left, top = max(0, self.x), max(0, self.y)
        right, bottom = min(canvas_width, self.right), min(canvas_height, self.bottom)
        if right <= left or bottom <= top:
            return None
        return BBox.from_points(left, top, right, bottom)

    def intersection(self, other: "BBox") -> "BBox | None":
        left, top = max(self.x, other.x), max(self.y, other.y)
        right, bottom = min(self.right, other.right), min(self.bottom, other.bottom)
        if right <= left or bottom <= top:
            return None
        return BBox.from_points(left, top, right, bottom)


@dataclass(frozen=True)
class LayerMeasurement:
    """Stable internal layer measurement contract for diagnostics and inspection."""

    index: int
    order: int
    layer_type: str
    bbox: BBox | None
    layer_id: str
    name: str | None
    visible: bool
    raw_layer: Any
    metadata: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))
    children: tuple["LayerMeasurement", ...] = ()

    @property
    def z_order(self) -> int:
        return self.order

    @property
    def effective_text_layer(self) -> TextLayer | None:
        layer = self.metadata.get("effective_layer")
        if isinstance(layer, TextLayer):
            return layer
        if isinstance(self.raw_layer, TextLayer):
            return self.raw_layer
        return None

    def text_descendants(self) -> Iterable["LayerMeasurement"]:
        for child in self.children:
            if child.layer_type == "text":
                yield child
            yield from child.text_descendants()


class LayerMeasurementEngine:
    """Measure layers once into reusable internal layer measurements."""

    def __init__(self, ctx: RenderContext, groups: GroupEngine, text: TextEngine):
        self._ctx = ctx
        self._groups = groups
        self._text = text

    def measure_layers(self, layers: Iterable[object]) -> list[LayerMeasurement]:
        measured: list[LayerMeasurement] = []
        for index, layer in enumerate(layers):
            measured.append(self.measure_layer(layer, index=index, order=index, path=(index,)))
        return measured

    def measure_layer(
        self,
        layer: object,
        *,
        index: int,
        order: int,
        path: tuple[int, ...],
    ) -> LayerMeasurement:
        layer_type = self._layer_type(layer)

        if isinstance(layer, GroupLayer):
            return self._measure_group_layer(layer, index, order, path)

        if isinstance(layer, TextLayer):
            return self._measure_text_layer(layer, index, order, path)

        if isinstance(
            layer,
            (
                ImageLayer,
                SvgLayer,
                ShapeLayer,
                ChartLayer,
                QRCodeLayer,
            ),
        ):
            bbox = self._measure_positioned_layer(layer)
            bbox = self._apply_composition_bounds(layer, bbox)
            return self._measurement(
                layer,
                index,
                order,
                path,
                layer_type,
                bbox,
                metadata=self._positioned_metadata(layer, bbox),
            )

        return self._measurement(
            layer, index, order, path, layer_type, None, metadata={"measurable": False}
        )

    def _measure_group_layer(
        self, layer: GroupLayer, index: int, order: int, path: tuple[int, ...]
    ) -> LayerMeasurement:
        placements, layout_box = self._groups.layout_group(layer)
        children = tuple(
            self._measure_group_child(child, position, size, index, order, path + (child_index,))
            for child_index, (child, position, size) in enumerate(placements)
        )
        bbox = BBox.union(
            child.bbox
            for child in children
            if child.visible and child.bbox is not None and not child.bbox.is_empty
        )
        if bbox is None:
            bbox = BBox(layout_box[0], layout_box[1], 0, 0)
        bbox = self._apply_composition_bounds(layer, bbox)
        metadata = {
            "child_count": len(layer.children),
            "direction": layer.direction,
            "gap": layer.gap,
            "padding": layer.padding,
            "layout_bbox": BBox(*layout_box),
            "children": children,
        }
        return self._measurement(
            layer, index, order, path, "group", bbox, metadata=metadata, children=children
        )

    def _measure_group_child(
        self,
        child: object,
        position: tuple[int, int],
        size: tuple[int, int],
        index: int,
        order: int,
        path: tuple[int, ...],
    ) -> LayerMeasurement:
        if isinstance(child, GroupLayer):
            placed = child.model_copy(update={"position": position, "align": None})
            placements, layout_box = self._groups.layout_group(child, origin=position)
            children = tuple(
                self._measure_group_child(
                    grandchild,
                    grandchild_position,
                    grandchild_size,
                    index,
                    order,
                    path + (child_index,),
                )
                for child_index, (grandchild, grandchild_position, grandchild_size) in enumerate(
                    placements
                )
            )
            bbox = BBox.union(
                grandchild.bbox
                for grandchild in children
                if grandchild.visible
                and grandchild.bbox is not None
                and not grandchild.bbox.is_empty
            )
            if bbox is None:
                bbox = BBox(layout_box[0], layout_box[1], 0, 0)
            bbox = self._apply_composition_bounds(placed, bbox)
            return self._measurement(
                placed,
                index,
                order,
                path,
                "group",
                bbox,
                metadata={
                    "position": position,
                    "size": size,
                    "layout_bbox": BBox(*layout_box),
                    "child_count": len(child.children),
                    "children": children,
                },
                children=children,
            )

        if isinstance(child, TextLayer):
            placed = self._groups.place_text_child(child, position, size)
            return self._measure_text_layer(
                placed, index, order, path, metadata={"position": position, "size": size}
            )

        if isinstance(child, (ImageLayer, SvgLayer)):
            placed = child.model_copy(update={"position": position, "align": Align.TOP_LEFT})
            bbox = BBox(position[0], position[1], size[0], size[1])
            bbox = self._apply_composition_bounds(placed, bbox)
            return self._measurement(
                placed,
                index,
                order,
                path,
                self._layer_type(child),
                bbox,
                metadata=self._positioned_metadata(placed, bbox),
            )

        if isinstance(child, ShapeLayer):
            placed = child.model_copy(update={"position": position, "align": None})
            bbox = BBox(position[0], position[1], size[0], size[1])
            bbox = self._apply_composition_bounds(placed, bbox)
            return self._measurement(
                placed,
                index,
                order,
                path,
                "shape",
                bbox,
                metadata=self._positioned_metadata(placed, bbox),
            )

        if isinstance(child, (ChartLayer, QRCodeLayer)):
            placed = child.model_copy(update={"position": position, "align": Align.TOP_LEFT})
            bbox = BBox(position[0], position[1], size[0], size[1])
            bbox = self._apply_composition_bounds(placed, bbox)
            return self._measurement(
                placed,
                index,
                order,
                path,
                self._layer_type(child),
                bbox,
                metadata=self._positioned_metadata(placed, bbox),
            )

        return self._measurement(
            child,
            index,
            order,
            path,
            self._layer_type(child),
            None,
            metadata={"position": position, "size": size, "measurable": False},
        )

    def _measure_text_layer(
        self,
        layer: TextLayer,
        index: int,
        order: int,
        path: tuple[int, ...],
        metadata: Mapping[str, Any] | None = None,
    ) -> LayerMeasurement:
        effective = self._text.effective_layer(layer)
        layout = self._text.measure_text_layout(effective)
        w, h = self._text.measure_text_rendered_size(effective, layout=layout)
        base_x, base_y = self._text.get_text_base_position(effective)
        x = self._text.get_horizontal_start_x(base_x, w, effective.align)
        y = self._text.get_vertical_start_y(base_y, h, effective.align)
        details = {
            "size": (w, h),
            "source_layer": layer,
            "effective_layer": effective,
            "auto_scaled": effective is not layer,
            "content": effective.content,
            "layout_size": layout["size"],
            "align": effective.align,
            "position": effective.position,
            "max_width": effective.max_width,
            "max_height": effective.max_height,
            "min_size": effective.min_size,
            "balance_lines": effective.balance_lines,
            "font_source": effective.font_source,
            "font_variations": effective.font_variations,
            "emoji_style": effective.emoji_style,
            "wrapped_lines": layout["wrapped_lines"],
            "effective_font_size": layout["effective_font_size"],
            "effective_font_sizes": layout["effective_font_sizes"],
        }
        if metadata:
            details.update(metadata)
        bbox = self._apply_composition_bounds(layer, BBox(x, y, w, h))
        return self._measurement(layer, index, order, path, "text", bbox, metadata=details)

    def _apply_composition_bounds(self, layer: object, bbox: BBox) -> BBox:
        if bbox.is_empty:
            return bbox

        bounds = composition_bounds(self._ctx, layer)
        if bounds is None:
            return bbox

        clipped = bbox.intersection(BBox(*bounds))
        if clipped is None:
            return BBox(bounds[0], bounds[1], 0, 0)
        return clipped

    def _measure_positioned_layer(self, layer: object) -> BBox:
        positioned = cast(Any, layer)
        if isinstance(layer, (ImageLayer, SvgLayer, ShapeLayer)):
            w, h = self._groups.measure_group_child(layer)
        elif isinstance(layer, QRCodeLayer):
            w, h = layer.size, layer.size
        else:
            w, h = positioned.width, positioned.height
        x = parse_coordinate(positioned.position[0], self._ctx.width)
        y = parse_coordinate(positioned.position[1], self._ctx.height)
        if positioned.align:
            x, y = apply_alignment(x, y, (w, h), positioned.align)
        return BBox(x, y, w, h)

    @staticmethod
    def _positioned_metadata(layer: object, bbox: BBox) -> Mapping[str, Any]:
        metadata = {
            "size": (bbox.width, bbox.height),
            "position": getattr(layer, "position", None),
            "align": getattr(layer, "align", None),
            "rotation": getattr(layer, "rotation", 0),
        }
        if isinstance(layer, (ImageLayer, SvgLayer)):
            metadata["path"] = layer.path
        if isinstance(layer, ShapeLayer):
            metadata["shape"] = layer.shape
        return metadata

    def _measurement(
        self,
        layer: object,
        index: int,
        order: int,
        path: tuple[int, ...],
        layer_type: str,
        bbox: BBox | None,
        *,
        metadata: Mapping[str, Any],
        children: tuple[LayerMeasurement, ...] = (),
    ) -> LayerMeasurement:
        return LayerMeasurement(
            index=index,
            order=order,
            layer_type=layer_type,
            bbox=bbox,
            layer_id=layer_id_for(layer, index, path),
            name=self._layer_name(layer),
            visible=self._visible(layer),
            raw_layer=layer,
            metadata=MappingProxyType(dict(metadata)),
            children=children,
        )

    @staticmethod
    def _layer_name(layer: object) -> str | None:
        name = getattr(layer, "name", None)
        return str(name) if name else None

    @staticmethod
    def _visible(layer: object) -> bool:
        return float(getattr(layer, "opacity", 1.0)) > 0.0

    @staticmethod
    def _layer_type(layer: object) -> str:
        layer_type = str(getattr(layer, "type", "unknown"))
        if layer_type in MEASURABLE_LAYER_TYPES:
            return layer_type
        return "unknown"
