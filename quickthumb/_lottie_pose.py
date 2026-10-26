"""Bake canonical pose states as bounded, held Lottie vector properties."""

import math

from PIL import Image

from quickthumb._base import apply_alignment, expanded_rotation_size, parse_coordinate
from quickthumb._path_svg import _bounded_number
from quickthumb._sampling import _MAX_CAPTURE_BYTES, _MAX_OBSERVATIONS
from quickthumb.errors import RenderingError
from quickthumb.models import BackgroundLayer, NullLayer, PathLayer, ShapeLayer
from quickthumb.motion import LayerState


def _property(value):
    return {"a": 0, "k": value}


def pose_boundaries(timelines):
    boundaries = {0.0}
    for timeline in timelines:
        for event in timeline.events if timeline is not None else ():
            boundaries.update((event.active_start, event.end))
            for track in event.tracks:
                boundaries.update(
                    event.active_start + key.time
                    for key in track.keyframes
                    if key.time <= event.duration
                )
    return boundaries


def _times(timeline, fps, boundaries):
    count = (
        math.ceil(timeline.duration * fps)
        if math.isfinite(timeline.duration * fps)
        else _MAX_OBSERVATIONS
    )
    selected = {time for time in boundaries if time <= timeline.duration}
    if count + len(selected) > _MAX_OBSERVATIONS:
        raise RenderingError(
            "Lottie exceeds 100000 pose samples; lower fps or simplify motion", path="/animation"
        )
    selected.update(index / fps for index in range(count))
    return sorted(selected)


def shape_source_box(canvas, layer):
    width, height = expanded_rotation_size((layer.width, layer.height), layer.rotation)
    x = parse_coordinate(layer.position[0], canvas.width)
    y = parse_coordinate(layer.position[1], canvas.height)
    if layer.align:
        x, y = apply_alignment(x, y, (width, height), layer.align)
    return x, y, width, height


def layer_pose(canvas, layer, shapes, timeline, fps, boundaries, geometry=None):
    """Return native source geometry and one canonical animated object transform."""
    if isinstance(layer, BackgroundLayer):
        return (
            shapes,
            {
                "o": _property(layer.opacity * 100),
                "r": _property(0),
                "p": _property([0, 0, 0]),
                "a": _property([0, 0, 0]),
                "s": _property([100, 100, 100]),
            },
            0,
        )
    x = parse_coordinate(layer.position[0], canvas.width)
    y = parse_coordinate(layer.position[1], canvas.height)
    width, height = getattr(layer, "width", 0), getattr(layer, "height", 0)
    anchor = [layer.anchor[0] * width, layer.anchor[1] * height, 0]
    static = {
        "ty": "tr",
        "p": _property([0, 0]),
        "a": _property([0, 0]),
        "s": _property([100, 100]),
        "r": _property(0),
        "o": _property(100),
    }
    if isinstance(layer, NullLayer):
        if geometry is not None:
            x, y = geometry.origin
        anchor = [0, 0, 0]
    elif isinstance(layer, PathLayer):
        vx, vy, vw, vh = layer.view_box or (0, 0, width, height)
        static.update(a=_property([vx, vy]), s=_property([width / vw * 100, height / vh * 100]))
    else:
        assert isinstance(layer, ShapeLayer)
        x, y, width, height = shape_source_box(canvas, layer)
        static.update(
            a=_property([layer.width / 2, layer.height / 2]),
            p=_property([width / 2, height / 2]),
            r=_property(layer.rotation),
        )
        if geometry is not None:
            x, y = geometry.origin
            width, height = geometry.body_size
            _, _, tx, _, _, ty = geometry.body_to_baked
            static.update(a=_property([0, 0]), p=_property([tx, ty]))
        if timeline is not None:
            if max(width * height, layer.width * layer.height) * 4 * 16 > _MAX_CAPTURE_BYTES:
                raise RenderingError(
                    "Shape pivot probe exceeds the canonical capture budget; reduce its size",
                    path="/width",
                )
            # Match the canonical whole-source pivot without serializing raster imagery.
            source = Image.new("RGBA", (width, height))
            probe = layer.model_copy(update={"position": (0, 0), "align": None, "animation": None})
            if geometry is not None:
                from quickthumb._export_base import _with_motion_color
                from quickthumb._parent_render import _opaque_reference

                probe = _with_motion_color(_opaque_reference(probe), "#FFFFFF")
            canvas._shapes.render_shape_layer(source, probe)
            left, top, right, bottom = source.getbbox() or (0, 0, width, height)
            anchor = [
                left + layer.anchor[0] * (right - left),
                top + layer.anchor[1] * (bottom - top),
                0,
            ]
        else:
            anchor = [0, 0, 0]
    transformed = [] if isinstance(layer, NullLayer) else [{"ty": "gr", "it": [*shapes, static]}]
    times = _times(timeline, fps, boundaries) if timeline is not None else [0.0]
    rows = []
    trim_rows = []
    trim = None
    if isinstance(layer, PathLayer) and layer.stroke:
        from quickthumb._lottie_trim import needs_trim, trim_length_bound, trim_properties

        if needs_trim(layer):
            trim = shapes[0]["it"][-2]
            length_bound = trim_length_bound(layer)
    for time in times:
        state = (
            timeline.sample(time, LayerState(anchor=layer.anchor))
            if timeline is not None
            else LayerState(anchor=layer.anchor)
        )
        if isinstance(layer, (ShapeLayer, NullLayer)) and state.scale <= 0:
            raise RenderingError(
                "Nonpositive uniform Shape/Null scale is not supported by this canonical renderer",
                path="/animation",
            )
        dx, dy = state.position or (0, 0)
        rotation = state.rotation + (
            layer.rotation
            if isinstance(layer, PathLayer) or isinstance(layer, NullLayer) and geometry is None
            else 0
        )
        position = [x + anchor[0] + dx, y + anchor[1] + dy, 0]
        sx, sy = state.scale * state.scale_x * 100, state.scale * state.scale_y * 100
        values = {
            "o": getattr(layer, "opacity", 1.0) * state.opacity * 100,
            "r": rotation,
            "p": position,
            "a": anchor,
            "s": [sx, sy, 100],
        }
        checks = [(v, 1) for v in position + anchor]
        checks.extend(
            (
                (rotation, max(1, width, height) * math.pi / 180),
                (sx, width / 100),
                (sy, height / 100),
            )
        )
        if any(not _bounded_number(value, scale) for value, scale in checks):
            raise RenderingError(
                "Lottie pose exceeds native coordinate precision", path="/animation"
            )
        rows.append(values)
        if trim is not None:
            trim_rows.append(trim_properties(layer, state, length_bound))
    if trim is not None:
        trim.update(_sampled_properties(times, trim_rows, fps))
    return transformed, _sampled_properties(times, rows, fps), len(times) if timeline else 0


def _sampled_properties(times, rows, fps):
    """Serialize constant or held sampled vector properties on the shared clock."""
    keys = {}
    for name in rows[0]:
        values = [row[name] for row in rows]
        if all(value == values[0] for value in values):
            keys[name] = _property(values[0])
        else:
            keys[name] = {
                "a": 1,
                "k": [
                    {"t": time * fps, "s": value if isinstance(value, list) else [value], "h": 1}
                    for time, value in zip(times, values, strict=True)
                ],
            }
    return keys
