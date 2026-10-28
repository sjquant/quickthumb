"""Bounded native PDF path geometry and paint admission."""

from quickthumb._path_curves import cubic_path_commands
from quickthumb._path_svg import native_path_problem
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

        commands = cubic_path_commands(layer)
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
