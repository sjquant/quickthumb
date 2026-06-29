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
import json
import math
import os
from functools import cached_property
from html import escape
from typing import TYPE_CHECKING

import jinja2
from PIL import ImageFont

from quickthumb._base import (
    apply_alignment,
    expanded_rotation_size,
    is_url,
    parse_coordinate,
    parse_padding,
)
from quickthumb._export_base import (
    Box,
    RasterFragment,
    TextRunLayout,
    _fmt,
    color_to_rgba,
    compute_text_layout,
    flatten_layers,
    rasterize_layers,
    split_backdrop_prefix,
    union_boxes,
    uses_image_fill,
)
from quickthumb.models import (
    Align,
    BackgroundLayer,
    Glow,
    LinearGradient,
    OutlineLayer,
    RadialGradient,
    Shadow,
    ShapeLayer,
    Stroke,
    SvgLayer,
    TextLayer,
)

if TYPE_CHECKING:
    from quickthumb.canvas import Canvas, RenderableLayer

_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), "templates")),
    autoescape=False,
    trim_blocks=True,
    lstrip_blocks=True,
    keep_trailing_newline=True,
)
_doc_tmpl = _env.get_template("document.html")


def _css_color(rgba: tuple, opacity: float = 1.0) -> str:
    r, g, b = rgba[:3]
    a = (rgba[3] / 255 if len(rgba) > 3 else 1.0) * opacity
    if a >= 1:
        return f"rgb({r},{g},{b})"
    return f"rgba({r},{g},{b},{a:.4g})"


# --- animation effect -> (entrance from-state, to-state) CSS property blocks ----
# Each keyframe interpolates a single element between a hidden and a shown state.
# Exit reuses the same pair with the keyframe direction reversed. Effects CSS
# cannot express faithfully reuse the closest analogue (documented in gotchas).
def _effect_states(effect) -> tuple[str, str]:
    """Return (hidden-state, shown-state) CSS declaration strings for an effect."""
    name = effect.effect
    if name in ("fade", "appear", "dissolve", "checkerboard"):
        return "opacity:0", "opacity:1"
    if name == "circle":
        return (
            "clip-path:circle(0% at 50% 50%);opacity:1",
            "clip-path:circle(75% at 50% 50%);opacity:1",
        )
    if name == "diamond":
        return (
            "clip-path:polygon(50% 50%,50% 50%,50% 50%,50% 50%);opacity:1",
            "clip-path:polygon(50% 0%,100% 50%,50% 100%,0% 50%);opacity:1",
        )
    if name == "box":
        # in: grow from the centre; out: shrink toward the centre (entrance still
        # ends fully shown -- the keyframe direction handles enter vs exit).
        if getattr(effect, "direction", "in") == "in":
            return (
                "clip-path:inset(50% 50% 50% 50%);opacity:1",
                "clip-path:inset(0 0 0 0);opacity:1",
            )
        return "clip-path:inset(0 0 0 0);opacity:0", "clip-path:inset(0 0 0 0);opacity:1"
    if name in ("wipe", "blinds"):
        direction = getattr(effect, "direction", "up")
        if name == "blinds":
            direction = "right" if effect.orientation == "vertical" else "down"
        insets = {
            "up": "inset(100% 0 0 0)",
            "down": "inset(0 0 100% 0)",
            "left": "inset(0 0 0 100%)",
            "right": "inset(0 100% 0 0)",
        }
        return f"clip-path:{insets[direction]};opacity:1", "clip-path:inset(0 0 0 0);opacity:1"
    if name == "wheel":
        return (
            "clip-path:polygon(50% 50%,50% 0%,50% 0%);opacity:1",
            "clip-path:circle(75% at 50% 50%);opacity:1",
        )
    return "opacity:0", "opacity:1"


def _css_gradient(gradient: LinearGradient | RadialGradient, box: Box, canvas: Canvas) -> str:
    """Build a CSS gradient over a box, approximating EffectsEngine geometry."""
    left, top, right, bottom = box
    width, height = right - left, bottom - top
    stops = sorted(gradient.stops, key=lambda stop: stop[1])

    if isinstance(gradient, LinearGradient):
        # Our angle uses screen coords (x right, y down); CSS measures
        # clockwise from "to top", so convert the direction vector.
        theta = math.radians(gradient.angle)
        dx, dy = math.cos(theta), math.sin(theta)
        css_angle = (math.degrees(math.atan2(dx, -dy))) % 360
        parts = [
            f"{_css_color(color_to_rgba(canvas, color))} {_fmt(round(pos * 100, 2))}%"
            for color, pos in stops
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
    def __init__(self, canvas: Canvas, embed_fonts: bool = False, responsive: bool = True):
        self._canvas = canvas
        self._embed_fonts = embed_fonts
        self._responsive = responsive
        self._body: list[str] = []
        self._keyframes: list[str] = []
        self._timeline: list[dict] = []
        self._font_faces: dict[str, tuple[str, str, str]] = {}
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
        return _document([stage], responsive=self._responsive, font_faces=self._font_faces)

    def render_stage(self) -> Stage:
        """Render the canvas into a reusable stage (used directly and by decks)."""
        canvas = self._canvas
        canvas._validate_image_paths()
        canvas._ctx.begin_render_pass()

        prefix, rest = split_backdrop_prefix(flatten_layers(canvas))
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

    def _layer_animations(self, layer: RenderableLayer) -> list:
        animation = getattr(layer, "animation", None)
        if animation is None:
            return []
        return animation if isinstance(animation, list) else [animation]

    def _register_animation(self, layer: RenderableLayer, element_id: str) -> tuple[str, bool]:
        """Record a layer's animation as timeline node(s) keyed to its element.

        Returns ``(extra_style, hidden)`` -- extra inline style for the element
        and whether it must start hidden (an entrance effect plays first).
        """
        animation = getattr(layer, "animation", None)
        effects = self._layer_animations(layer)
        if not effects:
            self._prev_anim_key = None
            return "", False

        key = id(animation)
        if key == self._prev_anim_key:
            # Same group animation object: add this element to the shared node(s).
            for node in self._prev_nodes:
                node["t"].append(element_id)
            hidden = effects[0].animate == "entrance"
            return ("visibility:hidden;" if hidden else ""), hidden

        nodes: list[dict] = []
        for effect in effects:
            hidden_state, shown_state = _effect_states(effect)
            kf = f"qt-k{self._next_kf}"
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
        hidden = effects[0].animate == "entrance"
        return ("visibility:hidden;" if hidden else ""), hidden

    # ------------------------------------------------------------------ layers

    def _emit_layer(self, layer: RenderableLayer):
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
        anim_style, _ = self._register_animation(layer, element_id)
        self._body.append(f'<{tag} id="{element_id}" style="{style}{anim_style}">{inner}</{tag}>')

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
            anim_style, _ = self._register_animation(layer, element_id)
            self._body.append(
                f'<img id="{element_id}" style="{style}{anim_style}" '
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
        rounded = layer.shape in ("rectangle", "ellipse", "pill")
        style += self._shape_effects_css(layer, rounded)
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

    def _shape_effects_css(self, layer: ShapeLayer, rounded: bool) -> str:
        """Approximate stroke/shadow/glow. Rounded shapes use box-shadow (which
        follows border-radius); clip-path shapes use filter drop-shadow."""
        box_shadows: list[str] = []
        filters: list[str] = []
        for effect in layer.effects:
            if isinstance(effect, Glow):
                rgba = color_to_rgba(self._canvas, effect.color)
                color = _css_color(rgba, effect.opacity)
                if rounded:
                    box_shadows.append(f"0 0 {effect.radius}px {effect.radius}px {color}")
                else:
                    filters.append(f"drop-shadow(0 0 {effect.radius}px {color})")
            elif isinstance(effect, Shadow):
                color = _css_color(color_to_rgba(self._canvas, effect.color))
                if rounded:
                    box_shadows.append(
                        f"{effect.offset_x}px {effect.offset_y}px {effect.blur_radius}px {color}"
                    )
                else:
                    filters.append(
                        f"drop-shadow({effect.offset_x}px {effect.offset_y}px "
                        f"{effect.blur_radius}px {color})"
                    )
            elif isinstance(effect, Stroke):
                color = _css_color(color_to_rgba(self._canvas, effect.color))
                if rounded:
                    box_shadows.append(f"0 0 0 {effect.width}px {color}")
                else:
                    # No clean clip-path outline; stack offsets as a thin border.
                    w = effect.width
                    filters.extend(
                        f"drop-shadow({dx}px {dy}px 0 {color})"
                        for dx, dy in ((w, 0), (-w, 0), (0, w), (0, -w))
                    )
        css = ""
        if box_shadows:
            css += f"box-shadow:{','.join(box_shadows)};"
        if filters:
            css += f"filter:{' '.join(filters)};"
        return css

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
            f"line-height:{ascent + descent}px;"
        )
        if weight != "400":
            css += f"font-weight:{weight};"
        if style == "italic":
            css += "font-style:italic;"
        if run.letter_spacing:
            css += f"letter-spacing:{run.letter_spacing}px;"

        shadows: list[str] = []
        for glow in run.glows:
            color = _css_color(color_to_rgba(self._canvas, glow.color), glow.opacity)
            shadows.append(f"0 0 {glow.radius}px {color}")
        for shadow in run.shadows:
            color = _css_color(color_to_rgba(self._canvas, shadow.color))
            shadows.append(
                f"{shadow.offset_x}px {shadow.offset_y}px {shadow.blur_radius}px {color}"
            )
        if shadows:
            css += f"text-shadow:{','.join(shadows)};"
        if run.strokes:
            stroke = run.strokes[-1]
            color = _css_color(color_to_rgba(self._canvas, stroke.color))
            css += f"-webkit-text-stroke:{stroke.width}px {color};paint-order:stroke fill;"

        if isinstance(run.fill, (LinearGradient, RadialGradient)) and run.fill_box is not None:
            gradient = _css_gradient(run.fill, run.fill_box, self._canvas)
            css += (
                f"background:{gradient};-webkit-background-clip:text;background-clip:text;"
                "color:transparent;-webkit-text-fill-color:transparent;"
            )
        else:
            css += f"color:{_css_color(run.color)};"

        parts.append(f'<span style="{css}">{escape(run.text)}</span>')
        return parts

    def _register_font(self, run: TextRunLayout) -> tuple[str, str, str]:
        font = run.font
        if isinstance(font, ImageFont.FreeTypeFont):
            family = font.getname()[0] or "sans-serif"
            path = getattr(font, "path", None)
        else:
            family = "sans-serif"
            path = None

        if isinstance(run.weight, int):
            weight = str(run.weight)
        elif isinstance(run.weight, str) and run.weight.isdigit():
            weight = run.weight
        elif run.bold or (isinstance(run.weight, str) and run.weight.lower() == "bold"):
            weight = "700"
        else:
            weight = "400"
        style = "italic" if run.italic else "normal"

        if path and isinstance(path, str) and self._embed_fonts:
            self._font_faces.setdefault(path, (family, weight, style))
        return family, weight, style

    # ------------------------------------------------------------- svg overlay

    def _emit_svg_layer(self, layer: SvgLayer):
        if layer.effects or is_url(layer.path):
            self._emit_raster_fallback(layer)
            return

        canvas = self._canvas
        from quickthumb._export_svg import SvgExporter

        helper = SvgExporter(canvas)
        svg_bytes, size = helper._read_svg_layer_bytes_and_size(layer)

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
        anim_style, _ = self._register_animation(layer, element_id)
        self._body.append(
            f'<img id="{element_id}" style="{style}{anim_style}" '
            f'src="data:image/svg+xml;base64,{encoded}" alt="">'
        )


def _css_font_family(family: str) -> str:
    safe = family.replace("'", "")
    return f"'{safe}', sans-serif" if family != "sans-serif" else "sans-serif"


class Stage:
    """A rendered canvas as portable HTML plus its animation timeline."""

    def __init__(
        self,
        width: int,
        height: int,
        body: str,
        keyframes: list[str],
        timeline: list[dict],
    ):
        self.width = width
        self.height = height
        self.body = body
        self.keyframes = keyframes
        self.timeline = timeline

    @cached_property
    def timeline_json(self) -> str:
        return json.dumps(self.timeline)


# --------------------------------------------------------------- document shell

_BASE_CSS = (
    "*{margin:0;padding:0;box-sizing:content-box}"
    "html,body{width:100%;height:100%}"
    "body{background:#000;overflow:hidden;font-family:sans-serif}"
    ".qt-frame{position:absolute;inset:0;display:flex;align-items:center;justify-content:center}"
    ".qt-stage{position:relative;overflow:hidden;transform-origin:center center;flex:none}"
)

_FIXED_CSS = (
    "*{margin:0;padding:0;box-sizing:content-box}"
    "body{font-family:sans-serif}"
    ".qt-stage{position:relative;overflow:hidden}"
)

# Scales the active stage to fit the frame, preserving aspect ratio.
_SCALE_JS = """
function qtFit(stage){
  var f=stage.parentElement;
  var s=Math.min(f.clientWidth/parseInt(stage.style.width), f.clientHeight/parseInt(stage.style.height));
  stage.style.transform='scale('+s+')';
}
"""

# Plays a stage's animation timeline, honouring on_click/with_previous/after_previous.
_TIMELINE_JS = """
function qtTimeline(stage){
  var nodes=JSON.parse(stage.getAttribute('data-qt-timeline')||'[]');
  var cursor=0;
  // Cache element references and entrance clip-paths once at construction.
  // Avoids repeated querySelector in the per-frame animation hot path.
  var elMap={};
  var origClips={};
  nodes.forEach(function(node){
    var isEntrance=node.a==='entrance';
    node.t.forEach(function(id){
      if(!elMap[id]){var el=stage.querySelector('#'+CSS.escape(id));if(el)elMap[id]=el;}
      if(isEntrance&&elMap[id]&&!(id in origClips)){origClips[id]=elMap[id].style.clipPath;}
    });
  });
  function resetElements(){
    nodes.forEach(function(node){
      if(node.a==='entrance'){
        node.t.forEach(function(id){
          var el=elMap[id];
          if(el){el.style.visibility='hidden';el.style.animation='';el.style.clipPath=origClips[id]||'';}
        });
      }
    });
  }
  function play(node){
    return new Promise(function(res){
      var dur=0;
      node.t.forEach(function(id){
        var el=elMap[id];
        if(!el)return;
        var origClip=origClips[id]||'';
        el.style.willChange='clip-path,opacity';
        el.style.visibility='visible';
        el.style.animation=node.k+' '+node.d+'s ease both '+node.delay+'s';
        function settle(){
          el.style.willChange='';
          el.style.animation='';
          if(node.a==='entrance'){el.style.clipPath=origClip;el.style.opacity='';}
          else{el.style.visibility='hidden';}
        }
        el.addEventListener('animationend',settle,{once:true});
        dur=Math.max(dur,(node.d+node.delay)*1000);
      });
      setTimeout(res,dur);
    });
  }
  function withCompanions(i){
    var group=[nodes[i]];var j=i+1;
    while(j<nodes.length&&nodes[j].tr==='with_previous'){group.push(nodes[j]);j++;}
    return {group:group,next:j};
  }
  async function runGroup(i){
    var gc=withCompanions(i);
    await Promise.all(gc.group.map(play));
    cursor=gc.next;
    while(cursor<nodes.length&&nodes[cursor].tr==='after_previous'){
      var ac=withCompanions(cursor);
      await Promise.all(ac.group.map(play));
      cursor=ac.next;
    }
  }
  async function autoLead(){
    while(cursor<nodes.length&&nodes[cursor].tr==='after_previous'){await runGroup(cursor);}
  }
  this.hasNext=function(){return cursor<nodes.length;};
  this.advance=function(){if(cursor<nodes.length)return runGroup(cursor);return Promise.resolve();};
  this.reset=function(){cursor=0;resetElements();};
  this.start=autoLead;
}
"""

_CANVAS_RUNTIME_TMPL = _env.from_string(
    _SCALE_JS
    + _TIMELINE_JS
    + """
(function(){
  var stage=document.querySelector('.qt-stage');
  if(!stage)return;
  var fit={{ responsive }};
  if(fit){function r(){qtFit(stage);}
    if(window.ResizeObserver){new ResizeObserver(r).observe(stage.parentElement);}
    else{window.addEventListener('resize',r);}r();}
  var tl=new qtTimeline(stage);
  tl.start();
  document.addEventListener('click',function(){if(tl.hasNext())tl.advance();});
})();
"""
)

_DECK_RUNTIME_TMPL = _env.from_string(
    _SCALE_JS
    + _TIMELINE_JS
    + """
(function(){
  var stages=Array.prototype.slice.call(document.querySelectorAll('.qt-stage'));
  if(!stages.length)return;
  var fit={{ responsive }};
  var current=0;
  var timelines=stages.map(function(s){return new qtTimeline(s);});
  function show(i){
    stages.forEach(function(s,j){s.style.display=j===i?'block':'none';});
    var s=stages[i];
    s.style.animation='qt-slide-in 0.5s ease both';
    if(fit)qtFit(s);
    timelines[i].reset();
    timelines[i].start();
  }
  function go(i){if(i<0||i>=stages.length)return;current=i;show(i);}
  if(fit){function r(){qtFit(stages[current]);}
    if(window.ResizeObserver){new ResizeObserver(r).observe(stages[0].parentElement);}
    else{window.addEventListener('resize',r);}}
  function advance(){
    if(timelines[current].hasNext())timelines[current].advance();
    else if(current<stages.length-1)go(current+1);
  }
  document.addEventListener('click',advance);
  document.addEventListener('keydown',function(e){
    if(e.key==='ArrowRight'||e.key===' '){advance();}
    else if(e.key==='ArrowLeft'){if(current>0)go(current-1);}
  });
  show(0);
})();
"""
)


def _font_face_css(font_faces: dict[str, tuple[str, str, str]]) -> str:
    faces = []
    for path, (family, weight, style) in font_faces.items():
        try:
            with open(path, "rb") as font_file:
                encoded = base64.b64encode(font_file.read()).decode("ascii")
        except OSError:
            continue
        faces.append(
            "@font-face{"
            f"font-family:'{family}';"
            f"src:url(data:font/ttf;base64,{encoded}) format('truetype');"
            f"font-weight:{weight};font-style:{style};}}"
        )
    return "".join(faces)


def _document(
    stages: list[Stage],
    responsive: bool,
    font_faces: dict[str, tuple[str, str, str]],
    deck: bool = False,
) -> str:
    keyframes = "".join(kf for stage in stages for kf in stage.keyframes)
    if deck:
        keyframes += "@keyframes qt-slide-in{from{opacity:0}to{opacity:1}}"
    base_css = _BASE_CSS if responsive else _FIXED_CSS
    css = base_css + _font_face_css(font_faces) + keyframes

    runtime_tmpl = _DECK_RUNTIME_TMPL if deck else _CANVAS_RUNTIME_TMPL
    runtime = runtime_tmpl.render(responsive=json.dumps(responsive))

    return _doc_tmpl.render(
        css=css,
        stages=stages,
        runtime=runtime,
        responsive=responsive,
        deck=deck,
    )


def export_canvas(canvas: Canvas, embed_fonts: bool = False, responsive: bool = True) -> str:
    return HtmlExporter(canvas, embed_fonts=embed_fonts, responsive=responsive).export()


def export_deck(
    canvases: list[Canvas], embed_fonts: bool = False, responsive: bool = True
) -> str:
    stages: list[Stage] = []
    font_faces: dict[str, tuple[str, str, str]] = {}
    for canvas in canvases:
        exporter = HtmlExporter(canvas, embed_fonts=embed_fonts, responsive=responsive)
        stages.append(exporter.render_stage())
        font_faces.update(exporter._font_faces)
    return _document(stages, responsive=responsive, font_faces=font_faces, deck=True)
