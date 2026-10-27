"""Polygonal path fill through a bounded, supersampled local viewport."""

import math
from collections.abc import Sequence
from typing import cast

from PIL import Image, ImageChops, ImageColor, ImageDraw

from quickthumb._base import RenderContext, parse_coordinate
from quickthumb._path_geometry import parse_path
from quickthumb.models import PathLayer


def render_path(image: Image.Image, layer: PathLayer, context: RenderContext) -> None:
    if layer.color is None:
        return
    x = parse_coordinate(layer.position[0], context.width)
    y = parse_coordinate(layer.position[1], context.height)
    vx, vy, vw, vh = layer.view_box or (0, 0, layer.width, layer.height)
    scale_x, scale_y = layer.width / vw, layer.height / vh
    contours = tuple(
        tuple(((px - vx) * scale_x, (py - vy) * scale_y) for px, py in contour)
        for contour in parse_path(layer.d)
        if len(contour) >= 3
    )
    points = [point for contour in contours for point in contour]
    if not points:
        return
    left = max(0, -x, math.floor(min(px for px, _ in points)))
    top = max(0, -y, math.floor(min(py for _, py in points)))
    right = min(layer.width, image.width - x, math.ceil(max(px for px, _ in points)))
    bottom = min(layer.height, image.height - y, math.ceil(max(py for _, py in points)))
    if right <= left or bottom <= top:
        return
    size = ((right - left) * 4, (bottom - top) * 4)
    mask = Image.new("1", size)
    for contour in contours:
        contour = _clip_polygon(contour, (left, top, right, bottom))
        if len(contour) < 3:
            continue
        part = Image.new("1", size)
        ImageDraw.Draw(part).polygon(
            [((px - left) * 4, (py - top) * 4) for px, py in contour], fill=1
        )
        mask = ImageChops.logical_xor(mask, part)
    alpha = mask.convert("L").resize((right - left, bottom - top), Image.Resampling.LANCZOS)
    color = cast(tuple[int, int, int, int], ImageColor.getcolor(layer.color, "RGBA"))
    if color[3] != 255:
        alpha = alpha.point(lambda value: round(value * color[3] / 255))
    painted = Image.new("RGBA", alpha.size, color)
    painted.putalpha(alpha)
    image.alpha_composite(painted, (x + left, y + top))


def _clip_polygon(
    points: Sequence[tuple[float, float]], bounds: tuple[int, int, int, int]
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
