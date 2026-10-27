"""Filled and stroked SVG paths through a bounded, supersampled local viewport."""

import math
from collections.abc import Sequence
from typing import cast

from PIL import Image, ImageChops, ImageColor, ImageDraw

from quickthumb._base import RenderContext, parse_coordinate
from quickthumb._effects import EffectsEngine
from quickthumb._path_dashes import dash_contours
from quickthumb._path_geometry import _Contour, flatten_path
from quickthumb._path_trim import trim_contours
from quickthumb.errors import RenderingError
from quickthumb.models import LinearGradient, PathLayer


def render_path(
    image: Image.Image, layer: PathLayer, context: RenderContext, effects: EffectsEngine
) -> None:
    if layer.color is None and layer.fill is None and layer.stroke is None:
        return
    x = parse_coordinate(layer.position[0], context.width)
    y = parse_coordinate(layer.position[1], context.height)
    vx, vy, vw, vh = layer.view_box or (0, 0, layer.width, layer.height)
    scale = (layer.width / vw, layer.height / vh)
    contours = flatten_path(layer.d, (vx, vy), scale)
    trimmed = (
        trim_contours(contours, layer.trim_start, layer.trim_end, layer.trim_offset, scale)
        if layer.stroke is not None
        else ()
    )
    paint_contours = contours if layer.color is not None or layer.fill is not None else trimmed
    points = [point for contour in paint_contours for point in contour.points]
    if not points:
        return
    padding = (
        layer.stroke_width / 2 * max(layer.miter_limit, math.sqrt(2))
        if layer.stroke and trimmed
        else 0
    )
    pad_x, pad_y = padding * scale[0], padding * scale[1]
    if not all(math.isfinite(value) for value in (pad_x, pad_y)):
        raise _stroke_limit()
    # Include the downsampling kernel around a clipped gradient, then composite only visible pixels.
    halo = 3 if layer.fill is not None else 0
    left = math.floor(max(0, -x - halo, min(px for px, _ in points) - pad_x - halo))
    top = math.floor(max(0, -y - halo, min(py for _, py in points) - pad_y - halo))
    right = math.ceil(
        min(layer.width, image.width - x + halo, max(px for px, _ in points) + pad_x + halo)
    )
    bottom = math.ceil(
        min(layer.height, image.height - y + halo, max(py for _, py in points) + pad_y + halo)
    )
    if right <= left or bottom <= top:
        return
    bounds = (left, top, right, bottom)
    size = ((right - left) * 4, (bottom - top) * 4)
    if layer.color is not None or layer.fill is not None:
        mask = Image.new("1", size)
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
        if layer.fill is not None:
            gradient_size = (layer.width * 4, layer.height * 4)
            region = (left * 4, top * 4, right * 4, bottom * 4)
            fill = layer.fill
            if isinstance(fill, LinearGradient):
                painted = effects.create_linear_gradient(
                    gradient_size, fill.angle, fill.stops, region=region
                )
            else:
                painted = effects.create_radial_gradient(
                    gradient_size, fill.stops, fill.center, region=region
                )
            painted.putalpha(ImageChops.multiply(painted.getchannel("A"), mask.convert("L")))
            painted = painted.resize((right - left, bottom - top), Image.Resampling.LANCZOS)
            image.alpha_composite(painted, (x + left, y + top))
        elif layer.color is not None:
            _paint_mask(image, mask, layer.color, (x + left, y + top))
    if layer.stroke is not None:
        mask = Image.new("1", size)
        strokes = dash_contours(trimmed, layer.dash_array, layer.dash_offset, scale)
        _stroke_mask(mask, strokes, layer, scale, bounds)
        _paint_mask(image, mask, layer.stroke, (x + left, y + top))


def _paint_mask(
    image: Image.Image, mask: Image.Image, color: str, position: tuple[int, int]
) -> None:
    alpha = mask.convert("L").resize((mask.width // 4, mask.height // 4), Image.Resampling.LANCZOS)
    rgba = cast(tuple[int, int, int, int], ImageColor.getcolor(color, "RGBA"))
    if rgba[3] != 255:
        alpha = alpha.point(lambda value: round(value * rgba[3] / 255))
    painted = Image.new("RGBA", alpha.size, rgba)
    painted.putalpha(alpha)
    image.alpha_composite(painted, position)


def _stroke_mask(
    mask: Image.Image,
    contours: tuple[_Contour, ...],
    layer: PathLayer,
    scale: tuple[float, float],
    bounds: tuple[int, int, int, int],
) -> None:
    radius = layer.stroke_width / 2
    if radius * max(scale) == 0:
        return
    draw = ImageDraw.Draw(mask)
    remaining = 65_536

    def polygon(points):
        nonlocal remaining
        remaining -= len(points)
        if remaining < 0 or not all(math.isfinite(v) for point in points for v in point):
            raise _stroke_limit()
        mapped = [(px * scale[0], py * scale[1]) for px, py in points]
        if not all(math.isfinite(v) for point in mapped for v in point):
            raise _stroke_limit()
        clipped = _clip_polygon(mapped, bounds)
        if len(clipped) >= 3:
            draw.polygon(
                [((px - bounds[0]) * 4, (py - bounds[1]) * 4) for px, py in clipped], fill=1
            )

    def circle(point):
        count = 4
        mapped_radius = radius * max(scale)
        while 2 * math.sin(math.pi / (2 * count)) ** 2 > 0.125 / mapped_radius:
            count *= 2
            if count > remaining:
                raise _stroke_limit()
        polygon(
            [
                (
                    point[0] + radius * math.cos(math.tau * i / count),
                    point[1] + radius * math.sin(math.tau * i / count),
                )
                for i in range(count)
            ]
        )

    for contour in contours:
        points = []
        for px, py in contour.points:
            point = (px / scale[0], py / scale[1])
            if not points or point != points[-1]:
                points.append(point)
        if contour.closed and len(points) > 1 and points[0] == points[-1]:
            points.pop()
        if len(points) == 1:
            if layer.line_cap == "round":
                circle(points[0])
            elif layer.line_cap == "square":
                cx, cy = points[0]
                tx, ty = contour.tangent[0] / scale[0], contour.tangent[1] / scale[1]
                length = math.hypot(tx, ty)
                if not math.isfinite(length) or length == 0:
                    raise _stroke_limit()
                dx, dy = tx / length * radius, ty / length * radius
                polygon(
                    [
                        (cx - dx + dy, cy - dy - dx),
                        (cx + dx + dy, cy + dy - dx),
                        (cx + dx - dy, cy + dy + dx),
                        (cx - dx - dy, cy - dy + dx),
                    ]
                )
            continue
        edges = list(
            zip(points, points[1:] + points[:1] if contour.closed else points[1:], strict=False)
        )
        directions = []
        for a, b in edges:
            dx, dy = b[0] - a[0], b[1] - a[1]
            length = math.hypot(dx, dy)
            if not math.isfinite(length) or length == 0:
                raise _stroke_limit()
            dx, dy = dx / length, dy / length
            directions.append((dx, dy))
            nx, ny = -dy * radius, dx * radius
            polygon(
                [
                    (a[0] + nx, a[1] + ny),
                    (b[0] + nx, b[1] + ny),
                    (b[0] - nx, b[1] - ny),
                    (a[0] - nx, a[1] - ny),
                ]
            )
        for index in range(len(points)) if contour.closed else range(1, len(points) - 1):
            before, after = directions[index - 1], directions[index % len(directions)]
            cx, cy = points[index]
            cross = before[0] * after[1] - before[1] * after[0]
            if cross == 0 and before == after:
                continue
            if layer.line_join == "round":
                circle((cx, cy))
                continue
            sign = -1 if cross > 0 else 1
            a = (-before[1] * sign, before[0] * sign)
            b = (-after[1] * sign, after[0] * sign)
            join = [(cx + a[0] * radius, cy + a[1] * radius)]
            denominator = 1 + before[0] * after[0] + before[1] * after[1]
            if layer.line_join == "miter" and denominator > 0:
                mx, my = (a[0] + b[0]) / denominator, (a[1] + b[1]) / denominator
                if math.hypot(mx, my) <= layer.miter_limit:
                    join.append((cx + mx * radius, cy + my * radius))
            join.extend(((cx + b[0] * radius, cy + b[1] * radius), (cx, cy)))
            polygon(join)
        if not contour.closed:
            for point, direction, sign in (
                (points[0], directions[0], -1),
                (points[-1], directions[-1], 1),
            ):
                if layer.line_cap == "round":
                    circle(point)
                elif layer.line_cap == "square":
                    dx, dy = direction[0] * radius * sign, direction[1] * radius * sign
                    nx, ny = -direction[1] * radius, direction[0] * radius
                    cx, cy = point
                    polygon(
                        [
                            (cx + nx, cy + ny),
                            (cx + nx + dx, cy + ny + dy),
                            (cx - nx + dx, cy - ny + dy),
                            (cx - nx, cy - ny),
                        ]
                    )


def _stroke_limit() -> RenderingError:
    return RenderingError(
        "Path stroke exceeds finite geometry or the bounded render plan; "
        "simplify d or reduce stroke width",
        code="path_stroke_limit",
        path="/d",
    )


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
