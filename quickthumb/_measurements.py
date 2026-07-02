from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from quickthumb._base import RenderContext, apply_alignment, parse_coordinate
from quickthumb._groups import GroupEngine
from quickthumb._text import TextEngine
from quickthumb.models import Align, GroupLayer, ImageLayer, ShapeLayer, SvgLayer, TextLayer


@dataclass(frozen=True)
class LayerBounds:
    """Canvas-space rectangle occupied by a rendered layer."""

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

    def as_tuple(self) -> tuple[int, int, int, int]:
        return self.x, self.y, self.width, self.height

    def is_empty(self) -> bool:
        return self.width <= 0 or self.height <= 0

    def is_fully_outside(self, canvas_width: int, canvas_height: int) -> bool:
        return (
            self.right <= 0 or self.bottom <= 0 or self.x >= canvas_width or self.y >= canvas_height
        )

    def is_partially_outside(self, canvas_width: int, canvas_height: int) -> bool:
        return self.x < 0 or self.y < 0 or self.right > canvas_width or self.bottom > canvas_height

    def clamped_to(self, canvas_width: int, canvas_height: int) -> "LayerBounds | None":
        left, top = max(0, self.x), max(0, self.y)
        right, bottom = min(canvas_width, self.right), min(canvas_height, self.bottom)
        if right <= left or bottom <= top:
            return None
        return LayerBounds(left, top, right - left, bottom - top)


@dataclass(frozen=True)
class LayerIdentity:
    """Stable internal identity for a measured layer or nested group child."""

    index: int
    layer_type: str
    path: tuple[int, ...]


@dataclass(frozen=True)
class MeasuredLayer:
    """Internal measurement contract shared by diagnostics and later inspection."""

    identity: LayerIdentity
    order: int
    z_order: int
    layer: object
    bbox: LayerBounds | None
    raw: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))
    children: tuple["MeasuredLayer", ...] = ()

    @property
    def layer_index(self) -> int:
        return self.identity.index

    @property
    def layer_type(self) -> str:
        return self.identity.layer_type

    def text_descendants(self) -> Iterable["MeasuredLayer"]:
        for child in self.children:
            if child.layer_type == "text":
                yield child
            yield from child.text_descendants()


class LayerMeasurementEngine:
    """Measure layers once into a reusable internal contract."""

    def __init__(self, ctx: RenderContext, groups: GroupEngine, text: TextEngine):
        self._ctx = ctx
        self._groups = groups
        self._text = text

    def measure_layers(self, layers: Iterable[object]) -> list[MeasuredLayer]:
        measured: list[MeasuredLayer] = []
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
    ) -> MeasuredLayer:
        identity = LayerIdentity(index=index, layer_type=self._layer_type(layer), path=path)

        if isinstance(layer, GroupLayer):
            return self._measure_group_layer(layer, identity, order)

        if isinstance(layer, TextLayer):
            return self._measure_text_layer(layer, identity, order)

        if isinstance(layer, (ImageLayer, SvgLayer, ShapeLayer)):
            bbox = self._measure_positioned_layer(layer)
            return self._measured(
                layer, identity, order, bbox, raw=self._positioned_raw(layer, bbox)
            )

        return self._measured(layer, identity, order, None, raw={"measurable": False})

    def _measure_group_layer(
        self, layer: GroupLayer, identity: LayerIdentity, order: int
    ) -> MeasuredLayer:
        placements, box = self._groups.layout_group(layer)
        children = tuple(
            self._measure_group_child(child, position, size, identity, order, child_index)
            for child_index, (child, position, size) in enumerate(placements)
        )
        raw = {
            "child_count": len(layer.children),
            "direction": layer.direction,
            "gap": layer.gap,
            "padding": layer.padding,
            "placements": tuple(
                {"path": child.identity.path, "position": child.raw.get("position"), "size": size}
                for child, (_, _, size) in zip(children, placements, strict=True)
            ),
        }
        return self._measured(layer, identity, order, LayerBounds(*box), raw=raw, children=children)

    def _measure_group_child(
        self,
        child: object,
        position: tuple[int, int],
        size: tuple[int, int],
        parent_identity: LayerIdentity,
        order: int,
        child_index: int,
    ) -> MeasuredLayer:
        identity = LayerIdentity(
            index=parent_identity.index,
            layer_type=self._layer_type(child),
            path=parent_identity.path + (child_index,),
        )

        if isinstance(child, GroupLayer):
            placements, box = self._groups.layout_group(child, origin=position)
            children = tuple(
                self._measure_group_child(
                    grandchild,
                    grandchild_position,
                    grandchild_size,
                    identity,
                    order,
                    index,
                )
                for index, (grandchild, grandchild_position, grandchild_size) in enumerate(
                    placements
                )
            )
            return self._measured(
                child,
                identity,
                order,
                LayerBounds(*box),
                raw={"position": position, "size": size, "child_count": len(child.children)},
                children=children,
            )

        if isinstance(child, TextLayer):
            placed = self._groups.place_text_child(child, position, size)
            return self._measure_text_layer(
                placed, identity, order, raw={"position": position, "size": size}
            )

        if isinstance(child, (ImageLayer, SvgLayer)):
            placed = child.model_copy(update={"position": position, "align": Align.TOP_LEFT})
            return self._measured(
                placed,
                identity,
                order,
                LayerBounds(position[0], position[1], size[0], size[1]),
                raw={"position": position, "size": size},
            )

        if isinstance(child, ShapeLayer):
            placed = child.model_copy(update={"position": position, "align": None})
            return self._measured(
                placed,
                identity,
                order,
                LayerBounds(position[0], position[1], size[0], size[1]),
                raw={"position": position, "size": size},
            )

        return self._measured(
            child, identity, order, None, raw={"position": position, "size": size}
        )

    def _measure_text_layer(
        self,
        layer: TextLayer,
        identity: LayerIdentity,
        order: int,
        raw: Mapping[str, Any] | None = None,
    ) -> MeasuredLayer:
        effective = self._text.effective_layer(layer)
        w, h = self._groups.measure_group_child(effective)
        base_x, base_y = self._text.get_text_base_position(effective)
        x = self._text.get_horizontal_start_x(base_x, w, effective.align)
        y = self._text.get_vertical_start_y(base_y, h, effective.align)
        metadata = {
            "size": (w, h),
            "source_layer": layer,
            "effective_layer": effective,
            "auto_scaled": effective is not layer,
        }
        if raw:
            metadata.update(raw)
        return self._measured(effective, identity, order, LayerBounds(x, y, w, h), raw=metadata)

    def _measure_positioned_layer(self, layer: ImageLayer | SvgLayer | ShapeLayer) -> LayerBounds:
        w, h = self._groups.measure_group_child(layer)
        x = parse_coordinate(layer.position[0], self._ctx.width)
        y = parse_coordinate(layer.position[1], self._ctx.height)
        if layer.align:
            x, y = apply_alignment(x, y, (w, h), layer.align)
        return LayerBounds(x, y, w, h)

    @staticmethod
    def _positioned_raw(
        layer: ImageLayer | SvgLayer | ShapeLayer, bbox: LayerBounds
    ) -> Mapping[str, Any]:
        raw = {
            "size": (bbox.width, bbox.height),
            "position": layer.position,
            "align": layer.align,
            "rotation": layer.rotation,
        }
        if isinstance(layer, (ImageLayer, SvgLayer)):
            raw["path"] = layer.path
        return raw

    @staticmethod
    def _measured(
        layer: object,
        identity: LayerIdentity,
        order: int,
        bbox: LayerBounds | None,
        *,
        raw: Mapping[str, Any],
        children: tuple[MeasuredLayer, ...] = (),
    ) -> MeasuredLayer:
        return MeasuredLayer(
            identity=identity,
            order=order,
            z_order=order,
            layer=layer,
            bbox=bbox,
            raw=MappingProxyType(dict(raw)),
            children=children,
        )

    @staticmethod
    def _layer_type(layer: object) -> str:
        return str(getattr(layer, "type", type(layer).__name__))
