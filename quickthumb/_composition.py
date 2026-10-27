from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from PIL import Image, ImageChops, ImageDraw, ImageFilter

from quickthumb._base import RenderContext, apply_alignment, parse_coordinate
from quickthumb._effects import EffectsEngine
from quickthumb._path_fill import fill_path_mask
from quickthumb._path_geometry import flatten_path
from quickthumb.errors import RenderingError, ValidationError
from quickthumb.models import Align, BackdropBlur, LayerClip, LayerMask

Bounds = tuple[int, int, int, int]


@dataclass(frozen=True)
class ComposedLayer:
    """A clipped/masked layer patch ready to composite at a canvas offset."""

    image: Image.Image
    offset: tuple[int, int]


def has_layer_composition(layer: Any) -> bool:
    """Return True when a layer uses the W4a composition boundary."""
    return requires_composition_boundary(layer)


def requires_composition_boundary(layer: Any) -> bool:
    """Return True when a layer needs isolated alpha-boundary composition."""
    return getattr(layer, "clip", None) is not None or getattr(layer, "mask", None) is not None


def has_mask_tracks(layer) -> bool:
    animations = getattr(layer, "animation", None)
    specs = animations if isinstance(animations, list) else [animations]
    return any(
        track.type.startswith("mask_")
        for spec in specs
        for track in (getattr(spec, "tracks", None) or ())
    )


def has_animated_masks(canvas) -> bool:
    return any(has_mask_tracks(layer) for layer in canvas._iter_layers_deep())


def validate_mask_animation(layer):
    if not has_mask_tracks(layer):
        return
    if any(isinstance(effect, BackdropBlur) for effect in getattr(layer, "effects", ())):
        raise ValidationError(
            "Animated masks do not support owner BackdropBlur",
            code="unsupported_mask_backdrop",
            path="/effects",
        )
    if not isinstance(getattr(layer, "mask", None), LayerMask):
        raise ValidationError("Mask tracks require a LayerMask shape mask", path="/animation")
    animations = layer.animation if isinstance(layer.animation, list) else [layer.animation]
    if any(getattr(spec, "stagger", None) is not None for spec in animations):
        raise ValidationError("Mask tracks do not support stagger", path="/animation")
    pending = [layer]
    while pending:
        child = pending.pop()
        if getattr(child, "value", None) is not None:
            raise ValidationError(
                "Animated masks do not yet support counter sources", path="/animation"
            )
        pending.extend(getattr(child, "children", ()))


def without_mask(layer):
    """Keep the owner's full rendered body as the animated mask's stable pivot reference."""
    return layer.model_copy(update={"mask": None})


def with_motion_mask(layer, state, ctx):
    """Resolve owner-timeline geometry before transforming the owner's isolated pixels."""
    if not has_mask_tracks(layer):
        return layer
    validate_mask_animation(layer)
    mask = layer.mask
    x, y, width, height = _mask_bounds(ctx, mask)
    # Resolve alignment once against the authored box; resizing does not move its top-left.
    dx, dy = state.mask_position or (0, 0)
    view_box = mask.view_box or (0, 0, width, height) if mask.shape == "path" else None
    width, height = state.mask_size or (width, height)
    if any(
        not math.isfinite(value) or abs(value) > 2**28 for value in (x + dx, y + dy, width, height)
    ):
        raise RenderingError(
            "Animated mask exceeds finite raster coordinate range", code="mask_geometry_range"
        )
    feather = mask.feather if state.mask_feather is None else state.mask_feather
    mask = mask.model_copy(
        update={
            "position": (x + dx, y + dy),
            "width": width,
            "height": height,
            "align": Align.TOP_LEFT,
            "feather": feather,
            "view_box": view_box,
        }
    )
    return layer.model_copy(update={"mask": mask})


def layer_depends_on_backdrop(layer: Any) -> bool:
    """Return True when a layer effect samples already-composited pixels."""
    return any(isinstance(effect, BackdropBlur) for effect in getattr(layer, "effects", []))


def composite_layer_with_boundary(
    ctx: RenderContext,
    effects: EffectsEngine,
    image: Image.Image,
    layer: Any,
    render_isolated: Callable[[Image.Image], None],
) -> None:
    """Render a layer in isolation, apply composition, then composite it onto image."""
    layer_surface = Image.new("RGBA", image.size, (0, 0, 0, 0))
    render_isolated(layer_surface)
    composed = apply_layer_composition(ctx, layer_surface, layer)
    if composed is None:
        return

    for effect in getattr(layer, "effects", []):
        if isinstance(effect, BackdropBlur):
            _apply_backdrop_blur(image, composed, effect)

    blend_mode = getattr(layer, "blend_mode", None)
    if blend_mode:
        overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
        overlay.alpha_composite(composed.image, composed.offset)
        blended = effects.apply_blend_mode(image, overlay, blend_mode)
        image.paste(blended, (0, 0), overlay.split()[3])
        return

    image.alpha_composite(composed.image, composed.offset)


def composition_bounds(ctx: RenderContext, layer: Any) -> Bounds | None:
    """Return the visible composition bounds as (x, y, width, height) when finite."""
    bounds: Bounds | None = None
    clip = getattr(layer, "clip", None)
    if isinstance(clip, LayerClip):
        bounds = _intersect_bounds(bounds, _clip_bounds(ctx, clip))

    mask = getattr(layer, "mask", None)
    if isinstance(mask, LayerMask) and not mask.invert:
        mask_bounds = _mask_bounds(ctx, mask)
        if mask.feather:
            pad = _mask_padding(mask)
            x, y, w, h = mask_bounds
            mask_bounds = x - pad, y - pad, w + 2 * pad, h + 2 * pad
        if mask.opacity == 0.0:
            mask_bounds = mask_bounds[0], mask_bounds[1], 0, 0
        bounds = _intersect_bounds(bounds, mask_bounds)

    return bounds


def apply_layer_composition(
    ctx: RenderContext, layer_image: Image.Image, layer: Any
) -> ComposedLayer | None:
    """Apply clip, mask, and boundary effects to an isolated layer image."""
    offset = _composition_offset(ctx, layer, layer_image)
    if offset is None:
        return None

    left, top, right, bottom = offset
    layer_patch = layer_image.crop((left, top, right, bottom))
    alpha = layer_patch.split()[3]

    clip = getattr(layer, "clip", None)
    if isinstance(clip, LayerClip):
        alpha = ImageChops.multiply(
            alpha, _clip_alpha(ctx, layer_patch.size, clip, offset=(left, top))
        )

    mask = getattr(layer, "mask", None)
    if isinstance(mask, LayerMask):
        alpha = ImageChops.multiply(
            alpha, _mask_alpha(ctx, layer_patch.size, mask, offset=(left, top))
        )

    layer_patch.putalpha(alpha)
    return ComposedLayer(image=layer_patch, offset=(left, top))


def _apply_backdrop_blur(
    image: Image.Image,
    composed: ComposedLayer,
    effect: BackdropBlur,
) -> None:
    if effect.opacity == 0.0:
        return

    x, y = composed.offset
    box = (x, y, x + composed.image.width, y + composed.image.height)
    backdrop = image.crop(box).filter(ImageFilter.GaussianBlur(effect.radius))
    alpha = composed.image.split()[3]
    if effect.opacity < 1.0:
        alpha = alpha.point(lambda value: int(value * effect.opacity))
    backdrop.putalpha(alpha)
    image.alpha_composite(backdrop, composed.offset)


def _intersect_bounds(current: Bounds | None, incoming: Bounds) -> Bounds | None:
    if current is None:
        return incoming

    left = max(current[0], incoming[0])
    top = max(current[1], incoming[1])
    right = min(current[0] + current[2], incoming[0] + incoming[2])
    bottom = min(current[1] + current[3], incoming[1] + incoming[3])
    if right <= left or bottom <= top:
        return left, top, 0, 0
    return left, top, right - left, bottom - top


def _composition_offset(
    ctx: RenderContext, layer: Any, layer_image: Image.Image
) -> tuple[int, int, int, int] | None:
    bounds = composition_bounds(ctx, layer)
    if bounds is None:
        bbox = layer_image.getbbox()
        return None if bbox is None else bbox

    x, y, width, height = bounds
    if width <= 0 or height <= 0:
        return None

    left = max(0, math.floor(x))
    top = max(0, math.floor(y))
    right = min(layer_image.width, math.ceil(x + width))
    bottom = min(layer_image.height, math.ceil(y + height))
    if right <= left or bottom <= top:
        return None
    return left, top, right, bottom


def _clip_alpha(
    ctx: RenderContext,
    size: tuple[int, int],
    clip: LayerClip,
    *,
    offset: tuple[int, int] = (0, 0),
) -> Image.Image:
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
        offset=offset,
    )


def _mask_alpha(
    ctx: RenderContext,
    size: tuple[int, int],
    mask: LayerMask,
    *,
    offset: tuple[int, int] = (0, 0),
) -> Image.Image:
    x, y, width, height = _mask_bounds(ctx, mask)
    pad = _mask_padding(mask)
    padded_size = size[0] + 2 * pad, size[1] + 2 * pad
    if (mask.feather or mask.shape == "path") and padded_size[0] * padded_size[1] * 16 > 67_108_864:
        raise RenderingError(
            "Mask exceeds the 64-million-sample surface budget", code="mask_surface_limit"
        )
    if mask.shape == "path":
        assert mask.d is not None  # Validated by LayerMask.
        vx, vy, vw, vh = mask.view_box or (0, 0, width, height)
        contours = flatten_path(mask.d, (vx, vy), (width / vw, height / vh))
        origin = (offset[0] - pad - x, offset[1] - pad - y)
        bounds = (
            max(0, origin[0]),
            max(0, origin[1]),
            min(width, origin[0] + padded_size[0]),
            min(height, origin[1] + padded_size[1]),
        )
        alpha = fill_path_mask(
            contours, (padded_size[0] * 4, padded_size[1] * 4), bounds, origin=origin
        ).convert("L")
        # Polygon drawing includes its last sample; mask viewports are half-open like shapes.
        right = min(alpha.width, max(0, math.floor((width - origin[0]) * 4)))
        bottom = min(alpha.height, max(0, math.floor((height - origin[1]) * 4)))
        alpha.paste(0, (right, 0, alpha.width, alpha.height))
        alpha.paste(0, (0, bottom, alpha.width, alpha.height))
        if mask.opacity != 1:
            alpha = alpha.point(lambda value: round(value * mask.opacity))
        alpha = alpha.resize(padded_size, Image.Resampling.LANCZOS)
    else:
        alpha = _shape_alpha(
            padded_size,
            x,
            y,
            width,
            height,
            shape=mask.shape,
            points=mask.points,
            opacity=mask.opacity,
            offset=(offset[0] - pad, offset[1] - pad),
        )
    if pad:
        alpha = alpha.filter(ImageFilter.GaussianBlur(mask.feather)).crop(
            (pad, pad, pad + size[0], pad + size[1])
        )
    if mask.invert:
        alpha = ImageChops.invert(alpha)
    return alpha


def _mask_padding(mask):
    if mask.feather > 1024:
        raise RenderingError(
            "Feathered mask exceeds the 64-million-sample surface budget", code="mask_surface_limit"
        )
    return math.ceil(mask.feather * 3)


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
    x = position[0] if isinstance(position[0], float) else parse_coordinate(position[0], ctx.width)
    y = position[1] if isinstance(position[1], float) else parse_coordinate(position[1], ctx.height)
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
    offset: tuple[int, int] = (0, 0),
) -> Image.Image:
    scale = 4
    alpha = Image.new("L", (size[0] * scale, size[1] * scale), 0)
    draw = ImageDraw.Draw(alpha)
    local_x = x - offset[0]
    local_y = y - offset[1]
    bbox = [
        local_x * scale,
        local_y * scale,
        (local_x + width) * scale - 1,
        (local_y + height) * scale - 1,
    ]
    fill = round(255 * opacity)
    if bbox[2] < bbox[0] or bbox[3] < bbox[1]:
        return alpha.resize(size, Image.Resampling.LANCZOS)

    if shape == "ellipse":
        draw.ellipse(bbox, fill=fill)
    elif shape == "pill":
        draw.rounded_rectangle(bbox, radius=min(width, height) * scale // 2, fill=fill)
    elif shape == "polygon":
        assert points is not None
        pixel_points = [
            ((local_x + px * width) * scale, (local_y + py * height) * scale) for px, py in points
        ]
        draw.polygon(pixel_points, fill=fill)
    else:
        draw.rounded_rectangle(bbox, radius=border_radius * scale, fill=fill)

    return alpha.resize(size, Image.Resampling.LANCZOS)
