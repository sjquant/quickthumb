"""Shared image effects, color utilities, gradients, and blending operations.

These are pure functions with no state — they can be reused by any renderer
(single-frame Canvas, Deck slides, video frames, etc.).
"""

import math
import os
from collections.abc import Callable
from io import BytesIO
from typing import cast
from urllib.request import urlopen

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter

from quickthumb.errors import RenderingError
from quickthumb.models import Align, BlendMode, Filter, FitMode, Glow, Grain, Shadow, Stroke

FULL_OPACITY = 255

# ---------------------------------------------------------------------------
# Color helpers
# ---------------------------------------------------------------------------

_DEFAULT_COLOR = (0, 0, 0)


def parse_color(color: str | tuple) -> tuple[int, ...]:
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

    return _DEFAULT_COLOR


def apply_opacity_to_color(color: tuple[int, ...], opacity: float) -> tuple[int, ...]:
    r, g, b = color[:3]

    if len(color) == 3:
        alpha = int(FULL_OPACITY * opacity)
        return (r, g, b, alpha)

    existing_alpha = color[3]
    alpha = int(existing_alpha * opacity)
    return (r, g, b, alpha)


# ---------------------------------------------------------------------------
# Basic image adjustments
# ---------------------------------------------------------------------------


def apply_opacity(image: Image.Image, opacity: float) -> Image.Image:
    if opacity == 1.0:
        return image

    alpha = image.split()[3]
    alpha = alpha.point(lambda x: int(x * opacity))
    image.putalpha(alpha)
    return image


def apply_brightness(image: Image.Image, brightness: float) -> Image.Image:
    if brightness == 1.0:
        return image

    enhancer = ImageEnhance.Brightness(image)
    return enhancer.enhance(brightness)


def apply_blur(image: Image.Image, radius: int) -> Image.Image:
    alpha = image.split()[3] if image.mode == "RGBA" else None
    blurred = image.filter(ImageFilter.GaussianBlur(radius=radius))
    if alpha is not None and blurred.mode == "RGBA":
        blurred.putalpha(alpha)
    return blurred


def apply_contrast(image: Image.Image, contrast: float) -> Image.Image:
    enhancer = ImageEnhance.Contrast(image)
    return enhancer.enhance(contrast)


def apply_saturation(image: Image.Image, saturation: float) -> Image.Image:
    enhancer = ImageEnhance.Color(image)
    return enhancer.enhance(saturation)


def apply_filter(image: Image.Image, effect: Filter) -> Image.Image:
    if effect.brightness != 1.0:
        image = apply_brightness(image, effect.brightness)
    if effect.blur > 0:
        image = apply_blur(image, effect.blur)
    if effect.contrast != 1.0:
        image = apply_contrast(image, effect.contrast)
    if effect.saturation != 1.0:
        image = apply_saturation(image, effect.saturation)
    return image


# ---------------------------------------------------------------------------
# Grain / noise
# ---------------------------------------------------------------------------


def generate_noise_image(
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


def blend_grain(
    image: Image.Image,
    intensity: float,
    monochrome: bool,
    seed: int | None,
    blend_mode: str,
    opacity: float,
) -> Image.Image:
    if opacity == 0.0:
        return image
    noise = generate_noise_image(image.size, intensity, monochrome, seed)
    if noise is None:
        return image
    r, g, b, original_alpha = image.split()
    blended = apply_blend_mode(image, noise, blend_mode)
    br, bg, bb, _ = blended.split()
    if opacity < 1.0:
        br = Image.blend(r, br, opacity)
        bg = Image.blend(g, bg, opacity)
        bb = Image.blend(b, bb, opacity)
    return Image.merge("RGBA", (br, bg, bb, original_alpha))


def apply_grain(image: Image.Image, effect: Grain) -> Image.Image:
    return blend_grain(
        image,
        effect.intensity,
        effect.monochrome,
        effect.seed,
        effect.blend_mode,
        effect.opacity,
    )


# ---------------------------------------------------------------------------
# Gradients
# ---------------------------------------------------------------------------


def create_gradient_lut(
    stops: list[tuple[str, float]],
) -> tuple[list[int], list[int], list[int], list[int]]:
    r_lut, g_lut, b_lut, a_lut = [], [], [], []

    parsed_stops = []
    for color, pos in stops:
        parsed_color = parse_color(color)
        if len(parsed_color) == 3:
            parsed_color = (*parsed_color, 255)
        parsed_stops.append((parsed_color, pos))

    for i in range(256):
        pos = i / 255.0

        color1, pos1 = parsed_stops[0]
        color2, pos2 = parsed_stops[-1]

        if pos <= pos1:
            r, g, b, a = color1[:4]
        elif pos >= pos2:
            r, g, b, a = color2[:4]
        else:
            r, g, b, a = color2[:4]  # fallback; overwritten below
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


def create_linear_gradient(
    size: tuple[int, int], angle: float, stops: list[tuple[str, float]]
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

    r_lut, g_lut, b_lut, a_lut = create_gradient_lut(stops)
    r = gradient_mask.point(r_lut)
    g = gradient_mask.point(g_lut)
    b = gradient_mask.point(b_lut)
    a = gradient_mask.point(a_lut)

    return Image.merge("RGBA", (r, g, b, a))


def create_radial_gradient(
    size: tuple[int, int], stops: list[tuple[str, float]], center: tuple[float, float]
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

    r_lut, g_lut, b_lut, a_lut = create_gradient_lut(stops)
    r = gradient_mask.point(r_lut)
    g = gradient_mask.point(g_lut)
    b = gradient_mask.point(b_lut)
    a = gradient_mask.point(a_lut)

    return Image.merge("RGBA", (r, g, b, a))


# ---------------------------------------------------------------------------
# Blending
# ---------------------------------------------------------------------------


def overlay_channel(base_val: int, overlay_val: int) -> int:
    base_norm = base_val / 255
    overlay_norm = overlay_val / 255
    if base_norm < 0.5:
        result = 2 * base_norm * overlay_norm
    else:
        result = 1 - 2 * (1 - base_norm) * (1 - overlay_norm)
    return int(result * 255)


def blend_manually(base: Image.Image, overlay: Image.Image) -> Image.Image:
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

            r = overlay_channel(base_pixel[0], overlay_pixel[0])
            g = overlay_channel(base_pixel[1], overlay_pixel[1])
            b = overlay_channel(base_pixel[2], overlay_pixel[2])
            a = overlay_pixel[3] if len(overlay_pixel) > 3 else 255

            result_data[x, y] = (r, g, b, a)

    return result


def apply_blend_func(
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


def apply_blend_mode(
    base: Image.Image, overlay: Image.Image, blend_mode: BlendMode | str
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
        return apply_blend_func(base, overlay, ImageChops.multiply)
    elif blend_mode_enum == BlendMode.OVERLAY:
        if hasattr(ImageChops, "overlay"):
            return apply_blend_func(base, overlay, ImageChops.overlay)
        return blend_manually(base, overlay)
    elif blend_mode_enum == BlendMode.SCREEN:
        return apply_blend_func(base, overlay, ImageChops.screen)
    elif blend_mode_enum == BlendMode.DARKEN:
        return apply_blend_func(base, overlay, ImageChops.darker)
    elif blend_mode_enum == BlendMode.LIGHTEN:
        return apply_blend_func(base, overlay, ImageChops.lighter)
    elif blend_mode_enum == BlendMode.NORMAL:
        result = base.copy()
        result.alpha_composite(overlay)
        return result

    raise RenderingError(f"Unsupported blend mode: {blend_mode_enum}")


# ---------------------------------------------------------------------------
# Image loading & fitting
# ---------------------------------------------------------------------------


def is_url(path: str) -> bool:
    return path.startswith("http://") or path.startswith("https://")


def load_image_from_url(url: str) -> Image.Image:
    with urlopen(url) as response:
        image_data = response.read()
    return Image.open(BytesIO(image_data))


def load_and_fit_image(
    image_path: str, canvas_size: tuple[int, int], fit: FitMode | str | None
) -> Image.Image:
    if is_url(image_path):
        img = load_image_from_url(image_path)
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


def resize_image(
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


def apply_border_radius(img: Image.Image, radius: int) -> Image.Image:
    """Clip image to a rounded rectangle mask with anti-aliased corners via supersampling."""
    w, h = img.size
    scale = 4
    mask_big = Image.new("L", (w * scale, h * scale), 0)
    draw = ImageDraw.Draw(mask_big)
    draw.rounded_rectangle([0, 0, w * scale - 1, h * scale - 1], radius=radius * scale, fill=255)
    mask = mask_big.resize((w, h), Image.Resampling.LANCZOS)
    result = img.copy()
    if result.mode != "RGBA":
        result = result.convert("RGBA")
    result.putalpha(mask)
    return result


# ---------------------------------------------------------------------------
# Coordinate & padding parsing
# ---------------------------------------------------------------------------


def parse_coordinate(value: int | str, dimension: int) -> int:
    if isinstance(value, int):
        return value

    percentage = float(value.rstrip("%"))
    return int(dimension * percentage / 100)


def parse_padding(
    padding: int | tuple[int, int] | tuple[int, int, int, int],
) -> tuple[int, int, int, int]:
    """Parse padding value into (top, right, bottom, left) tuple."""
    if isinstance(padding, int):
        return (padding, padding, padding, padding)
    elif isinstance(padding, tuple) and len(padding) == 2:
        padding_2 = cast(tuple[int, int], padding)
        vertical, horizontal = padding_2
        return (vertical, horizontal, vertical, horizontal)
    else:  # len(padding) == 4
        return cast(tuple[int, int, int, int], padding)


# ---------------------------------------------------------------------------
# Image-layer effects (shadow, stroke, glow, alignment)
# ---------------------------------------------------------------------------


def apply_image_alignment(
    x: int, y: int, img_size: tuple[int, int], align: Align
) -> tuple[int, int]:
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


def apply_image_shadow(
    canvas: Image.Image, img: Image.Image, x: int, y: int, shadow: Shadow
) -> None:
    """Composite a drop shadow for img onto canvas, placed behind the image."""
    alpha = img.split()[3]
    shadow_color = parse_color(shadow.color)

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


def apply_image_stroke(
    canvas: Image.Image, img: Image.Image, x: int, y: int, stroke: Stroke
) -> None:
    """Composite a stroke border around the alpha shape of img onto canvas."""
    alpha = img.split()[3]
    w = stroke.width

    # Pad the alpha with zeros so MaxFilter can dilate beyond the image edges
    padding = w + 1
    padded_size = (img.width + padding * 2, img.height + padding * 2)
    padded_alpha = Image.new("L", padded_size, 0)
    padded_alpha.paste(alpha, (padding, padding))

    expanded = padded_alpha.filter(ImageFilter.MaxFilter(w * 2 + 1))

    stroke_color = parse_color(stroke.color)
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


def apply_image_glow(canvas: Image.Image, img: Image.Image, x: int, y: int, glow: Glow) -> None:
    """Composite a blurred glow halo around the alpha shape of img onto canvas."""
    alpha = img.split()[3]
    padding = glow.radius * 3

    padded_size = (img.width + padding * 2, img.height + padding * 2)
    mask = Image.new("L", padded_size, 0)
    mask.paste(alpha, (padding, padding))
    mask = mask.filter(ImageFilter.GaussianBlur(glow.radius))

    if glow.opacity < 1.0:
        mask = mask.point(lambda v: int(v * glow.opacity))

    glow_color = parse_color(glow.color)
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
