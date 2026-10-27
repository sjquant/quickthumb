"""Trusted synchronous plugin pixels, isolated from the canvas backdrop."""

from copy import deepcopy

from PIL import Image

from quickthumb._base import RenderContext, apply_alignment, parse_coordinate
from quickthumb.errors import RenderingError
from quickthumb.models import PluginLayer
from quickthumb.plugins import PluginRegistry, PluginRenderContext


def plugin_context(layer: PluginLayer, ctx: RenderContext) -> PluginRenderContext:
    def read_asset(name: str) -> bytes:
        if name not in layer.assets:
            raise RenderingError(f"Plugin asset '{name}' is not declared in assets.")
        return ctx.asset_resolver.resolve(layer.assets[name], "plugin").data

    return PluginRenderContext((layer.width, layer.height), read_asset)


def plugin_image(layer: PluginLayer, context: PluginRenderContext, registry: PluginRegistry):
    """Capture canonical local RGBA with authored opacity, before placement."""
    callback = registry._raster_callback(layer)
    try:
        raw = callback(deepcopy(layer.params), context)
    except Exception as error:
        raise RenderingError(
            f"Plugin '{layer.renderer}' version '{layer.version}' failed: {error}",
            code="plugin_render_failed",
            layer_id=layer.id,
            suggestion="check the registered callback and its declared assets",
        ) from error
    if not isinstance(raw, bytes) or len(raw) != layer.width * layer.height * 4:
        raise RenderingError(
            f"Plugin '{layer.renderer}' must return exactly {layer.width * layer.height * 4} "
            "straight-alpha RGBA8 bytes.",
            code="plugin_invalid_rgba",
            layer_id=layer.id,
        )
    patch = Image.frombytes("RGBA", context.size, raw)
    if layer.opacity != 1:
        patch.putalpha(patch.getchannel("A").point(lambda alpha: int(alpha * layer.opacity)))
    return patch


def render_plugin_layer(
    image: Image.Image, layer: PluginLayer, ctx: RenderContext, registry: PluginRegistry
) -> None:
    context = plugin_context(layer, ctx)
    x = parse_coordinate(layer.position[0], ctx.width)
    y = parse_coordinate(layer.position[1], ctx.height)
    if layer.align is not None:
        x, y = apply_alignment(x, y, context.size, layer.align)
    with plugin_image(layer, context, registry) as patch:
        image.alpha_composite(patch, (x, y))
