"""Deterministic raster engines for the compact data-visualization layers."""

from __future__ import annotations

import math
from collections.abc import Sequence

from PIL import Image, ImageDraw

from quickthumb._base import RenderContext, apply_alignment, parse_coordinate
from quickthumb._effects import EffectsEngine
from quickthumb.errors import RenderingError
from quickthumb.models import (
    BarChartSpec,
    ChartData,
    ChartLayer,
    LineChartSpec,
    QRCodeLayer,
)


class VisualizationEngine:
    """Render charts and QR codes through one stable PIL path."""

    _SUPERSAMPLE = 4

    def __init__(self, ctx: RenderContext, effects: EffectsEngine):
        self._ctx = ctx
        self._effects = effects

    def render_chart(self, image: Image.Image, layer: ChartLayer) -> None:
        """Render the chart spec selected by its discriminator."""
        if isinstance(layer.spec, BarChartSpec):
            self._render_bar_chart(image, layer)
        else:
            self._render_line_chart(image, layer)

    def _render_bar_chart(self, image: Image.Image, layer: ChartLayer) -> None:
        """Render vertical bars against a baseline that includes zero."""
        if not isinstance(layer.spec, BarChartSpec):
            raise RenderingError("bar renderer received a non-bar chart spec")
        values = self._chart_values(layer.spec.data)
        if not values:
            return

        x, y = self._layer_origin(layer)
        width, height = layer.width, layer.height
        style = layer.spec.style
        surface = self._new_surface(width, height)
        draw = ImageDraw.Draw(surface, "RGBA")
        plot = self._plot_box(width, height, style.padding)
        if plot is None:
            return

        left, top, right, bottom = plot
        low = min(0.0, min(values))
        high = max(0.0, max(values))
        if low == high:
            return

        baseline = self._scale_value(0.0, low, high, top, bottom)
        slot = (right - left) / len(values)
        bar_width = max(1, int(round(slot * (1.0 - style.bar_gap))))
        for index, value in enumerate(values):
            bar_left = int(round(left + index * slot + (slot - bar_width) / 2))
            bar_right = bar_left + bar_width - 1
            value_y = self._scale_value(value, low, high, top, bottom)
            bar_top, bar_bottom = sorted((value_y, baseline))
            if bar_top == bar_bottom:
                continue
            color = style.negative_color if value < 0 and style.negative_color else style.color
            draw.rectangle(
                self._scaled_box(bar_left, bar_top, bar_right, bar_bottom),
                fill=self._rgba(color, layer.opacity * style.opacity),
            )

        self._composite_surface(image, surface, x, y)

    def _render_line_chart(self, image: Image.Image, layer: ChartLayer) -> None:
        """Render a line chart with points enabled by default."""
        self._render_line(image, layer)

    def render_qr_code(self, image: Image.Image, layer: QRCodeLayer) -> None:
        """Render a QR matrix with nearest-neighbour module boundaries."""
        try:
            import qrcode
            from qrcode.constants import (
                ERROR_CORRECT_H,
                ERROR_CORRECT_L,
                ERROR_CORRECT_M,
                ERROR_CORRECT_Q,
            )
        except ImportError:
            raise RenderingError(
                "qrcode is required for QR code rendering. Install quickthumb's dependencies."
            ) from None

        correction = {
            "L": ERROR_CORRECT_L,
            "M": ERROR_CORRECT_M,
            "Q": ERROR_CORRECT_Q,
            "H": ERROR_CORRECT_H,
        }[layer.error_correction]
        code = qrcode.QRCode(
            version=None,
            error_correction=correction,
            box_size=1,
            border=layer.quiet_zone,
        )
        try:
            code.add_data(layer.data, optimize=0)
            code.make(fit=True)
            matrix = code.get_matrix()
        except Exception as error:
            raise RenderingError(f"Could not render QR code: {error}") from error

        if layer.size < len(matrix):
            raise RenderingError(
                f"QR code size {layer.size} is too small for its {len(matrix)}x{len(matrix)} "
                "module matrix. Increase size or reduce the QR data/error correction."
            )

        x = parse_coordinate(layer.position[0], self._ctx.width)
        y = parse_coordinate(layer.position[1], self._ctx.height)
        if layer.align:
            x, y = apply_alignment(x, y, (layer.size, layer.size), layer.align)

        surface = Image.new("RGBA", (layer.size, layer.size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(surface, "RGBA")
        opacity = layer.opacity
        if layer.background is not None:
            draw.rectangle(
                (0, 0, layer.size - 1, layer.size - 1),
                fill=self._rgba(layer.background, opacity),
            )

        matrix_size = len(matrix)
        foreground = self._rgba(layer.foreground, opacity)
        for row, cells in enumerate(matrix):
            for column, cell in enumerate(cells):
                if not cell:
                    continue
                left = (column * layer.size) // matrix_size
                top = (row * layer.size) // matrix_size
                right = ((column + 1) * layer.size) // matrix_size
                bottom = ((row + 1) * layer.size) // matrix_size
                if right > left and bottom > top:
                    draw.rectangle((left, top, right - 1, bottom - 1), fill=foreground)

        image.alpha_composite(surface, (x, y))

    def _render_line(
        self,
        image: Image.Image,
        layer: ChartLayer,
    ) -> None:
        """Draw a line layer into an antialiased local surface."""
        if not isinstance(layer.spec, LineChartSpec):
            raise RenderingError("line renderer received a non-line chart spec")
        values = self._chart_values(layer.spec.data)
        if not values:
            return

        x, y = self._layer_origin(layer)
        style = layer.spec.style
        plot = self._plot_box(layer.width, layer.height, style.padding)
        if plot is None:
            return

        left, top, right, bottom = plot
        low, high = min(values), max(values)
        surface = self._new_surface(layer.width, layer.height)
        draw = ImageDraw.Draw(surface, "RGBA")
        points = [
            (
                self._scale_index(index, len(values), left, right),
                self._scale_value(value, low, high, top, bottom),
            )
            for index, value in enumerate(values)
        ]
        line_color = self._rgba(style.color, layer.opacity * style.opacity)

        if style.fill is not None and len(points) >= 2:
            fill_points = points + [(points[-1][0], bottom), (points[0][0], bottom)]
            draw.polygon(
                self._scaled_points(fill_points),
                fill=self._rgba(style.fill, layer.opacity * style.opacity * style.fill_opacity),
            )
        if len(points) >= 2:
            draw.line(
                self._scaled_points(points),
                fill=line_color,
                width=max(1, style.stroke_width * self._SUPERSAMPLE),
                joint="curve",
            )

        show_points = style.show_points
        if show_points and style.point_radius > 0:
            radius = style.point_radius * self._SUPERSAMPLE
            for point_x, point_y in self._scaled_points(points):
                draw.ellipse(
                    (point_x - radius, point_y - radius, point_x + radius, point_y + radius),
                    fill=line_color,
                )

        self._composite_surface(image, surface, x, y)

    def _layer_origin(self, layer: ChartLayer) -> tuple[int, int]:
        """Resolve a chart's canvas-space anchor and alignment."""
        x = parse_coordinate(layer.position[0], self._ctx.width)
        y = parse_coordinate(layer.position[1], self._ctx.height)
        if layer.align:
            return apply_alignment(x, y, (layer.width, layer.height), layer.align)
        return x, y

    def _chart_values(self, data: ChartData | Sequence[int | float]) -> list[float]:
        """Return normalized samples from a validated chart input."""
        if isinstance(data, ChartData):
            return data.values
        return [float(value) for value in data]

    def _plot_box(self, width: int, height: int, padding: int) -> tuple[int, int, int, int] | None:
        """Return an inset plot box, or no box when padding consumes the layer."""
        left, top = padding, padding
        right, bottom = width - padding - 1, height - padding - 1
        if right < left or bottom < top:
            return None
        return left, top, right, bottom

    def _scale_index(self, index: int, count: int, left: int, right: int) -> int:
        """Map a sample index across the plot width, including one-sample data."""
        if count <= 1:
            return (left + right) // 2
        return left + round(index * (right - left) / (count - 1))

    def _scale_value(self, value: float, low: float, high: float, top: int, bottom: int) -> int:
        """Map a numeric sample to a pixel, centering a constant series."""
        if low == high:
            return (top + bottom) // 2
        span = high - low
        if math.isfinite(span):
            fraction = (value - low) / span
        else:
            scale = max(abs(low), abs(high), 1.0)
            fraction = (value / scale - low / scale) / (high / scale - low / scale)
        return bottom - round(fraction * (bottom - top))

    def _new_surface(self, width: int, height: int) -> Image.Image:
        """Create a supersampled transparent layer surface."""
        scale = self._SUPERSAMPLE
        return Image.new("RGBA", (width * scale, height * scale), (0, 0, 0, 0))

    def _scaled_points(self, points: list[tuple[int, int]]) -> list[tuple[int, int]]:
        """Scale local chart coordinates for antialiased drawing."""
        return [(x * self._SUPERSAMPLE, y * self._SUPERSAMPLE) for x, y in points]

    def _scaled_box(
        self, left: int, top: int, right: int, bottom: int
    ) -> tuple[int, int, int, int]:
        """Scale an inclusive local rectangle for supersampled drawing."""
        scale = self._SUPERSAMPLE
        return left * scale, top * scale, (right + 1) * scale - 1, (bottom + 1) * scale - 1

    def _composite_surface(self, image: Image.Image, surface: Image.Image, x: int, y: int) -> None:
        """Downsample a local surface and composite it at its resolved origin."""
        size = (surface.width // self._SUPERSAMPLE, surface.height // self._SUPERSAMPLE)
        image.alpha_composite(surface.resize(size, Image.Resampling.LANCZOS), (x, y))

    def _rgba(self, color: str, opacity: float) -> tuple[int, int, int, int]:
        """Resolve a public color and multiply its alpha by layer/style opacity."""
        rgba = self._effects.parse_color(color)
        if len(rgba) == 3:
            rgba = (*rgba, 255)
        return (*rgba[:3], round(rgba[3] * opacity))
