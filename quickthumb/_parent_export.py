"""Document adapters for parent-linked scenes: static pixels or baked affine CSS."""

from __future__ import annotations

import math
from dataclasses import dataclass
from io import BytesIO
from typing import TYPE_CHECKING

from quickthumb._export_base import RasterFragment
from quickthumb._parent_render import (
    multiply,
    parent_rendering_problem,
    participating_layers,
    translate,
)
from quickthumb.models import (
    AnimationSpec,
    ChartLayer,
    ImageLayer,
    NullLayer,
    QRCodeLayer,
    VideoLayer,
)
from quickthumb.motion import TimelineEvent, compile_timeline

if TYPE_CHECKING:
    from quickthumb.canvas import Canvas

_GEOMETRY_TRACKS = {"position", "rotation", "scale", "scale_x", "scale_y", "opacity"}
MAX_PARENT_STOPS = 4097


def static_parent_fragment(canvas: Canvas) -> RasterFragment:
    """Capture the complete authored still through the shared raster adapter."""
    image = canvas._render_to_image()
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return RasterFragment(buffer.getvalue(), 0, 0, image.width, image.height)


def _has_animation(layer) -> bool:
    return bool(getattr(layer, "animation", None)) or any(
        _has_animation(child) for child in getattr(layer, "children", ())
    )


MAX_PARENT_ROWS = 32768
MAX_PARENT_EVALUATIONS = 1048576


@dataclass(frozen=True)
class ParentHtmlSampling:
    times: tuple[float, ...] = ()
    problem: str | None = None


def _static_source(layer, *, root=True):
    if isinstance(layer, VideoLayer) or getattr(layer, "value", None) is not None:
        return False
    if not root and getattr(layer, "animation", None) is not None:
        return False
    return all(_static_source(child, root=False) for child in getattr(layer, "children", ()))


def parent_html_sampling(canvas: Canvas) -> ParentHtmlSampling:
    """Bound a shared clock without rendering sources or allocating sample rows."""
    if problem := parent_rendering_problem(canvas):
        return ParentHtmlSampling(problem=problem)
    nodes = participating_layers(canvas)
    events = []
    for layer in canvas.layers:
        animation = getattr(layer, "animation", None)
        if id(layer) not in nodes:
            if _has_animation(layer):
                return ParentHtmlSampling(
                    problem="HTML parent baking requires no unrelated animation"
                )
            continue
        if not _static_source(layer):
            return ParentHtmlSampling(problem="HTML parent baking requires static local sources")
        if isinstance(layer, (ChartLayer, QRCodeLayer)) and animation is not None:
            return ParentHtmlSampling(
                problem="HTML parent baking cannot sample visualization sources"
            )
        specs = animation if isinstance(animation, list) else [animation] if animation else []
        if len(specs) > 1:
            return ParentHtmlSampling(problem="HTML parent baking supports one track spec per node")
        for spec in specs:
            if (
                not isinstance(spec, AnimationSpec)
                or spec.tracks is None
                or spec.stagger is not None
            ):
                return ParentHtmlSampling(problem="HTML parent baking supports track-only motion")
            if any(track.type not in _GEOMETRY_TRACKS for track in spec.tracks):
                return ParentHtmlSampling(
                    problem="HTML parent baking supports geometry/opacity only"
                )
            if any(getattr(track, "auto_orient", False) for track in spec.tracks):
                return ParentHtmlSampling(
                    problem="HTML parent baking cannot interpolate heading jumps"
                )
            if len({track.type for track in spec.tracks}) != len(spec.tracks):
                return ParentHtmlSampling(
                    problem="HTML parent baking supports one track per property"
                )
            axes = [track for track in spec.tracks if track.type in {"scale_x", "scale_y"}]
            if axes and (
                (spec.easing or "").endswith("_back")
                or any(
                    min(key.value for key in track.keyframes)
                    <= 0
                    <= max(key.value for key in track.keyframes)
                    for track in axes
                )
            ):
                # Raster propagates exact local collapse independently of its
                # floating-point world matrix. CSS cannot retain that flag
                # without changing the runtime or smearing adjacent samples.
                return ParentHtmlSampling(
                    problem="HTML parent baking cannot guarantee axis collapse"
                )
            scales = [track for track in spec.tracks if track.type == "scale"]
            if scales and (
                isinstance(layer, ImageLayer)
                or (spec.easing or "").endswith("_back")
                or any(key.value <= 0 for track in scales for key in track.keyframes)
            ):
                return ParentHtmlSampling(
                    problem="HTML parent baking requires continuous uniform scale"
                )
            event = compile_timeline(spec).events[0]
            if event.trigger is not None or event.active_start != 0:
                return ParentHtmlSampling(
                    problem="HTML parent baking requires one automatic zero-start clock"
                )
            events.append(event)
    times = _parent_sample_times(events)
    if times is None:
        return ParentHtmlSampling(problem="HTML parent baking exceeds the 4097-stop sampling bound")
    if len(nodes) * len(times) > MAX_PARENT_EVALUATIONS:
        return ParentHtmlSampling(problem="HTML parent baking exceeds 1048576 graph evaluations")
    sources = sum(not isinstance(layer, NullLayer) for layer in nodes.values())
    if sources * len(times) > MAX_PARENT_ROWS:
        return ParentHtmlSampling(problem="HTML parent baking exceeds the 32768 source-row bound")
    return ParentHtmlSampling(times=times)


def _parent_sample_times(events: list[TimelineEvent]) -> tuple[float, ...] | None:
    """Retain knots/interior detail and prevent full-turn temporal aliasing.

    Rotation subdivisions bound the sum of authored angular changes across the
    whole graph to three degrees per interval, using a conservative derivative
    bound of six for the current fixed easing registry (one for linear). This
    is not a general screen-space error bound: matrix interpolation remains an
    approximation, particularly for position paths and composed scale products.
    """
    duration = max((event.end for event in events), default=0.0)
    knots = {0.0, duration}
    rotation_segments = []
    for event in events:
        knots.add(event.end)
        for track in event.tracks:
            knots.update(key.time for key in track.keyframes)
            if len(knots) > MAX_PARENT_STOPS:
                return None
            if track.property == "rotation":
                for first, second in zip(track.keyframes, track.keyframes[1:], strict=False):
                    rate = abs(second.value - first.value) / (second.time - first.time)
                    rotation_segments.append(
                        (
                            first.time,
                            second.time,
                            rate
                            * (1 if (event.options.get("easing") or "linear") == "linear" else 6),
                        )
                    )
    ordered = sorted(knots)
    times = set(knots)
    for start, end in zip(ordered, ordered[1:], strict=False):
        rate = sum(rate for left, right, rate in rotation_segments if left < end and right > start)
        angle = rate * (end - start)
        if not math.isfinite(angle) or angle > 3 * MAX_PARENT_STOPS:
            return None
        # Interior samples keep short closed paths and compound motion visible,
        # even when an interval is shorter than one nominal 120Hz frame.
        intervals = max(8, math.ceil(angle / 3))
        if len(times) + intervals - 1 > MAX_PARENT_STOPS:
            return None
        times.update(start + (end - start) * (index / intervals) for index in range(1, intervals))
    available = MAX_PARENT_STOPS - len(times)
    intervals = min(available + 1, max(1, math.ceil(min(duration, 4096 / 120) * 120)))
    times.update(duration * (index / intervals) for index in range(1, intervals))
    return tuple(sorted(times))


@dataclass(frozen=True)
class ParentHtmlSource:
    png: bytes
    width: int
    height: int
    # Each row is (a, b, c, d, e, f, opacity) in shared-clock order.
    rows: tuple[tuple[float, ...], ...]


@dataclass(frozen=True)
class BakedParentHtml:
    times: tuple[float, ...]
    layer_ids: frozenset[int]
    sources: dict[int, ParentHtmlSource]


def _parent_row(node, sample) -> tuple[float, ...]:
    paint, _, state, _ = sample
    matrix = multiply(paint, translate(-node.padding, -node.padding))
    opacity = (
        0.0
        if state.hidden
        else (
            max(0.0, min(1.0, state.canonical.layer.opacity)) * state.canonical.alpha_scale
            if state.canonical
            else 1.0
        )
    )
    return (*matrix, opacity)


def bake_parent_html(canvas: Canvas, times: tuple[float, ...]) -> BakedParentHtml:
    """Bake detached source pixels and affine rows keyed by authored layer identity."""
    from quickthumb._export_video import _SlideAnimator

    # Nodes weakly reference their animation units, so keep the animator alive
    # until every sample has been collected. No graph objects escape the bake.
    animator = _SlideAnimator(canvas, {})
    plan = next(unit.parent_plan for unit in animator._units if unit.parent_plan is not None)
    visible = {layer_id: node for layer_id, node in plan.nodes.items() if node.image is not None}
    rows: dict[int, list[tuple[float, ...]]] = {layer_id: [] for layer_id in visible}
    for time in times:
        sample = plan.sample(time)
        for layer_id, node in visible.items():
            rows[layer_id].append(_parent_row(node, sample[id(node)]))
    sources = {}
    for layer_id, node in visible.items():
        buffer = BytesIO()
        node.image.save(buffer, format="PNG")
        sources[layer_id] = ParentHtmlSource(
            buffer.getvalue(), node.image.width, node.image.height, tuple(rows[layer_id])
        )
    return BakedParentHtml(times, frozenset(plan.nodes), sources)
