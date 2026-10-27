"""Bounded native PDF path geometry and paint admission."""

import math

from quickthumb._path_geometry import _arc_geometry, parse_path
from quickthumb._path_svg import _bounded_number, native_path_data, native_path_problem
from quickthumb.errors import RenderingError
from quickthumb.models import PathLayer


def native_pdf_path_problem(layer: PathLayer) -> str | None:
    """Use the same numeric bounds as SVG and declare PDF's opaque-shading limit."""
    if problem := native_path_problem(layer):
        return problem.replace("native SVG", "native PDF")
    if layer.fill is not None and any(
        len(color.lstrip("#")) == 8 and color[-2:].lower() != "ff" for color, _ in layer.fill.stops
    ):
        return "native PDF cannot preserve translucent gradient stops"
    from quickthumb._export_pdf import _require_reportlab

    _require_reportlab()
    try:
        # ReportLab populates its C-accelerated helpers dynamically at import time.
        from reportlab.lib.rl_accel import fp_str  # ty: ignore[unresolved-import]

        commands = pdf_path_commands(layer)
        if layer.stroke is not None and layer.stroke_width:
            if layer.dash_array and any(layer.dash_array) and 0 in layer.dash_array:
                return "native PDF cannot preserve zero-length dash paint"
            drawn = nonzero = False
            current = start = (0.0, 0.0)
            for kind, points in [*commands, ("M", ((0.0, 0.0),))]:
                if kind in {"M", "Z"}:
                    if drawn and not nonzero:
                        return "native PDF cannot preserve zero-length stroke caps"
                    drawn = nonzero = False
                else:
                    drawn = True
                    nonzero |= any(point != current for point in points)
                if kind == "M":
                    start = points[0]
                current = start if kind == "Z" else points[-1]
        vx, vy, vw, vh = layer.view_box or (0, 0, layer.width, layer.height)
        sx, sy = layer.width / vw, layer.height / vh
        values = [(vx, sx), (vy, sy), (1 / sx, layer.width * sx), (1 / sy, layer.height * sy)]
        values.extend(
            (value, scale)
            for _, points in commands
            for point in points
            for value, scale in zip(point, (sx, sy), strict=True)
        )
        values.extend(
            (value, max(sx, sy))
            for value in (
                layer.stroke_width,
                layer.dash_offset
                % (sum(layer.dash_array) * (2 if len(layer.dash_array) % 2 else 1))
                if layer.dash_array and any(layer.dash_array)
                else 0,
                *(layer.dash_array or ()),
            )
        )
        values.extend(
            (
                scale,
                max(
                    abs(origin),
                    abs(size),
                    *(abs(p[axis]) for _, points in commands for p in points),
                ),
            )
            for axis, (scale, origin, size) in enumerate(((sx, vx, vw), (sy, vy, vh)))
        )
        if any(abs(float(fp_str(value)) - value) * scale > 0.125 for value, scale in values):
            return "native PDF decimal coordinate precision exceeds 1/8 pixel"
    except RenderingError:
        return "native PDF arc conversion exceeds the 65536-command or coordinate precision limit"
    return None


def pdf_path_commands(layer: PathLayer):
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
                raise RenderingError("Native PDF arc command limit exceeded")
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
        raise RenderingError("Native PDF coordinate precision limit exceeded")
    return commands


def _ellipse_point(center, axis_x, axis_y, angle, tangent):
    cosine, sine = math.cos(angle), math.sin(angle)
    return tuple(
        c + x * (cosine - tangent * sine) + y * (sine + tangent * cosine)
        for c, x, y in zip(center, axis_x, axis_y, strict=True)
    )
