"""Repaint a visible path source at its sampled device density before compositing."""

import math

from PIL import Image

from quickthumb._base import RenderContext, parse_coordinate
from quickthumb._effects import EffectsEngine
from quickthumb._parent_render import affine_fragment, affine_state, multiply, translate
from quickthumb._path_geometry import flatten_path
from quickthumb._paths import render_path
from quickthumb.errors import RenderingError
from quickthumb.models import PathLayer
from quickthumb.motion import LayerState, _canonical_timeline


def render_path_frame(
    image: Image.Image,
    layer: PathLayer,
    context: RenderContext,
    effects: EffectsEngine,
    *,
    time: float | None = None,
    state: LayerState | None = None,
    render_scale: float = 1,
) -> None:
    """Apply motion about the authored viewport without clipping its source to the canvas."""
    if state is None:
        timeline = _canonical_timeline(layer) if time is not None else None
        state = LayerState(anchor=layer.anchor)
        if timeline is not None:
            assert time is not None
            state = timeline.sample(time, state)
    dash_offset = layer.dash_offset + state.dash_offset
    if not math.isfinite(dash_offset):
        raise RenderingError("sampled Path dash_offset must be finite", path="/dash_offset")
    layer = layer.model_copy(update={"dash_offset": dash_offset})
    opacity = layer.opacity * state.opacity
    if opacity <= 0 or state.scale * state.scale_x * state.scale_y == 0:
        return
    if (
        state == LayerState(anchor=layer.anchor)
        and not layer.rotation
        and opacity == 1
        and render_scale == 1
    ):
        render_path(image, layer, context, effects)
        return
    rotation = layer.rotation + state.rotation
    if not math.isfinite(rotation):
        raise _source_limit()
    state = state.with_values(rotation=rotation)
    x = parse_coordinate(layer.position[0], context.width)
    y = parse_coordinate(layer.position[1], context.height)
    matrix = multiply(translate(x, y), affine_state(state, (layer.width, layer.height)))
    matrix = multiply((render_scale, 0, 0, 0, render_scale, 0), matrix)
    a, b, c, d, e, f = matrix
    determinant = a * e - b * d
    if not math.isfinite(determinant):
        raise _source_limit()
    if determinant == 0:
        return
    # The maximum singular value covers nonuniform scale after rotation, and
    # remains valid when this source is later consumed by a full parent affine.
    norm = max(abs(a), abs(b), abs(d), abs(e))
    unit_a, unit_b, unit_d, unit_e = a / norm, b / norm, d / norm, e / norm
    trace = unit_a**2 + unit_b**2 + unit_d**2 + unit_e**2
    discriminant = max(0, trace**2 - 4 * (unit_a * unit_e - unit_b * unit_d) ** 2)
    maximum_scale = norm * math.sqrt((trace + math.sqrt(discriminant)) / 2)
    if not math.isfinite(maximum_scale):
        raise _source_limit()
    density = max(1, math.ceil(maximum_scale))
    inverse = (e / determinant, -b / determinant, -d / determinant, a / determinant)
    corners = [
        (
            inverse[0] * (px - c) + inverse[1] * (py - f),
            inverse[2] * (px - c) + inverse[3] * (py - f),
        )
        for px, py in (
            (-3, -3),
            (image.width + 3, -3),
            (-3, image.height + 3),
            (image.width + 3, image.height + 3),
        )
    ]
    if not all(math.isfinite(v) for point in corners for v in point):
        raise _source_limit()
    left = max(0, math.floor(min(px for px, _ in corners) - 3 / density))
    top = max(0, math.floor(min(py for _, py in corners) - 3 / density))
    right = min(layer.width, math.ceil(max(px for px, _ in corners) + 3 / density))
    bottom = min(layer.height, math.ceil(max(py for _, py in corners) + 3 / density))
    vx, vy, vw, vh = layer.view_box or (0, 0, layer.width, layer.height)
    contours = flatten_path(
        layer.d, (vx, vy), (layer.width / vw * density, layer.height / vh * density)
    )
    points = [point for contour in contours for point in contour.points]
    if not points:
        return
    if not all(math.isfinite(value) for point in points for value in point):
        raise _source_limit()
    padding = layer.stroke_width / 2 * max(layer.miter_limit, math.sqrt(2)) if layer.stroke else 0
    pad_x, pad_y = (
        padding * layer.width / vw + 3 / density,
        padding * layer.height / vh + 3 / density,
    )
    if not all(math.isfinite(value) for value in (pad_x, pad_y)):
        raise _source_limit()
    left = max(left, math.floor(min(px for px, _ in points) / density - pad_x))
    top = max(top, math.floor(min(py for _, py in points) / density - pad_y))
    right = min(right, math.ceil(max(px for px, _ in points) / density + pad_x))
    bottom = min(bottom, math.ceil(max(py for _, py in points) / density + pad_y))
    if right <= left or bottom <= top:
        return
    size = ((right - left) * density, (bottom - top) * density)
    # The painter uses 4x supersampling: at most 16M supersampled pixels and
    # one retained <=4MiB RGBA source per renderer, never one image per frame.
    if size[0] * size[1] > 1_048_576:
        raise _source_limit()
    key = (
        layer.model_dump_json(
            exclude={
                "position",
                "animation",
                "anchor",
                "parent",
                "rotation",
                "opacity",
                "id",
                "motion_key",
            }
        ),
        density,
        left,
        top,
        right,
        bottom,
    )
    cached = context.path_source
    if cached is not None and cached[0] == key:
        source = cached[1]
    else:
        source = Image.new("RGBA", size)
        scaled = layer.model_copy(
            update={
                "width": layer.width * density,
                "height": layer.height * density,
                "position": (-left * density, -top * density),
                "view_box": layer.view_box or (0, 0, layer.width, layer.height),
            }
        )
        render_path(source, scaled, context, effects)
        context.path_source = (key, source)
    sampled = multiply(matrix, (1 / density, 0, left, 0, 1 / density, top))
    fragment = affine_fragment(source, sampled, image.size)
    if fragment is not None:
        painted, position = fragment
        # Bicubic reconstruction can overshoot a translucent source's alpha.
        # Preserve its coverage ceiling and apply opacity once after geometry.
        maximum_alpha = source.getchannel("A").getextrema()[1]
        assert isinstance(maximum_alpha, (int, float))
        painted.putalpha(
            painted.getchannel("A").point(lambda value: round(min(value, maximum_alpha) * opacity))
        )
        image.alpha_composite(painted, position)


def _source_limit() -> RenderingError:
    return RenderingError(
        "Path motion exceeds the bounded visible-source render plan; reduce scale or output size",
        code="path_source_limit",
        path="/d",
    )
