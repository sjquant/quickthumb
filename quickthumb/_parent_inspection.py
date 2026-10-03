"""Authored-static parent frames for conservative world-layout observations."""

from __future__ import annotations

import math
from dataclasses import replace
from types import MappingProxyType
from typing import TYPE_CHECKING

from quickthumb._measurements import BBox, LayerMeasurement, LayerMeasurementEngine
from quickthumb._parent_render import (
    IDENTITY,
    Affine,
    authored_parent_frames,
    parent_geometry,
    parent_rendering_problem,
    participating_layers,
    settled_content,
)
from quickthumb.errors import RenderingError
from quickthumb.models import VideoLayer

if TYPE_CHECKING:
    from quickthumb.canvas import Canvas


def _point(matrix: Affine, x: float, y: float) -> tuple[float, float]:
    a, b, c, d, e, f = matrix
    point = (a * x + b * y + c, d * x + e * y + f)
    if not all(math.isfinite(value) for value in point):
        raise RenderingError("Parent layout bounds exceed finite coordinates")
    return point


def _snap(value: float) -> float:
    # Cardinal rotations otherwise expand an integer body by one whole pixel
    # because sin/cos arithmetic leaves a sub-nanopixel residue.
    nearest = round(value)
    return float(nearest) if abs(value - nearest) <= 1e-9 else value


def transform_bbox(box: BBox | None, frame: Affine) -> BBox | None:
    """Enclose the transformed measured body, without clipping to the viewport."""
    if box is None or frame == IDENTITY:
        return box
    if box.is_empty:
        x, y = _point(frame, box.x, box.y)
        return BBox(math.floor(_snap(x)), math.floor(_snap(y)), 0, 0)
    points = [_point(frame, x, y) for x in (box.x, box.right) for y in (box.y, box.bottom)]
    return BBox.from_points(
        math.floor(_snap(min(x for x, _ in points))),
        math.floor(_snap(min(y for _, y in points))),
        math.ceil(_snap(max(x for x, _ in points))),
        math.ceil(_snap(max(y for _, y in points))),
    )


def _world_measurement(measured: LayerMeasurement, frame: Affine) -> LayerMeasurement:
    children = tuple(_world_measurement(child, frame) for child in measured.children)
    metadata = dict(measured.metadata)
    if "children" in metadata:
        metadata["children"] = children
    if isinstance(metadata.get("layout_bbox"), BBox):
        metadata["layout_bbox"] = transform_bbox(metadata["layout_bbox"], frame)
    return replace(
        measured,
        bbox=transform_bbox(measured.bbox, frame),
        children=children,
        metadata=MappingProxyType(metadata),
    )


def measure_parent_layers(canvas: Canvas) -> list[LayerMeasurement]:
    """Measure supported parent scenes without allocating/rendering local sources.

    Text layout metadata stays authored-local. Bboxes are conservative world
    AABBs of the existing measured body, not tight painted-alpha footprints.
    """
    if problem := parent_rendering_problem(canvas):
        raise RenderingError(problem, code="unsupported_parent_rendering")
    layers = participating_layers(canvas)
    measure = LayerMeasurementEngine(canvas._ctx, canvas._groups, canvas._text)
    measured = measure.measure_layers(
        [settled_content(layer) if id(layer) in layers else layer for layer in canvas.layers]
    )
    measured = [
        replace(item, raw_layer=layer) for item, layer in zip(measured, canvas.layers, strict=True)
    ]
    by_identity = {id(item.raw_layer): item for item in measured}
    geometry = {
        key: parent_geometry(canvas, layer, by_identity[key]) for key, layer in layers.items()
    }
    ancestors, _ = authored_parent_frames(geometry)
    video_bodies = {
        key: BBox(*item.origin, *item.body_size)
        for key, item in geometry.items()
        if isinstance(item.layer, VideoLayer)
    }
    result = []
    for item in measured:
        key = id(item.raw_layer)
        if key in video_bodies:
            item = replace(
                item, bbox=measure._apply_composition_bounds(item.raw_layer, video_bodies[key])
            )
        result.append(_world_measurement(item, ancestors[key]) if key in ancestors else item)
    return result
