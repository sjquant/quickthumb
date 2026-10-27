"""Shared bounded even-odd path coverage for painted paths and alpha masks."""

from collections.abc import Sequence

from PIL import Image, ImageChops, ImageDraw

from quickthumb._path_geometry import _Contour


def fill_path_mask(
    contours: tuple[_Contour, ...],
    size: tuple[int, int],
    bounds: tuple[float, float, float, float],
    *,
    origin: tuple[float, float] | None = None,
) -> Image.Image:
    """Paint clipped local contours onto a four-times-resolution coverage surface."""
    left, top = origin if origin is not None else bounds[:2]
    mask = Image.new("1", size)
    if bounds[2] <= bounds[0] or bounds[3] <= bounds[1]:
        return mask
    for contour in contours:
        if len(contour.points) < 3:
            continue
        clipped = _clip_polygon(contour.points, bounds)
        if len(clipped) < 3:
            continue
        part = Image.new("1", size)
        ImageDraw.Draw(part).polygon(
            [((px - left) * 4, (py - top) * 4) for px, py in clipped], fill=1
        )
        mask = ImageChops.logical_xor(mask, part)
    return mask


def _clip_polygon(
    points: Sequence[tuple[float, float]], bounds: tuple[float, float, float, float]
) -> Sequence[tuple[float, float]]:
    """Keep drawing coordinates bounded even when a path crosses a distant viewport."""
    for axis, boundary, direction in (
        (0, bounds[0], 1),
        (0, bounds[2], -1),
        (1, bounds[1], 1),
        (1, bounds[3], -1),
    ):
        if not points:
            break
        output = []
        previous = points[-1]
        inside = direction * (previous[axis] - boundary) >= 0
        for point in points:
            next_inside = direction * (point[axis] - boundary) >= 0
            if inside != next_inside:
                t = (boundary - previous[axis]) / (point[axis] - previous[axis])
                x = previous[0] + t * (point[0] - previous[0])
                y = previous[1] + t * (point[1] - previous[1])
                output.append((boundary, y) if axis == 0 else (x, boundary))
            if next_inside:
                output.append(point)
            previous, inside = point, next_inside
        points = output
    return points
