"""Document adapters for parent-linked scenes: static pixels or baked affine CSS."""

from __future__ import annotations

import base64
import math
from dataclasses import dataclass
from io import BytesIO
from typing import TYPE_CHECKING

from quickthumb._export_base import RasterFragment, _motion_number
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

PARENT_PROPERTIES = {
    f"--qt-parent-{name}": "1" if name in {"a", "e", "opacity"} else "0"
    for name in ("a", "b", "c", "d", "e", "f", "opacity")
}
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


def parent_css_values(node, sample) -> dict[str, str]:
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
    values = {
        name: _motion_number(value)
        for name, value in zip(PARENT_PROPERTIES, (*matrix, opacity), strict=True)
    }
    return values


class ParentHtmlAdapter:
    """Bake independent numeric coefficients; CSS must not decompose matrices."""

    def __init__(self, canvas: Canvas, times: tuple[float, ...]):
        from quickthumb._export_video import _SlideAnimator

        self.animator = _SlideAnimator(canvas, {})
        self.plan = next(
            unit.parent_plan for unit in self.animator._units if unit.parent_plan is not None
        )
        self.times = times
        visible = [node for node in self.plan.nodes.values() if node.image is not None]
        self.values = {id(node): [] for node in visible}
        for time in times:
            sample = self.plan.sample(time)
            for node in visible:
                self.values[id(node)].append(parent_css_values(node, sample[id(node)]))
        self.registered = False

    def emit(self, exporter, layer) -> None:
        node = self.plan.nodes[id(layer)]
        if isinstance(layer, NullLayer) or node.image is None:
            return
        if not self.registered:
            exporter._keyframes.extend(
                f'@property {name}{{syntax:"<number>";inherits:false;initial-value:{value}}}'
                for name, value in PARENT_PROPERTIES.items()
            )
            self.registered = True
        values = self.values[id(node)]
        element_id = exporter._make_id()
        duration = self.times[-1]
        if duration > 0:
            keyframe = f"{exporter._keyframe_prefix}{exporter._next_kf}"
            exporter._next_kf += 1
            exporter._keyframes.append(
                "@keyframes "
                + keyframe
                + "{"
                + "".join(
                    _motion_number((time / duration) * 100)
                    + "%{"
                    + ";".join(f"{name}:{value}" for name, value in stop.items())
                    + "}"
                    for time, stop in zip(self.times, values, strict=True)
                )
                + "}"
            )
            exporter._timeline.append(
                {
                    "t": [element_id],
                    "k": keyframe,
                    "d": duration,
                    "delay": 0,
                    "tr": "with_previous" if exporter._timeline else "after_previous",
                    "a": "transform",
                    "e": "linear",
                    "initial": values[0],
                    "final": values[-1],
                }
            )
        buffer = BytesIO()
        node.image.save(buffer, format="PNG")
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        style = (
            f"position:absolute;left:0;top:0;width:{node.image.width}px;height:{node.image.height}px;"
            + ";".join(f"{name}:{value}" for name, value in values[0].items())
            + ";"
            "transform-origin:0 0;transform:matrix(var(--qt-parent-a),var(--qt-parent-d),"
            "var(--qt-parent-b),var(--qt-parent-e),var(--qt-parent-c),var(--qt-parent-f));"
            "opacity:var(--qt-parent-opacity);"
        )
        # Whole-stage Morph is disabled for parent scenes; do not expose keys
        # that could otherwise invite the runtime to replace this matrix.
        exporter._body.append(
            f'<img id="{element_id}" data-qt-parent-node="1" style="{style}" '
            f'src="data:image/png;base64,{encoded}" alt="">'
        )

    def emit_clock(self, exporter) -> None:
        """Retain timing even when every graph source is null or transparent."""
        if exporter._timeline or self.times[-1] == 0:
            return
        element_id = exporter._make_id()
        keyframe = f"{exporter._keyframe_prefix}{exporter._next_kf}"
        exporter._next_kf += 1
        exporter._keyframes.append(f"@keyframes {keyframe}" + "{from{opacity:0}to{opacity:0}}")
        exporter._timeline.append(
            {
                "t": [element_id],
                "k": keyframe,
                "d": self.times[-1],
                "delay": 0,
                "tr": "after_previous",
                "a": "transform",
                "e": "linear",
                "initial": {},
                "final": {},
            }
        )
        exporter._body.append(
            f'<span id="{element_id}" data-qt-parent-clock="1" aria-hidden="true" '
            'style="position:absolute;width:0;height:0;opacity:0;pointer-events:none"></span>'
        )
