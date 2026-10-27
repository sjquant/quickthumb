"""Bounded local arc-length correspondence over the existing SVG path compiler."""

import math
from bisect import bisect_right
from functools import lru_cache
from itertools import pairwise
from typing import cast

from quickthumb._path_geometry import _Contour, flatten_path
from quickthumb.errors import RenderingError, ValidationError

_SAMPLES = 256


def validate_morph_paths(paths: list[str]) -> None:
    """Reject incompatible authored topology before a timeline reaches a renderer."""
    for data in paths:
        _shape(data)
    for left, right in pairwise(paths):
        _plan(left, right)


def interpolate_path(left: str, right: str, ratio: float) -> str:
    """Keep authored endpoint commands and interpolate matched local contour points."""
    if ratio <= 0:
        return left
    if ratio >= 1:
        return right
    from quickthumb.motion import _interpolate

    source, target, topology = _plan(left, right)
    contours = tuple(
        _Contour(
            tuple(
                cast(tuple[float, float], _interpolate(a, b, ratio))
                for a, b in zip(first.points, second.points, strict=True)
            ),
            first.closed,
        )
        for first, second in zip(source, target, strict=True)
    )
    try:
        if _topology(contours) != topology:
            raise _invalid("sampled contour topology changes")
    except ValidationError as error:
        raise RenderingError(
            error.details[0].message, code="path_morph_topology", path="/path_morph"
        ) from error
    return " ".join(
        "M"
        + " L".join(f"{x!r} {y!r}" for x, y in _simplified(contour))
        + (" Z" if contour.closed else "")
        for contour in contours
    )


def _simplified(contour: _Contour):
    points = []
    for point in contour.points:
        while len(points) > 1 and _cross(points[-2], points[-1], point) == 0:
            points.pop()
        points.append(point)
    if contour.closed:
        while len(points) > 2 and _cross(points[-2], points[-1], points[0]) == 0:
            points.pop()
    return points


@lru_cache(maxsize=16)
def _plan(left: str, right: str):
    source, target = _shape(left), _shape(right)
    topology = _topology(source)
    if _topology(target) != topology:
        raise _invalid("contour count, order, closedness, winding or nesting differs")
    first = tuple(_resample(contour) for contour in source)
    second = []
    for a, b in zip(first, map(_resample, target), strict=True):
        if a.closed:
            normalized = _normalized((a, b))
            # Lowest cyclic shift wins equal scores; symmetric shapes remain deterministic.
            shift = min(
                range(_SAMPLES),
                key=lambda offset: math.fsum(
                    math.dist(point, normalized[1].points[(index + offset) % _SAMPLES]) ** 2
                    for index, point in enumerate(normalized[0].points)
                ),
            )
            b = _Contour(b.points[shift:] + b.points[:shift], True)
        second.append(b)
    result = tuple(second)
    if _topology(first) != topology or _topology(result) != topology:
        raise _invalid("resampling cannot preserve the authored topology")
    # Both endpoints must share one finite coordinate domain for point interpolation.
    _normalized((*first, *result))
    return first, result, topology


@lru_cache(maxsize=32)
def _shape(data: str) -> tuple[_Contour, ...]:
    try:
        compiled = flatten_path(data, (0, 0), (1, 1))
    except RenderingError as error:
        raise _invalid("authored geometry exceeds the existing subdivision plan") from error
    contours = []
    for contour in compiled:
        points = [
            point
            for index, point in enumerate(contour.points)
            if index == 0 or point != contour.points[index - 1]
        ]
        if contour.closed and len(points) > 1 and points[-1] == points[0]:
            points.pop()
        if len(points) > _SAMPLES:
            raise _invalid("authored contour exceeds the 256-point local subdivision limit")
        contours.append(_Contour(tuple(points), contour.closed))
    if not contours or len(contours) * _SAMPLES > 4096:
        raise _invalid("morph requires 1..16 nondegenerate contours (4096 sampled points)")
    result = tuple(contours)
    _topology(result)
    return result


def _resample(contour: _Contour) -> _Contour:
    points = contour.points + contour.points[:1] if contour.closed else contour.points
    lengths = [0.0]
    for a, b in pairwise(points):
        following = lengths[-1] + math.dist(a, b)
        if following <= lengths[-1] or not math.isfinite(following):
            raise _invalid("contour length exceeds finite precision")
        lengths.append(following)
    total = lengths[-1]
    if total == 0 or not math.isfinite(total):
        raise _invalid("contour length must be finite and positive")
    sampled = []
    intervals = _SAMPLES if contour.closed else _SAMPLES - 1
    for index in range(_SAMPLES):
        distance = total * (index / intervals)
        edge = min(bisect_right(lengths, distance) - 1, len(points) - 2)
        ratio = (distance - lengths[edge]) / (lengths[edge + 1] - lengths[edge])
        a, b = points[edge : edge + 2]
        sampled.append((a[0] + (b[0] - a[0]) * ratio, a[1] + (b[1] - a[1]) * ratio))
    # Refuse a polygon that loses a corner or bend by more than 1/4 local SVG unit.
    for point, distance in zip(points, lengths, strict=True):
        index = min(int(distance / total * intervals), intervals - 1)
        a, b = sampled[index], sampled[(index + 1) % _SAMPLES]
        dx, dy = b[0] - a[0], b[1] - a[1]
        denominator = dx * dx + dy * dy
        ratio = (
            min(1.0, max(0.0, ((point[0] - a[0]) * dx + (point[1] - a[1]) * dy) / denominator))
            if denominator
            else 0
        )
        if math.dist(point, (a[0] + ratio * dx, a[1] + ratio * dy)) > 0.25:
            raise _invalid("256 samples cannot preserve the contour within 1/4 local unit")
    return _Contour(tuple(sampled), contour.closed)


def _topology(contours: tuple[_Contour, ...]):
    normalized = _normalized(contours)
    edges = []
    winding = []
    for index, contour in enumerate(normalized):
        if len(contour.points) < (3 if contour.closed else 2):
            raise _invalid("degenerate contours are not supported")
        points = contour.points + contour.points[:1] if contour.closed else contour.points
        local_edges = list(pairwise(points))
        area = math.fsum(a[0] * b[1] - b[0] * a[1] for a, b in local_edges)
        if contour.closed and abs(area) <= 1e-12:
            raise _invalid("closed contours require nonzero signed area")
        winding.append((1 if area > 0 else -1) if contour.closed else 0)
        edges.extend((index, edge, a, b) for edge, (a, b) in enumerate(local_edges))
    work = 0
    for at, (contour, edge, a, b) in enumerate(edges):
        for other, other_edge, c, d in edges[at + 1 :]:
            if contour == other and (
                abs(edge - other_edge) == 1
                or (
                    normalized[contour].closed
                    and edge == 0
                    and other_edge == len(normalized[contour].points) - 1
                )
            ):
                shared, before, after = (b, a, d) if other_edge == edge + 1 else (a, b, c)
                if _cross(before, shared, after) == 0 and (
                    (before[0] - shared[0]) * (after[0] - shared[0])
                    + (before[1] - shared[1]) * (after[1] - shared[1])
                    > 0
                ):
                    raise _invalid("overlapping adjacent edges are ambiguous")
                continue
            work += 1
            if work > 1_000_000:
                raise _invalid("topology exceeds the bounded edge-pair plan")
            if (
                max(a[0], b[0]) < min(c[0], d[0])
                or max(c[0], d[0]) < min(a[0], b[0])
                or max(a[1], b[1]) < min(c[1], d[1])
                or max(c[1], d[1]) < min(a[1], b[1])
            ):
                continue
            if _cross(a, b, c) * _cross(a, b, d) <= 0 and _cross(c, d, a) * _cross(c, d, b) <= 0:
                raise _invalid("crossing or touching contours are ambiguous")
    return tuple(
        (
            contour.closed,
            winding[index],
            tuple(
                _inside(contour.points[0], other.points) if other.closed and index != at else False
                for at, other in enumerate(normalized)
            ),
        )
        for index, contour in enumerate(normalized)
    )


def _normalized(contours: tuple[_Contour, ...]) -> tuple[_Contour, ...]:
    points = [point for contour in contours for point in contour.points]
    if not points or not all(math.isfinite(value) for point in points for value in point):
        raise _invalid("contours require finite points")
    left, top = (min(point[axis] for point in points) for axis in (0, 1))
    span = max(max(point[0] for point in points) - left, max(point[1] for point in points) - top)
    if span == 0:
        raise _invalid("degenerate contours require a positive coordinate span")
    if not math.isfinite(span):
        raise _invalid("contours require a finite coordinate span")
    return tuple(
        _Contour(
            tuple(((x - left) / span, (y - top) / span) for x, y in contour.points), contour.closed
        )
        for contour in contours
    )


def _cross(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _inside(point, polygon):
    x, y = point
    result = False
    for a, b in pairwise(polygon + polygon[:1]):
        if (a[1] > y) != (b[1] > y) and x < a[0] + (y - a[1]) * (b[0] - a[0]) / (b[1] - a[1]):
            result = not result
    return result


def _invalid(reason: str) -> ValidationError:
    return ValidationError("Path morph: " + reason, code="path_morph_topology", path="/path_morph")
