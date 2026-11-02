import math
from typing import cast

from PIL import Image, ImageChops, ImageColor, ImageDraw

from quickthumb._base import RenderContext, apply_alignment, parse_coordinate
from quickthumb._effects import EffectsEngine
from quickthumb._images import ImageEngine
from quickthumb.models import (
    BackdropBlur,
    Glow,
    InnerShadow,
    LinearGradient,
    Shadow,
    ShapeLayer,
    Stroke,
)

TRIANGLE_POINTS = [(0.5, 0.0), (1.0, 1.0), (0.0, 1.0)]


class ShapeEngine:
    """Vector shape drawing with supersampled anti-aliasing and effects."""

    def __init__(self, ctx: RenderContext, effects: EffectsEngine, images: ImageEngine):
        self._ctx = ctx
        self._effects = effects
        self._images = images

    def _gradient_fill(self, fill, shape: Image.Image) -> Image.Image:
        """Paint a gradient through a drawn shape's alpha."""
        if isinstance(fill, LinearGradient):
            gradient = self._effects.create_linear_gradient(shape.size, fill.angle, fill.stops)
        else:
            gradient = self._effects.create_radial_gradient(shape.size, fill.stops, fill.center)
        gradient.putalpha(ImageChops.multiply(gradient.getchannel("A"), shape.getchannel("A")))
        return gradient

    def render_shape_layer(self, image: Image.Image, layer: ShapeLayer):
        x = parse_coordinate(layer.position[0], self._ctx.width)
        y = parse_coordinate(layer.position[1], self._ctx.height)

        # A gradient fill is painted through the shape's own alpha, so the shape
        # is drawn opaque first and tinted afterwards.
        fill_color = (
            (255, 255, 255, 255)
            if layer.fill is not None
            else self._effects.parse_color(layer.color)
        )

        # Draw at 4x and keep at 4x through rotation so both curved edges and
        # rotation edges are anti-aliased when downscaled with LANCZOS.
        scale = 4
        shape_w, shape_h = layer.width * scale, layer.height * scale
        shape_big = Image.new("RGBA", (shape_w, shape_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(shape_big)
        bbox = [0, 0, shape_w - 1, shape_h - 1]

        if layer.shape == "rectangle":
            draw.rounded_rectangle(bbox, radius=layer.border_radius * scale, fill=fill_color)
        elif layer.shape == "ellipse":
            draw.ellipse(bbox, fill=fill_color)
        elif layer.shape == "pill":
            draw.rounded_rectangle(bbox, radius=min(shape_w, shape_h) // 2, fill=fill_color)
        else:
            normalized = self.normalized_shape_points(layer)
            pixel_points = [(px * (shape_w - 1), py * (shape_h - 1)) for px, py in normalized]
            draw.polygon(pixel_points, fill=fill_color)

        if layer.fill is not None:
            # Tint before rotation so the gradient turns with the shape.
            shape_big = self._gradient_fill(layer.fill, shape_big)

        if layer.rotation != 0:
            shape_big = shape_big.rotate(
                -layer.rotation, expand=True, resample=Image.Resampling.BICUBIC
            )

        final_w = round(shape_big.width / scale)
        final_h = round(shape_big.height / scale)
        shape_img = shape_big.resize((final_w, final_h), Image.Resampling.LANCZOS)

        if layer.opacity < 1.0:
            shape_img = self._effects.apply_opacity(shape_img, layer.opacity)

        paste_x, paste_y = x, y
        if layer.align:
            paste_x, paste_y = apply_alignment(x, y, shape_img.size, layer.align)

        for effect in layer.effects:
            if isinstance(effect, InnerShadow):
                shape_img = self._effects.apply_inner_shadow(shape_img, effect)

        for effect in layer.effects:
            if isinstance(effect, BackdropBlur):
                self._images.apply_backdrop_blur(image, shape_img, paste_x, paste_y, effect)

        for effect in layer.effects:
            if isinstance(effect, Glow):
                self._images.apply_image_glow(image, shape_img, paste_x, paste_y, effect)
            elif isinstance(effect, Shadow):
                self._images.apply_image_shadow(image, shape_img, paste_x, paste_y, effect)

        for effect in layer.effects:
            if isinstance(effect, Stroke):
                if layer.shape in {"polygon", "star", "triangle"}:
                    self._render_polygon_stroke(image, layer, shape_img, paste_x, paste_y, effect)
                else:
                    self._images.apply_image_stroke(image, shape_img, paste_x, paste_y, effect)

        image.alpha_composite(shape_img, (paste_x, paste_y))

    def _render_polygon_stroke(self, image, layer, shape_img, x, y, stroke):
        """Paint an outside polygon border with bounded miter joins."""
        from quickthumb._path_geometry import _Contour
        from quickthumb._paths import stroke_mask

        padding = stroke.width * 4 + 3
        width, height = layer.width + padding * 2, layer.height + padding * 2
        mask = Image.new("1", (width * 4, height * 4))
        points = tuple(
            (px * (layer.width - 0.25), py * (layer.height - 0.25))
            for px, py in self.normalized_shape_points(layer)
        )
        contour = _Contour(points, closed=True)
        bounds = (-padding, -padding, layer.width + padding, layer.height + padding)
        stroke_mask(mask, (contour,), stroke.width * 2, (1, 1), bounds)
        ImageDraw.Draw(mask).polygon(
            [((px + padding) * 4, (py + padding) * 4) for px, py in points], fill=1
        )
        rgba = cast(tuple[int, int, int, int], ImageColor.getcolor(stroke.color, "RGBA"))
        border = Image.new("RGBA", mask.size, rgba)
        border.putalpha(mask.convert("L"))
        if layer.rotation:
            border = border.rotate(-layer.rotation, expand=True, resample=Image.Resampling.BICUBIC)
        border = border.resize(
            (round(border.width / 4), round(border.height / 4)), Image.Resampling.LANCZOS
        )
        opacity = layer.opacity * rgba[3] / 255
        if opacity < 1:
            border = self._effects.apply_opacity(border, opacity)
        self._images._composite_clamped(
            image,
            border,
            x + (shape_img.width - border.width) // 2,
            y + (shape_img.height - border.height) // 2,
        )

    def normalized_shape_points(self, layer: ShapeLayer) -> list[tuple[float, float]]:
        """Return shape outline points normalized to the 0..1 unit box."""
        if layer.shape == "triangle":
            return TRIANGLE_POINTS
        if layer.shape == "star":
            return self._star_points(layer.star_points, layer.inner_radius)
        return [(px, py) for px, py in layer.points or []]

    @staticmethod
    def _star_points(spikes: int, inner_radius: float) -> list[tuple[float, float]]:
        """Alternate outer/inner vertices around the unit-box center, first spike pointing up."""
        points = []
        for i in range(spikes * 2):
            radius = 0.5 if i % 2 == 0 else 0.5 * inner_radius
            angle = -math.pi / 2 + i * math.pi / spikes
            points.append((0.5 + radius * math.cos(angle), 0.5 + radius * math.sin(angle)))
        return points
