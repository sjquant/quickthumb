"""Full-affine rendering for explicit, top-level transform hierarchies.

An authored source keeps its established static appearance. ``body_to_baked``
expresses that engine's static-rotation framing, while ``paint`` maps its baked
pixels to the output. Children use ``paint @ body_to_baked``; the distinction
avoids rotating an already-baked source twice and preserves inherited shear.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from weakref import proxy

from PIL import Image

from quickthumb._base import apply_alignment, expanded_rotation_size, parse_coordinate
from quickthumb._export_base import (
    _blur_geometry,
    _with_motion_color,
    apply_canonical_alpha,
    color_group_has_backdrop,
    is_backdrop_dependent,
)
from quickthumb._measurements import LayerMeasurement, LayerMeasurementEngine
from quickthumb._parenting import validate_parent_graph
from quickthumb.errors import RenderingError
from quickthumb.models import (
    AnimationSpec,
    Background,
    ChartLayer,
    Glow,
    GroupLayer,
    ImageLayer,
    NullLayer,
    QRCodeLayer,
    Shadow,
    Stroke,
    TextLayer,
    VideoLayer,
)
from quickthumb.motion import LayerState, transform_matrix

if TYPE_CHECKING:
    from quickthumb.canvas import Canvas

Affine = tuple[float, float, float, float, float, float]
IDENTITY: Affine = (1, 0, 0, 0, 1, 0)


def multiply(left: Affine, right: Affine) -> Affine:
    """Compose affine matrices without decomposing their shear or reflection."""
    a, b, c, d, e, f = left
    g, h, i, j, k, end = right
    result = (
        a * g + b * j,
        a * h + b * k,
        a * i + b * end + c,
        d * g + e * j,
        d * h + e * k,
        d * i + e * end + f,
    )
    if not all(math.isfinite(value) for value in result):
        raise RenderingError("Parent transform matrix exceeds finite coordinates")
    return result


def translate(x: float, y: float) -> Affine:
    return (1, 0, x, 0, 1, y)


def affine_state(state: LayerState, size=(0, 0)) -> Affine:
    matrix = transform_matrix(state, size)
    return (*matrix[0], *matrix[1])


def participating_layers(canvas: Canvas) -> dict[int, Any]:
    """Return linked layers and every referenced top-level ancestor."""
    validate_parent_graph(canvas.layers)
    by_name = {
        getattr(layer, "id", None): layer for layer in canvas.layers if getattr(layer, "id", None)
    }
    result: dict[int, Any] = {}
    for layer in canvas.layers:
        if getattr(layer, "parent", None) is None:
            continue
        current = layer
        while id(current) not in result:
            result[id(current)] = current
            parent = getattr(current, "parent", None)
            if parent is None:
                break
            current = by_name[parent]
    return result


def _animated_descendant(layer) -> bool:
    return any(
        getattr(child, "animation", None) is not None or _animated_descendant(child)
        for child in getattr(layer, "children", ())
    )


def parent_rendering_problem(canvas: Canvas) -> str | None:
    """Describe unsupported source/composition boundaries without rendering assets."""
    nodes = participating_layers(canvas)
    last_backdrop = max(
        (
            index
            for index, layer in enumerate(canvas.layers)
            if is_backdrop_dependent(layer) or color_group_has_backdrop(layer)
        ),
        default=-1,
    )
    for index, layer in enumerate(canvas.layers):
        if id(layer) not in nodes:
            continue
        if not isinstance(layer, NullLayer) and index <= last_backdrop:
            return "Parent-linked imagery on or below backdrop-dependent layers is unsupported"
        if getattr(layer, "clip", None) is not None or getattr(layer, "mask", None) is not None:
            return "Parent-linked clip and mask coordinate spaces are not supported yet"
        if _has_counter(layer):
            return "Parent-linked animated text values need a stable source-layout adapter"
        if isinstance(layer, GroupLayer):
            if any(_has_composition(child) for child in layer.children):
                return "Parent-linked groups with clipped or masked descendants are unsupported"
            if layer.animation is None and _animated_descendant(layer):
                return "Parent-linked groups with independent descendant animations are unsupported"
        animation = getattr(layer, "animation", None)
        items = animation if isinstance(animation, list) else [animation]
        if any(isinstance(item, AnimationSpec) and item.stagger is not None for item in items):
            return "Parent-linked stagger has multiple local transforms and is unsupported"
    return None


def validate_parent_raster(canvas: Canvas) -> None:
    problem = parent_rendering_problem(canvas)
    if problem:
        raise RenderingError(problem, code="unsupported_parent_combination")


def _has_counter(layer) -> bool:
    return bool(
        isinstance(layer, TextLayer)
        and layer.value is not None
        or any(_has_counter(child) for child in getattr(layer, "children", ()))
    )


def _has_composition(layer) -> bool:
    return bool(
        getattr(layer, "clip", None) is not None
        or getattr(layer, "mask", None) is not None
        or any(_has_composition(child) for child in getattr(layer, "children", ()))
    )


def _padding(canvas: Canvas, layer) -> int:
    """Bound exterior source effects before final canvas clipping."""
    padding = 2
    for effect in getattr(layer, "effects", ()):
        if isinstance(effect, Background):
            padding = max(
                padding, effect.padding if isinstance(effect.padding, int) else max(effect.padding)
            )
        elif isinstance(effect, Stroke):
            padding = max(padding, effect.width)
        elif isinstance(effect, Shadow):
            padding = max(
                padding,
                abs(effect.offset_x) + 3 * effect.blur_radius,
                abs(effect.offset_y) + 3 * effect.blur_radius,
            )
        elif isinstance(effect, Glow):
            padding = max(padding, 3 * effect.radius)
    for child in (
        *getattr(layer, "children", ()),
        *(
            layer.content
            if isinstance(layer, TextLayer) and isinstance(layer.content, list)
            else ()
        ),
    ):
        padding = max(padding, _padding(canvas, child))
    if isinstance(layer, TextLayer):
        # Font ink is not confined to the logical layout box: italics overhang
        # horizontally and alignment can place ascenders/descenders beyond it.
        # Bound that extra ink separately from effect spread, including rich runs.
        ink_margin = 0
        for text, font, _ in canvas._text.iter_text_runs(layer):
            for line in text.split("\n"):
                bounds = font.getbbox(line)
                if bounds:
                    ink_margin = max(
                        ink_margin,
                        math.ceil(
                            max(
                                abs(bounds[0]),
                                max(0, bounds[2] - font.getlength(line)),
                                abs(bounds[1]),
                                abs(bounds[3]),
                            )
                        ),
                    )
        padding += ink_margin
    return padding + 2


def _opaque_reference(layer):
    updates = {}
    if hasattr(layer, "opacity"):
        updates["opacity"] = 1.0
    if isinstance(layer, GroupLayer):
        updates["children"] = [_opaque_reference(child) for child in layer.children]
    return layer.model_copy(update=updates) if updates else layer


@dataclass(frozen=True)
class ParentGeometry:
    """Authored static source frame, independent of its pixel preparation."""

    layer: Any
    origin: tuple[int, int]
    body_size: tuple[int, int]
    body_to_baked: Affine


def parent_geometry(
    canvas: Canvas, layer, measured: LayerMeasurement | None = None
) -> ParentGeometry:
    if isinstance(layer, NullLayer):
        origin = (
            parse_coordinate(layer.position[0], canvas.width),
            parse_coordinate(layer.position[1], canvas.height),
        )
        return ParentGeometry(
            layer, origin, (0, 0), affine_state(LayerState(rotation=layer.rotation))
        )
    measure = LayerMeasurementEngine(canvas._ctx, canvas._groups, canvas._text)
    if measured is None:
        measured = measure.measure_layer(layer, index=0, order=0, path=(0,))
    box = measured.metadata.get("layout_bbox", measured.bbox)
    assert box is not None
    body_size = (box.width, box.height)
    origin = (box.x, box.y)
    if isinstance(layer, VideoLayer):
        body_size = expanded_rotation_size((layer.width, layer.height), layer.rotation)
        origin = (
            parse_coordinate(layer.position[0], canvas.width),
            parse_coordinate(layer.position[1], canvas.height),
        )
        if layer.align:
            origin = apply_alignment(*origin, body_size, layer.align)
    if isinstance(layer, TextLayer):
        layer = canvas._text.effective_layer(layer)
    if not getattr(layer, "rotation", 0):
        return ParentGeometry(layer, origin, body_size, IDENTITY)
    unrotated = layer.model_copy(update={"rotation": 0.0})
    unrotated_box = measure.measure_layer(unrotated, index=0, order=0, path=(0,)).bbox
    assert unrotated_box is not None
    rotation = affine_state(LayerState(rotation=layer.rotation))
    body_to_baked = multiply(
        translate(body_size[0] / 2, body_size[1] / 2),
        multiply(rotation, translate(-unrotated_box.width / 2, -unrotated_box.height / 2)),
    )
    return ParentGeometry(layer, origin, body_size, body_to_baked)


def parent_order(layers: dict[int, Any]) -> list[int]:
    """Return parent-first keys for an already validated top-level graph."""
    names = {layer.id: key for key, layer in layers.items() if layer.id}
    result = []
    visited = set()
    for key in layers:
        pending = []
        while key not in visited:
            pending.append(key)
            visited.add(key)
            parent = layers[key].parent
            if parent is None:
                break
            key = names[parent]
        result.extend(reversed(pending))
    return result


def authored_parent_frames(geometry) -> tuple[dict[int, Affine], dict[int, Affine]]:
    """Compose static ancestor and child frames without evaluating animation."""
    layers = {key: item.layer for key, item in geometry.items()}
    names = {layer.id: key for key, layer in layers.items() if layer.id}
    ancestors: dict[int, Affine] = {}
    worlds: dict[int, Affine] = {}
    for key in parent_order(layers):
        item = geometry[key]
        ancestor = worlds[names[item.layer.parent]] if item.layer.parent else IDENTITY
        ancestors[key] = ancestor
        worlds[key] = multiply(multiply(ancestor, translate(*item.origin)), item.body_to_baked)
    return ancestors, worlds


@dataclass
class ParentNode:
    plan: ParentRenderPlan
    layer: Any
    origin: tuple[float, float]
    body_to_baked: Affine
    source: Any = None
    source_size: tuple[int, int] = (0, 0)
    padding: int = 0
    pivot_box: tuple[float, float, float, float] = (0, 0, 0, 0)
    image: Image.Image | None = None
    parent: ParentNode | None = None
    unit: Any = None

    def render_source(
        self, time: float | None = None, color: str | None = None, *, reference=False
    ):
        if isinstance(self.layer, NullLayer):
            return None
        surface = Image.new("RGBA", self.source_size)
        source = (
            _with_motion_color(_opaque_reference(self.source), "#FFFFFF")
            if reference
            else _with_motion_color(self.source, color)
        )
        canvas = self.plan.canvas
        if reference and isinstance(source, VideoLayer):
            time = source.start
        previous = canvas._ctx.motion_time
        canvas._ctx.motion_time = time
        try:
            if isinstance(source, GroupLayer):
                canvas._groups.render_group_layer(surface, source, time=time, sample_values=True)
            else:
                canvas._render_layer(surface, source, time)
        finally:
            canvas._ctx.motion_time = previous
        return surface


class ParentRenderPlan:
    """Prepared local sources and topologically ordered parent frames for one scene."""

    def __init__(self, canvas: Canvas):
        self.canvas = canvas
        validate_parent_raster(canvas)
        layers = participating_layers(canvas)
        self.nodes = {key: self._prepare(layer) for key, layer in layers.items()}
        names = {node.layer.id: node for node in self.nodes.values() if node.layer.id}
        for node in self.nodes.values():
            node.parent = names.get(node.layer.parent)
        self.order = [self.nodes[key] for key in parent_order(layers)]

    def _prepare(self, layer) -> ParentNode:
        canvas = self.canvas
        geometry = parent_geometry(canvas, layer)
        layer = geometry.layer
        origin, body_size = geometry.origin, geometry.body_size
        body_to_baked = geometry.body_to_baked
        if isinstance(layer, NullLayer):
            return ParentNode(proxy(self), layer, origin, body_to_baked)
        padding = _padding(canvas, layer)
        # Source placement is local, but the existing render context continues
        # to resolve percentages and text wrapping against the authored canvas.
        if isinstance(layer, TextLayer):
            source = canvas._groups.place_text_child(layer, (padding, padding), body_size)
        else:
            source = layer.model_copy(update={"position": (padding, padding), "align": None})
        node = ParentNode(
            proxy(self),
            layer,
            origin,
            body_to_baked,
            source,
            (max(1, body_size[0] + 2 * padding), max(1, body_size[1] + 2 * padding)),
            padding,
        )
        reference = node.render_source(reference=True)
        assert reference is not None
        bounds = reference.getbbox()
        if bounds is None:
            node.pivot_box = (0, 0, *body_size)
        else:
            node.pivot_box = (
                bounds[0] - padding,
                bounds[1] - padding,
                bounds[2] - bounds[0],
                bounds[3] - bounds[1],
            )
        node.image = node.render_source()
        if node.image is not None and node.image.getbbox() is None:
            node.image = None
        return node

    def sample(self, time: float):
        from quickthumb._export_video import _unit_state

        result = {}
        for node in self.order:
            state = _unit_state(node.unit, time)
            motion = (
                state.canonical.layer if state.canonical else LayerState(anchor=node.layer.anchor)
            )
            uniform = (
                motion.scale if not isinstance(node.layer, ImageLayer) and motion.scale > 0 else 1.0
            )
            left, top, width, height = node.pivot_box
            delta = multiply(
                translate(left, top),
                multiply(
                    affine_state(motion.with_values(scale=uniform), (width, height)),
                    translate(-left, -top),
                ),
            )
            parent_world = result[id(node.parent)][1] if node.parent else IDENTITY
            paint = multiply(parent_world, multiply(translate(*node.origin), delta))
            world = multiply(paint, node.body_to_baked)
            collapsed = (
                (result[id(node.parent)][3] if node.parent else False)
                or motion.scale_x == 0
                or motion.scale_y == 0
            )
            result[id(node)] = (paint, world, state, collapsed)
        return result

    def composite(
        self, node: ParentNode, frame: Image.Image, time: float, samples, render_scale: float
    ):
        from quickthumb._export_video import _animation_reveal

        paint, _, state, collapsed = samples[id(node)]
        if state.hidden or collapsed or isinstance(node.layer, NullLayer):
            return
        motion = state.canonical.layer if state.canonical else LayerState()
        image = (
            node.render_source(time, motion.color)
            if node.unit.component_duration > 0
            or node.unit.color_motion
            and motion.color is not None
            else node.image
        )
        if image is None:
            return
        if state.canonical:
            image = apply_canonical_alpha(
                image,
                motion.with_values(
                    opacity=motion.opacity * state.canonical.alpha_scale,
                    clip_progress=1.0,
                ),
            )
            progress = (
                1.0
                if isinstance(node.layer, (ChartLayer, QRCodeLayer))
                else min(motion.clip_progress, state.canonical.clip_scale)
            )
            if image is not None and progress < 1:
                width = round(node.pivot_box[2] * max(0, progress))
                if width <= 0:
                    return
                cutoff = round(node.pivot_box[0] + node.padding) + width + 1
                alpha = image.getchannel("A")
                alpha.paste(0, (max(0, min(image.width, cutoff)), 0, image.width, image.height))
                image = image.copy()
                image.putalpha(alpha)
        elif state.reveal:
            effect, progress = state.reveal
            bounds = image.getbbox()
            if bounds is None:
                return
            revealed = _animation_reveal(image.crop(bounds), effect, progress, node.unit.seed)
            if revealed is None:
                return
            image = Image.new("RGBA", node.source_size)
            image.paste(revealed, bounds[:2])
        if image is None:
            return
        matrix = multiply(paint, translate(-node.padding, -node.padding))
        margin = math.ceil(3 * motion.blur * render_scale)
        rendered = affine_fragment(
            image, matrix, frame.size, render_scale=render_scale, margin=margin
        )
        if rendered is None:
            return
        image, pos = rendered
        image, spread = _blur_geometry(image, motion.blur * render_scale)
        frame.alpha_composite(image, (pos[0] - spread, pos[1] - spread))


def affine_fragment(
    image: Image.Image, matrix: Affine, size: tuple[int, int], *, render_scale=1.0, margin=0
):
    """Warp once through the full matrix, bounded by the final output viewport."""
    a, b, c, d, e, f = (value * render_scale for value in matrix)
    determinant = a * e - b * d
    if determinant == 0:
        return None
    if not math.isfinite(determinant):
        raise RenderingError("Parent transform determinant exceeds finite coordinates")
    corners = [
        (a * x + b * y + c, d * x + e * y + f)
        for x, y in ((0, 0), (image.width, 0), (0, image.height), image.size)
    ]
    if not all(math.isfinite(value) for point in corners for value in point):
        raise RenderingError("Parent transform bounds exceed finite coordinates")
    left = max(-margin, math.floor(min(point[0] for point in corners)))
    top = max(-margin, math.floor(min(point[1] for point in corners)))
    right = min(size[0] + margin, math.ceil(max(point[0] for point in corners)))
    bottom = min(size[1] + margin, math.ceil(max(point[1] for point in corners)))
    if right <= left or bottom <= top:
        return None
    if a == e == 1 and b == d == 0 and float(c).is_integer() and float(f).is_integer():
        # Preserve exact straight-alpha source bytes for an integral translation;
        # an unnecessary RGBA affine pass would round through premultiplied alpha.
        return image.crop((left - int(c), top - int(f), right - int(c), bottom - int(f))), (
            left,
            top,
        )
    ia, ib, id_, ie = e / determinant, -b / determinant, -d / determinant, a / determinant
    inverse = (ia, ib, ia * (left - c) + ib * (top - f), id_, ie, id_ * (left - c) + ie * (top - f))
    return image.transform(
        (right - left, bottom - top),
        Image.Transform.AFFINE,
        inverse,
        resample=Image.Resampling.BICUBIC,
    ), (left, top)
