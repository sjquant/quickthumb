from io import BytesIO
from typing import cast
from urllib.request import urlopen

from PIL import Image, ImageDraw, ImageFilter

from quickthumb._base import RenderContext, apply_alignment, is_url, parse_coordinate
from quickthumb._effects import EffectsEngine
from quickthumb.errors import RenderingError
from quickthumb.models import (
    Align,
    BackdropBlur,
    Duotone,
    Filter,
    FitMode,
    Glow,
    Grain,
    ImageLayer,
    InnerShadow,
    Shadow,
    Stroke,
    SvgLayer,
)


class ImageEngine:
    """Raster and SVG overlay loading, sizing, effects, and compositing."""

    def __init__(self, ctx: RenderContext, effects: EffectsEngine):
        self._ctx = ctx
        self._effects = effects

    def load_image_from_url(self, url: str) -> Image.Image:
        with urlopen(url) as response:
            image_data = response.read()
        return Image.open(BytesIO(image_data))

    def load_and_fit_image(
        self, image_path: str, canvas_size: tuple[int, int], fit: FitMode | str | None
    ) -> Image.Image:
        img = self.load_image_from_url(image_path) if is_url(image_path) else Image.open(image_path)

        return self._fit_image(img.convert("RGBA"), canvas_size, fit, Image.Resampling.BICUBIC)

    @staticmethod
    def _fit_image(
        img: Image.Image,
        target_size: tuple[int, int],
        fit: FitMode | str | None,
        resample: Image.Resampling,
    ) -> Image.Image:
        """Scale img into target_size using FILL (stretch), COVER (crop), or CONTAIN (pad)."""
        target_w, target_h = target_size
        src_w, src_h = img.size

        if fit is None or fit == FitMode.FILL:
            return img.resize(target_size, resample)

        if fit == FitMode.COVER:
            scale = max(target_w / src_w, target_h / src_h)
            scaled_w, scaled_h = int(src_w * scale), int(src_h * scale)
            resized = img.resize((scaled_w, scaled_h), resample)
            left = (scaled_w - target_w) // 2
            top = (scaled_h - target_h) // 2
            return resized.crop((left, top, left + target_w, top + target_h))

        scale = min(target_w / src_w, target_h / src_h)
        scaled_w, scaled_h = int(src_w * scale), int(src_h * scale)
        resized = img.resize((scaled_w, scaled_h), resample)
        result = Image.new("RGBA", target_size, (0, 0, 0, 0))
        result.paste(resized, ((target_w - scaled_w) // 2, (target_h - scaled_h) // 2))
        return result

    def render_image_layer(self, image: Image.Image, layer: ImageLayer):
        # Load the image
        img = self.load_image_from_url(layer.path) if is_url(layer.path) else Image.open(layer.path)
        self._ctx.image_size_cache.setdefault(layer.path, img.size)

        img = img.convert("RGBA")

        if layer.remove_background:
            img = self._remove_background(img)

        if layer.width or layer.height:
            img = self._resize_image(img, layer.width, layer.height, layer.fit)

        if layer.border_radius > 0:
            img = self._apply_border_radius(img, layer.border_radius)

        self._composite_overlay_layer(image, img, layer)

    def render_svg_layer(self, image: Image.Image, layer: SvgLayer):
        img = self.rasterize_svg(layer)
        self._composite_overlay_layer(image, img, layer)

    def rasterize_svg(self, layer: SvgLayer) -> Image.Image:
        """Rasterize an SVG layer, reusing the result for identical path/size within a render."""
        key = (layer.path, layer.width, layer.height)
        cached = self._ctx.svg_raster_cache.get(key)
        if cached is None:
            cached = self._ctx.svg_raster_cache[key] = self._rasterize_svg_uncached(layer)
        return cached.copy()

    def _rasterize_svg_uncached(self, layer: SvgLayer) -> Image.Image:
        try:
            import cairosvg
        except ImportError:
            raise RenderingError(
                "cairosvg is required for SVG layers. "
                "Install it with: pip install 'quickthumb[svg]'"
            ) from None

        try:
            png_bytes = cairosvg.svg2png(
                url=layer.path,
                output_width=layer.width,
                output_height=layer.height,
            )
        except Exception as e:
            raise RenderingError(f"Failed to rasterize SVG '{layer.path}': {e}") from e

        if png_bytes is None:
            raise RenderingError(f"Failed to rasterize SVG '{layer.path}': no PNG data returned")

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
            img = self._effects.apply_opacity(img, layer.opacity)

        x = parse_coordinate(layer.position[0], self._ctx.width)
        y = parse_coordinate(layer.position[1], self._ctx.height)

        if layer.align is not None and layer.align != Align.TOP_LEFT:
            x, y = apply_alignment(x, y, img.size, layer.align)

        for effect in layer.effects:
            if isinstance(effect, Filter):
                img = self._effects.apply_filter(img, effect)
            elif isinstance(effect, Grain):
                img = self._effects.apply_grain(img, effect)
            elif isinstance(effect, Duotone):
                img = self._effects.apply_duotone(img, effect)
            elif isinstance(effect, InnerShadow):
                img = self._effects.apply_inner_shadow(img, effect)

        for effect in layer.effects:
            if isinstance(effect, BackdropBlur):
                self.apply_backdrop_blur(image, img, x, y, effect)

        for effect in layer.effects:
            if isinstance(effect, Glow):
                self.apply_image_glow(image, img, x, y, effect)
            elif isinstance(effect, Shadow):
                self.apply_image_shadow(image, img, x, y, effect)

        for effect in layer.effects:
            if isinstance(effect, Stroke):
                self.apply_image_stroke(image, img, x, y, effect)

        if layer.blend_mode:
            overlay_layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
            overlay_layer.alpha_composite(img, (x, y))
            blended = self._effects.apply_blend_mode(image, overlay_layer, layer.blend_mode)
            image.paste(blended, (0, 0), overlay_layer.split()[3])
        else:
            image.alpha_composite(img, (x, y))

    @staticmethod
    def _composite_clamped(canvas: Image.Image, layer_img: Image.Image, sx: int, sy: int):
        """Composite layer_img at (sx, sy), cropping the parts that fall off the canvas."""
        src_x, src_y = max(0, -sx), max(0, -sy)
        dst_x, dst_y = max(0, sx), max(0, sy)
        w = min(layer_img.width - src_x, canvas.width - dst_x)
        h = min(layer_img.height - src_y, canvas.height - dst_y)
        if w > 0 and h > 0:
            patch = layer_img.crop((src_x, src_y, src_x + w, src_y + h))
            canvas.alpha_composite(patch, (dst_x, dst_y))

    def apply_image_shadow(
        self, canvas: Image.Image, img: Image.Image, x: int, y: int, shadow: Shadow
    ):
        """Composite a drop shadow for img onto canvas, placed behind the image."""
        alpha = img.split()[3]
        shadow_color = self._effects.parse_color(shadow.color)

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
        self._composite_clamped(canvas, shadow_img, sx, sy)

    def apply_backdrop_blur(
        self, canvas: Image.Image, img: Image.Image, x: int, y: int, effect: BackdropBlur
    ):
        """Blur already-painted canvas pixels through img's alpha mask."""
        if effect.opacity == 0.0:
            return

        src_x, src_y = max(0, -x), max(0, -y)
        dst_x, dst_y = max(0, x), max(0, y)
        width = min(img.width - src_x, canvas.width - dst_x)
        height = min(img.height - src_y, canvas.height - dst_y)
        if width <= 0 or height <= 0:
            return

        box = (dst_x, dst_y, dst_x + width, dst_y + height)
        backdrop = canvas.crop(box).filter(ImageFilter.GaussianBlur(effect.radius))
        alpha = img.split()[3].crop((src_x, src_y, src_x + width, src_y + height))
        if effect.opacity < 1.0:
            alpha = alpha.point(lambda value: int(value * effect.opacity))
        backdrop.putalpha(alpha)
        canvas.alpha_composite(backdrop, (dst_x, dst_y))

    def apply_image_stroke(
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

        stroke_color = self._effects.parse_color(stroke.color)
        stroke_layer = Image.new("RGBA", padded_size, stroke_color)
        stroke_layer.putalpha(expanded)

        self._composite_clamped(canvas, stroke_layer, x - padding, y - padding)

    def apply_image_glow(self, canvas: Image.Image, img: Image.Image, x: int, y: int, glow: Glow):
        """Composite a blurred glow halo around the alpha shape of img onto canvas."""
        alpha = img.split()[3]
        padding = glow.radius * 3

        padded_size = (img.width + padding * 2, img.height + padding * 2)
        mask = Image.new("L", padded_size, 0)
        mask.paste(alpha, (padding, padding))
        mask = mask.filter(ImageFilter.GaussianBlur(glow.radius))

        if glow.opacity < 1.0:
            mask = mask.point(lambda v: int(v * glow.opacity))

        glow_color = self._effects.parse_color(glow.color)
        glow_layer = Image.new("RGBA", padded_size, glow_color)
        glow_layer.putalpha(mask)

        self._composite_clamped(canvas, glow_layer, x - padding, y - padding)

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
            from rembg import remove  # type: ignore[unresolved-import]
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
            return self._fit_image(img, (width, height), fit, Image.Resampling.LANCZOS)
        elif width:
            aspect_ratio = original_height / original_width
            new_height = int(width * aspect_ratio)
            return img.resize((width, new_height), Image.Resampling.LANCZOS)
        elif height:
            aspect_ratio = original_width / original_height
            new_width = int(height * aspect_ratio)
            return img.resize((new_width, height), Image.Resampling.LANCZOS)

        return img
