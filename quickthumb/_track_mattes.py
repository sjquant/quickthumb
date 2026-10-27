"""Scene-local track matte validation and canonical frame composition."""

from PIL import Image, ImageChops

from quickthumb.errors import ValidationError
from quickthumb.models import TrackMatte


def has_track_mattes(canvas) -> bool:
    return any(
        isinstance(getattr(layer, "mask", None), TrackMatte) for layer in canvas._iter_layers_deep()
    )


def validate_matte_graph(layers) -> None:
    """Validate references before rendering; only top-level scene layers are addressable."""
    from quickthumb._export_base import is_backdrop_dependent

    by_id = {layer.id: layer for layer in layers if getattr(layer, "id", None)}
    edges = {}
    locations = {}
    scene_layers = []
    pending = [(layer, f"/layers/{index}", True) for index, layer in enumerate(layers)]
    while pending:
        layer, pointer, top = pending.pop()
        scene_layers.append(layer)
        mask = getattr(layer, "mask", None)
        if isinstance(mask, TrackMatte):
            if not top or mask.layer not in by_id:
                raise ValidationError(
                    "Track mattes require an existing top-level source layer ID",
                    code="invalid_matte_source",
                    path=pointer + "/mask/layer",
                    layer_id=getattr(layer, "id", None),
                )
            edges[id(layer)] = id(by_id[mask.layer])
            locations[id(layer)] = pointer + "/mask/layer"
        pending.extend(
            (child, pointer + f"/children/{index}", False)
            for index, child in enumerate(getattr(layer, "children", ()))
        )
    if not edges:
        return
    done = set()
    for first in edges:
        active = set()
        node = first
        while node in edges and node not in done:
            if node in active:
                raise ValidationError("Track matte cycle", code="matte_cycle", path=locations[node])
            active.add(node)
            node = edges[node]
        done.update(active)
    endpoints = set(edges) | set(edges.values())
    descendants = [
        child
        for layer in layers
        if id(layer) in endpoints
        for child in getattr(layer, "children", ())
    ]
    while descendants:
        child = descendants.pop()
        if (
            getattr(child, "animation", None) is not None
            or getattr(child, "value", None) is not None
            or getattr(child, "type", None) == "video"
        ):
            raise ValidationError(
                "Matte source and target groups require static descendants",
                code="unsupported_matte_group_motion",
                path="/layers",
            )
        descendants.extend(getattr(child, "children", ()))
    if any(getattr(layer, "captions", None) for layer in scene_layers):
        raise ValidationError(
            "Track matte scenes do not support video captions",
            code="unsupported_matte_captions",
            path="/layers",
        )
    if any(is_backdrop_dependent(layer) for layer in scene_layers):
        raise ValidationError(
            "Track matte scenes do not support backdrop-dependent layers",
            code="unsupported_matte_backdrop",
            path="/layers",
        )


def render_matte_frame(animator, time, include_captions):
    """Resolve hidden matte sources once per frame in the complete scene clock."""
    canvas = animator._canvas
    units = animator._units
    by_id = {
        layer.id: unit for unit in units for layer in unit.layers if getattr(layer, "id", None)
    }
    sources = {
        layer.mask.layer
        for layer in canvas.layers
        if isinstance(getattr(layer, "mask", None), TrackMatte)
    }
    remaining = {}
    for unit in units:
        mask = getattr(unit.layers[0], "mask", None)
        if isinstance(mask, TrackMatte):
            key = id(by_id[mask.layer])
            remaining[key] = remaining.get(key, 0) + 1
    cache = {}

    def sample(unit):
        pending = [(unit, False)]
        while pending:
            current, ready = pending.pop()
            key = id(current)
            if key in cache:
                continue
            mask = getattr(current.layers[0], "mask", None)
            if isinstance(mask, TrackMatte) and not ready:
                pending.extend(((current, True), (by_id[mask.layer], False)))
                continue
            image = animator._composite_frame(
                [current],
                time,
                include_captions=include_captions,
                render_scale=animator._render_scale,
                downsample=False,
            )
            if isinstance(mask, TrackMatte):
                dependency = id(by_id[mask.layer])
                source = cache[dependency]
                alpha = source.getchannel("A")
                if mask.mode == "luma":
                    alpha = ImageChops.multiply(source.convert("L"), alpha)
                if mask.invert:
                    alpha = ImageChops.invert(alpha)
                image.putalpha(ImageChops.multiply(image.getchannel("A"), alpha))
                remaining[dependency] -= 1
                if remaining[dependency] == 0:
                    del cache[dependency]
                del source
            cache[key] = image
        return cache[id(unit)]

    frame = Image.new(
        "RGBA",
        (
            max(1, round(canvas.width * animator._render_scale)),
            max(1, round(canvas.height * animator._render_scale)),
        ),
    )
    for unit in units:
        if not any(getattr(layer, "id", None) in sources for layer in unit.layers):
            frame.alpha_composite(sample(unit))
            cache.pop(id(unit), None)
    if animator._render_scale != 1 and not animator._preview:
        frame = frame.resize((canvas.width, canvas.height), Image.Resampling.LANCZOS)
    return frame
