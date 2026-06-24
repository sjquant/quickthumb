"""PDF document exporter built on reportlab.

The canvas becomes a single PDF page sized to the canvas pixels (one point per
pixel). Backgrounds, gradients, outlines, shapes, and text are emitted as native
PDF vector primitives using the same geometry math as the PIL render path, so
the output stays selectable/scalable. Layers the format cannot express
faithfully (raster images, blend modes, blur effects, gradient/image glyph
fills, custom callbacks) are embedded as pixel-exact PNG fragments rendered
through the regular pipeline, exactly as the SVG and PPTX exporters do.

The page is drawn in a top-down coordinate system (origin at the top-left, y
increasing downward) by flipping reportlab's native bottom-up axes once up
front; text runs counter-flip locally so glyphs stay upright.
"""

from __future__ import annotations

import hashlib
import math
from io import BytesIO
from typing import TYPE_CHECKING

from PIL import ImageFont

from quickthumb._base import (
    apply_alignment,
    expanded_rotation_size,
    parse_coordinate,
    parse_padding,
)
from quickthumb._export_base import (
    Box,
    RasterFragment,
    TextBlockLayout,
    TextRunLayout,
    color_to_rgba,
    compute_text_layout,
    flatten_layers,
    rasterize_layers,
    split_backdrop_prefix,
)
from quickthumb.errors import RenderingError
from quickthumb.models import (
    BackgroundLayer,
    LinearGradient,
    OutlineLayer,
    RadialGradient,
    ShapeLayer,
    TextLayer,
)

if TYPE_CHECKING:
    from quickthumb.canvas import Canvas, RenderableLayer


def _require_reportlab():
    try:
        import reportlab  # noqa: F401
    except ImportError:
        raise RenderingError(
            "reportlab is required for PDF export. Install it with: pip install 'quickthumb[pdf]'"
        ) from None


class PdfExporter:
    def __init__(self, canvas: Canvas | None = None):
        _require_reportlab()
        # canvas is the single-canvas convenience target; the multi-page paths
        # take their canvases explicitly and leave this None.
        self._canvas = canvas
        self._font_names: dict[str, str] = {}  # font path -> registered reportlab name

    def export_bytes(self) -> bytes:
        buffer = BytesIO()
        self.save(buffer)
        return buffer.getvalue()

    def save(self, path_or_stream) -> None:
        if self._canvas is None:
            raise RenderingError("PdfExporter() needs a canvas for single-canvas export.")
        self.save_canvases([self._canvas], path_or_stream)

    def save_canvases(self, canvases: list[Canvas], path_or_stream) -> None:
        """Write one or more canvases to a multi-page PDF (one page per canvas)."""
        if not canvases:
            raise RenderingError("Cannot export a PDF with no pages.")
        if hasattr(path_or_stream, "write"):
            self._build(canvases, path_or_stream)
        else:
            with open(path_or_stream, "wb") as f:
                self._build(canvases, f)

    def export_bytes_canvases(self, canvases: list[Canvas]) -> bytes:
        buffer = BytesIO()
        self.save_canvases(canvases, buffer)
        return buffer.getvalue()

    def _build(self, canvases: list[Canvas], stream) -> None:
        from reportlab.pdfgen import canvas as rl_canvas

        first = canvases[0]
        pdf = rl_canvas.Canvas(stream, pagesize=(first.width, first.height))
        self._pdf = pdf
        for canvas in canvases:
            self._draw_page(canvas)
        pdf.save()

    def _draw_page(self, canvas: Canvas) -> None:
        canvas._validate_image_paths()
        canvas._ctx.begin_render_pass()
        self._canvas = canvas

        pdf = self._pdf
        pdf.setPageSize((canvas.width, canvas.height))
        # Flip to a top-left origin so canvas coordinates map straight through.
        # showPage() resets the CTM, so each page re-establishes the flip.
        pdf.translate(0, canvas.height)
        pdf.scale(1, -1)

        prefix, rest = split_backdrop_prefix(flatten_layers(canvas))
        if prefix:
            fragment = rasterize_layers(canvas, prefix)
            if fragment:
                self._draw_fragment(fragment)
        for layer in rest:
            self._emit_layer(layer)

        pdf.showPage()

    # ------------------------------------------------------------------ layers

    def _emit_layer(self, layer: RenderableLayer) -> None:
        if isinstance(layer, BackgroundLayer):
            self._emit_background(layer)
        elif isinstance(layer, OutlineLayer):
            self._emit_outline(layer)
        elif isinstance(layer, ShapeLayer):
            self._emit_shape(layer)
        elif isinstance(layer, TextLayer):
            self._emit_text(layer)
        else:  # ImageLayer, SvgLayer, CustomLayer, anything else
            self._emit_raster_fallback(layer)

    def _emit_raster_fallback(self, layer: RenderableLayer) -> None:
        fragment = rasterize_layers(self._canvas, [layer])
        if fragment:
            self._draw_fragment(fragment)

    def _draw_fragment(self, fragment: RasterFragment) -> None:
        from reportlab.lib.utils import ImageReader

        image = ImageReader(BytesIO(fragment.png_bytes))
        # drawImage expects a bottom-up box; in the flipped frame the fragment's
        # top-left is its origin, so place it and flip the image's own height.
        self._pdf.saveState()
        self._pdf.translate(fragment.x, fragment.y + fragment.height)
        self._pdf.scale(1, -1)
        self._pdf.drawImage(image, 0, 0, fragment.width, fragment.height, mask="auto")
        self._pdf.restoreState()

    # -------------------------------------------------------------- background

    def _emit_background(self, layer: BackgroundLayer) -> None:
        if layer.effects or layer.image or (layer.color is None and layer.gradient is None):
            self._emit_raster_fallback(layer)
            return

        width, height = self._canvas.width, self._canvas.height
        box = (0.0, 0.0, float(width), float(height))
        if layer.color is not None:
            rgba = color_to_rgba(self._canvas, layer.color, layer.opacity)
            self._fill_rect(box, rgba)
            return

        assert layer.gradient is not None  # guarded above
        # PDF shadings cannot express per-stop or uniform transparency, so a
        # translucent gradient falls back to a pixel-exact raster fragment.
        if layer.opacity < 1 or not self._gradient_is_opaque(layer.gradient):
            self._emit_raster_fallback(layer)
            return
        self._fill_gradient(layer.gradient, box)

    def _gradient_is_opaque(self, gradient: LinearGradient | RadialGradient) -> bool:
        return all(color_to_rgba(self._canvas, color)[3] == 255 for color, _ in gradient.stops)

    # ----------------------------------------------------------------- outline

    def _emit_outline(self, layer: OutlineLayer) -> None:
        canvas = self._canvas
        rgba = color_to_rgba(canvas, layer.color, layer.opacity)
        inset = layer.offset + layer.width / 2
        width = canvas.width - 2 * layer.offset - layer.width
        height = canvas.height - 2 * layer.offset - layer.width

        pdf = self._pdf
        pdf.saveState()
        self._set_stroke(rgba, layer.width)
        pdf.rect(inset, inset, width, height, fill=0, stroke=1)
        pdf.restoreState()

    # ------------------------------------------------------------------ shapes

    def _emit_shape(self, layer: ShapeLayer) -> None:
        if layer.effects:
            # Strokes, glows, and shadows have no faithful PDF vector form here.
            self._emit_raster_fallback(layer)
            return

        canvas = self._canvas
        x = parse_coordinate(layer.position[0], canvas.width)
        y = parse_coordinate(layer.position[1], canvas.height)
        width, height = layer.width, layer.height

        expanded = expanded_rotation_size((width, height), layer.rotation)
        paste_x, paste_y = (x, y)
        if layer.align:
            paste_x, paste_y = apply_alignment(x, y, expanded, layer.align)
        center_x = paste_x + expanded[0] / 2
        center_y = paste_y + expanded[1] / 2

        rgba = color_to_rgba(canvas, layer.color, layer.opacity)
        pdf = self._pdf
        pdf.saveState()
        pdf.translate(center_x, center_y)
        if layer.rotation:
            # Canvas rotation is clockwise-positive, which matches the flipped frame.
            pdf.rotate(layer.rotation)
        self._set_fill(rgba)
        self._shape_path(layer)
        pdf.restoreState()

    def _shape_path(self, layer: ShapeLayer) -> None:
        """Draw the shape centered on the current (already translated) origin."""
        pdf = self._pdf
        width, height = layer.width, layer.height
        left, top = -width / 2, -height / 2

        if layer.shape == "rectangle":
            if layer.border_radius:
                pdf.roundRect(left, top, width, height, layer.border_radius, fill=1, stroke=0)
            else:
                pdf.rect(left, top, width, height, fill=1, stroke=0)
            return
        if layer.shape == "ellipse":
            pdf.ellipse(left, top, left + width, top + height, fill=1, stroke=0)
            return
        if layer.shape == "pill":
            pdf.roundRect(left, top, width, height, min(width, height) / 2, fill=1, stroke=0)
            return

        normalized = self._canvas._shapes.normalized_shape_points(layer)
        if not normalized:
            return
        path = pdf.beginPath()
        path.moveTo(left + normalized[0][0] * width, top + normalized[0][1] * height)
        for px, py in normalized[1:]:
            path.lineTo(left + px * width, top + py * height)
        path.close()
        pdf.drawPath(path, fill=1, stroke=0)

    # -------------------------------------------------------------------- text

    def _emit_text(self, layer: TextLayer) -> None:
        layout = compute_text_layout(self._canvas, layer)
        if not any(layout.lines):
            return

        if self._text_needs_raster(layout):
            self._emit_raster_fallback(layer)
            return

        pdf = self._pdf
        pdf.saveState()
        if layout.rotation and layout.origin and layout.rot_center_local:
            origin_x, origin_y = layout.origin
            center_x, center_y = layout.rot_center_local
            pdf.translate(origin_x + center_x, origin_y + center_y)
            pdf.rotate(layout.rotation)
            pdf.translate(-center_x, -center_y)

        if layout.block_backgrounds and layout.block_bg_box:
            for background in layout.block_backgrounds:
                self._draw_text_background(background, layout.block_bg_box, layout.opacity)
        for line in layout.lines:
            for run in line:
                for background in run.backgrounds:
                    if run.bg_box:
                        self._draw_text_background(background, run.bg_box, layout.opacity)
                self._draw_text_run(run, layout.opacity)
        pdf.restoreState()

    @staticmethod
    def _text_needs_raster(layout: TextBlockLayout) -> bool:
        """Blur effects and non-solid glyph fills cannot be drawn as vector text."""
        for line in layout.lines:
            for run in line:
                if run.fill is not None or run.strokes or run.shadows or run.glows:
                    return True
        return False

    def _draw_text_background(self, background, content_box: Box, layer_opacity: float) -> None:
        pad_top, pad_right, pad_bottom, pad_left = parse_padding(background.padding)
        box = (
            content_box[0] - pad_left,
            content_box[1] - pad_top,
            content_box[2] + pad_right,
            content_box[3] + pad_bottom,
        )
        rgba = color_to_rgba(self._canvas, background.color, background.opacity * layer_opacity)
        self._fill_rect(box, rgba, radius=background.border_radius)

    def _draw_text_run(self, run: TextRunLayout, layer_opacity: float) -> None:
        rgba = run.color
        alpha = (rgba[3] / 255) * layer_opacity
        color_alpha = (rgba[0], rgba[1], rgba[2], int(round(alpha * 255)))
        font_name = self._register_font(run)

        self._set_fill(color_alpha)
        pdf = self._pdf
        pdf.saveState()
        pdf.setFont(font_name, run.size)
        # Counter-flip once so glyphs render upright in the top-down page frame;
        # in this flipped space a baseline at page-y sits at -y.
        pdf.scale(1, -1)
        if run.char_xs is not None:
            for char, char_x in zip(run.text, run.char_xs, strict=True):
                pdf.drawString(char_x, -run.baseline_y, char)
        else:
            pdf.drawString(run.pen_x, -run.baseline_y, run.text)
        pdf.restoreState()

    def _register_font(self, run: TextRunLayout) -> str:
        font = run.font
        path = getattr(font, "path", None) if isinstance(font, ImageFont.FreeTypeFont) else None
        if not isinstance(path, str):
            return "Helvetica"
        cached = self._font_names.get(path)
        if cached:
            return cached

        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        # A stable, path-derived name keeps the reportlab global font registry
        # collision-free and order-independent across exports in one process.
        name = "qt-" + hashlib.md5(path.encode("utf-8")).hexdigest()[:16]
        if name not in pdfmetrics.getRegisteredFontNames():
            try:
                pdfmetrics.registerFont(TTFont(name, path))
            except Exception:  # noqa: BLE001 - fall back to a core font on any load error
                return "Helvetica"
        self._font_names[path] = name
        return name

    # ----------------------------------------------------------------- drawing

    def _fill_rect(self, box: Box, rgba: tuple, radius: float = 0) -> None:
        left, top, right, bottom = box
        width, height = right - left, bottom - top
        pdf = self._pdf
        pdf.saveState()
        self._set_fill(rgba)
        if radius:
            pdf.roundRect(left, top, width, height, radius, fill=1, stroke=0)
        else:
            pdf.rect(left, top, width, height, fill=1, stroke=0)
        pdf.restoreState()

    def _fill_gradient(self, gradient: LinearGradient | RadialGradient, box: Box) -> None:
        left, top, right, bottom = box
        width, height = right - left, bottom - top
        stops = sorted(gradient.stops, key=lambda stop: stop[1])
        positions = [max(0.0, min(1.0, position)) for _, position in stops]
        # This path only runs for fully opaque gradients, so alpha is dropped.
        colors = [self._rl_color(color_to_rgba(self._canvas, color)[:3]) for color, _ in stops]

        pdf = self._pdf
        pdf.saveState()
        clip = pdf.beginPath()
        clip.rect(left, top, width, height)
        pdf.clipPath(clip, fill=0, stroke=0)

        center_x, center_y = left + width / 2, top + height / 2
        if isinstance(gradient, LinearGradient):
            diagonal = math.ceil(math.hypot(width, height))
            theta = math.radians(gradient.angle)
            dx, dy = math.cos(theta), math.sin(theta)
            pdf.linearGradient(
                center_x - dx * diagonal / 2,
                center_y - dy * diagonal / 2,
                center_x + dx * diagonal / 2,
                center_y + dy * diagonal / 2,
                colors,
                positions,
                extend=True,
            )
        else:
            focus_x = left + width * gradient.center[0]
            focus_y = top + height * gradient.center[1]
            max_dist = max(
                math.hypot(focus_x - left, focus_y - top),
                math.hypot(right - focus_x, focus_y - top),
                math.hypot(focus_x - left, bottom - focus_y),
                math.hypot(right - focus_x, bottom - focus_y),
            )
            pdf.radialGradient(
                focus_x,
                focus_y,
                max_dist * math.sqrt(2),
                colors,
                positions,
                extend=True,
            )
        pdf.restoreState()

    def _rl_color(self, rgba: tuple):
        from reportlab.lib.colors import Color

        r, g, b = rgba[0], rgba[1], rgba[2]
        a = rgba[3] / 255 if len(rgba) > 3 else 1.0
        return Color(r / 255, g / 255, b / 255, alpha=a)

    def _set_fill(self, rgba: tuple) -> None:
        self._pdf.setFillColor(self._rl_color(rgba))

    def _set_stroke(self, rgba: tuple, width: float) -> None:
        self._pdf.setStrokeColor(self._rl_color(rgba))
        self._pdf.setLineWidth(width)
