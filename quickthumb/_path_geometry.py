"""SVG polygonal path parsing, shared by validation and raster drawing."""

import math
import re
from functools import lru_cache

_TOKEN = re.compile(r"[A-Za-z]|[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?")


@lru_cache(maxsize=128)
def parse_path(data: str) -> tuple[tuple[tuple[float, float], ...], ...]:
    """Read M/L/H/V/Z subpaths; open contours close implicitly for filling."""
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

    contours: list[tuple[tuple[float, float], ...]] = []
    points: list[tuple[float, float]] = []
    current = (0.0, 0.0)
    moved = False
    command = ""
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token.isalpha():
            command = token
            index += 1
            if command.upper() not in {"M", "L", "H", "V", "Z"}:
                raise ValueError(f"SVG path command {command!r} is not supported; use M/L/H/V/Z")
            if command.upper() == "Z":
                if not moved:
                    raise ValueError("closepath requires a preceding moveto")
                if points:
                    current = points[0]
                    contours.append(tuple(points))
                    points = []
                command = ""
                continue
        if not command:
            raise ValueError("SVG path coordinates require a command")
        count = 2 if command.upper() in {"M", "L"} else 1
        values = tokens[index : index + count]
        if len(values) != count or any(value.isalpha() for value in values):
            raise ValueError(f"SVG path command {command!r} has incomplete coordinates")
        coordinates = [float(value) for value in values]
        if not all(math.isfinite(value) for value in coordinates):
            raise ValueError("SVG path coordinates must be finite")
        index += count
        relative = command.islower()
        if command.upper() in {"M", "L"}:
            point = (
                coordinates[0] + (current[0] if relative else 0),
                coordinates[1] + (current[1] if relative else 0),
            )
        elif command.upper() == "H":
            point = (coordinates[0] + (current[0] if relative else 0), current[1])
        else:
            point = (current[0], coordinates[0] + (current[1] if relative else 0))
        if command.upper() == "M":
            if points:
                contours.append(tuple(points))
            points = []
            moved = True
            command = "l" if relative else "L"
        elif not points:
            if not moved:
                raise ValueError("SVG path must begin with moveto")
            points.append(current)
        current = point
        if not all(math.isfinite(value) for value in current):
            raise ValueError("SVG path coordinates must be finite")
        points.append(current)
    if points:
        contours.append(tuple(points))
    return tuple(contours)
