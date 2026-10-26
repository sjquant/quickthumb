"""Native-vector Lottie subset; unsupported source features fail before writes."""

from __future__ import annotations

import math
from pathlib import Path
from typing import TYPE_CHECKING, cast

from PIL import ImageColor

from quickthumb._document import _ExportReceipt, canonical_json
from quickthumb._path_curves import cubic_path_commands
from quickthumb._path_svg import _bounded_number, native_path_problem
from quickthumb._shapes import TRIANGLE_POINTS, ShapeEngine
from quickthumb.errors import ErrorDetail, QuickthumbError, RenderingError
from quickthumb.models import (
    AnimationSpec,
    BackgroundLayer,
    ExportDiagnostic,
    LottieOptions,
    NullLayer,
    PathLayer,
    ShapeLayer,
    TextLayer,
)

if TYPE_CHECKING:
    from quickthumb.canvas import Canvas
    from quickthumb.deck import Deck
    from quickthumb.models import ExportPolicy


def _layer_problem(layer, reduced_motion: bool, canvas, linked: bool) -> tuple[str, str] | None:
    if not isinstance(layer, (BackgroundLayer, ShapeLayer, PathLayer, NullLayer, TextLayer)):
        return (
            "type",
            f"{getattr(layer, 'type', 'custom')} layers are not supported by static Lottie",
        )
    for field in (
        "fill",
        "gradient",
        "image",
        "effects",
        "clip",
        "mask",
        "blend_mode",
    ):
        if getattr(layer, field, None):
            return field, f"{field} is not supported by static Lottie"
    if isinstance(layer, TextLayer):
        from quickthumb._lottie_text import text_outlines, text_problem

        if problem := text_problem(layer, linked):
            return problem
        try:
            text_outlines(canvas, layer)
        except QuickthumbError as error:
            return (error.details[0].path or "/font").lstrip("/"), str(error)
        return None
    animation = getattr(layer, "animation", None)
    if animation and not reduced_motion:
        from quickthumb.motion import _is_path_track

        specs = animation if isinstance(animation, list) else [animation]
        supported = {"position", "scale", "scale_x", "scale_y", "rotation", "opacity"}
        if isinstance(layer, PathLayer):
            supported.update(("trim_start", "trim_end", "trim_offset"))
        for spec in specs:
            if (
                not isinstance(spec, AnimationSpec)
                or spec.effect is not None
                or spec.stagger is not None
            ):
                return (
                    "animation",
                    "Lottie pose motion requires canonical timelines without presets or stagger",
                )
            if any(
                track.type not in supported or _is_path_track(track) for track in spec.tracks or ()
            ):
                return (
                    "animation",
                    "Lottie supports position, scale, rotation, opacity and Path trim tracks",
                )
            if isinstance(layer, (ShapeLayer, NullLayer)) and any(
                track.type == "scale" and any(key.value <= 0 for key in track.keyframes)
                for track in spec.tracks or ()
            ):
                return (
                    "animation",
                    "Nonpositive uniform Shape/Null scale is not supported "
                    "by this canonical renderer",
                )
    if isinstance(layer, ShapeLayer) and animation and not reduced_motion and not linked:
        from quickthumb._lottie_pose import shape_source_box

        x, y, width, height = shape_source_box(canvas, layer)
        if x < 0 or y < 0 or x + width > canvas.width or y + height > canvas.height:
            return (
                "position",
                "Animated Shape source must fit inside the canvas; use an unclipped source",
            )
    if isinstance(layer, PathLayer):
        if layer.dash_array or layer.dash_offset:
            return "d", "Path dashes are not supported by native Lottie"
        # Lottie retains layer opacity natively; reuse the shared native numeric admission.
        if problem := native_path_problem(
            layer.model_copy(
                update={
                    "opacity": 1.0,
                    "rotation": 0.0,
                    "animation": None,
                    "trim_start": 0.0,
                    "trim_end": 1.0,
                    "trim_offset": 0.0,
                }
            )
        ):
            return "d", problem.replace("native SVG", "native Lottie")
        try:
            commands = cubic_path_commands(layer)
            _path_contours(layer, commands)
        except RenderingError as error:
            return "d", str(error)
        if layer.stroke:
            contours = []
            for kind, points in commands:
                if kind == "M":
                    contours.append(set())
                for point in points:
                    contours[-1].add(point)
            if any(len(points) < 2 for points in contours):
                return "d", "Degenerate stroked contours are not supported by static Lottie"
        if layer.stroke and (not animation or reduced_motion):
            from quickthumb._lottie_trim import trim_length_bound, trim_properties
            from quickthumb.motion import LayerState

            try:
                trim_properties(layer, LayerState(), trim_length_bound(layer))
            except RenderingError as error:
                return "trim_start", str(error)
        vx, vy, vw, vh = layer.view_box or (0, 0, layer.width, layer.height)
        if layer.stroke and layer.width / vw != layer.height / vh:
            return "stroke", "Lottie strokes currently require uniform view-box scaling"
        pad = layer.stroke_width * layer.miter_limit / 2 if layer.stroke else 0
        if any(
            not (vx + pad <= x <= vx + vw - pad and vy + pad <= y <= vy + vh - pad)
            for _, points in commands
            for x, y in points
        ):
            return (
                "d",
                "Path control hull and stroke margin must fit inside its viewport; "
                "Lottie viewport clipping is not supported",
            )
    return None


def _problems(source: Canvas | Deck, policy: ExportPolicy | None = None) -> list[ErrorDetail]:
    if hasattr(source, "slides"):
        return [
            ErrorDetail(
                code="unsupported_capability",
                category="export",
                path="/slides",
                message="Lottie currently requires a single Canvas",
            )
        ]
    from quickthumb._parent_render import participating_layers

    members = participating_layers(cast("Canvas", source))
    from quickthumb.motion import _iter_export_layer_locations

    errors = []
    for layer_id, pointer, layer in _iter_export_layer_locations(source):
        problem = _layer_problem(
            layer, bool(policy and policy.reduced_motion), source, id(layer) in members
        )
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


def validate_lottie(
    source: Canvas | Deck, policy: ExportPolicy | None = None
) -> list[ExportDiagnostic]:
    """List unsupported source features without resolving assets or rendering."""
    errors = _problems(source, policy)
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
            support="partial"
            if getattr(layer, "animation", None) and not (policy and policy.reduced_motion)
            else "native",
            layer_id=layer_id,
            message=(
                "Native vectors with held canonical property samples at LottieOptions.fps"
                if getattr(layer, "animation", None) and not (policy and policy.reduced_motion)
                else "Authored-static native vectors under reduced-motion policy"
                if policy and policy.reduced_motion
                else "Native Lottie vector"
            ),
        )
        for layer_id, _, layer in _iter_export_layer_locations(source)
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


def _shapes(canvas, layer):
    width, height = canvas.width, canvas.height
    if isinstance(layer, TextLayer):
        from quickthumb._lottie_text import text_outlines

        glyphs, color = text_outlines(canvas, layer)
        paint = _paint(color)
        paint["r"] = 1  # Preserve holes within each glyph, never cancel overlapping glyphs.
        transform = {
            "ty": "tr",
            "p": _property([0, 0]),
            "a": _property([0, 0]),
            "s": _property([100, 100]),
            "r": _property(0),
            "o": _property(100),
        }
        return [{"ty": "gr", "it": [*contours, paint, transform]} for contours in reversed(glyphs)]
    if isinstance(layer, NullLayer):
        return []
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
    contours = _path_contours(layer)
    # Lottie paints shape styles in reverse order; canonical Path paints fill, then stroke.
    paints = ([_paint(layer.stroke, layer)] if layer.stroke else []) + (
        [_paint(layer.color)] if layer.color else []
    )
    from quickthumb._lottie_trim import needs_trim

    if layer.stroke and needs_trim(layer):
        transform = {
            "ty": "tr",
            "p": _property([0, 0]),
            "a": _property([0, 0]),
            "s": _property([100, 100]),
            "r": _property(0),
            "o": _property(100),
        }
        stroke = {"ty": "gr", "it": [*contours, paints[0], {"ty": "tm", "m": 2}, transform]}
        # Native groups, like styles, paint in reverse order. Fill remains untrimmed.
        return [stroke] + (
            [{"ty": "gr", "it": [*contours, paints[-1], transform]}] if layer.color else []
        )
    return contours + paints


def _path_contours(layer: PathLayer, commands=None) -> list[dict]:
    """Convert canonical cubic commands into Lottie's relative tangent handles."""
    contours, points, incoming, outgoing = [], [], [], []
    current = start = (0.0, 0.0)

    def finish(closed):
        if not points:
            return
        if closed and len(points) > 1 and points[-1] == points[0]:
            incoming[0] = incoming.pop()
            points.pop()
            outgoing.pop()
        shape = _contour(points[:], closed)
        shape["ks"]["k"].update(i=incoming[:], o=outgoing[:])
        contours.append(shape)
        points.clear()
        incoming.clear()
        outgoing.clear()

    _, _, vw, vh = layer.view_box or (0, 0, layer.width, layer.height)
    scale = layer.width / vw, layer.height / vh
    for kind, controls in cubic_path_commands(layer) if commands is None else commands:
        if kind == "M":
            finish(False)
            current = start = controls[0]
        elif kind == "Z":
            finish(True)
            current = start
            continue
        if not points:
            points.append(list(current))
            incoming.append([0, 0])
            outgoing.append([0, 0])
        if kind in {"L", "C"}:
            end = controls[-1]
            before = (
                [a - b for a, b in zip(controls[0], current, strict=True)]
                if kind == "C"
                else [0, 0]
            )
            after = (
                [a - b for a, b in zip(controls[1], end, strict=True)] if kind == "C" else [0, 0]
            )
            if any(
                not _bounded_number(value, axis_scale)
                for handle in (before, after)
                for value, axis_scale in zip(handle, scale, strict=True)
            ):
                raise RenderingError("Native Lottie tangent precision limit exceeded")
            outgoing[-1] = before
            points.append(list(end))
            incoming.append(after)
            outgoing.append([0, 0])
            current = end
    finish(False)
    return contours


def write_lottie(
    canvas: Canvas, output_path: str, animation, policy: ExportPolicy | None = None
) -> _ExportReceipt:
    """Compile completely before opening the destination; no assets or raster frames."""
    problems = _problems(canvas, policy)
    if problems:
        raise RenderingError(details=problems)
    options = animation or LottieOptions()
    from quickthumb._lottie_pose import layer_pose, pose_boundaries
    from quickthumb._sampling import _MAX_OBSERVATIONS
    from quickthumb.motion import _canonical_timeline

    timelines = [
        None if policy and policy.reduced_motion else _canonical_timeline(layer)
        for layer in canvas.layers
    ]
    span = (
        max((timeline.duration for timeline in timelines if timeline is not None), default=0)
        + options.hold
    )
    if not math.isfinite(options.fps * span):
        raise RenderingError("Lottie frame span must be finite", path="/animation/hold")
    frame_count = max(1, math.ceil(options.fps * span))
    duration = frame_count / options.fps
    if not math.isfinite(duration):
        raise RenderingError("Lottie playback duration must be finite", path="/animation/fps")
    layers = []
    from quickthumb._lottie_parent import parent_frames
    from quickthumb.motion import _iter_export_layer_locations

    geometry, frame_indices, frames = parent_frames(canvas, frame_count)
    boundaries = pose_boundaries(timelines)
    pose_count = 0
    for index, (layer_id, pointer, layer) in enumerate(_iter_export_layer_locations(canvas)):
        assert isinstance(layer, (BackgroundLayer, ShapeLayer, PathLayer, NullLayer, TextLayer))
        try:
            shapes, keys, count = layer_pose(
                canvas,
                layer,
                _shapes(canvas, layer),
                timelines[index],
                options.fps,
                boundaries,
                geometry.get(id(layer)),
            )
        except QuickthumbError as error:
            raise RenderingError(
                details=[
                    detail.model_copy(
                        update={
                            "path": pointer + (detail.path or ""),
                            "layer_id": detail.layer_id or layer_id,
                        }
                    )
                    for detail in error.details
                ]
            ) from error
        pose_count += count
        if pose_count > _MAX_OBSERVATIONS:
            raise RenderingError(
                "Lottie exceeds 100000 total pose samples; lower fps or simplify motion",
                path=pointer,
                layer_id=layer_id,
            )
        layers.append(
            {
                "ty": 3 if isinstance(layer, NullLayer) else 4,
                "ind": index + 1,
                "nm": layer_id,
                "ddd": 0,
                "sr": 1,
                "ks": keys,
                "shapes": shapes,
                "ip": 0,
                "op": frame_count,
                "st": 0,
                "bm": 0,
            }
        )
        if isinstance(layer, NullLayer):
            del layers[-1]["shapes"]
        parent = getattr(layer, "parent", None)
        if parent:
            layers[-1]["parent"] = frame_indices[parent]
    layers.extend(frames)
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
    return _ExportReceipt([output_path], validate_lottie(canvas, policy), facts)
