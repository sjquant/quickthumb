"""SVG document exporter.

Backgrounds, outlines, shapes, and text are emitted as native SVG primitives
using the same geometry math as the PIL render path, so vector output stays
editable. Layers the format cannot express faithfully (raster images, image
glyph fills, blend modes, custom callbacks) are embedded as pixel-exact PNG
fragments rendered through the regular pipeline.
"""

from __future__ import annotations

import base64
import math
from typing import TYPE_CHECKING
from xml.sax.saxutils import escape, quoteattr

from PIL import ImageFont

from quickthumb._base import apply_alignment, expanded_rotation_size, is_url, parse_coordinate
from quickthumb._export_base import (
    Box,
    RasterFragment,
    TextRunLayout,
    color_to_rgba,
    flatten_layers,
    rasterize_layers,
    rgb_hex,
    split_backdrop_prefix,
    uses_image_fill,
)
from quickthumb.models import (
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


def _fmt(value: float) -> str:
    """Format a coordinate compactly: integers stay integers, floats keep 2 dp."""
    if isinstance(value, int) or float(value).is_integer():
        return str(int(value))
    return f"{value:.2f}"


class SvgExporter:
    def __init__(self, canvas: Canvas, embed_fonts: bool = False):
        self._canvas = canvas
        self._embed_fonts = embed_fonts
        self._defs: list[str] = []
        self._body: list[str] = []
        self._font_faces: dict[str, tuple[str, str, str]] = {}  # path -> (family, weight, style)
        self._next_id = 1

    def export(self) -> str:
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

        return self._assemble()

    def _assemble(self) -> str:
        width, height = self._canvas.width, self._canvas.height
        parts = [
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
        ]
        defs = list(self._defs)
        if self._embed_fonts and self._font_faces:
            defs.insert(0, self._font_face_style())
        if defs:
            parts.append("<defs>")
            parts.extend(defs)
            parts.append("</defs>")
        parts.extend(self._body)
        parts.append("</svg>")
        return "\n".join(parts)

    def _make_id(self, prefix: str) -> str:
        made = f"{prefix}{self._next_id}"
        self._next_id += 1
        return made

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

    def _emit_raster_fallback(self, layer: RenderableLayer):
        fragment = rasterize_layers(self._canvas, [layer])
        if fragment:
            self._emit_fragment(fragment)

    def _emit_fragment(self, fragment: RasterFragment):
        encoded = base64.b64encode(fragment.png_bytes).decode("ascii")
        self._body.append(
            f'<image x="{fragment.x}" y="{fragment.y}" '
            f'width="{fragment.width}" height="{fragment.height}" '
            f'xlink:href="data:image/png;base64,{encoded}"/>'
        )

    # -------------------------------------------------------------- background

    def _emit_background(self, layer: BackgroundLayer):
        if layer.effects or layer.image or (layer.color is None and layer.gradient is None):
            self._emit_raster_fallback(layer)
            return

        width, height = self._canvas.width, self._canvas.height
        if layer.color is not None:
            rgba = color_to_rgba(self._canvas, layer.color, layer.opacity)
            alpha = rgba[3] / 255
            opacity_attr = f' fill-opacity="{_fmt(round(alpha, 4))}"' if alpha < 1 else ""
            self._body.append(
                f'<rect width="{width}" height="{height}" fill="{rgb_hex(rgba)}"{opacity_attr}/>'
            )
            return

        assert layer.gradient is not None  # guarded above: color or gradient is set
        gradient_id = self._define_gradient(layer.gradient, (0.0, 0.0, width, height))
        opacity_attr = f' opacity="{_fmt(round(layer.opacity, 4))}"' if layer.opacity < 1 else ""
        self._body.append(
            f'<rect width="{width}" height="{height}" fill="url(#{gradient_id})"{opacity_attr}/>'
        )

    def _define_gradient(self, gradient: LinearGradient | RadialGradient, box: Box) -> str:
        """Define a gradient over a box, matching EffectsEngine's gradient geometry."""
        left, top, right, bottom = box
        width, height = right - left, bottom - top
        stops = sorted(gradient.stops, key=lambda stop: stop[1])
        stop_elements = []
        for color, position in stops:
            rgba = color_to_rgba(self._canvas, color)
            alpha = rgba[3] / 255
            opacity_attr = f' stop-opacity="{_fmt(round(alpha, 4))}"' if alpha < 1 else ""
            stop_elements.append(
                f'<stop offset="{_fmt(round(position, 4))}" '
                f'stop-color="{rgb_hex(rgba)}"{opacity_attr}/>'
            )

        gradient_id = self._make_id("grad")
        center_x, center_y = left + width / 2, top + height / 2
        if isinstance(gradient, LinearGradient):
            # The PIL ramp spans the box diagonal, centered on the box center.
            diagonal = math.ceil(math.hypot(width, height))
            theta = math.radians(gradient.angle)
            dx, dy = math.cos(theta), math.sin(theta)
            x1, y1 = center_x - dx * diagonal / 2, center_y - dy * diagonal / 2
            x2, y2 = center_x + dx * diagonal / 2, center_y + dy * diagonal / 2
            self._defs.append(
                f'<linearGradient id="{gradient_id}" gradientUnits="userSpaceOnUse" '
                f'x1="{_fmt(x1)}" y1="{_fmt(y1)}" x2="{_fmt(x2)}" y2="{_fmt(y2)}">'
                + "".join(stop_elements)
                + "</linearGradient>"
            )
        else:
            # PIL's radial ramp reaches the final stop at sqrt(2) x the largest
            # center-to-corner distance.
            focus_x = left + width * gradient.center[0]
            focus_y = top + height * gradient.center[1]
            max_dist = max(
                math.hypot(focus_x - left, focus_y - top),
                math.hypot(right - focus_x, focus_y - top),
                math.hypot(focus_x - left, bottom - focus_y),
                math.hypot(right - focus_x, bottom - focus_y),
            )
            radius = max_dist * math.sqrt(2)
            self._defs.append(
                f'<radialGradient id="{gradient_id}" gradientUnits="userSpaceOnUse" '
                f'cx="{_fmt(focus_x)}" cy="{_fmt(focus_y)}" r="{_fmt(radius)}">'
                + "".join(stop_elements)
                + "</radialGradient>"
            )
        return gradient_id

    # ----------------------------------------------------------------- outline

    def _emit_outline(self, layer: OutlineLayer):
        rgba = color_to_rgba(self._canvas, layer.color, layer.opacity)
        alpha = rgba[3] / 255
        inset = layer.offset + layer.width / 2
        width = self._canvas.width - 2 * layer.offset - layer.width
        height = self._canvas.height - 2 * layer.offset - layer.width
        opacity_attr = f' stroke-opacity="{_fmt(round(alpha, 4))}"' if alpha < 1 else ""
        self._body.append(
            f'<rect x="{_fmt(inset)}" y="{_fmt(inset)}" '
            f'width="{_fmt(width)}" height="{_fmt(height)}" fill="none" '
            f'stroke="{rgb_hex(rgba)}" stroke-width="{layer.width}"{opacity_attr}/>'
        )

    # ------------------------------------------------------------------ shapes

    def _emit_shape(self, layer: ShapeLayer):
        canvas = self._canvas
        x = parse_coordinate(layer.position[0], canvas.width)
        y = parse_coordinate(layer.position[1], canvas.height)
        width, height = layer.width, layer.height

        expanded = expanded_rotation_size((width, height), layer.rotation)
        paste_x, paste_y = (x, y)
        if layer.align:
            paste_x, paste_y = apply_alignment(x, y, expanded, layer.align)

        shape_x = paste_x + (expanded[0] - width) / 2
        shape_y = paste_y + (expanded[1] - height) / 2
        rotate = ""
        if layer.rotation != 0:
            center_x = paste_x + expanded[0] / 2
            center_y = paste_y + expanded[1] / 2
            rotate = f"rotate({_fmt(layer.rotation)} {_fmt(center_x)} {_fmt(center_y)})"

        rgba = color_to_rgba(canvas, layer.color)
        fill_alpha = rgba[3] / 255

        group_attrs = ""
        if layer.opacity < 1:
            group_attrs = f' opacity="{_fmt(round(layer.opacity, 4))}"'
        self._body.append(f"<g{group_attrs}>")

        geometry_box = (shape_x, shape_y, shape_x + width, shape_y + height)
        for effect in layer.effects:
            if isinstance(effect, Glow):
                glow_rgba = color_to_rgba(canvas, effect.color)
                filter_id = self._define_blur_filter(geometry_box, effect.radius)
                self._body.append(
                    self._shape_element(
                        layer,
                        shape_x,
                        shape_y,
                        f'fill="{rgb_hex(glow_rgba)}" opacity="{_fmt(round(effect.opacity, 4))}"'
                        f' filter="url(#{filter_id})"',
                        rotate,
                    )
                )
        for effect in layer.effects:
            if isinstance(effect, Shadow):
                shadow_rgba = color_to_rgba(canvas, effect.color)
                attrs = f'fill="{rgb_hex(shadow_rgba)}"'
                if effect.blur_radius > 0:
                    filter_id = self._define_blur_filter(geometry_box, effect.blur_radius)
                    attrs += f' filter="url(#{filter_id})"'
                transform = f"translate({effect.offset_x} {effect.offset_y})"
                if rotate:
                    transform += f" {rotate}"
                self._body.append(self._shape_element(layer, shape_x, shape_y, attrs, transform))
        for effect in layer.effects:
            if isinstance(effect, Stroke):
                stroke_rgba = color_to_rgba(canvas, effect.color)
                stroke_hex = rgb_hex(stroke_rgba)
                # PIL strokes dilate outward; a centered stroke of twice the
                # width painted behind the fill produces the same silhouette.
                self._body.append(
                    self._shape_element(
                        layer,
                        shape_x,
                        shape_y,
                        f'fill="{stroke_hex}" stroke="{stroke_hex}" '
                        f'stroke-width="{effect.width * 2}"',
                        rotate,
                    )
                )

        fill_attrs = f'fill="{rgb_hex(rgba)}"'
        if fill_alpha < 1:
            fill_attrs += f' fill-opacity="{_fmt(round(fill_alpha, 4))}"'
        self._body.append(self._shape_element(layer, shape_x, shape_y, fill_attrs, rotate))
        self._body.append("</g>")

    def _shape_element(
        self, layer: ShapeLayer, x: float, y: float, paint_attrs: str, transform: str
    ) -> str:
        width, height = layer.width, layer.height
        transform_attr = f' transform="{transform}"' if transform else ""

        if layer.shape == "rectangle":
            radius_attr = f' rx="{layer.border_radius}"' if layer.border_radius else ""
            return (
                f'<rect x="{_fmt(x)}" y="{_fmt(y)}" width="{width}" height="{height}"'
                f"{radius_attr} {paint_attrs}{transform_attr}/>"
            )
        if layer.shape == "ellipse":
            return (
                f'<ellipse cx="{_fmt(x + width / 2)}" cy="{_fmt(y + height / 2)}" '
                f'rx="{_fmt(width / 2)}" ry="{_fmt(height / 2)}" '
                f"{paint_attrs}{transform_attr}/>"
            )
        if layer.shape == "pill":
            return (
                f'<rect x="{_fmt(x)}" y="{_fmt(y)}" width="{width}" height="{height}" '
                f'rx="{_fmt(min(width, height) / 2)}" {paint_attrs}{transform_attr}/>'
            )

        normalized = self._canvas._shapes.normalized_shape_points(layer)
        points = " ".join(
            f"{_fmt(x + px * width)},{_fmt(y + py * height)}" for px, py in normalized
        )
        return f'<polygon points="{points}" {paint_attrs}{transform_attr}/>'

    def _define_blur_filter(self, box: Box, blur_radius: int, margin: float = 0) -> str:
        """A Gaussian blur filter with an explicit region around the element box."""
        pad = blur_radius * 3 + margin + 1
        filter_id = self._make_id("blur")
        self._defs.append(
            f'<filter id="{filter_id}" filterUnits="userSpaceOnUse" '
            f'x="{_fmt(box[0] - pad)}" y="{_fmt(box[1] - pad)}" '
            f'width="{_fmt(box[2] - box[0] + 2 * pad)}" '
            f'height="{_fmt(box[3] - box[1] + 2 * pad)}">'
            f'<feGaussianBlur stdDeviation="{blur_radius}"/></filter>'
        )
        return filter_id

    # -------------------------------------------------------------------- text

    def _emit_text(self, layer: TextLayer):
        if uses_image_fill(layer):
            self._emit_raster_fallback(layer)
            return

        from quickthumb._export_base import compute_text_layout

        layout = compute_text_layout(self._canvas, layer)
        if not any(layout.lines):
            return

        group_attrs = ""
        if layout.rotation != 0 and layout.origin and layout.rot_center_local:
            origin_x, origin_y = layout.origin
            center_x, center_y = layout.rot_center_local
            group_attrs += (
                f' transform="translate({_fmt(origin_x)} {_fmt(origin_y)}) '
                f'rotate({_fmt(layout.rotation)} {_fmt(center_x)} {_fmt(center_y)})"'
            )
        if layout.opacity < 1:
            group_attrs += f' opacity="{_fmt(round(layout.opacity, 4))}"'
        self._body.append(f"<g{group_attrs}>")

        if layout.block_backgrounds and layout.block_bg_box:
            for background in layout.block_backgrounds:
                self._emit_text_background(background, layout.block_bg_box)

        for line in layout.lines:
            for run in line:
                self._emit_text_run(run)

        self._body.append("</g>")

    def _emit_text_background(self, background, content_box: Box):
        from quickthumb._base import parse_padding

        pad_top, pad_right, pad_bottom, pad_left = parse_padding(background.padding)
        rgba = color_to_rgba(self._canvas, background.color, background.opacity)
        alpha = rgba[3] / 255
        radius_attr = f' rx="{background.border_radius}"' if background.border_radius else ""
        opacity_attr = f' fill-opacity="{_fmt(round(alpha, 4))}"' if alpha < 1 else ""
        self._body.append(
            f'<rect x="{_fmt(content_box[0] - pad_left)}" y="{_fmt(content_box[1] - pad_top)}" '
            f'width="{_fmt(content_box[2] - content_box[0] + pad_left + pad_right)}" '
            f'height="{_fmt(content_box[3] - content_box[1] + pad_top + pad_bottom)}"'
            f'{radius_attr} fill="{rgb_hex(rgba)}"{opacity_attr}/>'
        )

    def _emit_text_run(self, run: TextRunLayout):
        for background in run.backgrounds:
            if run.bg_box:
                self._emit_text_background(background, run.bg_box)

        for glow in run.glows:
            glow_rgba = color_to_rgba(self._canvas, glow.color)
            glow_hex = rgb_hex(glow_rgba)
            expansion = max(1, glow.radius // 2) * 2
            filter_id = self._define_blur_filter(run.ink_box, glow.radius, margin=expansion)
            self._body.append(
                self._text_element(
                    run,
                    f'fill="{glow_hex}" stroke="{glow_hex}" stroke-width="{expansion * 2}" '
                    f'opacity="{_fmt(round(glow.opacity, 4))}" filter="url(#{filter_id})"',
                )
            )

        for shadow in run.shadows:
            shadow_rgba = color_to_rgba(self._canvas, shadow.color)
            attrs = f'fill="{rgb_hex(shadow_rgba)}"'
            if shadow.blur_radius > 0:
                offset_box = (
                    run.ink_box[0] + shadow.offset_x,
                    run.ink_box[1] + shadow.offset_y,
                    run.ink_box[2] + shadow.offset_x,
                    run.ink_box[3] + shadow.offset_y,
                )
                filter_id = self._define_blur_filter(offset_box, shadow.blur_radius)
                attrs += f' filter="url(#{filter_id})"'
            self._body.append(
                self._text_element(run, attrs, dx=shadow.offset_x, dy=shadow.offset_y)
            )

        for stroke in run.strokes:
            stroke_hex = rgb_hex(color_to_rgba(self._canvas, stroke.color))
            self._body.append(
                self._text_element(
                    run,
                    f'fill="{stroke_hex}" stroke="{stroke_hex}" stroke-width="{stroke.width * 2}"',
                )
            )

        if isinstance(run.fill, (LinearGradient, RadialGradient)) and run.fill_box is not None:
            gradient_id = self._define_gradient(run.fill, run.fill_box)
            fill_attr = f'fill="url(#{gradient_id})"'
        else:
            alpha = run.color[3] / 255
            fill_attr = f'fill="{rgb_hex(run.color)}"'
            if alpha < 1:
                fill_attr += f' fill-opacity="{_fmt(round(alpha, 4))}"'
        self._body.append(self._text_element(run, fill_attr))

    def _text_element(
        self, run: TextRunLayout, paint_attrs: str, dx: float = 0, dy: float = 0
    ) -> str:
        if run.char_xs is not None:
            x_attr = " ".join(_fmt(x + dx) for x in run.char_xs)
        else:
            x_attr = _fmt(run.pen_x + dx)

        family, weight, style = self._register_font(run)
        font_attrs = f'font-family={quoteattr(family)} font-size="{run.size}px"'
        if weight != "400":
            font_attrs += f' font-weight="{weight}"'
        if style == "italic":
            font_attrs += ' font-style="italic"'

        return (
            f'<text x="{x_attr}" y="{_fmt(run.baseline_y + dy)}" {font_attrs} '
            f'{paint_attrs} xml:space="preserve">{escape(run.text)}</text>'
        )

    def _register_font(self, run: TextRunLayout) -> tuple[str, str, str]:
        """Resolve (family, css weight, css style) for a run and record it for embedding."""
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

        if path and isinstance(path, str):
            self._font_faces.setdefault(path, (family, weight, style))
        return f"{family}, sans-serif" if family != "sans-serif" else family, weight, style

    def _font_face_style(self) -> str:
        faces = []
        for path, (family, weight, style) in self._font_faces.items():
            try:
                with open(path, "rb") as font_file:
                    encoded = base64.b64encode(font_file.read()).decode("ascii")
            except OSError:
                continue
            faces.append(
                "@font-face{"
                f"font-family:'{family}';"
                f"src:url(data:font/ttf;base64,{encoded}) format('truetype');"
                f"font-weight:{weight};font-style:{style};"
                "}"
            )
        return "<style>" + "".join(faces) + "</style>" if faces else ""

    # ------------------------------------------------------------- svg overlay

    def _emit_svg_layer(self, layer: SvgLayer):
        if layer.effects or is_url(layer.path):
            self._emit_raster_fallback(layer)
            return

        canvas = self._canvas
        try:
            size = canvas._images.rasterize_svg(layer).size
        except Exception:
            self._emit_raster_fallback(layer)
            return

        x = parse_coordinate(layer.position[0], canvas.width)
        y = parse_coordinate(layer.position[1], canvas.height)
        expanded = expanded_rotation_size(size, layer.rotation)
        from quickthumb.models import Align

        if layer.align is not None and layer.align != Align.TOP_LEFT:
            x, y = apply_alignment(x, y, expanded, layer.align)

        local_x = x + (expanded[0] - size[0]) / 2
        local_y = y + (expanded[1] - size[1]) / 2
        attrs = ""
        if layer.rotation != 0:
            center_x = x + expanded[0] / 2
            center_y = y + expanded[1] / 2
            attrs += (
                f' transform="rotate({_fmt(layer.rotation)} {_fmt(center_x)} {_fmt(center_y)})"'
            )
        if layer.opacity < 1:
            attrs += f' opacity="{_fmt(round(layer.opacity, 4))}"'

        with open(layer.path, "rb") as svg_file:
            encoded = base64.b64encode(svg_file.read()).decode("ascii")
        self._body.append(
            f'<image x="{_fmt(local_x)}" y="{_fmt(local_y)}" '
            f'width="{size[0]}" height="{size[1]}"{attrs} '
            f'xlink:href="data:image/svg+xml;base64,{encoded}"/>'
        )
