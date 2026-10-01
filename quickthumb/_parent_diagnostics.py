"""Per-observation world pixels and editing context for static parent diagnostics."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, cast

from PIL import Image, ImageChops

from quickthumb._composition import _clip_alpha, _mask_alpha, has_layer_composition
from quickthumb._export_base import _with_motion_color
from quickthumb._measurements import LayerMeasurement
from quickthumb._parent_render import (
    Affine,
    ParentNode,
    ParentRenderPlan,
    _has_counter,
    affine_fragment,
    authored_parent_frames,
    multiply,
    settled_text_reference,
    translate,
)
from quickthumb._text import TextEngine
from quickthumb.models import AnimationSpec, Background, GroupLayer, ImageLayer, TextLayer
from quickthumb.motion import _capability_features_for

if TYPE_CHECKING:
    from quickthumb.canvas import Canvas


@dataclass
class _Placed:
    layer: Any
    position: tuple[int, int]
    size: tuple[int, int]


@dataclass
class _Root:
    node: ParentNode
    matrix: Affine
    layer_id: str
    operations: list[_Placed] = field(default_factory=list)
    prefix: Image.Image | None = None
    prefix_index: int = 0


@dataclass
class _Occurrence:
    root: _Root
    start: int = 0
    end: int = 0
    top: bool = False
    text: TextLayer | None = None
    structural: bool = False
    overridden: bool = False
    animated: bool = False
    inherited_rotation: bool = False
    parent: str | None = None


def _geometry_motion(layer) -> bool:
    animations = getattr(layer, "animation", None)
    items = animations if isinstance(animations, list) else [animations]
    features = {
        feature
        for item in items
        if isinstance(item, AnimationSpec)
        for feature in _capability_features_for(item)
    }
    geometry = {"position", "rotation", "scale_x", "scale_y"}
    if not isinstance(layer, ImageLayer):
        geometry.add("scale")
    return bool(features & geometry)


def _rotated(frame: Affine) -> bool:
    return any(
        abs(value - target) > 1e-12
        for value, target in zip(
            (frame[0], frame[1], frame[3], frame[4]), (1, 0, 0, 1), strict=True
        )
    )


class _BackgroundTextEngine(TextEngine):
    """Replay background-only variants without glyphs erasing their backing."""

    def _draw_text(self, *args, **kwargs):
        pass


class ParentDiagnosticSources:
    """Keep padded local content until its final world warp; cache only this call."""

    def __init__(self, canvas: Canvas, measurements: list[LayerMeasurement]):
        self.canvas = canvas
        self.background_text = _BackgroundTextEngine(
            canvas._ctx, canvas._fonts, canvas._effects, canvas._images
        )
        self.plan = ParentRenderPlan(canvas)
        ancestors, _ = authored_parent_frames(self.plan.nodes)
        self.occurrences: dict[str, _Occurrence] = {}
        inherited_motion = {}
        for node in self.plan.order:
            inherited_motion[id(node)] = bool(
                node.parent is not None
                and (inherited_motion[id(node.parent)] or _geometry_motion(node.parent.layer))
            )
        for measured in measurements:
            key = id(measured.raw_layer)
            if key not in self.plan.nodes:
                continue
            node = self.plan.nodes[key]
            root = _Root(
                node,
                multiply(
                    multiply(ancestors[key], translate(*node.origin)),
                    translate(-node.padding, -node.padding),
                ),
                measured.layer_id,
            )
            animated = bool(node.layer.animation) or inherited_motion[id(node)]
            occurrence = _Occurrence(
                root,
                top=True,
                animated=animated or _has_counter(node.layer),
                inherited_rotation=_rotated(ancestors[key]),
                parent=node.layer.parent,
            )
            if isinstance(node.source, TextLayer):
                occurrence.text = settled_text_reference(canvas, node.source)
            self.occurrences[measured.layer_id] = occurrence
            if isinstance(node.source, GroupLayer):
                self._group(measured, node.source, root, animated, False)

    def _group(self, measured, group, root, animated, overridden, origin=None):
        placements, _ = self.canvas._groups.layout_group(group, origin)
        suppress = overridden or group.animation is not None
        for child_measured, (child, position, size) in zip(
            measured.children, placements, strict=True
        ):
            active = self.canvas._groups._without_child_animation(child) if suppress else child
            child_motion = animated or bool(getattr(active, "animation", None))
            occurrence = _Occurrence(
                root,
                start=len(root.operations),
                structural=True,
                overridden=suppress,
                animated=child_motion or _has_counter(active),
                inherited_rotation=self.occurrences[measured.layer_id].inherited_rotation,
            )
            self.occurrences[child_measured.layer_id] = occurrence
            if isinstance(active, GroupLayer):
                self._group(child_measured, active, root, child_motion, suppress, position)
            else:
                if isinstance(active, TextLayer):
                    effective = settled_text_reference(self.canvas, active)
                    occurrence.text = self.canvas._groups.place_text_child(
                        effective, position, size
                    )
                root.operations.append(_Placed(active, position, size))
            occurrence.end = len(root.operations)

    def decorate(self, measurements):
        def visit(measured):
            occurrence = self.occurrences.get(measured.layer_id)
            if occurrence is None:
                return measured
            children = tuple(visit(child) for child in measured.children)
            metadata = dict(measured.metadata)
            if "children" in metadata:
                metadata["children"] = children
            metadata["parent_world"] = True
            metadata["inherited_rotation"] = occurrence.inherited_rotation
            metadata["effective_animation"] = occurrence.animated
            return replace(measured, children=children, metadata=MappingProxyType(metadata))

        return [visit(item) for item in measurements]

    def handles(self, measured) -> bool:
        return measured.layer_id in self.occurrences

    def overridden(self, measured) -> bool:
        item = self.occurrences.get(measured.layer_id)
        return bool(item and item.overridden)

    def _paint_operation(self, surface, operation):
        self.canvas._groups._render_group_child(
            surface,
            operation.layer,
            operation.position,
            operation.size,
            time=None,
            apply_motion=False,
            sample_values=True,
        )

    def _surface(self, occurrence):
        if occurrence.top:
            return occurrence.root.node.image
        surface = Image.new("RGBA", occurrence.root.node.source_size)
        for operation in occurrence.root.operations[occurrence.start : occurrence.end]:
            self._paint_operation(surface, operation)
        return surface

    def _composite_surface(self, image, surface, root):
        if surface is None:
            return
        fragment = affine_fragment(surface, root.matrix, image.size)
        if fragment is not None:
            rendered, position = fragment
            image.alpha_composite(rendered, position)

    def composite(self, running, measured):
        occurrence = self.occurrences[measured.layer_id]
        self._composite_surface(running, self._surface(occurrence), occurrence.root)

    def alpha(self, measured):
        box = measured.bbox
        assert box is not None
        occurrence = self.occurrences[measured.layer_id]
        surface = self._surface(occurrence)
        fragment = (
            affine_fragment(
                surface, occurrence.root.matrix, (self.canvas.width, self.canvas.height)
            )
            if surface is not None
            else None
        )
        if fragment is None:
            return Image.new("L", (box.width, box.height))
        image, (x, y) = fragment
        return image.getchannel("A").crop((box.x - x, box.y - y, box.right - x, box.bottom - y))

    def _prefix(self, occurrence):
        root = occurrence.root
        if root.prefix is None or root.prefix_index > occurrence.start:
            root.prefix = Image.new("RGBA", root.node.source_size)
            root.prefix_index = 0
        while root.prefix_index < occurrence.start:
            self._paint_operation(root.prefix, root.operations[root.prefix_index])
            root.prefix_index += 1
        return root.prefix

    def composed_text(self, measured) -> bool:
        occurrence = self.occurrences[measured.layer_id]
        return occurrence.top and has_layer_composition(occurrence.root.node.source)

    def _text_coverage(self, layer, source, occurrence):
        """Separate opacity-free glyph coverage from boundary antialiasing."""
        size = occurrence.root.node.source_size
        glyphs = Image.new("RGBA", size)
        geometric = _with_motion_color(layer, "#FFFFFF").model_copy(update={"opacity": 1.0})
        self.canvas._text.render_text_layer(glyphs, geometric, staging_reference=source)
        world = self.canvas._create_canvas()
        self._composite_surface(world, glyphs, occurrence.root)
        coverage = world.getchannel("A")
        core = Image.new("L", size, 255)
        # Sample either side of a partial inverted mask, retaining its real
        # attenuation. A zero-opacity inverted mask has no visible boundary.
        for boundary, painter in ((source.clip, _clip_alpha), (source.mask, _mask_alpha)):
            if boundary is None:
                continue
            if painter is _mask_alpha and boundary.invert and boundary.opacity == 0:
                continue
            allow_empty = painter is _mask_alpha and boundary.invert and boundary.opacity < 1
            if painter is _mask_alpha:
                boundary = boundary.model_copy(update={"opacity": 1.0})
            edge = painter(self.canvas._ctx, size, boundary)
            core = ImageChops.multiply(
                core,
                edge.point(
                    lambda value, allow_empty=allow_empty: 255
                    if value >= 243 or allow_empty and value <= 12
                    else 0
                ),
            )
        local = Image.new("RGBA", size, "white")
        local.putalpha(core)
        world = self.canvas._create_canvas()
        self._composite_surface(world, local, occurrence.root)
        return coverage, world.getchannel("A")

    def _visible_text_treatment(self, running, foreground, coverage, boundary):
        """Remove glyph AA coverage, preserving owner/mask/color attenuation.

        Glyph alpha is normalized against a separate opaque reference, so thin
        affine text retains evidence without treating its fringes as faint ink.
        At solid glyph pixels this is the owner's actual paint over the scene;
        the separately composed own Background remains the contrast backing.
        """
        visible = Image.new("RGBA", running.size, "white")
        visible.alpha_composite(running)
        pixels, ink = visible.load(), foreground.load()
        geometry, edges = coverage.load(), boundary.load()
        assert pixels is not None and ink is not None and geometry is not None and edges is not None
        marker = Image.new("L", visible.size)
        samples = marker.load()
        assert samples is not None
        bounds = foreground.getbbox()
        if bounds is not None:
            floor = 64 if coverage.getextrema()[1] >= 64 else 1
            for y in range(bounds[1], bounds[3]):
                for x in range(bounds[0], bounds[2]):
                    if geometry[x, y] < floor or edges[x, y] < 243 or not ink[x, y][3]:
                        continue
                    opacity = min(1.0, ink[x, y][3] / geometry[x, y])
                    backdrop = cast(tuple[int, int, int, int], pixels[x, y])
                    pixels[x, y] = tuple(
                        round(ink[x, y][channel] * opacity + backdrop[channel] * (1 - opacity))
                        for channel in range(3)
                    ) + (255,)
                    samples[x, y] = 255
        visible.putalpha(marker)
        return visible

    def text_images(self, running, measured):
        occurrence = self.occurrences[measured.layer_id]
        source = occurrence.text
        assert source is not None
        content = source.content
        if isinstance(content, list):
            content = [part.model_copy(update={"effects": []}) for part in content]
        foreground_layer = source.model_copy(
            update={"content": content, "effects": [], "auto_scale": False}
        )
        foreground = self.canvas._create_canvas()
        local = Image.new("RGBA", occurrence.root.node.source_size)
        self.canvas._text.render_text_layer(local, foreground_layer, staging_reference=source)
        sampling = None
        if self.composed_text(measured):
            sampling = self._text_coverage(foreground_layer, source, occurrence)
            local = occurrence.root.node.compose_source(local)
        self._composite_surface(foreground, local, occurrence.root)
        local_backing = self._prefix(occurrence) if occurrence.structural else None
        effects = [effect for effect in source.effects if isinstance(effect, Background)]
        part_background = isinstance(source.content, list) and any(
            isinstance(effect, Background) for part in source.content for effect in part.effects
        )
        if effects or part_background:
            content = source.content
            if isinstance(content, list):
                content = [
                    part.model_copy(
                        update={
                            "color": "#00000000",
                            "fill": None,
                            "effects": [
                                effect for effect in part.effects if isinstance(effect, Background)
                            ],
                        }
                    )
                    for part in content
                ]
            variant = source.model_copy(
                update={
                    "content": content,
                    "color": "#00000000",
                    "fill": None,
                    "effects": effects,
                    "auto_scale": False,
                }
            )
            if local_backing is None:
                local_backing = Image.new("RGBA", occurrence.root.node.source_size)
            else:
                local_backing = local_backing.copy()
            self.background_text.render_text_layer(local_backing, variant, staging_reference=source)
        backing = running
        if local_backing is not None:
            backing = running.copy()
            if self.composed_text(measured):
                local_backing = occurrence.root.node.compose_source(local_backing)
            self._composite_surface(backing, local_backing, occurrence.root)
        if sampling is not None:
            foreground = self._visible_text_treatment(running, foreground, *sampling)
        return backing, foreground

    def repair_context(self, finding):
        if finding.code not in {"off-canvas", "layer-overlap", "edge-crowding", "near-alignment"}:
            return finding
        occurrence = self.occurrences.get(finding.layer_id)
        if occurrence is None:
            return finding
        position = (
            f"the layout or position of containing group '{occurrence.root.layer_id}'"
            if occurrence.structural
            else "this layer's parent-local position"
            if occurrence.parent
            else "this layer's authored position"
        )
        goal = {
            "off-canvas": "bring its world bounds inside the canvas",
            "layer-overlap": "separate the indicated world-space footprints",
            "edge-crowding": "increase clearance from the indicated world-space edge or overlay",
            "near-alignment": "align the indicated world-space edges",
        }[finding.code]
        suggestion = (
            "resize the local content or containing group layout first, "
            f"then adjust {position} to {goal}"
            if finding.suggestion.startswith("resize")
            else f"adjust {position} to {goal}"
        )
        message = (
            finding.message.replace(finding.suggestion, suggestion)
            if finding.suggestion
            else finding.message
        )
        return finding.model_copy(
            update={
                "suggestion": suggestion,
                "message": message,
                "measured": dict(
                    finding.measured,
                    coordinate_space="world",
                    position_space="group_layout"
                    if occurrence.structural
                    else "parent_local"
                    if occurrence.parent
                    else "canvas",
                ),
            }
        )
