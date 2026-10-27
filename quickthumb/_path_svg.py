"""Shared native-SVG admission bounds for path exporters and capability reporting."""

import math

from quickthumb._export_base import _motion_number
from quickthumb._path_geometry import parse_path
from quickthumb.models import LinearGradient, PathLayer


def native_path_problem(layer: PathLayer) -> str | None:
    """Keep native coordinates within conservative float32 range and 1/8-pixel precision."""
    vx, vy, vw, vh = layer.view_box or (0, 0, layer.width, layer.height)
    sx, sy = layer.width / vw, layer.height / vh
    segments = parse_path(layer.d)
    values = [
        (layer.width, 1.0),
        (layer.height, 1.0),
        (1 / sx, layer.width * sx),
        (1 / sy, layer.height * sy),
        (vx, sx),
        (vy, sy),
        (vw, sx),
        (vh, sy),
    ]
    for segment in segments:
        values.extend(
            (value, scale)
            for point in segment.points
            for value, scale in zip(point, (sx, sy), strict=True)
        )
        if segment.arc:
            rx, ry, rotation, _, _ = segment.arc
            values.extend(
                (
                    (rx, sx),
                    (ry, sy),
                    (rotation % 360, max(abs(rx * sx), abs(ry * sy)) * math.pi / 180),
                )
            )
    values.extend(
        (
            (sx, max(abs(vx), abs(vw), *(abs(p[0]) for s in segments for p in s.points))),
            (sy, max(abs(vy), abs(vh), *(abs(p[1]) for s in segments for p in s.points))),
        )
    )
    if layer.stroke is not None:
        values.extend(
            (value, max(sx, sy)) for value in (layer.stroke_width, *(layer.dash_array or ()))
        )
        values.append((layer.miter_limit, 1.0))
    if layer.fill is not None:
        if any(not 0 <= position <= 1 for _, position in layer.fill.stops):
            return "native SVG cannot preserve gradient stops outside the 0..1 interval"
        if isinstance(layer.fill, LinearGradient):
            values.append((layer.fill.angle, max(layer.width, layer.height) * math.pi / 180))
        else:
            values.extend(
                ((layer.fill.center[0], layer.width), (layer.fill.center[1], layer.height))
            )
    for value, scale in values:
        if not _bounded_number(value, scale):
            return "native SVG numeric range or 1/8-pixel coordinate precision exceeded"
    return None


def native_path_data(layer: PathLayer) -> str:
    """Emit canonical commands so omitted arcs cannot become native cap dots."""
    commands = []
    current = start = (0.0, 0.0)
    drawn = False
    for segment in parse_path(layer.d):
        kind = segment.kind
        values = [value for point in segment.points for value in point]
        if kind == "Z" and not drawn:
            continue
        if kind == "A":
            if segment.points[0] == current:
                continue
            rx, ry, rotation, large, sweep = segment.arc
            kind = "A" if rx and ry else "L"
            if kind == "A":
                values = [abs(rx), abs(ry), rotation % 360, large, sweep, *values]
        commands.append(kind + " ".join(map(_motion_number, values)))
        if kind == "M":
            start = segment.points[0]
        drawn = kind not in {"M", "Z"}
        current = start if kind == "Z" else segment.points[-1]
    return " ".join(commands)


def _bounded_number(value: float, scale: float) -> bool:
    try:
        if not math.isfinite(value) or not math.isfinite(scale):
            return False
        if value == 0:
            return True
        exponent = math.frexp(value)[1]
        return -125 <= exponent <= 127 and math.ldexp(1.0, exponent - 24) * abs(scale) <= 0.125
    except OverflowError:
        return False
