"""Bounded native SVG stroke motion for the existing HTML timeline runtime."""

import math

from quickthumb._export_base import _motion_number
from quickthumb._path_geometry import flatten_path
from quickthumb._path_svg import _bounded_number, native_path_problem
from quickthumb.errors import RenderingError
from quickthumb.models import AnimationSpec, CubicBezierEasing, PathLayer, TrimOffsetTrack
from quickthumb.motion import (
    LayerState,
    Timeline,
    _has_spring_easing,
    _has_wiggle,
    compile_timeline,
)

_PROPERTIES = {"dash_offset", "trim_start", "trim_end", "trim_offset"}


def path_html_problem(layer: PathLayer) -> str | None:
    """Admit only one bounded stroke timeline whose complete trim window is representable."""
    if problem := native_path_problem(
        layer.model_copy(
            update={
                "animation": None,
                "trim_start": 0.0,
                "trim_end": 1.0,
            }
        )
    ):
        return problem
    if layer.stroke is None:
        return "native stroke motion requires a stroke"
    animation = layer.animation
    if animation is not None and (
        not isinstance(animation, AnimationSpec)
        or animation.tracks is None
        or any(track.type not in _PROPERTIES for track in animation.tracks)
    ):
        return "native stroke motion requires one stroke-property timeline"
    if _has_spring_easing(animation) or _has_wiggle(animation):
        return "native stroke motion does not support procedural easing or wiggle"
    vx, vy, vw, vh = layer.view_box or (0, 0, layer.width, layer.height)
    sx, sy = layer.width / vw, layer.height / vh
    try:
        contours = flatten_path(layer.d, (vx, vy), (sx, sy))
    except RenderingError:
        return "native stroke motion exceeds the bounded contour plan"
    if len(contours) != 1 or not any(
        a != b for a, b in zip(contours[0].points, contours[0].points[1:], strict=False)
    ):
        return "native stroke motion requires one nondegenerate contour"
    tracks = animation.tracks or () if animation is not None else ()
    trim = is_trim(layer)
    if trim:
        if contours[0].closed or layer.line_cap != "butt":
            return "native trim requires an open contour with butt caps"
        if (layer.dash_array and any(layer.dash_array)) or any(
            t.type == "dash_offset" for t in tracks
        ):
            return "native trim cannot preserve authored dashes after cutting"
    for track in tracks:
        if any(not _bounded_number(key.value, max(sx, sy)) for key in track.keyframes):
            return "native stroke motion exceeds numeric precision"
        easings = [
            animation.easing if animation is not None else None,
            *(key.easing for key in track.keyframes),
        ]
        if any(
            isinstance(easing, str)
            and easing.endswith("_back")
            or isinstance(easing, CubicBezierEasing)
            and any(y < 0 or y > 1 for y in easing.points[1::2])
            for easing in easings
        ):
            return "native stroke motion does not support overshooting easing"
    if trim:
        if (layer.trim_start, layer.trim_end) != (0, 1) and (
            layer.trim_start > layer.trim_end
            or layer.trim_start + layer.trim_offset < 0
            or layer.trim_end + layer.trim_offset > 1
        ):
            return "native trim requires a nonwrapping authored window before animation"
        bounds = {
            "trim_start": (layer.trim_start,) * 2,
            "trim_end": (layer.trim_end,) * 2,
            "trim_offset": (layer.trim_offset,) * 2,
        }
        for track in tracks:
            if track.type not in bounds:
                continue
            values = [key.value for key in track.keyframes]
            lo, hi = min(values), max(values)
            if isinstance(track, TrimOffsetTrack):
                before = bounds[track.type] if track.blend == "add" else (layer.trim_offset,) * 2
                lo, hi = before[0] + lo, before[1] + hi
            bounds[track.type] = (lo, hi)
        start, end, offset = (bounds[name] for name in ("trim_start", "trim_end", "trim_offset"))
        if start[1] > end[0] or start[0] + offset[0] < 0 or end[1] + offset[1] > 1:
            return "native trim requires a nonwrapping ordered window for every keyframe"
    if animation is not None and (
        compile_timeline(animation).events[0].duration > 4096 / 120
        or len(path_html_times(layer)) > 4097
    ):
        return "native stroke motion exceeds the 4097-stop HTML plan"
    try:
        stroke_style(layer, LayerState())
        if animation is not None:
            path_html_stops(layer)
    except RenderingError:
        return "native stroke phase exceeds numeric precision"
    return None


def is_trim(layer: PathLayer) -> bool:
    return (
        layer.trim_start != 0
        or layer.trim_end != 1
        or (
            isinstance(layer.animation, AnimationSpec)
            and any(track.type.startswith("trim_") for track in layer.animation.tracks or ())
        )
    )


def path_html_times(layer: PathLayer) -> set[float]:
    assert isinstance(layer.animation, AnimationSpec)
    event = compile_timeline(layer.animation).events[0]
    intervals = max(1, math.ceil(event.duration * 120))
    times = {event.duration * index / intervals for index in range(intervals + 1)}
    for track in event.tracks:
        times.update(key.time for key in track.keyframes)
        for left, right in zip(track.keyframes, track.keyframes[1:], strict=False):
            if left.hold:
                times.add(math.nextafter(right.time, -math.inf))
    return times


def stroke_style(layer: PathLayer, state: LayerState) -> dict[str, str]:
    values = {}
    phase = layer.dash_offset + state.dash_offset
    if is_trim(layer):
        start = layer.trim_start if state.trim_start is None else state.trim_start
        end = layer.trim_end if state.trim_end is None else state.trim_end
        offset = layer.trim_offset + state.trim_offset
        if start == 0 and end == 1:
            offset = 0
        span = end - start
        values["stroke-dasharray"] = f"{_motion_number(span)}px {_motion_number(2 - span)}px"
        phase = -start - offset
    _, _, vw, vh = layer.view_box or (0, 0, layer.width, layer.height)
    if not _bounded_number(phase, max(layer.width / vw, layer.height / vh)):
        raise RenderingError("native stroke phase exceeds numeric precision", path="/dash_offset")
    values["stroke-dashoffset"] = _motion_number(phase) + "px"
    return values


def path_html_stops(layer: PathLayer) -> tuple[dict[float, dict[str, str]], dict[str, str]]:
    assert isinstance(layer.animation, AnimationSpec)
    event = compile_timeline(layer.animation).events[0]
    timeline = Timeline(events=(event.model_copy(update={"start": 0.0, "delay": 0.0}),))
    stops = {
        100 * time / event.duration: stroke_style(layer, timeline.sample(time))
        for time in sorted(path_html_times(layer))
    }
    return stops, stops[100.0]
