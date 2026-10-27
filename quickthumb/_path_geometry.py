"""Bounded SVG path compilation and device-space curve flattening."""

import math
import re
from dataclasses import dataclass
from functools import lru_cache
from itertools import pairwise
from typing import Literal

from quickthumb.errors import RenderingError

_Point = tuple[float, float]
_TOKEN = re.compile(r"[A-Za-z]|[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?")
_PARAMETERS = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "S": 4, "Q": 4, "T": 2, "A": 7}
_MAX_POINTS = 65_536


@dataclass(frozen=True)
class _Segment:
    kind: Literal["M", "L", "Q", "C", "A", "Z"]
    points: tuple[_Point, ...] = ()
    arc: tuple[float, ...] = ()


@dataclass(frozen=True)
class _Contour:
    points: tuple[_Point, ...]
    closed: bool
    tangent: _Point = (1.0, 0.0)


@lru_cache(maxsize=128)
def parse_path(data: str) -> tuple[_Segment, ...]:
    """Compile absolute segments, resolving relative and smooth SVG commands."""
    tokens = _tokens(data)
    segments = []
    current = (0.0, 0.0)
    start = cubic = quadratic = None
    command = ""
    index = 0
    while index < len(tokens):
        if tokens[index].isalpha():
            command = tokens[index]
            index += 1
            if command.upper() not in _PARAMETERS and command.upper() != "Z":
                raise ValueError(
                    f"SVG path command {command!r} is not supported; use M/L/H/V/C/S/Q/T/A/Z"
                )
            if command.upper() == "Z":
                if start is None:
                    raise ValueError("closepath requires a preceding moveto")
                segments.append(_Segment("Z"))
                current, cubic, quadratic = start, None, None
                command = ""
                continue
        if not command:
            raise ValueError("SVG path coordinates require a command")
        kind = command.upper()
        if start is None and kind != "M":
            raise ValueError("SVG path must begin with moveto")
        count = _PARAMETERS[kind]
        numbers: list[float] = []
        for offset in range(count):
            if index >= len(tokens) or tokens[index].isalpha():
                raise ValueError(f"SVG path command {command!r} has incomplete coordinates")
            token = tokens[index]
            if kind == "A" and offset in (3, 4):
                # Consume a flag prefix without shifting the remaining token list.
                if token[0] not in "01":
                    raise ValueError("SVG arc flags must be 0 or 1")
                numbers.append(float(token[0]))
                if len(token) > 1:
                    tokens[index] = token[1:]
                    continue
            else:
                numbers.append(float(token))
            index += 1
        if not all(math.isfinite(value) for value in numbers):
            raise ValueError("SVG path coordinates must be finite")
        origin = current if command.islower() else (0.0, 0.0)
        points: tuple[_Point, ...]
        if kind == "A":
            points = ((numbers[5] + origin[0], numbers[6] + origin[1]),)
        elif kind == "H":
            points = ((numbers[0] + origin[0], current[1]),)
        elif kind == "V":
            points = ((current[0], numbers[0] + origin[1]),)
        else:
            points = tuple(
                (numbers[i] + origin[0], numbers[i + 1] + origin[1]) for i in range(0, count, 2)
            )
        normalized: Literal["M", "L", "Q", "C", "A"]
        if kind == "M":
            normalized, start = "M", points[0]
            command = "l" if command.islower() else "L"
        elif kind in {"L", "H", "V"}:
            normalized = "L"
        elif kind in {"C", "S"}:
            normalized = "C"
            if kind == "S":
                points = (_reflected(current, cubic), *points)
        elif kind == "A":
            normalized = "A"
        else:
            normalized = "Q"
            if kind == "T":
                points = (_reflected(current, quadratic), *points)
        if not all(math.isfinite(value) for point in points for value in point):
            raise ValueError("SVG path coordinates must be finite")
        segments.append(_Segment(normalized, points, tuple(numbers[:5]) if kind == "A" else ()))
        current = points[-1]
        cubic = points[-2] if normalized == "C" else None
        quadratic = points[0] if normalized == "Q" else None
    return tuple(segments)


def flatten_path(data: str, origin: _Point, scale: _Point) -> tuple[_Contour, ...]:
    """Flatten curves to 1/8 pixel chord tolerance after mapping to the local frame."""
    contours = []
    points: list[_Point] = []
    current = start = (0.0, 0.0)
    local_current = local_start = (0.0, 0.0)
    total = 0
    for segment in parse_path(data):
        mapped = tuple(
            ((x - origin[0]) * scale[0], (y - origin[1]) * scale[1]) for x, y in segment.points
        )
        if segment.kind in {"M", "Z"}:
            if points:
                contours.append(_Contour(tuple(points), segment.kind == "Z"))
                points = []
            current = start if segment.kind == "Z" else mapped[0]
            local_current = local_start if segment.kind == "Z" else segment.points[0]
            if segment.kind == "M":
                start, local_start = current, local_current
            continue
        if segment.kind == "A" and local_current == segment.points[0]:
            continue
        if not points:
            points.append(current)
            total += 1
        if segment.kind == "L":
            added = mapped
        elif segment.kind == "A":
            added = _flatten_arc(
                local_current, segment.points[0], segment.arc, origin, scale, _MAX_POINTS - total
            )
        else:
            added = _flatten_curve((current, *mapped), _MAX_POINTS - total)
        points.extend(added)
        total += len(added)
        current = mapped[-1]
        local_current = segment.points[-1]
        if total > _MAX_POINTS:
            raise _subdivision_limit()
    if points:
        contours.append(_Contour(tuple(points), False))
    return tuple(contours)


def _flatten_arc(
    start: _Point, end: _Point, arc: tuple[float, ...], origin: _Point, scale: _Point, budget: int
) -> list[_Point]:
    endpoint = ((end[0] - origin[0]) * scale[0], (end[1] - origin[1]) * scale[1])
    if start == end:
        return []
    if arc[0] == 0 or arc[1] == 0:
        return [endpoint]
    center, axis_x, axis_y, theta, delta = _arc_geometry(start, end, arc, origin, scale)
    radius = math.hypot(*axis_x) + math.hypot(*axis_y)
    pending = [(theta, theta + delta, 0)]
    points = []
    while pending:
        a, b, depth = pending.pop()
        # The two mapped axis lengths bound ellipse chord error, even with anisotropic scaling.
        if radius == 0 or 2 * math.sin((b - a) / 4) ** 2 <= 0.125 / radius:
            point = (
                center[0] + axis_x[0] * math.cos(b) + axis_y[0] * math.sin(b),
                center[1] + axis_x[1] * math.cos(b) + axis_y[1] * math.sin(b),
            )
            if not all(math.isfinite(value) for value in point):
                raise _arc_range_limit()
            points.append(point)
            if len(points) > budget:
                raise _subdivision_limit()
        else:
            if depth == 20:
                raise _subdivision_limit()
            middle = a / 2 + b / 2
            pending.extend(((middle, b, depth + 1), (a, middle, depth + 1)))
    points[-1] = endpoint
    return points


def _arc_geometry(
    start: _Point, end: _Point, arc: tuple[float, ...], origin: _Point, scale: _Point
):
    """Return a mapped ellipse and angular interval for a nondegenerate SVG arc."""
    rx, ry, rotation, large, sweep = arc
    # SVG endpoint-to-center conversion: https://www.w3.org/TR/SVG/implnote.html#ArcConversionEndpointToCenter
    # Subtract endpoints before normalization to preserve small arcs at large translated origins.
    half = []
    for a, b in zip(start, end, strict=True):
        difference = a - b
        half.append(difference / 2 if math.isfinite(difference) else a / 2 - b / 2)
    unit = max(abs(value) for value in (*half, rx, ry))
    log_rx, log_ry = math.log(abs(rx)) - math.log(unit), math.log(abs(ry)) - math.log(unit)
    rx, ry = abs(rx) / unit, abs(ry) / unit
    phi = math.radians(rotation % 360)
    cosine, sine = math.cos(phi), math.sin(phi)
    dx, dy = half[0] / unit, half[1] / unit
    xp, yp = cosine * dx + sine * dy, -sine * dx + cosine * dy
    correction = math.hypot(xp / rx, yp / ry) if rx and ry else math.inf
    if not math.isfinite(correction):
        # Tiny radii can require a perfectly representable correction larger than float range.
        lx = math.log(abs(xp)) - log_rx if xp else -math.inf
        ly = math.log(abs(yp)) - log_ry if yp else -math.inf
        largest = max(lx, ly)
        if not math.isfinite(largest):
            raise _arc_range_limit()
        adjustment = largest + math.log(math.hypot(math.exp(lx - largest), math.exp(ly - largest)))
        try:
            rx, ry = math.exp(log_rx + adjustment), math.exp(log_ry + adjustment)
        except OverflowError as error:
            raise _arc_range_limit() from error
        if not rx or not ry:
            raise _arc_range_limit()
    elif correction > 1:
        rx, ry = rx * correction, ry * correction
    ux, uy = xp / rx, yp / ry
    length = math.hypot(ux, uy)
    if not length or not all(math.isfinite(value) for value in (rx, ry, length)):
        raise _arc_range_limit()
    factor = math.sqrt(max(0.0, 1 - length * length))
    if large == sweep:
        factor = -factor
    cxp, cyp = factor * rx * uy / length, -factor * ry * ux / length
    cx = cosine * cxp - sine * cyp - dx
    cy = sine * cxp + cosine * cyp - dy
    first = ((xp - cxp) / rx, (yp - cyp) / ry)
    last = ((-xp - cxp) / rx, (-yp - cyp) / ry)
    theta = math.atan2(first[1], first[0])
    delta = math.atan2(
        first[0] * last[1] - first[1] * last[0], first[0] * last[0] + first[1] * last[1]
    )
    if delta == 0:
        raise _arc_range_limit()
    if sweep and delta < 0:
        delta += math.tau
    elif not sweep and delta > 0:
        delta -= math.tau
    # Keep the normalized ellipse until mapping; huge local coordinates may map to a tiny frame.
    sx, sy = unit * scale[0], unit * scale[1]
    center = (
        (start[0] - origin[0]) * scale[0] + cx * sx,
        (start[1] - origin[1]) * scale[1] + cy * sy,
    )
    axis_x = (rx * cosine * sx, rx * sine * sy)
    axis_y = (-ry * sine * sx, ry * cosine * sy)
    radius = math.hypot(*axis_x) + math.hypot(*axis_y)
    if not all(math.isfinite(value) for value in (*center, *axis_x, *axis_y, radius)):
        raise _arc_range_limit()
    return center, axis_x, axis_y, theta, delta


def _arc_range_limit() -> RenderingError:
    return RenderingError(
        "Arc geometry exceeds finite numerical precision; simplify d or its coordinate range",
        code="path_arc_range_limit",
        path="/d",
    )


def _tokens(data: str) -> list[str]:
    tokens = []
    end = 0
    previous_number = False
    for match in _TOKEN.finditer(data):
        gap = data[end : match.start()]
        token = match.group()
        number = not token.isalpha()
        if (
            gap.strip(" \t\r\n,")
            or gap.count(",") > 1
            or ("," in gap and not (previous_number and number))
        ):
            raise ValueError("invalid SVG path separator")
        tokens.append(token)
        previous_number, end = number, match.end()
    if data[end:].strip() or not tokens:
        raise ValueError("path d must contain SVG moveto coordinates")
    return tokens


def _reflected(current: _Point, control: _Point | None) -> _Point:
    if control is None:
        return current
    return current[0] + (current[0] - control[0]), current[1] + (current[1] - control[1])


def _flatten_curve(controls: tuple[_Point, ...], budget: int) -> list[_Point]:
    pending = [(controls, 0)]
    points = []
    while pending:
        curve, depth = pending.pop()
        if _flat_enough(curve):
            points.append(curve[-1])
            if len(points) > budget:
                raise _subdivision_limit()
        else:
            if depth == 20:
                raise _subdivision_limit()
            row = curve
            left, right = [row[0]], [row[-1]]
            while len(row) > 1:
                row = tuple((a[0] / 2 + b[0] / 2, a[1] / 2 + b[1] / 2) for a, b in pairwise(row))
                left.append(row[0])
                right.append(row[-1])
            pending.extend(((tuple(reversed(right)), depth + 1), (tuple(left), depth + 1)))
    return points


def _flat_enough(points: tuple[_Point, ...]) -> bool:
    scale = max(abs(value) for point in points for value in point) or 1.0
    normalized = tuple((x / scale, y / scale) for x, y in points)
    start, end = normalized[0], normalized[-1]
    dx, dy = end[0] - start[0], end[1] - start[1]
    length_squared = dx * dx + dy * dy
    for x, y in normalized[1:-1]:
        px, py = x - start[0], y - start[1]
        t = min(1.0, max(0.0, (px * dx + py * dy) / length_squared)) if length_squared else 0
        if math.hypot(px - t * dx, py - t * dy) > 0.125 / scale:
            return False
    return True


def _subdivision_limit() -> RenderingError:
    return RenderingError(
        "Path curve subdivision exceeds the bounded render plan; "
        "simplify d or reduce its mapped scale",
        code="path_subdivision_limit",
        path="/d",
    )
