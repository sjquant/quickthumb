"""Bounded local-distance dash runs for the existing path stroker."""

import math
from itertools import pairwise

from quickthumb._path_geometry import _Contour
from quickthumb.errors import RenderingError


def dash_contours(
    contours: tuple[_Contour, ...],
    pattern: tuple[float, ...] | None,
    offset: float,
    scale: tuple[float, float],
) -> tuple[_Contour, ...]:
    """Keep corners within each dash and join painted runs across a closed seam."""
    if not pattern or not any(pattern):
        return contours
    if len(pattern) % 2:
        pattern = pattern * 2
    cycle = math.fsum(pattern)
    output = []
    work = 0
    for contour in contours:
        points = []
        for x, y in contour.points:
            point = (x / scale[0], y / scale[1])
            if not all(math.isfinite(value) for value in point):
                raise _dash_limit()
            if not points or point != points[-1]:
                points.append(point)
        if contour.closed and points[-1] != points[0]:
            points.append(points[0])
        index = 0
        phase = offset % cycle
        while phase > 0:
            work += 1
            if work > 65_536:
                raise _dash_limit()
            if phase <= pattern[index]:
                break
            phase -= pattern[index]
            index = (index + 1) % len(pattern)
        remaining = pattern[index] - phase
        runs = []
        run = []
        last_ends_at_seam = False

        def advance(point, at_end, runs, tangent):
            nonlocal index, remaining, run, work, last_ends_at_seam
            while remaining == 0:
                work += 1
                if work > 65_536:
                    raise _dash_limit()
                if index % 2 == 0:
                    runs.append(_Contour(tuple(run or [point, point]), False, tangent))
                    last_ends_at_seam = at_end
                    run = []
                if at_end:
                    return
                index = (index + 1) % len(pattern)
                remaining = pattern[index]

        tangent = (
            (points[1][0] - points[0][0], points[1][1] - points[0][1])
            if len(points) > 1
            else (1.0, 0.0)
        )
        advance(points[0], len(points) == 1, runs, tangent)
        first_starts_at_seam = bool(runs) or index % 2 == 0
        for edge, (a, b) in enumerate(pairwise(points)):
            dx, dy = b[0] - a[0], b[1] - a[1]
            length = math.hypot(dx, dy)
            if not math.isfinite(length):
                raise _dash_limit()
            distance = 0.0
            point = a
            while distance < length:
                work += 1
                if work > 65_536:
                    raise _dash_limit()
                available = length - distance
                step = min(remaining, available)
                next_distance = length if step == available else distance + step
                if next_distance <= distance:
                    raise _dash_limit()
                end = (
                    b
                    if next_distance == length
                    else (
                        a[0] + dx * (next_distance / length),
                        a[1] + dy * (next_distance / length),
                    )
                )
                if index % 2 == 0:
                    if not run:
                        run = [point]
                    run.append(end)
                remaining = 0.0 if step == remaining else remaining - step
                distance, point = next_distance, end
                advance(point, edge == len(points) - 2 and distance == length, runs, (dx, dy))
        if run:
            runs.append(_Contour(tuple(run), False))
            last_ends_at_seam = True
        elif len(points) == 1 and index % 2 == 0 and not runs:
            runs.append(_Contour((points[0], points[0]), False, tangent))
            last_ends_at_seam = True
        closed = contour.closed and first_starts_at_seam and last_ends_at_seam
        if closed and len(runs) > 1:
            runs[0] = _Contour(runs[-1].points[:-1] + runs[0].points, False)
            runs.pop()
            closed = False
        for run in runs:
            work += len(run.points)
            if work > 65_536:
                raise _dash_limit()
            output.append(
                _Contour(
                    tuple((x * scale[0], y * scale[1]) for x, y in run.points),
                    closed and len(run.points) > 2,
                    (run.tangent[0] * scale[0], run.tangent[1] * scale[1]),
                )
            )
    return tuple(output)


def _dash_limit() -> RenderingError:
    return RenderingError(
        "Path dash geometry exceeds finite precision or the bounded render plan; "
        "use longer dash intervals or simplify d",
        code="path_dash_limit",
        path="/dash_array",
    )
