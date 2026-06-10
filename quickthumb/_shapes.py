from PIL import Image, ImageDraw

from quickthumb._text import TextMixin
from quickthumb.models import Glow, Shadow, ShapeLayer, Stroke


class ShapesMixin(TextMixin):
    def _render_shape_layer(self, image: Image.Image, layer: ShapeLayer):
        x = self._parse_coordinate(layer.position[0], self.width)
        y = self._parse_coordinate(layer.position[1], self.height)

        fill_color = self._parse_color(layer.color)

        # Draw at 4x and keep at 4x through rotation so both curved edges and
        # rotation edges are anti-aliased when downscaled with LANCZOS.
        scale = 4
        shape_w, shape_h = layer.width * scale, layer.height * scale
        shape_big = Image.new("RGBA", (shape_w, shape_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(shape_big)
        bbox = [0, 0, shape_w - 1, shape_h - 1]

        if layer.shape == "rectangle":
            draw.rounded_rectangle(bbox, radius=layer.border_radius * scale, fill=fill_color)
        else:  # ellipse
            draw.ellipse(bbox, fill=fill_color)

        if layer.rotation != 0:
            shape_big = shape_big.rotate(
                -layer.rotation, expand=True, resample=Image.Resampling.BICUBIC
            )

        final_w = round(shape_big.width / scale)
        final_h = round(shape_big.height / scale)
        shape_img = shape_big.resize((final_w, final_h), Image.Resampling.LANCZOS)

        if layer.opacity < 1.0:
            shape_img = self._apply_opacity(shape_img, layer.opacity)

        paste_x, paste_y = x, y
        if layer.align:
            paste_x, paste_y = self._apply_image_alignment(x, y, shape_img.size, layer.align)

        for effect in layer.effects:
            if isinstance(effect, Glow):
                self._apply_image_glow(image, shape_img, paste_x, paste_y, effect)
            elif isinstance(effect, Shadow):
                self._apply_image_shadow(image, shape_img, paste_x, paste_y, effect)

        for effect in layer.effects:
            if isinstance(effect, Stroke):
                self._apply_image_stroke(image, shape_img, paste_x, paste_y, effect)

        image.alpha_composite(shape_img, (paste_x, paste_y))
