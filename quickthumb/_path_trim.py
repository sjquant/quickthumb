"""Bounded stroke trim windows over flattened local SVG contour lengths."""

import math
from itertools import pairwise

from quickthumb._path_geometry import _Contour
from quickthumb.errors import RenderingError


def trim_window(start: float, end: float, offset: float) -> tuple[float, float] | None:
    """Normalize the canonical cyclic window; None is full, equal endpoints are empty."""
    if start == 0 and end == 1:
        return None
    if start == end or (start == 1 and end == 0):
        return (0.0, 0.0)
    first, last = ((value + offset % 1) % 1 for value in (start, end))
    if first == last:
        raise _trim_limit()
    return first, last


def trim_contours(
    contours: tuple[_Contour, ...],
    start: float,
    end: float,
    offset: float,
    scale: tuple[float, float],
) -> tuple[_Contour, ...]:
    """Slice a cyclic global distance window without connecting separate contours."""
    window = trim_window(start, end, offset)
    if window is None:
        return contours
    if window[0] == window[1]:
        return ()
    edges = []
    lengths = []
    try:
        for contour in contours:
            points = [(x / scale[0], y / scale[1]) for x, y in contour.points]
            if contour.closed and points[-1] != points[0]:
                points.append(points[0])
            lengths.append([math.dist(a, b) for a, b in pairwise(points)])
            edges.append(points)
        totals = [math.fsum(values) for values in lengths]
        total = math.fsum(totals)
    except OverflowError as error:
        raise _trim_limit() from error
    if not math.isfinite(total):
        raise _trim_limit()
    if total == 0:
        return ()
    first, last = window
    windows = sorted(
        [(first * total, last * total)]
        if first < last
        else [(first * total, total), (0.0, last * total)]
    )
    output = []
    cursor = 0.0
    work = 0
    for contour, points, distances, length in zip(contours, edges, lengths, totals, strict=True):
        runs = []
        for begin, finish in windows:
            left, right = max(0, begin - cursor), min(length, finish - cursor)
            if left >= right:
                continue
            if left == 0 and right == length:
                work += len(contour.points)
                if work > 65_536:
                    raise _trim_limit()
                runs.append(contour)
                continue
            run = []
            distance = 0.0
            for (a, b), edge_length in zip(pairwise(points), distances, strict=True):
                lo, hi = max(left, distance), min(right, distance + edge_length)
                if lo < hi:
                    for value in (lo, hi):
                        ratio = (value - distance) / edge_length
                        point = (
                            a
                            if ratio == 0
                            else b
                            if ratio == 1
                            else (
                                a[0] + (b[0] - a[0]) * ratio,
                                a[1] + (b[1] - a[1]) * ratio,
                            )
                        )
                        mapped = (point[0] * scale[0], point[1] * scale[1])
                        if not run or run[-1] != mapped:
                            run.append(mapped)
                distance += edge_length
            work += len(run)
            if len(run) < 2 or work > 65_536:
                raise _trim_limit()
            runs.append(_Contour(tuple(run), False))
        if contour.closed and len(runs) == 2 and runs[0].points[0] == runs[-1].points[-1]:
            runs = [_Contour(runs[-1].points[:-1] + runs[0].points, False)]
        output.extend(runs)
        cursor += length
    return tuple(output)


def _trim_limit() -> RenderingError:
    return RenderingError(
        "Path trim exceeds finite precision or the bounded geometry plan; "
        "simplify d or widen the trim interval",
        code="path_trim_limit",
        path="/trim_start",
    )
