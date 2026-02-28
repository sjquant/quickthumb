import contextlib
import hashlib
import math
import os
import warnings
from collections.abc import Callable
from io import BytesIO
from typing import Literal, TypedDict, cast
from urllib.request import urlopen

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from typing_extensions import Self

from quickthumb.errors import RenderingError, ValidationError
from quickthumb.font_cache import FontCache
from quickthumb.models import (
    Align,
    Background,
    BackgroundEffect,
    BackgroundLayer,
    BlendMode,
    CanvasModel,
    Filter,
    FitMode,
    Glow,
    ImageEffect,
    ImageLayer,
    LayerType,
    LinearGradient,
    OutlineLayer,
    RadialGradient,
    Shadow,
    ShapeEffect,
    ShapeLayer,
    Stroke,
    TextEffect,
    TextLayer,
    TextPart,
)

FileFormat = Literal["JPEG", "WEBP", "PNG"]

DEFAULT_TEXT_SIZE = 16
DEFAULT_TEXT_COLOR = (0, 0, 0)
DEFAULT_LINE_HEIGHT_MULTIPLIER = 1.2
FULL_OPACITY = 255
LINE_HEIGHT_REFERENCE = "Aby"

FontType = ImageFont.FreeTypeFont | ImageFont.ImageFont


class TextPartData(TypedDict):
    color: tuple[int, int, int]
    font_name: str
    size: int
    bold: bool
    italic: bool
    weight: int | str | None
    line_height_multiplier: float
    letter_spacing: int
    stroke_effects: list[Stroke]
    shadow_effects: list[Shadow]
    glow_effects: list[Glow]
    background_effects: list[Background]
    text: str


class TextPartMetadata(TypedDict):
    font: FontType
    width: int


class Canvas:
    def __init__(self, width: int, height: int, layers: list[LayerType] | None = None):
        if width <= 0:
            raise ValidationError("width must be > 0")
        if height <= 0:
            raise ValidationError("height must be > 0")

        self.width = width
        self.height = height
        self._layers: list[LayerType] = layers or []

    @property
    def layers(self) -> list[LayerType]:
        return self._layers

    @classmethod
    def from_aspect_ratio(cls, ratio: str, base_width: int) -> Self:
        width_ratio, height_ratio = ratio.split(":")
        calculated_height = int(base_width * int(height_ratio) / int(width_ratio))
        return cls(base_width, calculated_height)

    def background(
        self,
        color: str | tuple | None = None,
        gradient: LinearGradient | RadialGradient | None = None,
        image: str | None = None,
        opacity: float = 1.0,
        blend_mode: BlendMode | str | None = None,
        fit: FitMode | str | None = None,
        effects: list[BackgroundEffect] | None = None,
    ) -> Self:
        layer = BackgroundLayer(
            type="background",
            color=color,
            gradient=gradient,
            image=image,
            opacity=opacity,
            blend_mode=blend_mode,  # type: ignore
            fit=fit,  # type: ignore
            effects=effects or [],
        )
        self._layers.append(layer)
        return self

    def text(
        self,
        content: str | list[TextPart] | None = None,
        font: str | None = None,
        size: int | None = None,
        color: str | None = None,
        position: (
            tuple[int, int] | tuple[str, str] | tuple[int, str] | tuple[str, int] | None
        ) = None,
        align: Align | str | tuple[str, str] | None = None,
        bold: bool = False,
        italic: bool = False,
        weight: int | str | None = None,
        max_width: int | str | None = None,
        effects: list | None = None,
        line_height: float | None = None,
        letter_spacing: int | None = None,
        auto_scale: bool = False,
        rotation: float = 0,
        opacity: float = 1.0,
    ) -> Self:
        if content is None:
            raise ValidationError("content is required")

        layer = TextLayer(
            type="text",
            content=content,
            font=font,
            size=size,
            color=color,
            position=position,
            align=align,  # type: ignore[arg-type]  # Pydantic validator handles conversion
            bold=bold,
            italic=italic,
            weight=weight,
            max_width=max_width,
            effects=effects or [],
            line_height=line_height,
            letter_spacing=letter_spacing,
            auto_scale=auto_scale,
            rotation=rotation,
            opacity=opacity,
        )
        self._layers.append(layer)
        return self

    def outline(self, width: int, color: str, offset: int = 0, opacity: float = 1.0) -> Self:
        layer = OutlineLayer(
            type="outline",
            width=width,
            color=color,
            offset=offset,
            opacity=opacity,
        )
        self._layers.append(layer)
        return self

    def shape(
        self,
        shape: Literal["rectangle", "ellipse"],
        position: tuple,
        width: int,
        height: int,
        color: str,
        border_radius: int = 0,
        opacity: float = 1.0,
        rotation: float = 0.0,
        align: Align | str | tuple[str, str] | None = None,
        effects: list[ShapeEffect] | None = None,
    ) -> Self:
        layer = ShapeLayer(
            type="shape",
            shape=shape,
            position=position,
            width=width,
            height=height,
            color=color,
            border_radius=border_radius,
            opacity=opacity,
            rotation=rotation,
            align=align,  # type: ignore[arg-type]  # Pydantic validator handles conversion
            effects=effects or [],
        )
        self._layers.append(layer)
        return self

    def image(
        self,
        path: str,
        position: tuple[int, int] | tuple[str, str] | tuple[int, str] | tuple[str, int],
        width: int | None = None,
        height: int | None = None,
        opacity: float = 1.0,
        rotation: float = 0.0,
        align: Align | str | tuple[str, str] = Align.TOP_LEFT,
        remove_background: bool = False,
        border_radius: int = 0,
        effects: list[ImageEffect] | None = None,
    ) -> Self:
        """Add an image overlay layer to the canvas.

        Args:
            path: Local file path or URL to the image
            position: (x, y) position in pixels or percentages (e.g., (50, 100) or ("50%", "50%"))
            width: Image width in pixels (preserves aspect ratio if height is None)
            height: Image height in pixels (preserves aspect ratio if width is None)
            opacity: Image opacity from 0.0 (transparent) to 1.0 (opaque)
            rotation: Rotation angle in degrees
            align: Image alignment, accepts:
                   - Align enum (e.g., Align.CENTER, Align.TOP_LEFT)
                   - String shortcut (e.g., "center", "top-left", "bottom-right")
                   - Tuple (horizontal, vertical) (e.g., ("center", "middle"))

        Returns:
            Self for method chaining
        """
        layer = ImageLayer(
            type="image",
            path=path,
            position=position,  # Pydantic validator handles conversion
            width=width,
            height=height,
            opacity=opacity,
            rotation=rotation,
            remove_background=remove_background,
            align=align,  # type: ignore[arg-type]  # Pydantic validator handles conversion
            border_radius=border_radius,
            effects=effects or [],
        )
        self._layers.append(layer)
        return self

    def render(
        self,
        output_path: str,
        format: FileFormat | None = None,
        quality: int | None = None,
    ):
        self._validate_image_paths()
        image = self._render_to_image()
        self._save_to_file(image, output_path, quality, format=format)

    def to_json(self) -> str:
        return CanvasModel(
            width=self.width, height=self.height, layers=self._layers
        ).model_dump_json()

    @classmethod
    def from_json(cls, data: str) -> Self:
        canvas_model = CanvasModel.model_validate_json(data)
        return cls(width=canvas_model.width, height=canvas_model.height, layers=canvas_model.layers)

    def to_base64(self, format: FileFormat = "PNG", quality: int | None = None) -> str:
        import base64

        self._validate_image_paths()
        image = self._render_to_image()
        converted_image = self._convert_for_format(image, format)
        save_kwargs = self._build_save_kwargs(format, quality)

        buffer = BytesIO()
        converted_image.save(buffer, format=format, **save_kwargs)
        buffer.seek(0)

        return base64.b64encode(buffer.read()).decode("utf-8")

    def to_data_url(self, format: FileFormat = "PNG", quality: int | None = None) -> str:
        mime_types: dict[FileFormat, str] = {
            "PNG": "image/png",
            "JPEG": "image/jpeg",
            "WEBP": "image/webp",
        }

        base64_data = self.to_base64(format=format, quality=quality)
        mime_type = mime_types[format]

        return f"data:{mime_type};base64,{base64_data}"

    def _create_canvas(self) -> Image.Image:
        return Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))

    def _render_to_image(self) -> Image.Image:
        image = self._create_canvas()

        for layer in self._layers:
            if isinstance(layer, BackgroundLayer):
                self._render_background_layer(image, layer)
            elif isinstance(layer, TextLayer):
                self._render_text_layer(image, layer)
            elif isinstance(layer, OutlineLayer):
                self._render_outline_layer(image, layer)
            elif isinstance(layer, ImageLayer):
                self._render_image_layer(image, layer)
            elif isinstance(layer, ShapeLayer):
                self._render_shape_layer(image, layer)

        return image

    def _save_to_file(
        self,
        image: Image.Image,
        output_path: str,
        quality: int | None = None,
        format: FileFormat | None = None,
    ):
        file_format = format or self._detect_format(output_path)
        converted_image = self._convert_for_format(image, file_format)
        save_kwargs = self._build_save_kwargs(file_format, quality)

        converted_image.save(output_path, format=file_format, **save_kwargs)

    def _build_save_kwargs(self, file_format: FileFormat, quality: int | None) -> dict:
        if quality is None:
            return {}

        if file_format in ("JPEG", "WEBP"):
            return {"quality": quality}

        raise RenderingError(
            f"Quality parameter is only supported for JPEG and WEBP formats, not {file_format}."
        )

    def _validate_image_paths(self):
        for layer in self._layers:
            if (
                isinstance(layer, BackgroundLayer)
                and layer.image
                and not self._is_url(layer.image)
                and not os.path.exists(layer.image)
            ):
                raise FileNotFoundError(f"{layer.image}")
            elif (
                isinstance(layer, ImageLayer)
                and not self._is_url(layer.path)
                and not os.path.exists(layer.path)
            ):
                raise FileNotFoundError(f"{layer.path}")

    def _detect_format(self, output_path: str) -> FileFormat:
        extension = os.path.splitext(output_path)[1].lower()
        format_map: dict[str, FileFormat] = {
            ".png": "PNG",
            ".jpg": "JPEG",
            ".jpeg": "JPEG",
            ".webp": "WEBP",
        }
        try:
            return format_map[extension]
        except KeyError:
            raise RenderingError(
                f"Unsupported file format: {extension}.\nSupported formats: {format_map.keys()}."
            ) from None

    def _convert_for_format(self, image: Image.Image, file_format: FileFormat) -> Image.Image:
        if file_format == "JPEG":
            rgb_image = Image.new("RGB", image.size, (255, 255, 255))
            rgb_image.paste(image, mask=image.split()[3] if image.mode == "RGBA" else None)
            return rgb_image
        return image

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

    def _render_background_layer(self, image: Image.Image, layer: BackgroundLayer):
        layer_image = self._create_layer_image(image.size, layer)
        if not layer_image:
            return

        for effect in layer.effects:
            layer_image = self._apply_filter(layer_image, effect)

        if layer.opacity < 1.0 and not layer.color:
            layer_image = self._apply_opacity(layer_image, layer.opacity)

        if layer.blend_mode:
            blended = self._apply_blend_mode(image, layer_image, layer.blend_mode)
            image.paste(blended, (0, 0))
        else:
            image.alpha_composite(layer_image)

    def _create_layer_image(
        self, size: tuple[int, int], layer: BackgroundLayer
    ) -> Image.Image | None:
        if layer.color:
            color = self._parse_color(layer.color)
            if layer.opacity < 1.0:
                color = self._apply_opacity_to_color(color, layer.opacity)
            return Image.new("RGBA", size, color)

        if layer.gradient:
            if isinstance(layer.gradient, LinearGradient):
                return self._create_linear_gradient(
                    size, layer.gradient.angle, layer.gradient.stops
                )
            if isinstance(layer.gradient, RadialGradient):
                return self._create_radial_gradient(
                    size, layer.gradient.stops, layer.gradient.center
                )

        if layer.image:
            return self._load_and_fit_image(layer.image, size, layer.fit)

        return None

    def _apply_opacity(self, image: Image.Image, opacity: float) -> Image.Image:
        if opacity == 1.0:
            return image

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

    def _apply_opacity_to_color(self, color: tuple[int, ...], opacity: float) -> tuple[int, ...]:
        r, g, b = color[:3]

        if len(color) == 3:
            alpha = int(FULL_OPACITY * opacity)
            return (r, g, b, alpha)

        existing_alpha = color[3]
        alpha = int(existing_alpha * opacity)
        return (r, g, b, alpha)

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

    def _render_outline_layer(self, image: Image.Image, layer: OutlineLayer):
        draw = ImageDraw.Draw(image)
        color = self._parse_color(layer.color)
        if layer.opacity < 1.0:
            color = self._apply_opacity_to_color(color, layer.opacity)

        x1 = layer.offset
        y1 = layer.offset
        x2 = self.width - layer.offset - 1
        y2 = self.height - layer.offset - 1

        for i in range(layer.width):
            draw.rectangle([x1 + i, y1 + i, x2 - i, y2 - i], outline=color)

    def _render_shape_layer(self, image: Image.Image, layer: ShapeLayer):
        x = self._parse_coordinate(layer.position[0], self.width)
        y = self._parse_coordinate(layer.position[1], self.height)

        fill_color = self._parse_color(layer.color)

        # Draw shape on a temp image (shape-sized) so rotation/opacity work cleanly
        shape_img = Image.new("RGBA", (layer.width, layer.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(shape_img)
        bbox = [0, 0, layer.width - 1, layer.height - 1]

        if layer.shape == "rectangle":
            draw.rounded_rectangle(bbox, radius=layer.border_radius, fill=fill_color)
        else:  # ellipse
            draw.ellipse(bbox, fill=fill_color)

        if layer.rotation != 0:
            shape_img = shape_img.rotate(
                -layer.rotation, expand=True, resample=Image.Resampling.BICUBIC
            )

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
            img = self._resize_image(img, layer.width, layer.height)

        if layer.border_radius > 0:
            img = self._apply_border_radius(img, layer.border_radius)

        if layer.rotation != 0:
            img = img.rotate(-layer.rotation, expand=True, resample=Image.Resampling.BICUBIC)

        if layer.opacity < 1.0:
            img = self._apply_opacity(img, layer.opacity)

        x = self._parse_coordinate(layer.position[0], self.width)
        y = self._parse_coordinate(layer.position[1], self.height)

        if layer.align is not None and layer.align != Align.TOP_LEFT:
            x, y = self._apply_image_alignment(x, y, img.size, layer.align)

        for effect in layer.effects:
            if isinstance(effect, Filter):
                img = self._apply_filter(img, effect)

        for effect in layer.effects:
            if isinstance(effect, Glow):
                self._apply_image_glow(image, img, x, y, effect)
            elif isinstance(effect, Shadow):
                self._apply_image_shadow(image, img, x, y, effect)

        for effect in layer.effects:
            if isinstance(effect, Stroke):
                self._apply_image_stroke(image, img, x, y, effect)

        image.alpha_composite(img, (x, y))

    def _apply_image_shadow(
        self, canvas: Image.Image, img: Image.Image, x: int, y: int, shadow: Shadow
    ):
        """Composite a drop shadow for img onto canvas, placed behind the image."""
        alpha = img.split()[3]
        shadow_color = self._parse_color(shadow.color)
        shadow_img = Image.new("RGBA", img.size, shadow_color)
        shadow_img.putalpha(alpha)

        if shadow.blur_radius > 0:
            shadow_img = shadow_img.filter(ImageFilter.GaussianBlur(shadow.blur_radius))

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
        """Clip image to a rounded rectangle mask."""
        w, h = img.size
        mask = Image.new("L", (w, h), 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle([0, 0, w - 1, h - 1], radius=radius, fill=255)
        result = img.copy()
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

    def _resize_image(self, img: Image.Image, width: int | None, height: int | None) -> Image.Image:
        """Resize image preserving aspect ratio if only one dimension specified."""
        original_width, original_height = img.size

        if width and height:
            return img.resize((width, height), Image.Resampling.LANCZOS)
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

    def _render_text_layer(self, image: Image.Image, layer: TextLayer):
        if layer.opacity < 1.0:
            temp = Image.new("RGBA", image.size, (0, 0, 0, 0))
            if isinstance(layer.content, list):
                self._render_rich_text(temp, layer)
            else:
                self._render_simple_text(temp, layer)
            self._apply_opacity(temp, layer.opacity)
            image.alpha_composite(temp)
        elif isinstance(layer.content, list):
            self._render_rich_text(image, layer)
        else:
            self._render_simple_text(image, layer)

    def _find_max_fitting_size(self, max_size: int, fits: Callable[[int], bool]) -> int:
        """Binary search for the largest font size in [1, max_size] where fits() returns True."""
        best = 1
        lo, hi = 1, max_size
        while lo <= hi:
            mid = (lo + hi) // 2
            if fits(mid):
                best = mid
                lo = mid + 1
            else:
                hi = mid - 1
        return best

    def _auto_scale_simple_text(self, layer: TextLayer) -> TextLayer:
        assert layer.max_width is not None
        max_width_px = self._parse_coordinate(layer.max_width, self.width)
        base_size = layer.size or DEFAULT_TEXT_SIZE
        content = layer.content if isinstance(layer.content, str) else ""

        def fits(size: int) -> bool:
            font = self._load_font_variant(layer.font, size, layer.bold, layer.italic, layer.weight)
            lines = self._wrap_text(content, font, max_width_px, layer.letter_spacing)
            return all(
                self._measure_text_bounds(line, font, layer.letter_spacing or 0)[0] <= max_width_px
                for line in lines
            )

        best_size = self._find_max_fitting_size(base_size, fits)
        return layer.model_copy(update={"size": best_size})

    def _scale_rich_text_parts(self, layer: TextLayer, scale_factor: float) -> list[TextPart]:
        return [
            part.model_copy(
                update={"size": max(1, int(self._resolve_size(part, layer) * scale_factor))}
            )
            for part in cast(list[TextPart], layer.content)
        ]

    def _measure_rich_line_width(self, line_parts: list[TextPartData]) -> int:
        width = 0
        for part in line_parts:
            font = self._load_font_variant(
                part["font_name"], part["size"], part["bold"], part["italic"], part["weight"]
            )
            w, _ = self._measure_text_bounds(part["text"], font, part["letter_spacing"])
            width += w
        return width

    def _auto_scale_rich_text(self, layer: TextLayer) -> TextLayer:
        assert layer.max_width is not None
        max_width_px = self._parse_coordinate(layer.max_width, self.width)
        base_size = layer.size or DEFAULT_TEXT_SIZE

        def fits(size: int) -> bool:
            scaled_parts = self._scale_rich_text_parts(layer, size / base_size)
            temp_layer = layer.model_copy(update={"content": scaled_parts, "size": size})
            lines = self._prepare_rich_text_lines(temp_layer)
            return all(
                self._measure_rich_line_width(line_parts) <= max_width_px for line_parts in lines
            )

        best_size = self._find_max_fitting_size(base_size, fits)
        final_parts = self._scale_rich_text_parts(layer, best_size / base_size)
        return layer.model_copy(update={"content": final_parts, "size": best_size})

    def _render_simple_text(self, image: Image.Image, layer: TextLayer):
        # Apply auto-scaling if enabled
        if layer.auto_scale and layer.max_width:
            layer = self._auto_scale_simple_text(layer)

        # If rotation is needed, render to temporary image first
        if layer.rotation != 0:
            self._render_rotated_simple_text(image, layer)
            return

        draw = ImageDraw.Draw(image)
        font = self._load_font(layer)
        color = self._parse_color(layer.color) if layer.color else DEFAULT_TEXT_COLOR
        content = layer.content if isinstance(layer.content, str) else ""

        stroke_effects = self._get_stroke_effects(layer.effects)
        shadow_effects = self._get_shadow_effects(layer.effects)
        glow_effects = self._get_glow_effects(layer.effects)
        background_effects = self._get_background_effects(layer.effects)

        if layer.max_width:
            max_width_px = self._parse_coordinate(layer.max_width, self.width)
            lines = self._wrap_text(content, font, max_width_px, layer.letter_spacing)
            self._render_multiline_text(draw, lines, font, color, layer, image)
        elif "\n" in content:
            lines = content.split("\n")
            self._render_multiline_text(draw, lines, font, color, layer, image)
        elif layer.letter_spacing:
            self._render_letter_spaced_text(
                draw,
                image,
                content,
                font,
                color,
                layer,
                glow_effects,
                shadow_effects,
                stroke_effects,
                background_effects,
            )
        else:
            self._render_normal_text(
                draw,
                image,
                content,
                font,
                color,
                layer,
                glow_effects,
                shadow_effects,
                stroke_effects,
                background_effects,
            )

    def _render_rich_text(self, image: Image.Image, layer: TextLayer):
        if not isinstance(layer.content, list):
            return

        # Apply auto-scaling if enabled
        if layer.auto_scale and layer.max_width:
            layer = self._auto_scale_rich_text(layer)

        # If rotation is needed, render to temporary image first
        if layer.rotation != 0:
            self._render_rotated_rich_text(image, layer)
            return

        draw = ImageDraw.Draw(image)
        lines = self._prepare_rich_text_lines(layer)
        line_heights, total_height = self._calculate_rich_text_dimensions(layer, lines)
        base_x, start_y = self._calculate_start_position(layer, total_height)

        self._draw_rich_text_lines(draw, image, layer, lines, line_heights, base_x, start_y)

    def _calculate_rich_text_dimensions(
        self, layer: TextLayer, lines: list[list[TextPartData]]
    ) -> tuple[list[int], int]:
        total_height = 0
        line_heights = []

        for line_parts in lines:
            max_line_height = 0
            if not line_parts:
                ref_font = self._load_font(layer)
                lh_mult = layer.line_height or DEFAULT_LINE_HEIGHT_MULTIPLIER
                max_line_height = self._calculate_line_height(ref_font, lh_mult)
            else:
                for part in line_parts:
                    font = self._load_font_variant(
                        part["font_name"],
                        part["size"],
                        part["bold"],
                        part["italic"],
                        part["weight"],
                    )
                    lh = self._calculate_line_height(font, part["line_height_multiplier"])
                    max_line_height = max(max_line_height, lh)

            line_heights.append(max_line_height)
            total_height += max_line_height

        return line_heights, total_height

    def _calculate_start_position(self, layer: TextLayer, total_height: int) -> tuple[int, int]:
        base_x, base_y = self._get_text_base_position(layer)
        start_y = self._get_vertical_start_y(base_y, total_height, layer.align)
        return base_x, start_y

    def _draw_rich_text_lines(
        self,
        draw: ImageDraw.ImageDraw,
        image: Image.Image,
        layer: TextLayer,
        lines: list[list[TextPartData]],
        line_heights: list[int],
        base_x: int,
        start_y: int,
    ):
        current_y = start_y
        for i, line_parts in enumerate(lines):
            line_height = line_heights[i]

            line_width = 0
            part_metadata: list[TextPartMetadata] = []

            for part in line_parts:
                font = self._load_font_variant(
                    part["font_name"],
                    part["size"],
                    part["bold"],
                    part["italic"],
                    part["weight"],
                )

                w, _ = self._measure_text_bounds(part["text"], font, part["letter_spacing"])
                part_metadata.append({"font": font, "width": w})
                line_width += w

            current_x = self._get_horizontal_start_x(base_x, line_width, layer.align)

            for j, part in enumerate(line_parts):
                meta = part_metadata[j]
                font = meta["font"]
                width = meta["width"]

                # Calculate vertical offset to center text within line box
                bbox = font.getbbox(part["text"])
                text_height = int(bbox[3] - bbox[1])
                vertical_offset = (line_height - text_height) // 2
                adjusted_y = current_y + vertical_offset

                self._render_text_part(draw, image, part, font, (current_x, adjusted_y))
                current_x += width

            current_y += line_height

    def _prepare_rich_text_lines(self, layer: TextLayer) -> list[list[TextPartData]]:
        lines: list[list[TextPartData]] = [[]]

        for part in cast(list[TextPart], layer.content):
            color = self._resolve_color(part, layer)
            size = self._resolve_size(part, layer)
            bold = self._resolve_bold(part, layer)
            italic = self._resolve_italic(part, layer)
            weight = self._resolve_weight(part, layer)
            font_name = self._resolve_font_name(part, layer)
            lh_mult = self._resolve_line_height(part, layer)
            letter_spacing = self._resolve_letter_spacing(part, layer)

            combined_effects = list(layer.effects) + list(part.effects)

            part_data: TextPartData = {
                "color": color,
                "font_name": font_name,
                "size": size,
                "bold": bold,
                "italic": italic,
                "weight": weight,
                "line_height_multiplier": lh_mult,
                "letter_spacing": letter_spacing,
                "stroke_effects": self._get_stroke_effects(combined_effects),
                "shadow_effects": self._get_shadow_effects(combined_effects),
                "glow_effects": self._get_glow_effects(combined_effects),
                "background_effects": self._get_background_effects(combined_effects),
                "text": part.text,
            }

            if "\n" in part.text:
                segments = part.text.split("\n")
                for i, segment in enumerate(segments):
                    if i > 0:
                        lines.append([])
                    if segment:
                        line = part_data.copy()
                        line["text"] = segment
                        lines[-1].append(line)
            else:
                lines[-1].append(part_data)

        return lines

    def _resolve_color(self, part: TextPart, layer: TextLayer):
        if part.color:
            return self._parse_color(part.color)
        if layer.color:
            return self._parse_color(layer.color)
        return DEFAULT_TEXT_COLOR

    def _resolve_size(self, part: TextPart, layer: TextLayer):
        if part.size is not None:
            return part.size
        if layer.size:
            return layer.size
        return DEFAULT_TEXT_SIZE

    def _resolve_bold(self, part: TextPart, layer: TextLayer):
        if part.bold is not None:
            return part.bold
        return layer.bold

    def _resolve_italic(self, part: TextPart, layer: TextLayer):
        if part.italic is not None:
            return part.italic
        return layer.italic

    def _resolve_weight(self, part: TextPart, layer: TextLayer):
        if part.weight is not None:
            return part.weight
        return layer.weight

    def _resolve_font_name(self, part: TextPart, layer: TextLayer):
        if part.font is not None:
            return part.font
        return layer.font

    def _resolve_line_height(self, part: TextPart, layer: TextLayer):
        if part.line_height is not None:
            return part.line_height
        if layer.line_height:
            return layer.line_height
        return DEFAULT_LINE_HEIGHT_MULTIPLIER

    def _resolve_letter_spacing(self, part: TextPart, layer: TextLayer):
        if part.letter_spacing is not None:
            return part.letter_spacing
        if layer.letter_spacing:
            return layer.letter_spacing
        return 0

    def _render_text_part(
        self,
        draw: ImageDraw.ImageDraw,
        image: Image.Image,
        part_data: TextPartData,
        font: FontType,
        position: tuple[int, int],
    ):
        text = part_data["text"]
        x, y = position

        # Render background effects first
        for bg in part_data["background_effects"]:
            self._render_background(image, text, font, (x, y), bg)

        # Render glow and shadow effects
        for glow in part_data["glow_effects"]:
            self._render_glow(image, text, font, (x, y), glow)

        for shadow in part_data["shadow_effects"]:
            self._render_shadow(image, text, font, (x, y), shadow)

        # Render text
        if part_data["letter_spacing"]:
            self._draw_text_with_letter_spacing(
                draw,
                text,
                (x, y),
                font,
                part_data["color"],
                part_data["letter_spacing"],
                part_data["stroke_effects"],
            )
        else:
            self._draw_text(
                draw, text, (x, y), font, part_data["color"], part_data["stroke_effects"]
            )

    def _render_multiline_text(
        self,
        draw: ImageDraw.ImageDraw,
        lines: list[str],
        font: FontType,
        color: tuple[int, ...],
        layer: TextLayer,
        image: Image.Image,
    ):
        line_height_multiplier = layer.line_height or DEFAULT_LINE_HEIGHT_MULTIPLIER
        line_height = self._calculate_line_height(font, line_height_multiplier)
        total_height = line_height * len(lines)

        base_x, base_y = self._get_text_base_position(layer)

        start_y = self._get_vertical_start_y(base_y, total_height, layer.align)

        glow_effects = self._get_glow_effects(layer.effects)
        shadow_effects = self._get_shadow_effects(layer.effects)
        stroke_effects = self._get_stroke_effects(layer.effects)
        background_effects = self._get_background_effects(layer.effects)

        for i, line in enumerate(lines):
            line_width, _ = self._measure_text_bounds(
                line, font, layer.letter_spacing or 0, line_height_multiplier
            )

            y = start_y + i * line_height
            x = self._get_horizontal_start_x(base_x, line_width, layer.align)

            for bg in background_effects:
                self._render_background(image, line, font, (x, y), bg, "lt")

            for glow in glow_effects:
                self._render_glow(image, line, font, (x, y), glow)

            for shadow in shadow_effects:
                self._render_shadow(image, line, font, (x, y), shadow)

            if layer.letter_spacing:
                self._draw_text_with_letter_spacing(
                    draw, line, (x, y), font, color, layer.letter_spacing, stroke_effects
                )
            else:
                self._draw_text(draw, line, (x, y), font, color, stroke_effects)

    def _get_text_base_position(self, layer: TextLayer) -> tuple[int, int]:
        """Return base (x, y) for text, deriving from alignment when position is not set."""
        if layer.position is not None:
            return (
                self._parse_coordinate(layer.position[0], self.width),
                self._parse_coordinate(layer.position[1], self.height),
            )
        if layer.align:
            h_map = {"left": 0, "center": self.width // 2, "right": self.width}
            v_map = {"top": 0, "middle": self.height // 2, "bottom": self.height}
            return h_map[layer.align.horizontal], v_map[layer.align.vertical]
        return 0, 0

    def _calculate_text_position(self, layer: TextLayer) -> tuple[int, int]:
        return self._get_text_base_position(layer)

    def _render_text_effects(
        self,
        image: Image.Image,
        content: str,
        font: FontType,
        position: tuple[int, int],
        glow_effects: list[Glow],
        shadow_effects: list[Shadow],
        anchor: str,
    ):
        for glow in glow_effects:
            self._render_glow(image, content, font, position, glow, anchor)
        for shadow in shadow_effects:
            self._render_shadow(image, content, font, position, shadow, anchor)

    def _render_letter_spaced_text(
        self,
        draw: ImageDraw.ImageDraw,
        image: Image.Image,
        content: str,
        font: FontType,
        color: tuple[int, ...],
        layer: TextLayer,
        glow_effects: list[Glow],
        shadow_effects: list[Shadow],
        stroke_effects: list[Stroke],
        background_effects: list[Background],
    ):
        letter_spacing = layer.letter_spacing or 0
        total_width, char_widths = self._calculate_spaced_text_width(content, font, letter_spacing)
        bbox = font.getbbox(content)
        text_height = int(bbox[3] - bbox[1])

        base_x, base_y = self._calculate_text_position(layer)
        x = self._get_horizontal_start_x(base_x, total_width, layer.align)
        y = self._get_vertical_start_y(base_y, text_height, layer.align)
        position = (x, y)

        for bg in background_effects:
            self._render_background(
                image, content, font, position, bg, "lt", width_override=total_width
            )

        for glow in glow_effects:
            self._render_letter_spaced_glow(
                image, content, font, position, glow, letter_spacing, char_widths
            )

        for shadow in shadow_effects:
            self._render_letter_spaced_shadow(
                image, content, font, position, shadow, letter_spacing, char_widths
            )

        self._draw_text_with_letter_spacing(
            draw, content, position, font, color, letter_spacing, stroke_effects, char_widths
        )

    def _render_normal_text(
        self,
        draw: ImageDraw.ImageDraw,
        image: Image.Image,
        content: str,
        font: FontType,
        color: tuple[int, ...],
        layer: TextLayer,
        glow_effects: list[Glow],
        shadow_effects: list[Shadow],
        stroke_effects: list[Stroke],
        background_effects: list[Background],
    ):
        position = self._calculate_text_position(layer)
        anchor = self._get_text_anchor(layer.align)

        for bg in background_effects:
            self._render_background(image, content, font, position, bg, anchor)

        self._render_text_effects(
            image, content, font, position, glow_effects, shadow_effects, anchor
        )

        self._draw_text(draw, content, position, font, color, stroke_effects, anchor)

    def _render_rotated_simple_text(self, image: Image.Image, layer: TextLayer):
        """Render simple text with rotation applied.

        Rotation is performed by rendering text to a temporary image, rotating it,
        then compositing the result onto the main canvas. This approach preserves
        all text effects during rotation.
        """
        font = self._load_font(layer)
        color = self._parse_color(layer.color) if layer.color else DEFAULT_TEXT_COLOR
        content = layer.content if isinstance(layer.content, str) else ""

        stroke_effects = self._get_stroke_effects(layer.effects)
        shadow_effects = self._get_shadow_effects(layer.effects)
        glow_effects = self._get_glow_effects(layer.effects)
        background_effects = self._get_background_effects(layer.effects)

        text_width, text_height = self._measure_simple_text_size(layer, font, content)
        padding = self._calculate_text_effects_padding(stroke_effects, shadow_effects, glow_effects)
        temp_image, temp_draw = self._create_temp_image_for_text(text_width, text_height, padding)

        temp_layer = layer.model_copy(update={"position": (padding, padding), "align": None})

        self._render_simple_text_to_temp_image(
            temp_draw,
            temp_image,
            temp_layer,
            font,
            color,
            content,
            stroke_effects,
            shadow_effects,
            glow_effects,
            background_effects,
        )

        self._rotate_and_composite_text(image, temp_image, layer)

    def _measure_simple_text_size(
        self, layer: TextLayer, font: FontType, content: str
    ) -> tuple[int, int]:
        """Calculate text bounding box size accounting for wrapping."""
        line_height_mult = layer.line_height or DEFAULT_LINE_HEIGHT_MULTIPLIER

        if layer.max_width:
            max_width_px = self._parse_coordinate(layer.max_width, self.width)
            lines = self._wrap_text(content, font, max_width_px, layer.letter_spacing)
            return self._measure_text_bounds(
                "\n".join(lines),
                font,
                layer.letter_spacing or 0,
                line_height_mult,
            )

        return self._measure_text_bounds(
            content,
            font,
            layer.letter_spacing or 0,
            line_height_mult,
        )

    def _render_simple_text_to_temp_image(
        self,
        temp_draw: ImageDraw.ImageDraw,
        temp_image: Image.Image,
        temp_layer: TextLayer,
        font: FontType,
        color: tuple[int, ...],
        content: str,
        stroke_effects: list[Stroke],
        shadow_effects: list[Shadow],
        glow_effects: list[Glow],
        background_effects: list[Background],
    ) -> None:
        """Render text with effects to temporary image, choosing the appropriate method."""
        if temp_layer.max_width:
            max_width_px = self._parse_coordinate(temp_layer.max_width, self.width)
            lines = self._wrap_text(content, font, max_width_px, temp_layer.letter_spacing)
            self._render_multiline_text(temp_draw, lines, font, color, temp_layer, temp_image)
        elif "\n" in content:
            lines = content.split("\n")
            self._render_multiline_text(temp_draw, lines, font, color, temp_layer, temp_image)
        elif temp_layer.letter_spacing:
            self._render_letter_spaced_text(
                temp_draw,
                temp_image,
                content,
                font,
                color,
                temp_layer,
                glow_effects,
                shadow_effects,
                stroke_effects,
                background_effects,
            )
        else:
            self._render_normal_text(
                temp_draw,
                temp_image,
                content,
                font,
                color,
                temp_layer,
                glow_effects,
                shadow_effects,
                stroke_effects,
                background_effects,
            )

    def _render_rotated_rich_text(self, image: Image.Image, layer: TextLayer):
        """Render rich text with rotation applied.

        Rotation is performed by rendering to a temporary image, rotating it,
        then compositing the result. This preserves all text effects and handles
        per-part styling correctly.
        """
        if not isinstance(layer.content, list):
            return

        text_width, text_height = self._measure_rich_text_size(layer)
        padding = self._calculate_rich_text_effects_padding(layer)
        temp_image, temp_draw = self._create_temp_image_for_text(text_width, text_height, padding)
        temp_layer = layer.model_copy(update={"position": (padding, padding), "align": None})

        self._render_rich_text_to_temp_image(temp_draw, temp_image, temp_layer)
        self._rotate_and_composite_text(image, temp_image, layer)

    def _measure_rich_text_size(self, layer: TextLayer) -> tuple[int, int]:
        """Calculate rich text bounding box size."""
        lines = self._prepare_rich_text_lines(layer)
        _, total_height = self._calculate_rich_text_dimensions(layer, lines)

        max_width = 0
        for line_parts in lines:
            line_width = self._measure_rich_line_width(line_parts)
            max_width = max(max_width, line_width)

        return max_width, total_height

    def _calculate_rich_text_effects_padding(self, layer: TextLayer) -> int:
        """Calculate padding for rich text effects from both layer and part-level effects."""
        all_stroke_effects: list[Stroke] = []
        all_shadow_effects: list[Shadow] = []
        all_glow_effects: list[Glow] = []

        all_stroke_effects.extend(self._get_stroke_effects(layer.effects))
        all_shadow_effects.extend(self._get_shadow_effects(layer.effects))
        all_glow_effects.extend(self._get_glow_effects(layer.effects))

        if isinstance(layer.content, list):
            for part in layer.content:
                all_stroke_effects.extend(self._get_stroke_effects(part.effects))
                all_shadow_effects.extend(self._get_shadow_effects(part.effects))
                all_glow_effects.extend(self._get_glow_effects(part.effects))

        return self._calculate_text_effects_padding(
            all_stroke_effects, all_shadow_effects, all_glow_effects
        )

    def _render_rich_text_to_temp_image(
        self,
        temp_draw: ImageDraw.ImageDraw,
        temp_image: Image.Image,
        temp_layer: TextLayer,
    ) -> None:
        """Render rich text with effects to temporary image."""
        temp_lines = self._prepare_rich_text_lines(temp_layer)
        temp_line_heights, temp_total_height = self._calculate_rich_text_dimensions(
            temp_layer, temp_lines
        )
        base_x, start_y = self._calculate_start_position(temp_layer, temp_total_height)
        self._draw_rich_text_lines(
            temp_draw, temp_image, temp_layer, temp_lines, temp_line_heights, base_x, start_y
        )

    def _calculate_text_effects_padding(
        self, stroke_effects: list[Stroke], shadow_effects: list[Shadow], glow_effects: list[Glow]
    ) -> int:
        """Calculate extra space needed around text to prevent effect clipping."""
        padding = 0

        for stroke in stroke_effects:
            padding = max(padding, stroke.width)

        for shadow in shadow_effects:
            shadow_extent = max(abs(shadow.offset_x), abs(shadow.offset_y)) + shadow.blur_radius * 3
            padding = max(padding, shadow_extent)

        for glow in glow_effects:
            glow_extent = glow.radius * 3
            padding = max(padding, glow_extent)

        return max(padding, 10)

    def _create_temp_image_for_text(
        self, width: int, height: int, padding: int
    ) -> tuple[Image.Image, ImageDraw.ImageDraw]:
        """Create transparent temporary image sized for content plus effect padding."""
        temp_width = width + padding * 2
        temp_height = height + padding * 2
        temp_image = Image.new("RGBA", (temp_width, temp_height), (0, 0, 0, 0))
        temp_draw = ImageDraw.Draw(temp_image)
        return temp_image, temp_draw

    def _rotate_and_composite_text(
        self, image: Image.Image, temp_image: Image.Image, layer: TextLayer
    ) -> None:
        """Rotate temporary text image and composite onto main canvas with alignment."""
        rotated = temp_image.rotate(-layer.rotation, expand=True, resample=Image.Resampling.BICUBIC)

        raw_x, raw_y = layer.position if layer.position else (0, 0)
        base_x = self._parse_coordinate(raw_x, self.width)
        base_y = self._parse_coordinate(raw_y, self.height)

        if layer.align:
            base_x, base_y = self._apply_image_alignment(base_x, base_y, rotated.size, layer.align)

        image.alpha_composite(rotated, (base_x, base_y))

    def _get_text_anchor(self, align: Align | None) -> str:
        if not align:
            return "lt"

        horizontal_align = align.horizontal
        vertical_align = align.vertical

        h_anchor = {"left": "l", "center": "m", "right": "r"}[horizontal_align]
        v_anchor = {"top": "t", "middle": "m", "bottom": "b"}[vertical_align]

        return h_anchor + v_anchor

    def _wrap_text(
        self, text: str, font, max_width: int, letter_spacing: int | None = None
    ) -> list[str]:
        words = text.split()
        lines = []
        current_line: list[str] = []

        for word in words:
            test_line = " ".join(current_line + [word])

            width, _ = self._measure_text_bounds(test_line, font, letter_spacing or 0)

            if width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                    current_line = [word]
                else:
                    lines.append(word)

        if current_line:
            lines.append(" ".join(current_line))

        return lines

    def _measure_text_bounds(
        self,
        text: str,
        font: FontType,
        letter_spacing: int = 0,
        line_height_multiplier: float = DEFAULT_LINE_HEIGHT_MULTIPLIER,
    ) -> tuple[int, int]:
        if not text:
            return 0, 0

        if "\n" not in text:
            if letter_spacing:
                char_widths = self._calculate_char_widths(text, font)
                width = sum(char_widths) + letter_spacing * (len(char_widths) - 1)
            else:
                bbox = font.getbbox(text)
                width = int(bbox[2] - bbox[0])

            bbox = font.getbbox(text)
            height = int(bbox[3] - bbox[1])
            return width, height

        lines = text.split("\n")
        max_width = 0

        for line in lines:
            if not line:
                continue

            if letter_spacing:
                char_widths = self._calculate_char_widths(line, font)
                line_width = sum(char_widths) + letter_spacing * (len(char_widths) - 1)
            else:
                bbox = font.getbbox(line)
                line_width = int(bbox[2] - bbox[0])

            max_width = max(max_width, line_width)

        line_height = self._calculate_line_height(font, line_height_multiplier)
        total_height = line_height * len(lines)

        return max_width, total_height

    def _calculate_line_height(self, font: FontType, multiplier: float) -> int:
        bbox = font.getbbox(LINE_HEIGHT_REFERENCE)
        base_height = bbox[3] - bbox[1]
        return int(base_height * multiplier)

    def _calculate_char_widths(self, text: str, font) -> list[int]:
        widths = []
        for char in text:
            bbox = font.getbbox(char)
            widths.append(int(bbox[2] - bbox[0]))
        return widths

    def _calculate_spaced_text_width(
        self, text: str, font, letter_spacing: int
    ) -> tuple[int, list[int]]:
        char_widths = self._calculate_char_widths(text, font)
        total_width = sum(char_widths) + letter_spacing * (len(text) - 1)
        return total_width, char_widths

    def _get_vertical_start_y(self, base_y: int, total_height: int, align: Align | None) -> int:
        if not align:
            return base_y

        vertical_align = align.vertical
        if vertical_align == "middle":
            return base_y - total_height // 2
        elif vertical_align == "bottom":
            return base_y - total_height
        return base_y

    def _get_horizontal_start_x(self, base_x: int, line_width: int, align: Align | None) -> int:
        if not align:
            return base_x

        horizontal_align = align.horizontal
        if horizontal_align == "center":
            return base_x - line_width // 2
        elif horizontal_align == "right":
            return base_x - line_width
        return base_x

    def _iterate_letter_spaced_positions(
        self, text: str, letter_spacing: int, char_widths: list[int], start_x: int
    ):
        current_x = start_x
        for i, char in enumerate(text):
            yield char, current_x
            current_x += char_widths[i] + letter_spacing

    def _calculate_letter_spaced_layout(
        self, text: str, font: FontType, letter_spacing: int, char_widths: list[int]
    ) -> tuple[int, int, int]:
        total_width = sum(char_widths) + letter_spacing * (len(char_widths) - 1)
        bbox = font.getbbox(text, anchor="ls")
        text_height = int(bbox[3] - bbox[1])
        baseline_offset = int(-bbox[1])
        return total_width, text_height, baseline_offset

    def _draw_text_with_letter_spacing(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        position: tuple[int, int],
        font: FontType,
        color: tuple[int, ...],
        letter_spacing: int,
        stroke_effects: list[Stroke] | None = None,
        char_widths: list[int] | None = None,
    ):
        x, y = position
        widths = char_widths if char_widths is not None else self._calculate_char_widths(text, font)
        strokes = stroke_effects or []

        # Calculate baseline position from the top position
        # Use "ls" (left-baseline) anchor to get bbox relative to baseline
        # bbox[1] is negative (top is above baseline), bbox[3] is positive (bottom below)
        # baseline_y = y - bbox[1] converts top position to baseline position
        bbox = font.getbbox(text, anchor="ls")
        baseline_y = int(y - bbox[1])

        for char, char_x in self._iterate_letter_spaced_positions(text, letter_spacing, widths, x):
            self._draw_text(draw, char, (char_x, baseline_y), font, color, strokes, "ls")

    def _draw_text(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        position: tuple[int, int],
        font: FontType,
        color: tuple[int, ...],
        stroke_effects: list[Stroke],
        anchor: str = "lt",
    ):
        if stroke_effects:
            for stroke in stroke_effects:
                draw.text(
                    position,
                    text,
                    font=font,
                    fill=color,
                    stroke_width=stroke.width,
                    stroke_fill=self._parse_color(stroke.color),
                    anchor=anchor,
                )
        else:
            draw.text(position, text, font=font, fill=color, anchor=anchor)

    def _render_glow(
        self,
        image: Image.Image,
        text: str,
        font: FontType,
        position: tuple[int, int],
        glow: Glow,
        anchor: str = "lt",
    ):
        temp_draw = ImageDraw.Draw(image)
        bbox = temp_draw.textbbox((0, 0), text, font=font, anchor=anchor)
        text_width = int(bbox[2] - bbox[0])
        text_height = int(bbox[3] - bbox[1])

        expansion = max(1, glow.radius // 2)
        blur_padding = max(glow.radius * 3, 1)
        total_padding = blur_padding + expansion

        draw_x = int(total_padding - bbox[0])
        draw_y = int(total_padding - bbox[1])

        temp_w = text_width + 2 * total_padding
        temp_h = text_height + 2 * total_padding

        glow_mask = Image.new("L", (temp_w, temp_h), 0)
        mask_draw = ImageDraw.Draw(glow_mask)

        mask_draw.text(
            (draw_x, draw_y),
            text,
            font=font,
            fill=255,
            stroke_width=expansion * 2,
            stroke_fill=255,
            anchor=anchor,
        )

        glow_mask = glow_mask.filter(ImageFilter.GaussianBlur(radius=glow.radius))

        glow_color = self._parse_color(glow.color)
        glow_layer = Image.new("RGBA", (temp_w, temp_h), glow_color)

        if glow.opacity < 1.0:
            glow_mask = glow_mask.point(lambda x: int(x * glow.opacity))

        glow_layer.putalpha(glow_mask)

        paste_x = position[0] - draw_x
        paste_y = position[1] - draw_y

        image.paste(glow_layer, (paste_x, paste_y), glow_layer)

    def _render_letter_spaced_glow(
        self,
        image: Image.Image,
        text: str,
        font: FontType,
        position: tuple[int, int],
        glow: Glow,
        letter_spacing: int,
        char_widths: list[int],
    ):
        if not text:
            return

        expansion = max(1, glow.radius // 2)
        blur_padding = max(glow.radius * 3, 1)
        total_padding = blur_padding + expansion

        total_width, text_height, baseline_offset = self._calculate_letter_spaced_layout(
            text, font, letter_spacing, char_widths
        )

        temp_w = total_width + 2 * total_padding
        temp_h = text_height + 2 * total_padding

        glow_mask = Image.new("L", (temp_w, temp_h), 0)
        mask_draw = ImageDraw.Draw(glow_mask)

        baseline_y = total_padding + baseline_offset
        for char, char_x in self._iterate_letter_spaced_positions(
            text, letter_spacing, char_widths, total_padding
        ):
            mask_draw.text(
                (char_x, baseline_y),
                char,
                font=font,
                fill=255,
                stroke_width=expansion * 2,
                stroke_fill=255,
                anchor="ls",
            )

        glow_mask = glow_mask.filter(ImageFilter.GaussianBlur(radius=glow.radius))

        glow_color = self._parse_color(glow.color)
        glow_layer = Image.new("RGBA", (temp_w, temp_h), glow_color)

        if glow.opacity < 1.0:
            glow_mask = glow_mask.point(lambda x: int(x * glow.opacity))

        glow_layer.putalpha(glow_mask)

        paste_x = position[0] - total_padding
        paste_y = position[1] - total_padding

        image.paste(glow_layer, (int(paste_x), int(paste_y)), glow_layer)

    def _render_shadow(
        self,
        image: Image.Image,
        text: str,
        font: FontType,
        position: tuple[int, int],
        shadow: Shadow,
        anchor: str = "lt",
    ):
        temp_draw = ImageDraw.Draw(image)
        bbox = temp_draw.textbbox((0, 0), text, font=font, anchor=anchor)
        text_width = int(bbox[2] - bbox[0])
        text_height = int(bbox[3] - bbox[1])

        padding = max(shadow.blur_radius * 3, 1)

        draw_x = int(padding - bbox[0])
        draw_y = int(padding - bbox[1])

        temp_w = text_width + 2 * padding
        temp_h = text_height + 2 * padding

        shadow_layer = Image.new("RGBA", (temp_w, temp_h), (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow_layer)

        shadow_color = self._parse_color(shadow.color)
        shadow_draw.text((draw_x, draw_y), text, font=font, fill=shadow_color, anchor=anchor)

        if shadow.blur_radius > 0:
            shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=shadow.blur_radius))

        paste_x = position[0] + shadow.offset_x - draw_x
        paste_y = position[1] + shadow.offset_y - draw_y

        image.paste(shadow_layer, (paste_x, paste_y), shadow_layer)

    def _render_letter_spaced_shadow(
        self,
        image: Image.Image,
        text: str,
        font: FontType,
        position: tuple[int, int],
        shadow: Shadow,
        letter_spacing: int,
        char_widths: list[int],
    ):
        if not text:
            return

        padding = max(shadow.blur_radius * 3, 1)
        total_width, text_height, baseline_offset = self._calculate_letter_spaced_layout(
            text, font, letter_spacing, char_widths
        )

        temp_w = total_width + 2 * padding
        temp_h = text_height + 2 * padding

        shadow_layer = Image.new("RGBA", (temp_w, temp_h), (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow_layer)
        shadow_color = self._parse_color(shadow.color)

        baseline_y = padding + baseline_offset
        for char, char_x in self._iterate_letter_spaced_positions(
            text, letter_spacing, char_widths, padding
        ):
            shadow_draw.text(
                (char_x, baseline_y),
                char,
                font=font,
                fill=shadow_color,
                anchor="ls",
            )

        if shadow.blur_radius > 0:
            shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=shadow.blur_radius))

        paste_x = position[0] + shadow.offset_x - padding
        paste_y = position[1] + shadow.offset_y - padding

        image.paste(shadow_layer, (int(paste_x), int(paste_y)), shadow_layer)

    def _render_background(
        self,
        image: Image.Image,
        text: str,
        font: FontType,
        position: tuple[int, int],
        background: Background,
        anchor: str = "lt",
        width_override: int | None = None,
    ):
        """Render background box behind text with padding and optional rounded corners.

        The background is positioned relative to the text anchor point, accounting for
        the text bounding box offset. This ensures the background aligns correctly
        regardless of text alignment (left, center, right).
        """
        # Get text dimensions from bounding box
        bbox = font.getbbox(text, anchor=anchor)
        text_width = width_override if width_override is not None else int(bbox[2] - bbox[0])
        text_height = int(bbox[3] - bbox[1])

        # Parse padding (supports uniform, 2-value, or 4-value formats)
        pad_top, pad_right, pad_bottom, pad_left = self._parse_padding(background.padding)

        # Calculate background dimensions including padding
        bg_width = text_width + pad_left + pad_right
        bg_height = text_height + pad_top + pad_bottom

        # Create background layer and apply color with opacity
        bg_layer = Image.new("RGBA", (bg_width, bg_height), (0, 0, 0, 0))
        bg_draw = ImageDraw.Draw(bg_layer)
        bg_color = self._apply_opacity_to_color(
            self._parse_color(background.color), background.opacity
        )

        # Draw background shape (rounded rectangle or normal rectangle)
        # Use (bg_width - 1, bg_height - 1) so arcs are not clipped at image boundary
        if background.border_radius > 0:
            self._draw_rounded_rectangle(
                bg_draw,
                [(0, 0), (bg_width - 1, bg_height - 1)],
                background.border_radius,
                fill=bg_color,
            )
        else:
            bg_draw.rectangle([(0, 0), (bg_width - 1, bg_height - 1)], fill=bg_color)

        # Calculate paste position
        # bbox[0], bbox[1] are the text bounding box offsets from the anchor point
        # For center-aligned text, these are typically negative (text extends left/up from anchor)
        # The background must be positioned to maintain proper padding around the text
        offset_x = int(pad_left - bbox[0])
        offset_y = int(pad_top - bbox[1])
        paste_x = position[0] - offset_x
        paste_y = position[1] - offset_y

        image.paste(bg_layer, (paste_x, paste_y), bg_layer)

    def _parse_padding(
        self, padding: int | tuple[int, int] | tuple[int, int, int, int]
    ) -> tuple[int, int, int, int]:
        """Parse padding value into (top, right, bottom, left) tuple.

        Args:
            padding: Can be:
                - int: uniform padding on all sides
                - tuple[int, int]: (vertical, horizontal) padding
                - tuple[int, int, int, int]: (top, right, bottom, left) padding

        Returns:
            Tuple of (top, right, bottom, left) padding values
        """
        if isinstance(padding, int):
            return (padding, padding, padding, padding)
        elif isinstance(padding, tuple) and len(padding) == 2:
            padding_2 = cast(tuple[int, int], padding)
            vertical, horizontal = padding_2
            return (vertical, horizontal, vertical, horizontal)
        else:  # len(padding) == 4
            return cast(tuple[int, int, int, int], padding)

    def _draw_rounded_rectangle(
        self,
        draw: ImageDraw.ImageDraw,
        coords: list[tuple[int, int]],
        radius: int,
        fill: tuple[int, ...] | None = None,
    ):
        """Draw a rounded rectangle on the given draw context."""
        x0, y0 = coords[0]
        x1, y1 = coords[1]
        draw.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=fill)

    def _load_font(self, layer: TextLayer) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        return self._load_font_variant(
            layer.font,
            layer.size or DEFAULT_TEXT_SIZE,
            layer.bold,
            layer.italic,
            layer.weight,
        )

    def _load_font_variant(
        self,
        font_name: str | None,
        size: int,
        bold: bool | None,
        italic: bool | None,
        weight: int | str | None = None,
    ) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        try:
            if font_name and self._is_url(font_name):
                if bold or italic or weight:
                    warnings.warn(
                        "Bold/italic/weight flags are ignored for webfont URLs. "
                        "Provide separate font URLs for styled variants.",
                        UserWarning,
                        stacklevel=3,
                    )
                font_path = self._download_and_cache_font(font_name)
                return ImageFont.truetype(font_path, size)

            if font_name:
                with contextlib.suppress(OSError):
                    return ImageFont.truetype(font_name, size)

                font_path = FontCache.get_instance().find_font(
                    font_name, bold or False, italic or False, weight=weight
                )

                if font_path:
                    return ImageFont.truetype(font_path, size)

            default_font_path = FontCache.get_instance().default_font()

            return (
                ImageFont.truetype(default_font_path, size)
                if default_font_path
                else ImageFont.load_default(size)
            )

        except OSError as e:
            raise RenderingError(f"Could not load font '{font_name}'.") from e

    def _get_style_string(self, bold: bool, italic: bool) -> str:
        if bold and italic:
            return "Bold Italic"
        if bold:
            return "Bold"
        if italic:
            return "Italic"
        return ""

    def _parse_coordinate(self, value: int | str, dimension: int) -> int:
        if isinstance(value, int):
            return value

        percentage = float(value.rstrip("%"))
        return int(dimension * percentage / 100)

    def _get_stroke_effects(self, effects: list[TextEffect]) -> list[Stroke]:
        return [e for e in effects if isinstance(e, Stroke)]

    def _get_shadow_effects(self, effects: list[TextEffect]) -> list[Shadow]:
        return [e for e in effects if isinstance(e, Shadow)]

    def _get_glow_effects(self, effects: list[TextEffect]) -> list[Glow]:
        return [e for e in effects if isinstance(e, Glow)]

    def _get_background_effects(self, effects: list[TextEffect]) -> list[Background]:
        return [e for e in effects if isinstance(e, Background)]

    def _is_url(self, path: str) -> bool:
        return path.startswith("http://") or path.startswith("https://")

    def _load_image_from_url(self, url: str) -> Image.Image:
        with urlopen(url) as response:
            image_data = response.read()
        return Image.open(BytesIO(image_data))

    def _download_and_cache_font(self, url: str) -> str:
        url_hash = hashlib.md5(url.encode()).hexdigest()
        extension = os.path.splitext(url)[1] or ".ttf"
        cache_filename = f"quickthumb_font_{url_hash}{extension}"
        cache_path = os.path.join("/tmp", cache_filename)

        if os.path.exists(cache_path):
            return cache_path

        try:
            with urlopen(url) as response:
                font_data = response.read()
            with open(cache_path, "wb") as f:
                f.write(font_data)
            return cache_path
        except Exception as e:
            raise RenderingError(f"Failed to download font from '{url}'.") from e

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
