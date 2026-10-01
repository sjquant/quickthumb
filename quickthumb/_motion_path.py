"""Bounded, deterministic cubic geometry shared by motion and HTML sampling."""

from __future__ import annotations

import math
from bisect import bisect_left
from dataclasses import dataclass
from functools import lru_cache

Point = tuple[float, float]
Controls = tuple[Point, Point, Point, Point]


def _mix(left: Point, right: Point, ratio: float) -> Point:
    return (
        (1 - ratio) * left[0] + ratio * right[0],
        (1 - ratio) * left[1] + ratio * right[1],
    )


def _point(controls: Controls, parameter: float) -> Point:
    """Evaluate the actual cubic with de Casteljau interpolation."""
    a, b, c, d = controls
    ab, bc, cd = _mix(a, b, parameter), _mix(b, c, parameter), _mix(c, d, parameter)
    return _mix(_mix(ab, bc, parameter), _mix(bc, cd, parameter), parameter)


@dataclass(frozen=True)
class _Arc:
    controls: Controls
    scale: float
    parameters: tuple[float, ...]
    lengths: tuple[float, ...]

    def parameter(self, progress: float) -> float:
        if self.lengths[-1] == 0:
            return 0.0
        distance = min(1.0, max(0.0, progress)) * self.lengths[-1]
        index = max(1, bisect_left(self.lengths, distance))
        low, high = self.lengths[index - 1 : index + 1]
        ratio = (distance - low) / (high - low) if high > low else 0.0
        return self.parameters[index - 1] + ratio * (
            self.parameters[index] - self.parameters[index - 1]
        )


@lru_cache(maxsize=64)
def _arc(controls: Controls) -> _Arc:
    """Flatten in parameter space once; retain at most 4097 entries per cubic.

    Control-to-linear-parameter deviation, unlike chord flatness alone, also
    subdivides straight cubics with nonlinear speed. Normalized coordinates
    keep the subdivision and length sums finite for very large valid inputs.
    """
    scale = max(abs(number) for point in controls for number in point) or 1.0
    normalized: Controls = tuple((x / scale, y / scale) for x, y in controls)  # type: ignore[assignment]
    extent = max(math.dist(normalized[0], point) for point in normalized)
    tolerance = max(extent * 1e-7, 1e-15)
    parameters, lengths = [0.0], [0.0]
    previous = normalized[0]

    def visit(curve: Controls, low: float, high: float, depth: int) -> None:
        nonlocal previous
        a, b, c, d = curve
        error = max(math.dist(b, _mix(a, d, 1 / 3)), math.dist(c, _mix(a, d, 2 / 3)))
        if error <= tolerance or depth == 12:
            parameters.append(high)
            lengths.append(lengths[-1] + math.dist(previous, d))
            previous = d
            return
        ab, bc, cd = _mix(a, b, 0.5), _mix(b, c, 0.5), _mix(c, d, 0.5)
        abc, bcd = _mix(ab, bc, 0.5), _mix(bc, cd, 0.5)
        middle = _mix(abc, bcd, 0.5)
        half = (low + high) / 2
        visit((a, ab, abc, middle), low, half, depth + 1)
        visit((middle, bcd, cd, d), half, high, depth + 1)

    visit(normalized, 0.0, 1.0, 0)
    return _Arc(normalized, scale, tuple(parameters), tuple(lengths))


def _heading(controls: Controls, parameter: float) -> float | None:
    a, b, c, d = controls
    u = 1 - parameter
    dx = 3 * (
        u * u * (b[0] - a[0]) + 2 * u * parameter * (c[0] - b[0]) + parameter**2 * (d[0] - c[0])
    )
    dy = 3 * (
        u * u * (b[1] - a[1]) + 2 * u * parameter * (c[1] - b[1]) + parameter**2 * (d[1] - c[1])
    )
    if math.hypot(dx, dy) <= 1e-14:
        # Endpoint stationary derivatives and interior cusps need a one-sided
        # direction. Never depend on previously sampled frames or seek order.
        point = _point(controls, parameter)
        candidates = []
        if parameter < 1:
            candidates.append((point, _point(controls, min(1.0, parameter + 1e-5))))
        if parameter > 0:
            candidates.append((_point(controls, max(0.0, parameter - 1e-5)), point))
        for left, right in candidates:
            dx, dy = right[0] - left[0], right[1] - left[1]
            if dx != 0 or dy != 0:
                break
    return math.degrees(math.atan2(dy, dx)) if dx != 0 or dy != 0 else None


def sample_segment(
    left: Point,
    right: Point,
    outgoing: Point | None,
    incoming: Point | None,
    progress: float,
) -> tuple[Point, float | None]:
    """Return on-curve position and clockwise heading at eased distance progress."""
    progress = min(1.0, max(0.0, progress))
    if outgoing is None and incoming is None:
        scale = max(abs(number) for point in (left, right) for number in point) or 1.0
        dx, dy = right[0] / scale - left[0] / scale, right[1] / scale - left[1] / scale
        return _mix(left, right, progress), (
            math.degrees(math.atan2(dy, dx)) if dx != 0 or dy != 0 else None
        )
    outgoing, incoming = outgoing or (0.0, 0.0), incoming or (0.0, 0.0)
    arc = _arc(
        (
            left,
            (left[0] + outgoing[0], left[1] + outgoing[1]),
            (right[0] + incoming[0], right[1] + incoming[1]),
            right,
        )
    )
    parameter = arc.parameter(progress)
    if progress == 0:
        point = left
    elif progress == 1:
        point = right
    else:
        normalized = _point(arc.controls, parameter)
        point = normalized[0] * arc.scale, normalized[1] * arc.scale
    return point, _heading(arc.controls, parameter)
