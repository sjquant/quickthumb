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
