"""Shared native-vector cubic conversion with bounded device-space arc error."""

import math

from quickthumb._path_geometry import _arc_geometry, parse_path
from quickthumb._path_svg import _bounded_number, native_path_data
from quickthumb.errors import RenderingError
from quickthumb.models import PathLayer


def cubic_path_commands(layer: PathLayer):
    """Convert quadratics exactly and ellipses to device-bounded cubic curves."""
    _, _, vw, vh = layer.view_box or (0, 0, layer.width, layer.height)
    scale = layer.width / vw, layer.height / vh
    current = start = (0.0, 0.0)
    commands = []
    for segment in parse_path(native_path_data(layer)):
        kind, points = segment.kind, segment.points
        if kind == "Q":
            control, end = points
            points = (
                tuple(a + (b - a) * 2 / 3 for a, b in zip(current, control, strict=True)),
                tuple(a + (b - a) * 2 / 3 for a, b in zip(end, control, strict=True)),
                end,
            )
            kind = "C"
        if kind == "A":
            center, axis_x, axis_y, theta, delta = _arc_geometry(
                current, points[0], segment.arc, (0, 0), (1, 1)
            )
            radius = math.hypot(axis_x[0] * scale[0], axis_x[1] * scale[1]) + math.hypot(
                axis_y[0] * scale[0], axis_y[1] * scale[1]
            )
            # A conservative sixth-order error bound; never approximate an arc by straight edges.
            step = min(0.5, (0.125 / radius) ** (1 / 6)) if radius else 0.5
            count = math.ceil(abs(delta) / step)
            if len(commands) + count > 65536:
                raise RenderingError("Native path arc command limit exceeded")
            for index in range(count):
                a, b = theta + delta * index / count, theta + delta * (index + 1) / count
                factor = 4 / 3 * math.tan((b - a) / 4)
                first = _ellipse_point(center, axis_x, axis_y, a, factor)
                last = _ellipse_point(center, axis_x, axis_y, b, -factor)
                end = (
                    points[0]
                    if index + 1 == count
                    else _ellipse_point(center, axis_x, axis_y, b, 0)
                )
                commands.append(("C", (first, last, end)))
        else:
            commands.append((kind, points))
        if kind == "M":
            start = points[0]
        current = start if kind == "Z" else points[-1]
    if len(commands) > 65536 or any(
        not _bounded_number(value, axis_scale)
        for _, points in commands
        for point in points
        for value, axis_scale in zip(point, scale, strict=True)
    ):
        raise RenderingError("Native path coordinate precision limit exceeded")
    return commands


def _ellipse_point(center, axis_x, axis_y, angle, tangent):
    cosine, sine = math.cos(angle), math.sin(angle)
    return tuple(
        c + x * (cosine - tangent * sine) + y * (sine + tangent * cosine)
        for c, x, y in zip(center, axis_x, axis_y, strict=True)
    )
