"""Deterministic raster engines for the compact data-visualization layers."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from PIL import Image, ImageDraw, ImageFont

from quickthumb._base import RenderContext, apply_alignment, parse_coordinate
from quickthumb._effects import EffectsEngine
from quickthumb.errors import RenderingError
from quickthumb.models import (
    AnimationSpec,
    BarChartSpec,
    ChartData,
    ChartLayer,
    LineChartSpec,
    QRCodeLayer,
)


@dataclass(frozen=True)
class VisualizationState:
    """Normalized, renderer-local state sampled from the shared motion timeline."""

    bar_progress: tuple[float, ...] = ()
    line_progress: float = 1.0
    area_progress: float = 1.0
    point_progress: tuple[float, ...] = ()
    value_progress: float = 1.0
    qr_module_progress: tuple[float, ...] = ()


_COMPONENT_PRESETS = frozenset(
    {"bar_grow", "line_draw", "area_reveal", "point_pop", "value_count_up", "qr_reveal"}
)


def _component_animation(animation: object, names: frozenset[str] = _COMPONENT_PRESETS):
    """Return the first canonical visualization animation from a layer input."""
    candidates = animation if isinstance(animation, list) else [animation]
    for candidate in candidates:
        if isinstance(candidate, AnimationSpec) and (
            candidate.effect is None or candidate.effect.type in names
        ):
            return candidate
    return None


def _compile_component_timeline(animation: AnimationSpec):
    """Compile one component animation lazily, avoiding the import cycle at module load."""
    from quickthumb.motion import LayerState, compile_timeline

    return compile_timeline(animation), LayerState


def _sample_component_progress(timeline, layer_state, time: float, offset: float = 0.0) -> float:
    """Sample a compiled component timeline through normalized clip progress."""
    sampled = timeline.sample(time - offset, layer_state(clip_progress=0.0))
    return min(1.0, max(0.0, sampled.clip_progress))


class VisualizationEngine:
    """Render charts and QR codes through one stable PIL path."""

    _SUPERSAMPLE = 4

    def __init__(self, ctx: RenderContext, effects: EffectsEngine):
        self._ctx = ctx
        self._effects = effects

    def render_chart(
        self, image: Image.Image, layer: ChartLayer, time: float | None = None
    ) -> None:
        """Render the chart spec selected by its discriminator."""
        state = self._chart_state(layer, time)
        if isinstance(layer.spec, BarChartSpec):
            self._render_bar_chart(image, layer, state)
        else:
            self._render_line_chart(image, layer, state)

    def _render_bar_chart(
        self, image: Image.Image, layer: ChartLayer, state: VisualizationState
    ) -> None:
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
            progress = state.bar_progress[index] if index < len(state.bar_progress) else 1.0
            value *= progress
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
            if style.show_values or self._has_value_count_up(layer.animation):
                shown_value = value / max(progress, 1e-12) * state.value_progress
                self._draw_value(
                    draw,
                    f"{shown_value:g}",
                    bar_left * self._SUPERSAMPLE,
                    max(top, bar_top) * self._SUPERSAMPLE,
                    self._rgba(style.color, layer.opacity * style.opacity),
                )

        self._composite_surface(image, surface, x, y)

    def _render_line_chart(
        self, image: Image.Image, layer: ChartLayer, state: VisualizationState
    ) -> None:
        """Render a line chart with points enabled by default."""
        self._render_line(image, layer, state)

    def render_qr_code(
        self, image: Image.Image, layer: QRCodeLayer, time: float | None = None
    ) -> None:
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
        module_progress = self._qr_state(layer, time, matrix_size).qr_module_progress
        for row, cells in enumerate(matrix):
            for column, cell in enumerate(cells):
                if not cell:
                    continue
                module_index = row * matrix_size + column
                if module_index < len(module_progress) and module_progress[module_index] <= 0:
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
        state: VisualizationState,
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

        line_progress = state.line_progress
        visible_points = self._partial_points(points, line_progress)
        if style.fill is not None and len(points) >= 2 and state.area_progress > 0:
            fill_points = self._partial_points(points, state.area_progress)
            if len(fill_points) < 2:
                fill_points = []
            if fill_points:
                fill_points += [(fill_points[-1][0], bottom), (fill_points[0][0], bottom)]
                draw.polygon(
                    self._scaled_points(fill_points),
                    fill=self._rgba(style.fill, layer.opacity * style.opacity * style.fill_opacity),
                )
        if len(visible_points) >= 2:
            draw.line(
                self._scaled_points(visible_points),
                fill=line_color,
                width=max(1, style.stroke_width * self._SUPERSAMPLE),
                joint="curve",
            )

        show_points = style.show_points
        if show_points and style.point_radius > 0:
            base_radius = style.point_radius * self._SUPERSAMPLE
            for index, (point_x, point_y) in enumerate(self._scaled_points(points)):
                progress = (
                    state.point_progress[index]
                    if index < len(state.point_progress)
                    else 1.0
                )
                if progress <= 0:
                    continue
                radius = base_radius * progress
                draw.ellipse(
                    (point_x - radius, point_y - radius, point_x + radius, point_y + radius),
                    fill=line_color,
                )

        if style.show_values or self._has_value_count_up(layer.animation):
            for index, (point_x, point_y) in enumerate(points):
                progress = state.value_progress
                shown_value = values[index] * progress
                self._draw_value(
                    draw,
                    f"{shown_value:g}",
                    point_x * self._SUPERSAMPLE,
                    point_y * self._SUPERSAMPLE,
                    line_color,
                )

        self._composite_surface(image, surface, x, y)

    def _chart_state(self, layer: ChartLayer, time: float | None) -> VisualizationState:
        values = self._chart_values(layer.spec.data)
        animation = _component_animation(layer.animation)
        if time is None or animation is None:
            return VisualizationState(
                bar_progress=(1.0,) * len(values),
                point_progress=(1.0,) * len(values),
                value_progress=1.0,
            )
        timeline, layer_state = _compile_component_timeline(animation)
        stagger = animation.stagger.delay if animation.stagger is not None else 0.0
        return VisualizationState(
            bar_progress=tuple(
                _sample_component_progress(timeline, layer_state, time, index * stagger)
                for index in range(len(values))
            )
            if animation.effect is None or animation.effect.type == "bar_grow"
            else (1.0,) * len(values),
            line_progress=(
                _sample_component_progress(timeline, layer_state, time)
                if animation.effect is None or animation.effect.type == "line_draw"
                else 1.0
            ),
            area_progress=(
                _sample_component_progress(timeline, layer_state, time)
                if animation.effect is None or animation.effect.type == "area_reveal"
                else 1.0
            ),
            point_progress=tuple(
                _sample_component_progress(timeline, layer_state, time, index * stagger)
                for index in range(len(values))
            )
            if animation.effect is None or animation.effect.type == "point_pop"
            else (1.0,) * len(values),
            value_progress=(
                _sample_component_progress(timeline, layer_state, time)
                if animation.effect is None or animation.effect.type == "value_count_up"
                else 1.0
            ),
        )

    def _qr_state(
        self, layer: QRCodeLayer, time: float | None, matrix_size: int
    ) -> VisualizationState:
        # The matrix is generated by the caller; this state only supplies a
        # deterministic row-major reveal threshold for its modules.
        animation = _component_animation(layer.animation, frozenset({"qr_reveal"}))
        if time is None or animation is None:
            return VisualizationState()
        timeline, layer_state = _compile_component_timeline(animation)
        stagger = animation.stagger.delay if animation.stagger is not None else 0.0
        count = max(1, matrix_size * matrix_size)
        progress = _sample_component_progress(timeline, layer_state, time)
        if stagger == 0:
            return VisualizationState(
                qr_module_progress=tuple(
                    1.0 if progress * count > index else 0.0 for index in range(count)
                )
            )
        return VisualizationState(qr_module_progress=tuple(
            1.0
            if _sample_component_progress(timeline, layer_state, time, index * stagger) >= 1.0
            else 0.0
            for index in range(count)
        ))

    def _has_value_count_up(self, animation: object) -> bool:
        return _component_animation(animation, frozenset({"value_count_up"})) is not None

    def _draw_value(
        self,
        draw: ImageDraw.ImageDraw,
        value: str,
        x: int,
        y: int,
        color: tuple[int, int, int, int],
    ) -> None:
        font = ImageFont.load_default(size=4 * self._SUPERSAMPLE)
        bbox = draw.textbbox((0, 0), value, font=font)
        draw.text(
            (x - (bbox[2] - bbox[0]) // 2, y - (bbox[3] - bbox[1]) - 2),
            value,
            font=font,
            fill=color,
        )

    def _partial_points(
        self, points: list[tuple[int, int]], progress: float
    ) -> list[tuple[int, int]]:
        if len(points) < 2 or progress >= 1.0:
            return points
        if progress <= 0.0:
            return []
        position = progress * (len(points) - 1)
        end = min(len(points) - 1, math.floor(position))
        visible = points[: end + 1]
        if end < len(points) - 1:
            ratio = position - end
            left, right = points[end], points[end + 1]
            visible.append((round(left[0] + (right[0] - left[0]) * ratio),
                            round(left[1] + (right[1] - left[1]) * ratio)))
        return visible

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
