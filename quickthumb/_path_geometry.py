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
_PARAMETERS = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "S": 4, "Q": 4, "T": 2}
_MAX_POINTS = 65_536


@dataclass(frozen=True)
class _Segment:
    kind: Literal["M", "L", "Q", "C", "Z"]
    points: tuple[_Point, ...] = ()


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
                    f"SVG path command {command!r} is not supported; use M/L/H/V/C/S/Q/T/Z"
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
        values = tokens[index : index + count]
        if len(values) != count or any(value.isalpha() for value in values):
            raise ValueError(f"SVG path command {command!r} has incomplete coordinates")
        numbers = [float(value) for value in values]
        if not all(math.isfinite(value) for value in numbers):
            raise ValueError("SVG path coordinates must be finite")
        index += count
        origin = current if command.islower() else (0.0, 0.0)
        if kind == "H":
            points = ((numbers[0] + origin[0], current[1]),)
        elif kind == "V":
            points = ((current[0], numbers[0] + origin[1]),)
        else:
            points = tuple(
                (numbers[i] + origin[0], numbers[i + 1] + origin[1]) for i in range(0, count, 2)
            )
        normalized: Literal["M", "L", "Q", "C"]
        if kind == "M":
            normalized, start = "M", points[0]
            command = "l" if command.islower() else "L"
        elif kind in {"L", "H", "V"}:
            normalized = "L"
        elif kind in {"C", "S"}:
            normalized = "C"
            if kind == "S":
                points = (_reflected(current, cubic), *points)
        else:
            normalized = "Q"
            if kind == "T":
                points = (_reflected(current, quadratic), *points)
        if not all(math.isfinite(value) for point in points for value in point):
            raise ValueError("SVG path coordinates must be finite")
        segments.append(_Segment(normalized, points))
        current = points[-1]
        cubic = points[-2] if normalized == "C" else None
        quadratic = points[0] if normalized == "Q" else None
    return tuple(segments)


def flatten_path(data: str, origin: _Point, scale: _Point) -> tuple[tuple[_Point, ...], ...]:
    """Flatten curves to 1/8 pixel chord tolerance after mapping to the local frame."""
    contours = []
    points: list[_Point] = []
    current = start = (0.0, 0.0)
    total = 0
    for segment in parse_path(data):
        mapped = tuple(
            ((x - origin[0]) * scale[0], (y - origin[1]) * scale[1]) for x, y in segment.points
        )
        if segment.kind in {"M", "Z"}:
            if points:
                contours.append(tuple(points))
                points = []
            current = start if segment.kind == "Z" else mapped[0]
            if segment.kind == "M":
                start = current
            continue
        if not points:
            points.append(current)
            total += 1
        if segment.kind == "L":
            added = mapped
        else:
            added = _flatten_curve((current, *mapped), _MAX_POINTS - total)
        points.extend(added)
        total += len(added)
        current = mapped[-1]
        if total > _MAX_POINTS:
            raise _subdivision_limit()
    if points:
        contours.append(tuple(points))
    return tuple(contours)


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
