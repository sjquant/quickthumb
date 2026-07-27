"""HTML document exporter.

The canvas becomes a fixed-size *stage* (a ``<div>`` at the canvas pixel
dimensions) whose children are absolutely positioned with the same geometry
math as the raster renderer, so the layout is a faithful, deterministic twin of
the PNG/SVG/PDF/PPTX output -- it never reflows. To adapt to the viewport the
whole stage is scaled as one unit (``transform: scale()`` via a small
ResizeObserver), preserving the composition exactly while letting it fill any
screen. Set ``responsive=False`` to emit the bare fixed-size stage instead.

Backgrounds, outlines, shapes, and text are emitted as native HTML/CSS;
raster images, image glyph fills, blend modes, and custom callbacks are
embedded as pixel-exact PNG fragments rendered through the regular pipeline.

Per-layer ``Animation`` effects map to CSS keyframes driven by a tiny JS
timeline runtime that honours the same ``on_click``/``with_previous``/
``after_previous`` sequencing PowerPoint uses. Browsers hint and rasterize
fonts differently from PIL, so text placement is a close approximation rather
than pixel-identical (like the PPTX exporter), and a handful of exotic effects
(blinds, checkerboard, wheel, dissolve) fall back to a close CSS analogue.
"""

from __future__ import annotations

import base64
import hashlib
import json
import math
import re
from dataclasses import dataclass
from html import escape
from importlib.resources import files
from typing import TYPE_CHECKING

from PIL import ImageFont

from quickthumb._base import (
    apply_alignment,
    expanded_rotation_size,
    is_url,
    parse_coordinate,
    parse_padding,
)
from quickthumb._composition import has_layer_composition
from quickthumb._export_base import (
    Box,
    RasterFragment,
    TextRunLayout,
    _css_string,
    _fmt,
    color_to_rgba,
    compute_text_layout,
    flatten_layers,
    font_face_declarations,
    font_variation_settings,
    rasterize_layers,
    read_svg_layer_bytes_and_size,
    resolve_font_face,
    split_backdrop_prefix,
    union_boxes,
    uses_image_fill,
    validate_legacy_animation_export,
)
from quickthumb.errors import RenderingError
from quickthumb.models import (
    Align,
    AnimationSpec,
    BackgroundLayer,
    Glow,
    GroupLayer,
    LinearGradient,
    OutlineLayer,
    RadialGradient,
    Shadow,
    ShapeLayer,
    Stroke,
    SvgLayer,
    TextLayer,
)
from quickthumb.motion import compile_timeline

if TYPE_CHECKING:
    from quickthumb.canvas import Canvas, RenderableLayer


def _css_color(rgba: tuple, opacity: float = 1.0) -> str:
    r, g, b = rgba[:3]
    a = (rgba[3] / 255 if len(rgba) > 3 else 1.0) * opacity
    if a >= 1:
        return f"rgb({r},{g},{b})"
    return f"rgba({r},{g},{b},{a:.4g})"


# Direction -> clip-path inset that hides the element past that edge. Shared by
# the layer wipe/blinds effects and the slide wipe/comb/blinds transitions.
_WIPE_INSETS = {
    "up": "inset(100% 0 0 0)",
    "down": "inset(0 0 100% 0)",
    "left": "inset(0 0 0 100%)",
    "right": "inset(0 100% 0 0)",
}
_SHOWN_OPACITY = "var(--qt-opacity,1)"


# --- animation effect -> (entrance from-state, to-state) CSS property blocks ----
# Each keyframe interpolates a single element between a hidden and a shown state.
# Exit reuses the same pair with the keyframe direction reversed. Effects CSS
# cannot express faithfully reuse the closest analogue (documented in gotchas).
def _effect_states(effect) -> tuple[str, str]:
    """Return (hidden-state, shown-state) CSS declaration strings for an effect."""
    name = effect.effect
    if name in ("fade", "appear", "dissolve", "checkerboard"):
        return "opacity:0", f"opacity:{_SHOWN_OPACITY}"
    if name == "circle":
        return (
            f"clip-path:circle(0% at 50% 50%);opacity:{_SHOWN_OPACITY}",
            f"clip-path:circle(75% at 50% 50%);opacity:{_SHOWN_OPACITY}",
        )
    if name == "diamond":
        return (
            f"clip-path:polygon(50% 50%,50% 50%,50% 50%,50% 50%);opacity:{_SHOWN_OPACITY}",
            f"clip-path:polygon(50% 0%,100% 50%,50% 100%,0% 50%);opacity:{_SHOWN_OPACITY}",
        )
    if name == "box":
        # PowerPoint's box(in) reads closer to a soft centre reveal than a hard
        # rectangular crop on text, so use an oval mask for the HTML analogue.
        if getattr(effect, "direction", "in") == "in":
            return (
                f"clip-path:ellipse(0% 0% at 50% 50%);opacity:{_SHOWN_OPACITY}",
                f"clip-path:ellipse(75% 75% at 50% 50%);opacity:{_SHOWN_OPACITY}",
            )
        return (
            "clip-path:inset(0 0 0 0);opacity:0",
            f"clip-path:inset(0 0 0 0);opacity:{_SHOWN_OPACITY}",
        )
    if name in ("wipe", "blinds"):
        direction = getattr(effect, "direction", "up")
        if name == "blinds":
            direction = "right" if effect.orientation == "vertical" else "down"
        return (
            f"clip-path:{_WIPE_INSETS[direction]};opacity:{_SHOWN_OPACITY}",
            f"clip-path:inset(0 0 0 0);opacity:{_SHOWN_OPACITY}",
        )
    if name == "wheel":
        return (
            f"clip-path:polygon(50% 50%,50% 0%,50% 0%);opacity:{_SHOWN_OPACITY}",
            f"clip-path:circle(75% at 50% 50%);opacity:{_SHOWN_OPACITY}",
        )
    return "opacity:0", f"opacity:{_SHOWN_OPACITY}"


def _canonical_effect_states(event) -> tuple[str, str]:
    """Return a deterministic CSS analogue for one normalized motion event."""
    effect = event.effect
    if effect in {"fade", "typewriter"}:
        if effect == "typewriter":
            return "clip-path:inset(0 100% 0 0);opacity:1", "clip-path:inset(0);opacity:1"
        return "opacity:0", "opacity:1"
    if effect in {"zoom", "pop"}:
        return "transform:scale(.8);opacity:1", "transform:scale(1);opacity:1"
    if effect in {"rise", "fall", "slide"}:
        distance = float(event.options.get("distance", 48.0) or 0.0)
        origin = (
            event.options.get("from")
            or {
                "rise": "bottom",
                "fall": "top",
                "slide": "left",
            }[effect]
        )
        offsets = {
            "top": (0, -distance),
            "bottom": (0, distance),
            "left": (-distance, 0),
            "right": (distance, 0),
            "center": (0, 0),
        }
        x, y = offsets[origin]
        return f"transform:translate({x}px,{y}px);opacity:1", "transform:translate(0,0);opacity:1"
    return "opacity:0", "opacity:1"


def _canonical_target_count(layer: RenderableLayer, animation: AnimationSpec) -> int:
    """Return semantic target cardinality for HTML timing."""
    stagger = animation.stagger
    if stagger is None:
        return 1
    if stagger.target == "children" and isinstance(layer, GroupLayer):
        return len(layer.children)
    if isinstance(layer, TextLayer):
        content = (
            layer.content
            if isinstance(layer.content, str)
            else "".join(part.text for part in layer.content)
        )
        if stagger.target == "characters":
            return len(content)
        if stagger.target == "words":
            return len(re.findall(r"\S+", content))
        if stagger.target == "lines":
            return len(content.split("\n"))
    return 1


def _remap_linear_stops(
    positions: list[float], block: Box, element: Box, dx: float, dy: float
) -> list[float]:
    """Re-express a block's gradient stops in an element's local 0..1 space.

    The raster engine lays the 0..1 ramp across the block's *diagonal* (not its
    projected extent), centred on the block, then crops -- so a box shows only
    the middle slice of the ramp, never the full colour range. This reproduces
    that exact mapping for one element (e.g. a line-span): a stop at fraction
    ``q`` sits ``(q-0.5)*diagonal`` from the block centre along the gradient
    direction, which is then converted to a fraction of the element's own
    gradient line (its projected extent, centred on the element). Results can
    fall outside [0, 1]; CSS handles that, which is how each line shows just its
    portion of the shared gradient.
    """
    (bx0, by0, bx1, by1), (ex0, ey0, ex1, ey1) = block, element
    diagonal = math.hypot(bx1 - bx0, by1 - by0)
    element_extent = abs((ex1 - ex0) * dx) + abs((ey1 - ey0) * dy)
    if element_extent == 0 or diagonal == 0:
        return positions
    center_offset = ((ex0 + ex1 - bx0 - bx1) / 2) * dx + ((ey0 + ey1 - by0 - by1) / 2) * dy
    return [((q - 0.5) * diagonal - center_offset) / element_extent + 0.5 for q in positions]


def _css_gradient(
    gradient: LinearGradient | RadialGradient,
    box: Box,
    canvas: Canvas,
    element_box: Box | None = None,
) -> str:
    """Build a CSS gradient over a box, approximating EffectsEngine geometry.

    The raster renderer maps a gradient across the whole ``box`` (e.g. a
    multi-line text block). A CSS gradient, though, is relative to the element
    it paints on -- one line-span at a time -- so passing ``element_box`` (that
    span's box) remaps a linear gradient's stops to the slice of ``box`` the
    element actually covers, keeping the colours continuous across lines instead
    of restarting on each one.
    """
    left, top, right, bottom = box
    width, height = right - left, bottom - top
    stops = sorted(gradient.stops, key=lambda stop: stop[1])

    if isinstance(gradient, LinearGradient):
        # Our angle uses screen coords (x right, y down); CSS measures
        # clockwise from "to top", so convert the direction vector.
        theta = math.radians(gradient.angle)
        dx, dy = math.cos(theta), math.sin(theta)
        css_angle = (math.degrees(math.atan2(dx, -dy))) % 360
        # PIL ramps across the box diagonal and crops, so the painted box only
        # ever shows the middle slice of the colour range. Remap the stops onto
        # whatever box CSS actually paints (the element, else this box) to match.
        paint_box = element_box if element_box is not None else box
        positions = _remap_linear_stops([pos for _, pos in stops], box, paint_box, dx, dy)
        parts = [
            f"{_css_color(color_to_rgba(canvas, color))} {_fmt(round(pos * 100, 2))}%"
            for (color, _), pos in zip(stops, positions, strict=True)
        ]
        return f"linear-gradient({_fmt(round(css_angle, 2))}deg,{','.join(parts)})"

    focus_x = width * gradient.center[0]
    focus_y = height * gradient.center[1]
    max_dist = max(
        math.hypot(focus_x, focus_y),
        math.hypot(width - focus_x, focus_y),
        math.hypot(focus_x, height - focus_y),
        math.hypot(width - focus_x, height - focus_y),
    )
    radius = max_dist * math.sqrt(2)
    parts = [
        f"{_css_color(color_to_rgba(canvas, color))} {_fmt(round(pos * radius, 2))}px"
        for color, pos in stops
    ]
    return (
        f"radial-gradient(circle {_fmt(round(radius, 2))}px at "
        f"{_fmt(round(focus_x, 2))}px {_fmt(round(focus_y, 2))}px,{','.join(parts)})"
    )


class HtmlExporter:
    def __init__(
        self,
        canvas: Canvas,
        embed_fonts: bool = False,
        responsive: bool = True,
        keyframe_prefix: str = "qt-k",
        reduced_motion: bool = False,
    ):
        self._canvas = canvas
        if not reduced_motion:
            validate_legacy_animation_export(canvas)
        self._embed_fonts = embed_fonts
        self._responsive = responsive
        self._reduced_motion = reduced_motion
        self._keyframe_prefix = keyframe_prefix
        self._body: list[str] = []
        self._keyframes: list[str] = []
        self._timeline: list[dict] = []
        self._font_faces: dict[str, tuple[str, str, str]] = {}
        # SVG <filter> defs (id -> markup) for faithful glow/shadow/stroke,
        # deduplicated by a content hash so identical effects share one filter.
        self._svg_filters: dict[str, str] = {}
        self._next_id = 1
        self._next_kf = 1
        # Track group-animation identity so flattened group children sharing one
        # animation object animate together as a single timeline node.
        self._prev_anim_key: int | None = None
        self._prev_nodes: list[dict] = []

    # ----------------------------------------------------------------- assembly

    def export(self) -> str:
        """Render a complete, standalone HTML document for the canvas."""
        stage = self.render_stage()
        return _document(
            [stage],
            responsive=self._responsive,
            font_faces=self._font_faces,
            svg_filters=self._svg_filters,
            reduced_motion=self._reduced_motion,
        )

    def _effect_filter_css(self, effects, width: float, height: float, *, is_text: bool) -> str:
        """Return a CSS ``filter:url(#id)`` reproducing the Glow/Shadow (and, for
        non-text shapes, Stroke) effects exactly as the raster engine draws them,
        registering the shared SVG ``<filter>``. Empty string if none apply.

        The raster engine derives each effect from the layer's alpha silhouette
        and composites it behind the layer: Shadow = Gaussian-blurred (sigma =
        blur_radius) offset silhouette; Glow = blurred silhouette x opacity (text
        also dilates first); Stroke = silhouette dilated outward by its width.
        SVG filter primitives map onto these one-to-one -- and feGaussianBlur's
        stdDeviation *is* the sigma, so no CSS blur-radius fudge is needed.
        """
        shaded = [e for e in effects if isinstance(e, (Shadow, Glow))]
        strokes = [] if is_text else [e for e in effects if isinstance(e, Stroke)]
        if not shaded and not strokes:
            return ""

        pad = 1.0
        for effect in shaded:
            if isinstance(effect, Shadow):
                pad = max(pad, effect.blur_radius * 2 + abs(effect.offset_x) + abs(effect.offset_y))
            else:
                pad = max(pad, effect.radius * 3)
        for stroke in strokes:
            pad = max(pad, stroke.width + 1)
        # Filter region as a fraction of the box, capped so a tiny element with a
        # big glow doesn't allocate a runaway offscreen buffer.
        margin = min(pad / max(1.0, min(width, height)), 4.0) * 100
        region = (
            f'x="{_fmt(round(-margin, 2))}%" y="{_fmt(round(-margin, 2))}%" '
            f'width="{_fmt(round(100 + 2 * margin, 2))}%" '
            f'height="{_fmt(round(100 + 2 * margin, 2))}%"'
        )

        body: list[str] = []
        nodes: list[str] = []
        index = 0
        for effect in shaded:
            index += 1
            rgb = color_to_rgba(self._canvas, effect.color)
            color = f"rgb({rgb[0]},{rgb[1]},{rgb[2]})"
            if isinstance(effect, Shadow):
                alpha = rgb[3] / 255 if len(rgb) > 3 else 1.0
                body.append(
                    f'<feGaussianBlur in="SourceAlpha" '
                    f'stdDeviation="{_fmt(effect.blur_radius)}" result="b{index}"/>'
                    f'<feOffset in="b{index}" dx="{effect.offset_x}" '
                    f'dy="{effect.offset_y}" result="o{index}"/>'
                    f'<feFlood flood-color="{color}" '
                    f'flood-opacity="{_fmt(round(alpha, 4))}" result="c{index}"/>'
                    f'<feComposite in="c{index}" in2="o{index}" '
                    f'operator="in" result="e{index}"/>'
                )
            else:
                source = "SourceAlpha"
                if is_text:
                    body.append(
                        f'<feMorphology in="SourceAlpha" operator="dilate" '
                        f'radius="{max(1, effect.radius // 2)}" result="d{index}"/>'
                    )
                    source = f"d{index}"
                body.append(
                    f'<feGaussianBlur in="{source}" '
                    f'stdDeviation="{_fmt(effect.radius)}" result="b{index}"/>'
                    f'<feFlood flood-color="{color}" '
                    f'flood-opacity="{_fmt(round(effect.opacity, 4))}" result="c{index}"/>'
                    f'<feComposite in="c{index}" in2="b{index}" '
                    f'operator="in" result="e{index}"/>'
                )
            nodes.append(f"e{index}")
        for stroke in strokes:
            index += 1
            rgb = color_to_rgba(self._canvas, stroke.color)
            color = f"rgb({rgb[0]},{rgb[1]},{rgb[2]})"
            body.append(
                f'<feMorphology in="SourceAlpha" operator="dilate" '
                f'radius="{_fmt(stroke.width)}" result="m{index}"/>'
                f'<feFlood flood-color="{color}" result="c{index}"/>'
                f'<feComposite in="c{index}" in2="m{index}" '
                f'operator="in" result="e{index}"/>'
            )
            nodes.append(f"e{index}")

        merge = "".join(f'<feMergeNode in="{n}"/>' for n in nodes)
        inner = "".join(body) + f'<feMerge>{merge}<feMergeNode in="SourceGraphic"/></feMerge>'
        fid = "qt-fx" + hashlib.md5((region + inner).encode()).hexdigest()[:10]
        self._svg_filters[fid] = f'<filter id="{fid}" {region}>{inner}</filter>'
        return f"filter:url(#{fid});"

    def render_stage(self) -> Stage:
        """Render the canvas into a reusable stage (used directly and by decks)."""
        canvas = self._canvas
        canvas._validate_image_paths()
        canvas._ctx.begin_render_pass()

        prefix, rest = split_backdrop_prefix(flatten_layers(canvas))
        if not self._reduced_motion and any(
            getattr(layer, "animation", None) is not None for layer in prefix
        ):
            raise RenderingError(
                "HTML export cannot animate layers that must be rasterized together for "
                "blend-mode or custom-layer backdrop compositing. Move animated layers "
                "after those backdrop-dependent layers, or remove the blend/custom layer."
            )
        if prefix:
            fragment = rasterize_layers(canvas, prefix)
            if fragment:
                self._emit_fragment(fragment)
        for layer in rest:
            self._emit_layer(layer)

        return Stage(
            width=canvas.width,
            height=canvas.height,
            body="\n".join(self._body),
            keyframes=list(self._keyframes),
            timeline=list(self._timeline),
        )

    def _make_id(self) -> str:
        element_id = f"qt-l{self._next_id}"
        self._next_id += 1
        return element_id

    # ----------------------------------------------------------- animation glue

    def _register_animation(self, layer: RenderableLayer, element_id: str) -> str:
        """Record a layer's animation as timeline node(s) keyed to its element.

        Returns the extra inline style for the element -- ``visibility:hidden;``
        when an entrance effect must play before the layer is first shown, else
        an empty string.
        """
        if self._reduced_motion:
            self._prev_anim_key = None
            self._prev_nodes = []
            return ""
        animation = getattr(layer, "animation", None)
        if animation is None:
            effects = []
        elif isinstance(animation, list):
            effects = animation
        else:
            effects = [animation]
        if not effects:
            self._prev_anim_key = None
            return ""

        if isinstance(effects[0], AnimationSpec):
            return self._register_canonical_animation(effects[0], element_id, layer)

        hidden = "visibility:hidden;" if effects[0].animate == "entrance" else ""
        key = id(animation)
        if key == self._prev_anim_key:
            # Same group animation object: add this element to the shared node(s).
            for node in self._prev_nodes:
                node["t"].append(element_id)
            return hidden

        nodes: list[dict] = []
        for effect in effects:
            hidden_state, shown_state = _effect_states(effect)
            kf = f"{self._keyframe_prefix}{self._next_kf}"
            self._next_kf += 1
            if effect.animate == "entrance":
                start, end = hidden_state, shown_state
            else:
                start, end = shown_state, hidden_state
            self._keyframes.append("@keyframes " + kf + "{from{" + start + "}to{" + end + "}}")
            nodes.append(
                {
                    "t": [element_id],
                    "k": kf,
                    "d": effect.duration,
                    "delay": effect.delay,
                    "tr": effect.trigger,
                    "a": effect.animate,
                }
            )
        self._timeline.extend(nodes)
        self._prev_anim_key = key
        self._prev_nodes = nodes
        return hidden

    def _register_canonical_animation(
        self, animation: AnimationSpec, element_id: str, layer: RenderableLayer
    ) -> str:
        """Compile a canonical timeline into the existing HTML timeline format."""
        timeline = compile_timeline(animation)
        target_count = _canonical_target_count(layer, animation)
        nodes: list[dict] = []
        for event in timeline.events:
            kf = f"{self._keyframe_prefix}{self._next_kf}"
            self._next_kf += 1
            hidden, shown = _canonical_effect_states(event)
            self._keyframes.append(f"@keyframes {kf}{{from{{{hidden}}}to{{{shown}}}}}")
            duration = event.duration
            if event.stagger is not None:
                duration += float(event.stagger.get("delay", 0.0)) * max(0, target_count - 1)
            nodes.append(
                {
                    "t": [element_id],
                    "k": kf,
                    "d": duration,
                    "delay": event.start + event.delay,
                    "tr": None,
                    "a": "entrance",
                }
            )
        self._timeline.extend(nodes)
        self._prev_anim_key = id(animation)
        self._prev_nodes = nodes
        return "visibility:hidden;" if nodes else ""

    # ------------------------------------------------------------------ layers

    def _emit_layer(self, layer: RenderableLayer):
        if has_layer_composition(layer):
            self._emit_raster_fallback(layer)
            return

        if isinstance(layer, BackgroundLayer):
            self._emit_background(layer)
        elif isinstance(layer, OutlineLayer):
            self._emit_outline(layer)
        elif isinstance(layer, ShapeLayer):
            self._emit_shape(layer)
        elif isinstance(layer, TextLayer):
            self._emit_text(layer)
        elif isinstance(layer, SvgLayer):
            self._emit_svg_layer(layer)
        else:  # ImageLayer or anything else the format cannot express natively
            self._emit_raster_fallback(layer)

    def _append_element(
        self, layer: RenderableLayer, tag: str, style: str, inner: str = ""
    ) -> None:
        """Append one positioned element, wiring up any per-layer animation."""
        element_id = self._make_id()
        anim_style = self._register_animation(layer, element_id)
        identity = self._identity_attr(layer)
        self._body.append(
            f'<{tag} id="{element_id}"{identity} style="{style}{anim_style}">{inner}</{tag}>'
        )

    @staticmethod
    def _identity_attr(layer: RenderableLayer) -> str:
        key = getattr(layer, "motion_key", None)
        return "" if key is None else f' data-qt-motion-key="{_attr(key)}"'

    def _emit_raster_fallback(self, layer: RenderableLayer):
        fragment = rasterize_layers(self._canvas, [layer])
        if fragment:
            self._emit_fragment(fragment, layer)

    def _emit_fragment(self, fragment: RasterFragment, layer: RenderableLayer | None = None):
        encoded = base64.b64encode(fragment.png_bytes).decode("ascii")
        style = (
            f"position:absolute;left:{fragment.x}px;top:{fragment.y}px;"
            f"width:{fragment.width}px;height:{fragment.height}px;"
        )
        if layer is not None:
            element_id = self._make_id()
            anim_style = self._register_animation(layer, element_id)
            identity = self._identity_attr(layer)
            self._body.append(
                f'<img id="{element_id}"{identity} style="{style}{anim_style}" '
                f'src="data:image/png;base64,{encoded}" alt="">'
            )
        else:
            self._body.append(f'<img style="{style}" src="data:image/png;base64,{encoded}" alt="">')

    # -------------------------------------------------------------- background

    def _emit_background(self, layer: BackgroundLayer):
        if layer.effects or layer.image or (layer.color is None and layer.gradient is None):
            self._emit_raster_fallback(layer)
            return

        width, height = self._canvas.width, self._canvas.height
        style = f"position:absolute;left:0;top:0;width:{width}px;height:{height}px;"
        if layer.color is not None:
            rgba = color_to_rgba(self._canvas, layer.color, layer.opacity)
            style += f"background:{_css_color(rgba)};"
        else:
            assert layer.gradient is not None
            grad = _css_gradient(layer.gradient, (0, 0, width, height), self._canvas)
            style += f"background:{grad};"
            if layer.opacity < 1:
                style += f"opacity:{_fmt(round(layer.opacity, 4))};"
        self._append_element(layer, "div", style)

    # ----------------------------------------------------------------- outline

    def _emit_outline(self, layer: OutlineLayer):
        rgba = color_to_rgba(self._canvas, layer.color, layer.opacity)
        width = self._canvas.width - 2 * layer.offset
        height = self._canvas.height - 2 * layer.offset
        # box-sizing:border-box keeps the border inside the box, matching PIL's
        # inward-drawn outline inset by `offset` with thickness `width`.
        style = (
            f"position:absolute;left:{layer.offset}px;top:{layer.offset}px;"
            f"width:{width}px;height:{height}px;box-sizing:border-box;"
            f"border:{layer.width}px solid {_css_color(rgba)};"
        )
        self._append_element(layer, "div", style)

    # ------------------------------------------------------------------ shapes

    def _emit_shape(self, layer: ShapeLayer):
        canvas = self._canvas
        x = parse_coordinate(layer.position[0], canvas.width)
        y = parse_coordinate(layer.position[1], canvas.height)
        width, height = layer.width, layer.height

        expanded = expanded_rotation_size((width, height), layer.rotation)
        paste_x, paste_y = x, y
        if layer.align:
            paste_x, paste_y = apply_alignment(x, y, expanded, layer.align)
        shape_x = paste_x + (expanded[0] - width) / 2
        shape_y = paste_y + (expanded[1] - height) / 2

        rgba = color_to_rgba(canvas, layer.color)
        style = (
            f"position:absolute;left:{_fmt(shape_x)}px;top:{_fmt(shape_y)}px;"
            f"width:{width}px;height:{height}px;background:{_css_color(rgba)};"
        )
        style += self._shape_geometry_css(layer)
        style += self._shape_effects_css(layer)
        if layer.rotation:
            style += f"transform:rotate({_fmt(layer.rotation)}deg);"
        if layer.opacity < 1:
            style += f"opacity:{_fmt(round(layer.opacity, 4))};"
        self._append_element(layer, "div", style)

    def _shape_geometry_css(self, layer: ShapeLayer) -> str:
        width, height = layer.width, layer.height
        if layer.shape == "rectangle":
            return f"border-radius:{layer.border_radius}px;" if layer.border_radius else ""
        if layer.shape == "ellipse":
            return "border-radius:50%;"
        if layer.shape == "pill":
            return f"border-radius:{_fmt(min(width, height) / 2)}px;"
        normalized = self._canvas._shapes.normalized_shape_points(layer)
        points = ",".join(f"{_fmt(px * 100)}% {_fmt(py * 100)}%" for px, py in normalized)
        return f"clip-path:polygon({points});"

    def _shape_effects_css(self, layer: ShapeLayer) -> str:
        """Render stroke/shadow/glow through one SVG filter that reproduces the
        raster engine's blur/dilate math exactly (see _effect_filter_css). This
        replaces the old box-shadow/drop-shadow approximations, which could not
        match PIL's Gaussian sigma, dilated glow, or true polygon outline."""
        return self._effect_filter_css(layer.effects, layer.width, layer.height, is_text=False)

    # -------------------------------------------------------------------- text

    def _emit_text(self, layer: TextLayer):
        if uses_image_fill(layer):
            self._emit_raster_fallback(layer)
            return

        layout = compute_text_layout(self._canvas, layer)
        if not any(layout.lines):
            return

        boxes: list[Box] = []
        for line in layout.lines:
            for run in line:
                boxes.append(run.ink_box)
                if run.bg_box:
                    boxes.append(run.bg_box)
        if layout.block_box:
            boxes.append(layout.block_box)
        if layout.block_bg_box:
            boxes.append(layout.block_bg_box)
        bounds = union_boxes(boxes)
        if bounds is None:
            return

        if layout.rotation and layout.origin and layout.rot_center_local:
            origin_x, origin_y = layout.origin
            cx, cy = layout.rot_center_local
            wrap_x, wrap_y, wrap_w, wrap_h = origin_x, origin_y, cx * 2, cy * 2
            transform = f"transform:rotate({_fmt(layout.rotation)}deg);transform-origin:center;"
        else:
            wrap_x, wrap_y = bounds[0], bounds[1]
            wrap_w, wrap_h = bounds[2] - bounds[0], bounds[3] - bounds[1]
            transform = ""

        style = (
            f"position:absolute;left:{_fmt(wrap_x)}px;top:{_fmt(wrap_y)}px;"
            f"width:{_fmt(wrap_w)}px;height:{_fmt(wrap_h)}px;{transform}"
        )
        if layout.opacity < 1:
            style += f"opacity:{_fmt(round(layout.opacity, 4))};"

        inner: list[str] = []
        if layout.block_backgrounds and layout.block_bg_box:
            for background in layout.block_backgrounds:
                inner.append(
                    self._text_background_html(background, layout.block_bg_box, wrap_x, wrap_y)
                )
        for line in layout.lines:
            for run in line:
                inner.extend(self._text_run_html(run, wrap_x, wrap_y))

        self._append_element(layer, "div", style, "".join(inner))

    def _text_background_html(self, background, content_box: Box, ox: float, oy: float) -> str:
        pad_top, pad_right, pad_bottom, pad_left = parse_padding(background.padding)
        rgba = color_to_rgba(self._canvas, background.color, background.opacity)
        left = content_box[0] - pad_left - ox
        top = content_box[1] - pad_top - oy
        width = content_box[2] - content_box[0] + pad_left + pad_right
        height = content_box[3] - content_box[1] + pad_top + pad_bottom
        radius = f"border-radius:{background.border_radius}px;" if background.border_radius else ""
        return (
            f'<div style="position:absolute;left:{_fmt(left)}px;top:{_fmt(top)}px;'
            f"width:{_fmt(width)}px;height:{_fmt(height)}px;"
            f'background:{_css_color(rgba)};{radius}"></div>'
        )

    def _text_run_html(self, run: TextRunLayout, ox: float, oy: float) -> list[str]:
        parts: list[str] = []
        for background in run.backgrounds:
            if run.bg_box:
                parts.append(self._text_background_html(background, run.bg_box, ox, oy))

        family, weight, style = self._register_font(run)
        if isinstance(run.font, ImageFont.FreeTypeFont):
            ascent, descent = run.font.getmetrics()
        else:
            ascent, descent = run.size, 0

        css = (
            f"position:absolute;left:{_fmt(run.pen_x - ox)}px;"
            f"top:{_fmt(run.baseline_y - ascent - oy)}px;white-space:pre;"
            f"font-family:{_css_font_family(family)};font-size:{run.size}px;"
            f"line-height:{ascent + descent}px;" + _TEXT_PRECISION_CSS
        )
        if weight != "400":
            css += f"font-weight:{weight};"
        if style == "italic":
            css += "font-style:italic;"
        css += f"font-variant-emoji:{'emoji' if run.emoji_style == 'color' else 'text'};"
        if run.font_variations:
            css += f"font-variation-settings:{font_variation_settings(run.font_variations)};"
        if run.letter_spacing:
            css += f"letter-spacing:{run.letter_spacing}px;"

        # Glow/shadow as an SVG filter (dilate+blur / offset+blur) instead of
        # text-shadow, so the soft edge matches PIL's Gaussian sigma exactly and
        # a glow can dilate the glyph the way the raster glow does.
        if run.glows or run.shadows:
            ink_w = run.ink_box[2] - run.ink_box[0]
            ink_h = run.ink_box[3] - run.ink_box[1]
            css += self._effect_filter_css([*run.shadows, *run.glows], ink_w, ink_h, is_text=True)
        if run.strokes:
            stroke = run.strokes[-1]
            color = _css_color(color_to_rgba(self._canvas, stroke.color))
            css += f"-webkit-text-stroke:{stroke.width}px {color};paint-order:stroke fill;"

        if isinstance(run.fill, (LinearGradient, RadialGradient)) and run.fill_box is not None:
            # The span paints the gradient over its own border box (its width by
            # the line height), so hand that box in to slice the block gradient.
            ink_w = run.ink_box[2] - run.ink_box[0]
            span_box = (
                run.pen_x,
                run.baseline_y - ascent,
                run.pen_x + ink_w,
                run.baseline_y + descent,
            )
            gradient = _css_gradient(run.fill, run.fill_box, self._canvas, element_box=span_box)
            css += (
                f"background:{gradient};-webkit-background-clip:text;background-clip:text;"
                "color:transparent;-webkit-text-fill-color:transparent;"
            )
        else:
            css += f"color:{_css_color(run.color)};"

        parts.append(f'<span style="{css}">{escape(run.text)}</span>')
        return parts

    def _register_font(self, run: TextRunLayout) -> tuple[str, str, str]:
        family, weight, style, path = resolve_font_face(run)
        if path and self._embed_fonts:
            self._font_faces.setdefault(path, (family, weight, style))
        return family, weight, style

    # ------------------------------------------------------------- svg overlay

    def _emit_svg_layer(self, layer: SvgLayer):
        if layer.effects or is_url(layer.path):
            self._emit_raster_fallback(layer)
            return

        canvas = self._canvas
        svg_bytes, size = read_svg_layer_bytes_and_size(layer)

        x = parse_coordinate(layer.position[0], canvas.width)
        y = parse_coordinate(layer.position[1], canvas.height)
        expanded = expanded_rotation_size(size, layer.rotation)
        if layer.align is not None and layer.align != Align.TOP_LEFT:
            x, y = apply_alignment(x, y, expanded, layer.align)
        local_x = x + (expanded[0] - size[0]) / 2
        local_y = y + (expanded[1] - size[1]) / 2

        style = (
            f"position:absolute;left:{_fmt(local_x)}px;top:{_fmt(local_y)}px;"
            f"width:{size[0]}px;height:{size[1]}px;"
        )
        if layer.rotation:
            style += f"transform:rotate({_fmt(layer.rotation)}deg);transform-origin:center;"
        if layer.opacity < 1:
            style += f"opacity:{_fmt(round(layer.opacity, 4))};"
        encoded = base64.b64encode(svg_bytes).decode("ascii")
        element_id = self._make_id()
        anim_style = self._register_animation(layer, element_id)
        identity = self._identity_attr(layer)
        self._body.append(
            f'<img id="{element_id}"{identity} style="{style}{anim_style}" '
            f'src="data:image/svg+xml;base64,{encoded}" alt="">'
        )


# The raster renderer kerns via HarfBuzz (Pillow's raqm layout) just like the
# browser, so kerning is left on to match. It does antialias in grayscale,
# though, so force grayscale AA to avoid subpixel colour fringing on platforms
# (notably macOS) that would otherwise render text with subpixel AA.
_TEXT_PRECISION_CSS = "-webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale;"


def _css_font_family(family: str) -> str:
    return f"{_css_string(family)}, sans-serif" if family != "sans-serif" else "sans-serif"


@dataclass
class Stage:
    """A rendered canvas as portable HTML plus its animation timeline."""

    width: int
    height: int
    body: str
    keyframes: list[str]
    timeline: list[dict]
    # Slide-transition wiring, filled in by _document for decks. transition_anim
    # animates the incoming stage, transition_exit the outgoing one; transition_z
    # ("over"/"under") sets their stacking; transition_dur drives the cleanup timer.
    transition_anim: str = ""
    transition_exit: str = ""
    transition_z: str = "over"
    transition_dur: str = "0"
    transition_click: str = "1"
    transition_after: str = ""
    transition_morph: str = ""
    speaker_notes: str = ""


# --------------------------------------------------------------- document shell

_HTML_RESOURCE_PACKAGE = "quickthumb.html"
_STAGE_TEMPLATE_START = "{{#stage}}\n"
_STAGE_TEMPLATE_END = "{{/stage}}"


def _html_resource(name: str) -> str:
    return files(_HTML_RESOURCE_PACKAGE).joinpath(name).read_text(encoding="utf-8")


def _document_template_parts() -> tuple[str, str]:
    template = _html_resource("document.html")
    before_stage, stage_block = template.split(_STAGE_TEMPLATE_START, 1)
    stage_template, after_stage = stage_block.split(_STAGE_TEMPLATE_END, 1)
    return before_stage + after_stage, stage_template.strip("\n")


def _render_template(template: str, values: dict[str, str]) -> str:
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace("{{ " + key + " }}", value)
    return rendered


def _base_css_resource(responsive: bool, deck: bool) -> str:
    if responsive:
        return "base.css"
    if deck:
        return "fixed_deck.css"
    return "fixed.css"


def _runtime_js(responsive: bool, deck: bool) -> str:
    runtime_resource = "deck_runtime.js" if deck else "canvas_runtime.js"
    runtime = _render_template(
        _html_resource(runtime_resource),
        {"responsive": json.dumps(responsive)},
    )
    return _html_resource("timeline.js") + "\n" + runtime


# --- slide transition -> incoming-stage entrance keyframe -----------------------
# Deck slide changes animate the *incoming* stage (and, for push/uncover, the
# outgoing one). Effects that move a stage compose with the responsive fit via
# scale(var(--qt-scale,1)) so the scale-to-viewport survives the transform
# animation; clip/opacity effects leave the inline scale untouched. Exotic PPTX
# transitions (wheel, wedge, checker, comb, dissolve) fall back to the closest
# CSS analogue -- the same parity tradeoff the layer animations make.
_TR_SCALE = "scale(var(--qt-scale,1))"
_TR_OFFSET = "translate(var(--qt-stage-x,0),var(--qt-stage-y,0))"
_HOME = f"transform:{_TR_OFFSET} translate(0,0) {_TR_SCALE}"

# Direction -> off-screen transform for the incoming (..._IN) and outgoing
# (..._OUT) stages of a directional slide change. PowerPoint names a push/cover
# by where the content travels, so "left" sends the old slide off the left edge
# and brings the new one in from the right.
_DIR_IN = {
    "left": "translateX(100vw)",
    "right": "translateX(-100vw)",
    "up": "translateY(100vh)",
    "down": "translateY(-100vh)",
}
_DIR_OUT = {
    "left": "translateX(-100vw)",
    "right": "translateX(100vw)",
    "up": "translateY(-100vh)",
    "down": "translateY(100vh)",
}


def _transition_states(transition) -> tuple[str, str]:
    """Return (from-state, to-state) CSS for a transition's incoming stage.

    Only reached from ``_transition_plan`` for non-directional reveals -- cut,
    push and uncover are handled there -- so ``cover`` is the one directional
    case that arrives here (the new slide sliding in over a static old one).
    """
    effect = transition.effect
    if effect in ("fade", "morph", "dissolve", "random", "checker"):
        return "opacity:0", "opacity:1"
    if effect in ("wipe", "comb", "blinds"):
        direction = getattr(transition, "direction", "up")
        if effect == "blinds":
            direction = "right" if transition.orientation == "vertical" else "down"
        elif effect == "comb":
            direction = "left" if transition.orientation == "vertical" else "up"
        return f"clip-path:{_WIPE_INSETS[direction]}", "clip-path:inset(0 0 0 0)"
    if effect == "cover":
        direction = getattr(transition, "direction", "left")
        return (
            f"transform:{_TR_OFFSET} {_DIR_IN[direction]} {_TR_SCALE}",
            _HOME,
        )
    if effect == "zoom":
        factor = "0.6" if getattr(transition, "direction", "in") == "in" else "1.4"
        return (
            f"transform:{_TR_OFFSET} scale(calc(var(--qt-scale,1)*{factor}));opacity:0",
            f"transform:{_TR_OFFSET} {_TR_SCALE};opacity:1",
        )
    if effect == "newsflash":
        return (
            f"transform:{_TR_OFFSET} rotate(-180deg) scale(calc(var(--qt-scale,1)*0.1));opacity:0",
            f"transform:{_TR_OFFSET} rotate(0deg) {_TR_SCALE};opacity:1",
        )
    if effect == "split":
        if transition.orientation == "vertical":
            return "clip-path:inset(50% 0 50% 0)", "clip-path:inset(0 0 0 0)"
        return "clip-path:inset(0 50% 0 50%)", "clip-path:inset(0 0 0 0)"
    if effect == "diamond":
        return (
            "clip-path:polygon(50% 50%,50% 50%,50% 50%,50% 50%)",
            "clip-path:polygon(50% 0%,100% 50%,50% 100%,0% 50%)",
        )
    # circle, wheel, wedge -> expanding circular reveal.
    return "clip-path:circle(0% at 50% 50%)", "clip-path:circle(75% at 50% 50%)"


def _transition_plan(transition) -> tuple[tuple | None, tuple | None, str]:
    """Plan a slide change as ``(enter, exit, z)``.

    ``enter``/``exit`` are ``(from, to)`` CSS state tuples for the incoming and
    outgoing stages (``None`` = that stage doesn't animate), and ``z`` is
    ``"over"`` or ``"under"`` -- whether the incoming slide sits above the
    outgoing one during the change. Keeping the outgoing slide on screen
    (static beneath, or sliding out for push/uncover) is what stops the
    previous slide from blanking before the new one arrives.
    """
    effect = transition.effect if transition else "fade"
    if effect == "cut":
        return None, None, "over"
    if effect == "push":
        direction = getattr(transition, "direction", "left")
        enter = (f"transform:{_TR_OFFSET} {_DIR_IN[direction]} {_TR_SCALE}", _HOME)
        leave = (_HOME, f"transform:{_TR_OFFSET} {_DIR_OUT[direction]} {_TR_SCALE}")
        return enter, leave, "over"
    if effect == "uncover":
        direction = getattr(transition, "direction", "down")
        # The new slide waits, fully shown, underneath; the old one slides away.
        return None, (_HOME, f"transform:{_TR_OFFSET} {_DIR_OUT[direction]} {_TR_SCALE}"), "under"
    # Everything else animates the incoming slide on top of a static outgoing one.
    states = _transition_states(transition) if transition else ("opacity:0", "opacity:1")
    return states, None, "over"


def _document(
    stages: list[Stage],
    responsive: bool,
    font_faces: dict[str, tuple[str, str, str]],
    deck: bool = False,
    transitions: list | None = None,
    notes: list[str | None] | None = None,
    svg_filters: dict[str, str] | None = None,
    reduced_motion: bool = False,
) -> str:
    keyframes = [kf for stage in stages for kf in stage.keyframes]
    if deck:
        transitions = transitions or [None] * len(stages)
        notes = notes or [None] * len(stages)
        for index, (stage, transition, speaker_notes) in enumerate(
            zip(stages, transitions, notes, strict=True)
        ):
            if reduced_motion:
                stage.speaker_notes = speaker_notes or ""
                stage.transition_anim = ""
                stage.transition_exit = ""
                stage.transition_z = "over"
                stage.transition_dur = "0"
                stage.transition_click = "1"
                stage.transition_after = ""
                stage.transition_morph = ""
                continue
            # No transition set keeps the historical 0.5s cross-fade default.
            duration = 0.5 if transition is None else transition.duration
            enter, leave, z = _transition_plan(transition)
            stage.speaker_notes = speaker_notes or ""
            stage.transition_z = z
            stage.transition_dur = _fmt(duration)
            stage.transition_click = (
                "1" if transition is None or transition.advance_on_click else "0"
            )
            stage.transition_after = (
                ""
                if transition is None or transition.advance_after is None
                else _fmt(transition.advance_after)
            )
            stage.transition_morph = (
                "1" if transition is not None and transition.effect == "morph" else ""
            )
            timing = f"{_fmt(duration)}s ease both"
            if enter is not None:
                name = f"qt-t{index}"
                keyframes.append(
                    "@keyframes " + name + "{from{" + enter[0] + "}to{" + enter[1] + "}}"
                )
                stage.transition_anim = f"{name} {timing}"
            if leave is not None:
                name = f"qt-x{index}"
                keyframes.append(
                    "@keyframes " + name + "{from{" + leave[0] + "}to{" + leave[1] + "}}"
                )
                stage.transition_exit = f"{name} {timing}"
    css = _html_resource(_base_css_resource(responsive, deck))
    if deck:
        css += _html_resource("presenter.css")
    css += font_face_declarations(font_faces) + "".join(keyframes)
    runtime = _runtime_js(responsive=responsive, deck=deck)
    filters = "".join((svg_filters or {}).values())
    document_template, stage_template = _document_template_parts()
    stage_markup = "\n".join(
        _render_stage_template(stage_template, stage, index=index, deck=deck)
        for index, stage in enumerate(stages)
    )
    state_id = hashlib.sha256(stage_markup.encode("utf-8")).hexdigest()[:16]
    return _render_template(
        document_template,
        {
            "css": css,
            "filters": filters,
            "frame_open": '<div class="qt-frame">' if responsive else "",
            "frame_close": "</div>" if responsive else "",
            "runtime": runtime,
            "stages": stage_markup,
            "state_id": state_id,
        },
    )


def _render_stage_template(template: str, stage: Stage, index: int, deck: bool) -> str:
    style = f"width:{stage.width}px;height:{stage.height}px;"
    if deck and index > 0:
        style += "display:none;"
    return _render_template(
        template,
        {
            "timeline": _attr(json.dumps(stage.timeline)),
            "slide_index": str(index),
            "deck_attrs": _deck_stage_attrs(stage) if deck else "",
            "hidden": " hidden" if deck and index > 0 else "",
            "style": _attr(style),
            "body": stage.body,
        },
    )


def _deck_stage_attrs(stage: Stage) -> str:
    attrs = {
        "data-qt-transition": stage.transition_anim,
        "data-qt-exit": stage.transition_exit,
        "data-qt-z": stage.transition_z,
        "data-qt-dur": stage.transition_dur,
        "data-qt-click": stage.transition_click,
        "data-qt-after": stage.transition_after,
        "data-qt-morph": stage.transition_morph,
        "data-qt-notes": stage.speaker_notes,
    }
    return "".join(f' {name}="{_attr(value)}"' for name, value in attrs.items())


def _attr(value: str) -> str:
    return escape(value, quote=True)


def export_deck(
    canvases: list[Canvas],
    embed_fonts: bool = False,
    responsive: bool = True,
    transitions: list | None = None,
    notes: list[str | None] | None = None,
    reduced_motion: bool = False,
) -> str:
    stages: list[Stage] = []
    font_faces: dict[str, tuple[str, str, str]] = {}
    svg_filters: dict[str, str] = {}
    for index, canvas in enumerate(canvases):
        exporter = HtmlExporter(
            canvas,
            embed_fonts=embed_fonts,
            responsive=responsive,
            keyframe_prefix=f"qt-s{index}-k",
            reduced_motion=reduced_motion,
        )
        stages.append(exporter.render_stage())
        font_faces.update(exporter._font_faces)
        svg_filters.update(exporter._svg_filters)
    return _document(
        stages,
        responsive=responsive,
        font_faces=font_faces,
        deck=True,
        transitions=None if reduced_motion else transitions,
        notes=notes,
        svg_filters=svg_filters,
        reduced_motion=reduced_motion,
    )
