import math
import os
from collections.abc import Callable

from PIL import Image, ImageChops, ImageEnhance, ImageFilter

from quickthumb._base import DEFAULT_TEXT_COLOR, FULL_OPACITY, CanvasBase
from quickthumb.errors import RenderingError
from quickthumb.models import BlendMode, Filter, Grain


class EffectsMixin(CanvasBase):
    def _parse_color(self, color: str | tuple) -> tuple[int, ...]:
        if isinstance(color, tuple):
            return color

        hex_color = color.lstrip("#")

        if len(hex_color) == 6:
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            return (r, g, b)

        if len(hex_color) == 8:
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            a = int(hex_color[6:8], 16)
            return (r, g, b, a)

        return DEFAULT_TEXT_COLOR

    def _apply_opacity(self, image: Image.Image, opacity: float) -> Image.Image:
        if opacity == 1.0:
            return image

        if image.mode != "RGBA":
            image = image.convert("RGBA")
        alpha = image.split()[3]
        alpha = alpha.point(lambda x: int(x * opacity))
        image.putalpha(alpha)
        return image

    def _apply_brightness(self, image: Image.Image, brightness: float) -> Image.Image:
        if brightness == 1.0:
            return image

        enhancer = ImageEnhance.Brightness(image)
        return enhancer.enhance(brightness)

    def _apply_blur(self, image: Image.Image, radius: int) -> Image.Image:
        alpha = image.split()[3] if image.mode == "RGBA" else None
        blurred = image.filter(ImageFilter.GaussianBlur(radius=radius))
        if alpha is not None and blurred.mode == "RGBA":
            blurred.putalpha(alpha)
        return blurred

    def _apply_contrast(self, image: Image.Image, contrast: float) -> Image.Image:
        enhancer = ImageEnhance.Contrast(image)
        return enhancer.enhance(contrast)

    def _apply_saturation(self, image: Image.Image, saturation: float) -> Image.Image:
        enhancer = ImageEnhance.Color(image)
        return enhancer.enhance(saturation)

    def _apply_filter(self, image: Image.Image, effect: Filter) -> Image.Image:
        if effect.brightness != 1.0:
            image = self._apply_brightness(image, effect.brightness)
        if effect.blur > 0:
            image = self._apply_blur(image, effect.blur)
        if effect.contrast != 1.0:
            image = self._apply_contrast(image, effect.contrast)
        if effect.saturation != 1.0:
            image = self._apply_saturation(image, effect.saturation)
        return image

    @staticmethod
    def _generate_noise_image(
        size: tuple[int, int],
        intensity: float,
        monochrome: bool,
        seed: int | None,
    ) -> Image.Image | None:
        import random as _random

        pixel_count = size[0] * size[1]
        max_val = int(intensity * 255)

        if max_val == 0:
            return None

        lut = bytes(i * max_val // 255 for i in range(256))

        if seed is not None:
            rng = _random.Random(seed)
            if monochrome:
                raw = rng.randbytes(pixel_count)
            else:
                raw_r, raw_g, raw_b = (
                    rng.randbytes(pixel_count),
                    rng.randbytes(pixel_count),
                    rng.randbytes(pixel_count),
                )
        else:
            if monochrome:
                raw = os.urandom(pixel_count)
            else:
                raw_r, raw_g, raw_b = (
                    os.urandom(pixel_count),
                    os.urandom(pixel_count),
                    os.urandom(pixel_count),
                )

        if monochrome:
            ch = Image.frombytes("L", size, raw).point(lut)
            noise_img = Image.merge("RGB", [ch, ch, ch])
        else:
            noise_img = Image.merge(
                "RGB",
                [
                    Image.frombytes("L", size, raw_r).point(lut),
                    Image.frombytes("L", size, raw_g).point(lut),
                    Image.frombytes("L", size, raw_b).point(lut),
                ],
            )
        return noise_img.convert("RGBA")

    def _blend_grain(
        self,
        image: Image.Image,
        intensity: float,
        monochrome: bool,
        seed: int | None,
        blend_mode: str,
        opacity: float,
    ) -> Image.Image:
        if opacity == 0.0:
            return image
        noise = self._generate_noise_image(image.size, intensity, monochrome, seed)
        if noise is None:
            return image
        r, g, b, original_alpha = image.split()
        blended = self._apply_blend_mode(image, noise, blend_mode)
        br, bg, bb, _ = blended.split()
        if opacity < 1.0:
            br = Image.blend(r, br, opacity)
            bg = Image.blend(g, bg, opacity)
            bb = Image.blend(b, bb, opacity)
        return Image.merge("RGBA", (br, bg, bb, original_alpha))

    def _apply_grain(self, image: Image.Image, effect: Grain) -> Image.Image:
        return self._blend_grain(
            image,
            effect.intensity,
            effect.monochrome,
            effect.seed,
            effect.blend_mode,
            effect.opacity,
        )

    def _apply_opacity_to_color(self, color: tuple[int, ...], opacity: float) -> tuple[int, ...]:
        r, g, b = color[:3]

        if len(color) == 3:
            alpha = int(FULL_OPACITY * opacity)
            return (r, g, b, alpha)

        existing_alpha = color[3]
        alpha = int(existing_alpha * opacity)
        return (r, g, b, alpha)

    def _create_gradient_lut(
        self, stops: list[tuple[str, float]]
    ) -> tuple[list[int], list[int], list[int], list[int]]:
        r_lut, g_lut, b_lut, a_lut = [], [], [], []

        parsed_stops = []
        for color, pos in stops:
            parsed_color = self._parse_color(color)
            # Ensure color has alpha channel (default to 255 if not provided)
            if len(parsed_color) == 3:
                parsed_color = (*parsed_color, 255)
            parsed_stops.append((parsed_color, pos))

        parsed_stops.sort(key=lambda stop: stop[1])

        for i in range(256):
            pos = i / 255.0

            color1, pos1 = parsed_stops[0]
            color2, pos2 = parsed_stops[-1]

            if pos <= pos1:
                r, g, b, a = color1[:4]
            elif pos >= pos2:
                r, g, b, a = color2[:4]
            else:
                for j in range(len(parsed_stops) - 1):
                    c1, p1 = parsed_stops[j]
                    c2, p2 = parsed_stops[j + 1]
                    if p1 <= pos <= p2:
                        ratio = (pos - p1) / (p2 - p1) if p2 != p1 else 0
                        r = int(c1[0] + (c2[0] - c1[0]) * ratio)
                        g = int(c1[1] + (c2[1] - c1[1]) * ratio)
                        b = int(c1[2] + (c2[2] - c1[2]) * ratio)
                        a = int(c1[3] + (c2[3] - c1[3]) * ratio)
                        break

            r_lut.append(r)
            g_lut.append(g)
            b_lut.append(b)
            a_lut.append(a)

        return r_lut, g_lut, b_lut, a_lut

    def _create_linear_gradient(
        self, size: tuple[int, int], angle: float, stops: list[tuple[str, float]]
    ) -> Image.Image:
        width, height = size

        diagonal = int(math.ceil(math.sqrt(width**2 + height**2)))

        gradient_mask = Image.linear_gradient("L")
        gradient_mask = gradient_mask.resize((diagonal, diagonal))
        # Rotate. Image.linear_gradient is vertical (top-to-bottom).
        # Angle 0 in our API is horizontal (left-to-right).
        # So we need to rotate -90 degrees to get horizontal, then add user angle.
        # Note: PIL rotate is counter-clockwise.
        gradient_mask = gradient_mask.rotate(90 - angle, expand=False)

        left = (diagonal - width) // 2
        top = (diagonal - height) // 2
        gradient_mask = gradient_mask.crop((left, top, left + width, top + height))

        r_lut, g_lut, b_lut, a_lut = self._create_gradient_lut(stops)
        r = gradient_mask.point(r_lut)
        g = gradient_mask.point(g_lut)
        b = gradient_mask.point(b_lut)
        a = gradient_mask.point(a_lut)

        return Image.merge("RGBA", (r, g, b, a))

    def _create_radial_gradient(
        self, size: tuple[int, int], stops: list[tuple[str, float]], center: tuple[float, float]
    ) -> Image.Image:
        width, height = size

        cx, cy = center

        center_x_px = width * cx
        center_y_px = height * cy

        dist_tl = math.sqrt(center_x_px**2 + center_y_px**2)
        dist_tr = math.sqrt((width - center_x_px) ** 2 + center_y_px**2)
        dist_bl = math.sqrt(center_x_px**2 + (height - center_y_px) ** 2)
        dist_br = math.sqrt((width - center_x_px) ** 2 + (height - center_y_px) ** 2)
        max_dist_px = max(dist_tl, dist_tr, dist_bl, dist_br)

        grad_size = int(2 * max_dist_px)
        gradient_mask = Image.radial_gradient("L")
        gradient_mask = gradient_mask.resize((grad_size, grad_size))

        grad_center = grad_size // 2
        left = grad_center - int(center_x_px)
        top = grad_center - int(center_y_px)

        gradient_mask = gradient_mask.crop((left, top, left + width, top + height))

        r_lut, g_lut, b_lut, a_lut = self._create_gradient_lut(stops)
        r = gradient_mask.point(r_lut)
        g = gradient_mask.point(g_lut)
        b = gradient_mask.point(b_lut)
        a = gradient_mask.point(a_lut)

        return Image.merge("RGBA", (r, g, b, a))

    def _apply_blend_func(
        self,
        base: Image.Image,
        overlay: Image.Image,
        blend_func: Callable[[Image.Image, Image.Image], Image.Image],
    ) -> Image.Image:
        base_rgb = Image.new("RGB", base.size)
        base_rgb.paste(base, mask=base.split()[3])

        overlay_rgb = Image.new("RGB", overlay.size)
        overlay_rgb.paste(overlay, mask=overlay.split()[3])

        blended_rgb = blend_func(base_rgb, overlay_rgb)

        base_alpha = base.split()[3]
        overlay_alpha = overlay.split()[3]
        combined_alpha = ImageChops.lighter(base_alpha, overlay_alpha)

        result = blended_rgb.convert("RGBA")
        result.putalpha(combined_alpha)

        return result

    def _apply_blend_mode(
        self, base: Image.Image, overlay: Image.Image, blend_mode: BlendMode | str
    ) -> Image.Image:
        if base.size != overlay.size:
            overlay = overlay.resize(base.size)
        if base.mode != "RGBA":
            base = base.convert("RGBA")
        if overlay.mode != "RGBA":
            overlay = overlay.convert("RGBA")

        blend_mode_enum = blend_mode
        if isinstance(blend_mode_enum, str):
            try:
                blend_mode_enum = BlendMode(blend_mode_enum)
            except ValueError:
                raise RenderingError(f"Unsupported blend mode: {blend_mode}") from None

        if blend_mode_enum == BlendMode.MULTIPLY:
            return self._apply_blend_func(base, overlay, ImageChops.multiply)
        elif blend_mode_enum == BlendMode.OVERLAY:
            if hasattr(ImageChops, "overlay"):
                return self._apply_blend_func(base, overlay, ImageChops.overlay)
            return self._blend_manually(base, overlay)
        elif blend_mode_enum == BlendMode.SCREEN:
            return self._apply_blend_func(base, overlay, ImageChops.screen)
        elif blend_mode_enum == BlendMode.DARKEN:
            return self._apply_blend_func(base, overlay, ImageChops.darker)
        elif blend_mode_enum == BlendMode.LIGHTEN:
            return self._apply_blend_func(base, overlay, ImageChops.lighter)
        elif blend_mode_enum == BlendMode.NORMAL:
            result = base.copy()
            result.alpha_composite(overlay)
            return result

        raise RenderingError(f"Unsupported blend mode: {blend_mode_enum}")

    def _blend_manually(self, base: Image.Image, overlay: Image.Image) -> Image.Image:
        base_data = base.load()
        if base_data is None:
            raise RenderingError("Failed to load base image")
        overlay_data = overlay.load()
        if overlay_data is None:
            raise RenderingError("Failed to load overlay image")
        result = Image.new("RGBA", base.size)
        result_data = result.load()
        if result_data is None:
            raise RenderingError("Failed to load result image")

        for y in range(base.size[1]):
            for x in range(base.size[0]):
                base_pixel = base_data[x, y]
                overlay_pixel = overlay_data[x, y]

                if isinstance(base_pixel, int | float):
                    raise RenderingError("Base pixel is a float")
                if isinstance(overlay_pixel, int | float):
                    raise RenderingError("Overlay pixel is a float")

                r = self._overlay_channel(base_pixel[0], overlay_pixel[0])
                g = self._overlay_channel(base_pixel[1], overlay_pixel[1])
                b = self._overlay_channel(base_pixel[2], overlay_pixel[2])
                a = overlay_pixel[3] if len(overlay_pixel) > 3 else 255

                result_data[x, y] = (r, g, b, a)

        return result

    def _overlay_channel(self, base_val: int, overlay_val: int) -> int:
        base_norm = base_val / 255
        overlay_norm = overlay_val / 255
        if base_norm < 0.5:
            result = 2 * base_norm * overlay_norm
        else:
            result = 1 - 2 * (1 - base_norm) * (1 - overlay_norm)
        return int(result * 255)
