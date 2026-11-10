"""Canonical stroke windows expressed as native Lottie trim modifiers."""

import math
from itertools import pairwise

from quickthumb._path_curves import cubic_path_commands
from quickthumb._path_trim import trim_window
from quickthumb.errors import RenderingError


def needs_trim(layer):
    if (layer.trim_start, layer.trim_end) != (0, 1):
        return True
    specs = layer.animation if isinstance(layer.animation, list) else [layer.animation]
    return any(
        track.type in {"trim_start", "trim_end", "trim_offset"}
        for spec in specs
        if spec is not None
        for track in spec.tracks or ()
    )


def trim_length_bound(layer):
    """Control-polygon upper bound for native endpoint rounding in device pixels."""
    current = start = (0.0, 0.0)
    lengths = []
    for kind, points in cubic_path_commands(layer):
        if kind == "M":
            current = start = points[0]
        elif kind == "Z":
            lengths.append(math.dist(current, start))
            current = start
        else:
            lengths.extend(math.dist(a, b) for a, b in pairwise((current, *points)))
            current = points[-1]
    _, _, vw, vh = layer.view_box or (0, 0, layer.width, layer.height)
    return math.fsum(lengths) * max(layer.width / vw, layer.height / vh)


def trim_properties(layer, state, length_bound):
    start = layer.trim_start if state.trim_start is None else state.trim_start
    end = layer.trim_end if state.trim_end is None else state.trim_end
    offset = layer.trim_offset + state.trim_offset
    if not math.isfinite(offset):
        raise RenderingError("Lottie trim offset must remain finite", path="/trim_offset")
    window = trim_window(start, end, offset)
    return _properties(window, state, length_bound)


def contour_lengths(layer):
    """Canonical local lengths and the bounded flattening work used to obtain them."""
    from quickthumb._path_geometry import flatten_path

    vx, vy, vw, vh = layer.view_box or (0, 0, layer.width, layer.height)
    scale = (layer.width / vw, layer.height / vh)
    lengths = []
    work = 0
    for contour in flatten_path(layer.d, (vx, vy), scale):
        points = [(x / scale[0], y / scale[1]) for x, y in contour.points]
        if contour.closed and points[-1] != points[0]:
            points.append(points[0])
        lengths.append(math.fsum(math.dist(a, b) for a, b in pairwise(points)))
        work += len(points)
    return lengths, work


def contour_trim_properties(layer, state, length_bound, lengths):
    """Map the canonical global window to each contour, retaining contour order."""
    total = math.fsum(lengths)
    start = layer.trim_start if state.trim_start is None else state.trim_start
    end = layer.trim_end if state.trim_end is None else state.trim_end
    offset = layer.trim_offset + state.trim_offset
    if not math.isfinite(offset):
        raise RenderingError("Lottie trim offset must remain finite", path="/trim_offset")
    window = trim_window(start, end, offset)
    if window is None:
        return [_properties(None, state, length_bound) for _ in lengths]
    if window[0] == window[1]:
        return [_properties((0.0, 0.0), state, length_bound) for _ in lengths]
    if window[0] <= window[1]:
        windows = [(window[0] * total, window[1] * total)]
    else:
        windows = [(0.0, window[1] * total), (window[0] * total, total)]
    rows = []
    cursor = 0.0
    for length in lengths:
        intervals = [
            (max(0.0, lo - cursor) / length, min(length, hi - cursor) / length)
            for lo, hi in windows
            if length and max(cursor, lo) < min(cursor + length, hi)
        ]
        if not intervals:
            local = (0.0, 0.0)
        elif intervals == [(0.0, 1.0)]:
            local = None
        elif len(intervals) == 1:
            local = intervals[0]
        else:
            local = (intervals[-1][0], intervals[0][1])
        rows.append(_properties(local, state, length_bound))
        cursor += length
    return rows


def _properties(window, state, length_bound):
    if window is None:
        return {"s": 0, "e": 100, "o": 0}
    first, last = window
    if first == last:
        return {"s": 0, "e": 0, "o": 0}
    width = (last - first) % 1
    # lottie-web rounds the offset endpoints to four decimals and swaps s/e.
    # Encode a positive width plus offset, retaining canonical wrapped windows.
    rounded = [math.floor(v * 10000 + 0.5) / 10000 for v in (first, first + width)]
    scale = abs(state.scale) * max(abs(state.scale_x), abs(state.scale_y))
    error = max(abs(a - b) for a, b in zip((first, first + width), rounded, strict=True))
    if (
        rounded[0] == rounded[1]
        or (rounded[1] - rounded[0] >= 1)
        or error * length_bound * scale > 0.125
    ):
        raise RenderingError(
            "Lottie trim endpoint precision exceeds 1/8 pixel or collapses its interval; "
            "widen the interval or simplify the Path",
            path="/trim_start",
        )
    return {"s": 0, "e": width * 100, "o": first * 360}
