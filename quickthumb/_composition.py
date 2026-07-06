from __future__ import annotations

from typing import Any

from PIL import Image, ImageChops, ImageDraw

from quickthumb._base import RenderContext, apply_alignment, parse_coordinate
from quickthumb.models import Align, LayerClip, LayerMask


def has_layer_composition(layer: Any) -> bool:
    """Return True when a layer uses the W4a composition boundary."""
    return getattr(layer, "clip", None) is not None or getattr(layer, "mask", None) is not None


def composition_bounds(ctx: RenderContext, layer: Any) -> tuple[int, int, int, int] | None:
    """Return the visible composition bounds as (x, y, width, height) when finite."""
    bounds: tuple[int, int, int, int] | None = None
    clip = getattr(layer, "clip", None)
    if isinstance(clip, LayerClip):
        bounds = _intersect_bounds(bounds, _clip_bounds(ctx, clip))

    mask = getattr(layer, "mask", None)
    if isinstance(mask, LayerMask) and not mask.invert:
        bounds = _intersect_bounds(bounds, _mask_bounds(ctx, mask))

    return bounds


def apply_layer_composition(
    ctx: RenderContext, layer_image: Image.Image, layer: Any
) -> Image.Image:
    """Apply clip and mask primitives to a full-canvas rendered layer image."""
    alpha = layer_image.split()[3]

    clip = getattr(layer, "clip", None)
    if isinstance(clip, LayerClip):
        alpha = ImageChops.multiply(alpha, _clip_alpha(ctx, layer_image.size, clip))

    mask = getattr(layer, "mask", None)
    if isinstance(mask, LayerMask):
        alpha = ImageChops.multiply(alpha, _mask_alpha(ctx, layer_image.size, mask))

    result = layer_image.copy()
    result.putalpha(alpha)
    return result


def _intersect_bounds(
    current: tuple[int, int, int, int] | None, incoming: tuple[int, int, int, int]
) -> tuple[int, int, int, int] | None:
    if current is None:
        return incoming

    left = max(current[0], incoming[0])
    top = max(current[1], incoming[1])
    right = min(current[0] + current[2], incoming[0] + incoming[2])
    bottom = min(current[1] + current[3], incoming[1] + incoming[3])
    if right <= left or bottom <= top:
        return None
    return left, top, right - left, bottom - top


def _clip_alpha(ctx: RenderContext, size: tuple[int, int], clip: LayerClip) -> Image.Image:
    x, y, width, height = _clip_bounds(ctx, clip)
    return _shape_alpha(
        size,
        x,
        y,
        width,
        height,
        shape="rectangle",
        border_radius=clip.border_radius,
        opacity=1.0,
    )


def _mask_alpha(ctx: RenderContext, size: tuple[int, int], mask: LayerMask) -> Image.Image:
    x, y, width, height = _mask_bounds(ctx, mask)
    alpha = _shape_alpha(
        size,
        x,
        y,
        width,
        height,
        shape=mask.shape,
        points=mask.points,
        opacity=mask.opacity,
    )
    if mask.invert:
        alpha = ImageChops.invert(alpha)
    return alpha


def _clip_bounds(ctx: RenderContext, clip: LayerClip) -> tuple[int, int, int, int]:
    return _aligned_bounds(ctx, clip.position, clip.width, clip.height, clip.align)


def _mask_bounds(ctx: RenderContext, mask: LayerMask) -> tuple[int, int, int, int]:
    return _aligned_bounds(ctx, mask.position, mask.width, mask.height, mask.align)


def _aligned_bounds(
    ctx: RenderContext,
    position: tuple[int | str, int | str],
    width: int,
    height: int,
    align: Align | None,
) -> tuple[int, int, int, int]:
    x = parse_coordinate(position[0], ctx.width)
    y = parse_coordinate(position[1], ctx.height)
    if align is not None and align != Align.TOP_LEFT:
        x, y = apply_alignment(x, y, (width, height), align)
    return x, y, width, height


def _shape_alpha(
    size: tuple[int, int],
    x: int,
    y: int,
    width: int,
    height: int,
    *,
    shape: str,
    border_radius: int = 0,
    points: list[tuple[float, float]] | None = None,
    opacity: float = 1.0,
) -> Image.Image:
    scale = 4
    alpha = Image.new("L", (size[0] * scale, size[1] * scale), 0)
    draw = ImageDraw.Draw(alpha)
    bbox = [
        x * scale,
        y * scale,
        (x + width) * scale - 1,
        (y + height) * scale - 1,
    ]
    fill = round(255 * opacity)

    if shape == "ellipse":
        draw.ellipse(bbox, fill=fill)
    elif shape == "pill":
        draw.rounded_rectangle(bbox, radius=min(width, height) * scale // 2, fill=fill)
    elif shape == "polygon":
        assert points is not None
        pixel_points = [((x + px * width) * scale, (y + py * height) * scale) for px, py in points]
        draw.polygon(pixel_points, fill=fill)
    else:
        draw.rounded_rectangle(bbox, radius=border_radius * scale, fill=fill)

    return alpha.resize(size, Image.Resampling.LANCZOS)
