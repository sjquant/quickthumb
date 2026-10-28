"""Native Lottie links over canonical local parent frames; never bake ancestors."""

import math

from quickthumb._parent_render import parent_geometry, participating_layers
from quickthumb._path_svg import _bounded_number
from quickthumb.errors import RenderingError


def parent_frames(canvas, frame_count):
    """Return canonical geometry and source-name -> native body-frame indices."""
    members = participating_layers(canvas)
    geometry = {key: parent_geometry(canvas, layer) for key, layer in members.items()}
    indices = {
        layer.id: index + 1
        for index, layer in enumerate(canvas.layers)
        if getattr(layer, "id", None)
    }
    referenced = {parent for layer in canvas.layers if (parent := getattr(layer, "parent", None))}
    frames = []
    for index, layer in enumerate(canvas.layers):
        if getattr(layer, "id", None) not in referenced or not getattr(layer, "rotation", 0):
            continue
        item = geometry[id(layer)]
        # Canonical body_to_baked is a static rotation plus its source-framing translation.
        _, _, x, _, _, y = item.body_to_baked
        if not all(_bounded_number(v, 1) for v in (x, y)) or not _bounded_number(
            layer.rotation, max(1, *item.body_size) * math.pi / 180
        ):
            raise RenderingError(
                "Lottie parent frame exceeds native precision",
                path=f"/layers/{index}/rotation",
                layer_id=layer.id,
            )
        frame_index = len(canvas.layers) + len(frames) + 1
        indices[layer.id] = frame_index
        frames.append(
            {
                "ty": 3,
                "ind": frame_index,
                "parent": index + 1,
                "nm": f"{layer.id} [body frame]",
                "ip": 0,
                "op": frame_count,
                "st": 0,
                "ks": {
                    "o": {"a": 0, "k": 100},
                    "r": {"a": 0, "k": layer.rotation},
                    "p": {"a": 0, "k": [x, y, 0]},
                    "a": {"a": 0, "k": [0, 0, 0]},
                    "s": {"a": 0, "k": [100, 100, 100]},
                },
            }
        )
    return geometry, indices, frames
