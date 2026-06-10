from io import BytesIO
from typing import cast
from urllib.request import urlopen

from PIL import Image, ImageDraw, ImageFilter

from quickthumb._effects import EffectsMixin
from quickthumb.errors import RenderingError
from quickthumb.models import (
    Align,
    Filter,
    FitMode,
    Glow,
    Grain,
    ImageLayer,
    Shadow,
    Stroke,
    SvgLayer,
)


class ImagesMixin(EffectsMixin):
    def _parse_coordinate(self, value: int | str, dimension: int) -> int:
        if isinstance(value, int):
            return value

        percentage = float(value.rstrip("%"))
        return int(dimension * percentage / 100)

    def _is_url(self, path: str) -> bool:
        return path.startswith("http://") or path.startswith("https://")

    def _load_image_from_url(self, url: str) -> Image.Image:
        with urlopen(url) as response:
            image_data = response.read()
        return Image.open(BytesIO(image_data))

    def _load_and_fit_image(
        self, image_path: str, canvas_size: tuple[int, int], fit: FitMode | str | None
    ) -> Image.Image:
        if self._is_url(image_path):
            img = self._load_image_from_url(image_path)
        else:
            img = Image.open(image_path)

        img = img.convert("RGBA")
        canvas_width, canvas_height = canvas_size
        img_width, img_height = img.size

        if fit is None or fit == FitMode.FILL:
            return img.resize(canvas_size)

        if fit == FitMode.COVER:
            scale = max(canvas_width / img_width, canvas_height / img_height)
            new_width = int(img_width * scale)
            new_height = int(img_height * scale)
            resized = img.resize((new_width, new_height))

            left = (new_width - canvas_width) // 2
            top = (new_height - canvas_height) // 2
            return resized.crop((left, top, left + canvas_width, top + canvas_height))

        scale = min(canvas_width / img_width, canvas_height / img_height)
        new_width = int(img_width * scale)
        new_height = int(img_height * scale)
        resized = img.resize((new_width, new_height))

        result = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
        paste_x = (canvas_width - new_width) // 2
        paste_y = (canvas_height - new_height) // 2
        result.paste(resized, (paste_x, paste_y))
        return result

    def _render_image_layer(self, image: Image.Image, layer: ImageLayer):
        # Load the image
        if self._is_url(layer.path):
            img = self._load_image_from_url(layer.path)
        else:
            img = Image.open(layer.path)

        img = img.convert("RGBA")

        if layer.remove_background:
            img = self._remove_background(img)

        if layer.width or layer.height:
            img = self._resize_image(img, layer.width, layer.height, layer.fit)

        if layer.border_radius > 0:
            img = self._apply_border_radius(img, layer.border_radius)

        self._composite_overlay_layer(image, img, layer)

    def _render_svg_layer(self, image: Image.Image, layer: SvgLayer):
        img = self._rasterize_svg(layer)
        self._composite_overlay_layer(image, img, layer)

    def _rasterize_svg(self, layer: SvgLayer) -> Image.Image:
        try:
            import cairosvg
        except ImportError:
            raise RenderingError(
                "cairosvg is required for SVG layers. "
                "Install it with: pip install 'quickthumb[svg]'"
            ) from None

        size_kwargs: dict[str, int] = {}
        if layer.width:
            size_kwargs["output_width"] = layer.width
        if layer.height:
            size_kwargs["output_height"] = layer.height

        try:
            png_bytes = cairosvg.svg2png(url=layer.path, **size_kwargs)
        except Exception as e:
            raise RenderingError(f"Failed to rasterize SVG '{layer.path}': {e}") from e

        return Image.open(BytesIO(png_bytes)).convert("RGBA")

    def _composite_overlay_layer(
        self, image: Image.Image, img: Image.Image, layer: ImageLayer | SvgLayer
    ):
        """Apply rotation, opacity, alignment, effects, and blending shared by overlay layers."""
        if layer.rotation != 0:
            scale = 4
            large = img.resize((img.width * scale, img.height * scale), Image.Resampling.LANCZOS)
            large = large.rotate(-layer.rotation, expand=True, resample=Image.Resampling.BICUBIC)
            img = large.resize(
                (round(large.width / scale), round(large.height / scale)),
                Image.Resampling.LANCZOS,
            )

        if layer.opacity < 1.0:
            img = self._apply_opacity(img, layer.opacity)

        x = self._parse_coordinate(layer.position[0], self.width)
        y = self._parse_coordinate(layer.position[1], self.height)

        if layer.align is not None and layer.align != Align.TOP_LEFT:
            x, y = self._apply_image_alignment(x, y, img.size, layer.align)

        for effect in layer.effects:
            if isinstance(effect, Filter):
                img = self._apply_filter(img, effect)
            elif isinstance(effect, Grain):
                img = self._apply_grain(img, effect)

        for effect in layer.effects:
            if isinstance(effect, Glow):
                self._apply_image_glow(image, img, x, y, effect)
            elif isinstance(effect, Shadow):
                self._apply_image_shadow(image, img, x, y, effect)

        for effect in layer.effects:
            if isinstance(effect, Stroke):
                self._apply_image_stroke(image, img, x, y, effect)

        if layer.blend_mode:
            overlay_layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
            overlay_layer.alpha_composite(img, (x, y))
            blended = self._apply_blend_mode(image, overlay_layer, layer.blend_mode)
            image.paste(blended, (0, 0), overlay_layer.split()[3])
        else:
            image.alpha_composite(img, (x, y))

    def _apply_image_shadow(
        self, canvas: Image.Image, img: Image.Image, x: int, y: int, shadow: Shadow
    ):
        """Composite a drop shadow for img onto canvas, placed behind the image."""
        alpha = img.split()[3]
        shadow_color = self._parse_color(shadow.color)

        blur = shadow.blur_radius
        if blur > 0:
            # Pad the shadow canvas by 2× the blur radius so GaussianBlur can spread
            # freely in all directions without being clipped to the shape bounding box.
            pad = blur * 2
            padded_size = (img.width + pad * 2, img.height + pad * 2)
            padded_alpha = Image.new("L", padded_size, 0)
            padded_alpha.paste(alpha, (pad, pad))
            shadow_img = Image.new("RGBA", padded_size, shadow_color)
            shadow_img.putalpha(padded_alpha)
            shadow_img = shadow_img.filter(ImageFilter.GaussianBlur(blur))
            sx = x + shadow.offset_x - pad
            sy = y + shadow.offset_y - pad
        else:
            shadow_img = Image.new("RGBA", img.size, shadow_color)
            shadow_img.putalpha(alpha)
            sx = x + shadow.offset_x
            sy = y + shadow.offset_y
        src_x = max(0, -sx)
        src_y = max(0, -sy)
        dst_x = max(0, sx)
        dst_y = max(0, sy)
        w = min(shadow_img.width - src_x, canvas.width - dst_x)
        h = min(shadow_img.height - src_y, canvas.height - dst_y)
        if w > 0 and h > 0:
            patch = shadow_img.crop((src_x, src_y, src_x + w, src_y + h))
            canvas.alpha_composite(patch, (dst_x, dst_y))

    def _apply_image_stroke(
        self, canvas: Image.Image, img: Image.Image, x: int, y: int, stroke: Stroke
    ):
        """Composite a stroke border around the alpha shape of img onto canvas."""
        alpha = img.split()[3]
        w = stroke.width

        # Pad the alpha with zeros so MaxFilter can dilate beyond the image edges
        padding = w + 1
        padded_size = (img.width + padding * 2, img.height + padding * 2)
        padded_alpha = Image.new("L", padded_size, 0)
        padded_alpha.paste(alpha, (padding, padding))

        expanded = padded_alpha.filter(ImageFilter.MaxFilter(w * 2 + 1))

        stroke_color = self._parse_color(stroke.color)
        stroke_layer = Image.new("RGBA", padded_size, stroke_color)
        stroke_layer.putalpha(expanded)

        sx = x - padding
        sy = y - padding
        src_x = max(0, -sx)
        src_y = max(0, -sy)
        dst_x = max(0, sx)
        dst_y = max(0, sy)
        ww = min(stroke_layer.width - src_x, canvas.width - dst_x)
        hh = min(stroke_layer.height - src_y, canvas.height - dst_y)
        if ww > 0 and hh > 0:
            patch = stroke_layer.crop((src_x, src_y, src_x + ww, src_y + hh))
            canvas.alpha_composite(patch, (dst_x, dst_y))

    def _apply_image_glow(self, canvas: Image.Image, img: Image.Image, x: int, y: int, glow: Glow):
        """Composite a blurred glow halo around the alpha shape of img onto canvas."""
        alpha = img.split()[3]
        padding = glow.radius * 3

        padded_size = (img.width + padding * 2, img.height + padding * 2)
        mask = Image.new("L", padded_size, 0)
        mask.paste(alpha, (padding, padding))
        mask = mask.filter(ImageFilter.GaussianBlur(glow.radius))

        if glow.opacity < 1.0:
            mask = mask.point(lambda v: int(v * glow.opacity))

        glow_color = self._parse_color(glow.color)
        glow_layer = Image.new("RGBA", padded_size, glow_color)
        glow_layer.putalpha(mask)

        sx = x - padding
        sy = y - padding
        src_x = max(0, -sx)
        src_y = max(0, -sy)
        dst_x = max(0, sx)
        dst_y = max(0, sy)
        ww = min(glow_layer.width - src_x, canvas.width - dst_x)
        hh = min(glow_layer.height - src_y, canvas.height - dst_y)
        if ww > 0 and hh > 0:
            patch = glow_layer.crop((src_x, src_y, src_x + ww, src_y + hh))
            canvas.alpha_composite(patch, (dst_x, dst_y))

    def _apply_border_radius(self, img: Image.Image, radius: int) -> Image.Image:
        """Clip image to a rounded rectangle mask with anti-aliased corners via supersampling."""
        w, h = img.size
        scale = 4
        mask_big = Image.new("L", (w * scale, h * scale), 0)
        draw = ImageDraw.Draw(mask_big)
        draw.rounded_rectangle(
            [0, 0, w * scale - 1, h * scale - 1], radius=radius * scale, fill=255
        )
        mask = mask_big.resize((w, h), Image.Resampling.LANCZOS)
        result = img.copy()
        if result.mode != "RGBA":
            result = result.convert("RGBA")
        result.putalpha(mask)
        return result

    def _remove_background(self, img: Image.Image) -> Image.Image:
        try:
            from rembg import remove
        except ImportError:
            raise ImportError(
                "rembg is required for background removal. "
                "Install it with: pip install quickthumb[rembg]"
            ) from None
        return cast(Image.Image, remove(img))

    def _resize_image(
        self,
        img: Image.Image,
        width: int | None,
        height: int | None,
        fit: FitMode | None = None,
    ) -> Image.Image:
        """Resize image preserving aspect ratio if only one dimension specified."""
        original_width, original_height = img.size

        if width and height:
            if fit is None or fit == FitMode.FILL:
                return img.resize((width, height), Image.Resampling.LANCZOS)

            if fit == FitMode.COVER:
                scale = max(width / original_width, height / original_height)
                scaled_width = int(original_width * scale)
                scaled_height = int(original_height * scale)
                resized = img.resize((scaled_width, scaled_height), Image.Resampling.LANCZOS)
                left = (scaled_width - width) // 2
                top = (scaled_height - height) // 2
                return resized.crop((left, top, left + width, top + height))

            scale = min(width / original_width, height / original_height)
            scaled_width = int(original_width * scale)
            scaled_height = int(original_height * scale)
            resized = img.resize((scaled_width, scaled_height), Image.Resampling.LANCZOS)

            result = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            paste_x = (width - scaled_width) // 2
            paste_y = (height - scaled_height) // 2
            result.paste(resized, (paste_x, paste_y))
            return result
        elif width:
            aspect_ratio = original_height / original_width
            new_height = int(width * aspect_ratio)
            return img.resize((width, new_height), Image.Resampling.LANCZOS)
        elif height:
            aspect_ratio = original_width / original_height
            new_width = int(height * aspect_ratio)
            return img.resize((new_width, height), Image.Resampling.LANCZOS)

        return img

    def _apply_image_alignment(
        self, x: int, y: int, img_size: tuple[int, int], align: Align
    ) -> tuple[int, int]:
        """Apply alignment offset to image position.

        Args:
            x: Base x position
            y: Base y position
            img_size: (width, height) of the image
            align: Align enum value

        Returns:
            Adjusted (x, y) position
        """
        img_width, img_height = img_size
        vertical = align.vertical
        horizontal = align.horizontal

        if horizontal == "center":
            x = x - img_width // 2
        elif horizontal == "right":
            x = x - img_width

        if vertical == "middle":
            y = y - img_height // 2
        elif vertical == "bottom":
            y = y - img_height

        return x, y
