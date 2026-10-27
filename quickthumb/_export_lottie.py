"""Static native-vector Lottie subset; unsupported source features fail before writes."""

from __future__ import annotations

import math
from pathlib import Path
from typing import TYPE_CHECKING, cast

from PIL import ImageColor

from quickthumb._base import apply_alignment, parse_coordinate
from quickthumb._document import _ExportReceipt, canonical_json
from quickthumb._path_geometry import parse_path
from quickthumb._shapes import TRIANGLE_POINTS, ShapeEngine
from quickthumb.errors import ErrorDetail, RenderingError
from quickthumb.models import (
    BackgroundLayer,
    ExportDiagnostic,
    LottieOptions,
    PathLayer,
    ShapeLayer,
)

if TYPE_CHECKING:
    from quickthumb.canvas import Canvas
    from quickthumb.deck import Deck


def _layer_problem(layer) -> tuple[str, str] | None:
    if not isinstance(layer, (BackgroundLayer, ShapeLayer, PathLayer)):
        return (
            "type",
            f"{getattr(layer, 'type', 'custom')} layers are not supported by static Lottie",
        )
    for field in (
        "animation",
        "parent",
        "fill",
        "gradient",
        "image",
        "effects",
        "clip",
        "mask",
        "blend_mode",
        "rotation",
    ):
        if getattr(layer, field, None):
            return field, f"{field} is not supported by static Lottie"
    if isinstance(layer, PathLayer):
        if (
            layer.dash_array
            or layer.dash_offset
            or (layer.trim_start, layer.trim_end, layer.trim_offset) != (0, 1, 0)
        ):
            return "d", "Path dashes and trimming require a later Lottie geometry layer"
        segments = parse_path(layer.d)
        if any(segment.kind not in {"M", "L", "Z"} for segment in segments):
            return "d", "Static Lottie paths currently require straight M/L/H/V/Z segments"
        if layer.stroke:
            contours = []
            for segment in segments:
                if segment.kind == "M":
                    contours.append(set())
                if segment.points:
                    contours[-1].add(segment.points[0])
            if any(len(points) < 2 for points in contours):
                return "d", "Degenerate stroked contours are not supported by static Lottie"
        vx, vy, vw, vh = layer.view_box or (0, 0, layer.width, layer.height)
        if layer.stroke and layer.width / vw != layer.height / vh:
            return "stroke", "Lottie strokes currently require uniform view-box scaling"
        pad = layer.stroke_width * layer.miter_limit / 2 if layer.stroke else 0
        if any(
            not (vx + pad <= x <= vx + vw - pad and vy + pad <= y <= vy + vh - pad)
            for segment in segments
            for x, y in segment.points
        ):
            return (
                "d",
                "Path paint must fit inside its viewport; "
                "Lottie viewport clipping is not supported",
            )
    return None


def _problems(source: Canvas | Deck) -> list[ErrorDetail]:
    if hasattr(source, "slides"):
        return [
            ErrorDetail(
                code="unsupported_capability",
                category="export",
                path="/slides",
                message="Lottie currently requires a single Canvas",
            )
        ]
    source._validate_layer_identities()
    from quickthumb.motion import _iter_export_layer_locations

    errors = []
    for layer_id, pointer, layer in _iter_export_layer_locations(source):
        problem = _layer_problem(layer)
        if isinstance(layer, BackgroundLayer) and pointer != "/layers/0":
            problem = "type", "A Lottie background must be the first layer"
        if problem:
            field, message = problem
            errors.append(
                ErrorDetail(
                    code="unsupported_capability",
                    category="export",
                    path=f"{pointer}/{field}",
                    layer_id=layer_id,
                    message=message,
                    suggestion="remove this feature or export to another target",
                )
            )
    return errors


def validate_lottie(source: Canvas | Deck) -> list[ExportDiagnostic]:
    """List unsupported source features without resolving assets or rendering."""
    errors = _problems(source)
    if errors:
        return [
            ExportDiagnostic(
                target="lottie",
                feature="layer_representation",
                support="unsupported",
                layer_id=error.layer_id,
                message=error.format(),
            )
            for error in errors
        ]
    from quickthumb.motion import _iter_export_layer_locations

    return [
        ExportDiagnostic(
            target="lottie",
            feature="layer_representation",
            support="native",
            layer_id=layer_id,
            message="Static native Lottie vector",
        )
        for layer_id, _, _ in _iter_export_layer_locations(source)
    ]


def _property(value):
    return {"a": 0, "k": value}


def _contour(points, closed):
    return {
        "ty": "sh",
        "ks": _property(
            {"v": points, "i": [[0, 0] for _ in points], "o": [[0, 0] for _ in points], "c": closed}
        ),
    }


def _paint(color, stroke=None):
    rgba = (
        cast(tuple[int, int, int, int], ImageColor.getcolor(color, "RGBA"))
        if isinstance(color, str)
        else (*color[:3], color[3] if len(color) == 4 else 255)
    )
    result = {
        "ty": "st" if stroke else "fl",
        "c": _property([v / 255 for v in rgba[:3]]),
        "o": _property(rgba[3] / 255 * 100),
    }
    if stroke:
        result.update(
            w=_property(stroke.stroke_width),
            lc={"butt": 1, "round": 2, "square": 3}[stroke.line_cap],
            lj={"miter": 1, "round": 2, "bevel": 3}[stroke.line_join],
            ml=stroke.miter_limit,
        )
    else:
        result["r"] = 2  # Canonical Path fills use even-odd contours.
    return result


def _shapes(layer, width, height):
    if isinstance(layer, BackgroundLayer):
        return (
            [
                {
                    "ty": "rc",
                    "s": _property([width, height]),
                    "p": _property([width / 2, height / 2]),
                    "r": _property(0),
                },
                _paint(layer.color),
            ]
            if layer.color is not None
            else []
        )
    if isinstance(layer, ShapeLayer):
        w, h = layer.width, layer.height
        if layer.shape in {"rectangle", "ellipse", "pill"}:
            geometry = {
                "ty": "el" if layer.shape == "ellipse" else "rc",
                "d": 1,
                "s": _property([w, h]),
                "p": _property([w / 2, h / 2]),
            }
            if layer.shape != "ellipse":
                geometry["r"] = _property(
                    min(w, h) / 2
                    if layer.shape == "pill"
                    else min(layer.border_radius, w / 2, h / 2)
                )
        else:
            points = (
                TRIANGLE_POINTS
                if layer.shape == "triangle"
                else ShapeEngine._star_points(layer.star_points, layer.inner_radius)
                if layer.shape == "star"
                else layer.points
            )
            # PIL's fourfold source polygon spans [0, size*4-1].
            geometry = _contour([[x * (w - 0.25), y * (h - 0.25)] for x, y in points], True)
        return [geometry, _paint(layer.color)]
    contours, points = [], []
    for segment in parse_path(layer.d):
        if segment.kind == "M":
            if points:
                contours.append(_contour(points, False))
            points = [list(segment.points[0])]
        elif segment.kind == "L":
            if not points:
                points = [contours[-1]["ks"]["k"]["v"][0]]
            points.append(list(segment.points[0]))
        else:
            contours.append(_contour(points, True))
            points = []
    if points:
        contours.append(_contour(points, False))
    # Lottie paints shape styles in reverse order; canonical Path paints fill, then stroke.
    paints = ([_paint(layer.stroke, layer)] if layer.stroke else []) + (
        [_paint(layer.color)] if layer.color else []
    )
    return contours + paints


def write_lottie(canvas: Canvas, output_path: str, animation) -> _ExportReceipt:
    """Compile completely before opening the destination; no assets or raster frames."""
    problems = _problems(canvas)
    if problems:
        raise RenderingError(details=problems)
    options = animation or LottieOptions()
    if not math.isfinite(options.fps * options.hold):
        raise RenderingError("Lottie frame span must be finite", path="/animation/hold")
    frame_count = max(1, math.ceil(options.fps * options.hold))
    duration = frame_count / options.fps
    if not math.isfinite(duration):
        raise RenderingError("Lottie playback duration must be finite", path="/animation/fps")
    layers = []
    from quickthumb.motion import _iter_export_layer_locations

    for index, (layer_id, _, layer) in enumerate(_iter_export_layer_locations(canvas)):
        assert isinstance(layer, (BackgroundLayer, ShapeLayer, PathLayer))
        position, anchor, scale = [0, 0, 0], [0, 0, 0], [100, 100, 100]
        if not isinstance(layer, BackgroundLayer):
            x = parse_coordinate(layer.position[0], canvas.width)
            y = parse_coordinate(layer.position[1], canvas.height)
            if isinstance(layer, ShapeLayer) and layer.align:
                x, y = apply_alignment(x, y, (layer.width, layer.height), layer.align)
            position = [x, y, 0]
            if isinstance(layer, PathLayer):
                vx, vy, vw, vh = layer.view_box or (0, 0, layer.width, layer.height)
                anchor, scale = [vx, vy, 0], [layer.width / vw * 100, layer.height / vh * 100, 100]
        layers.append(
            {
                "ty": 4,
                "ind": index + 1,
                "nm": layer_id,
                "ddd": 0,
                "sr": 1,
                "ks": {
                    "o": _property(layer.opacity * 100),
                    "r": _property(0),
                    "p": _property(position),
                    "a": _property(anchor),
                    "s": _property(scale),
                },
                "shapes": _shapes(layer, canvas.width, canvas.height),
                "ip": 0,
                "op": frame_count,
                "st": 0,
                "bm": 0,
            }
        )
    payload = {
        "v": "5.13.0",
        "ver": 10001,
        "fr": options.fps,
        "ip": 0,
        "op": frame_count,
        "w": canvas.width,
        "h": canvas.height,
        "nm": "Quickthumb",
        "ddd": 0,
        "assets": [],
        "layers": list(reversed(layers)),
    }
    document = canonical_json(payload)
    Path(output_path).write_text(document, encoding="utf-8")
    from quickthumb._export_video import _AnimationFacts

    facts = _AnimationFacts(canvas.width, canvas.height, frame_count, duration, options.fps)
    return _ExportReceipt([output_path], validate_lottie(canvas), facts)
