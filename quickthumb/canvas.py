import os
from contextlib import contextmanager
from typing import Literal

import pydantic_core
from PIL import Image, ImageDraw, ImageFont
from typing_extensions import Self

from quickthumb.errors import RenderingError, ValidationError
from quickthumb.models import (
    BackgroundLayer,
    BlendMode,
    CanvasModel,
    LayerType,
    LinearGradient,
    OutlineLayer,
    TextLayer,
)

FileFormat = Literal["JPEG", "WEBP", "PNG"]

DEFAULT_TEXT_SIZE = 16
DEFAULT_TEXT_COLOR = (0, 0, 0)
FULL_OPACITY = 255


@contextmanager
def convert_pydantic_errors():
    try:
        yield
    except pydantic_core.ValidationError as e:
        errors = e.errors()
        if errors:
            error_locs = ",".join(errors[0].get("loc", []))
            error_msg = errors[0].get("msg", "validation error")
            final_msg = f"{error_locs}: {error_msg}" if error_locs else error_msg
            raise ValidationError(final_msg) from e
        raise ValidationError("validation error") from e


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
    def from_aspect_ratio(cls, ratio: str, base_width: int):
        width_ratio, height_ratio = ratio.split(":")
        calculated_height = int(base_width * int(height_ratio) / int(width_ratio))
        return cls(base_width, calculated_height)

    def background(
        self,
        color: str | tuple | None = None,
        gradient: LinearGradient | None = None,
        image: str | None = None,
        opacity: float = 1.0,
        blend_mode: BlendMode | str | None = None,
    ) -> Self:
        with convert_pydantic_errors():
            layer = BackgroundLayer(
                type="background",
                color=color,
                gradient=gradient,
                image=image,
                opacity=opacity,
                blend_mode=blend_mode,
            )
        self._layers.append(layer)
        return self

    def text(
        self,
        content: str,
        font: str | None = None,
        size: int | None = None,
        color: str | None = None,
        position: tuple[int, int] | tuple[str, str] | None = None,
        align: tuple[str, str] | None = None,
        stroke: tuple[int, str] | None = None,
        bold: bool = False,
        italic: bool = False,
    ) -> Self:
        with convert_pydantic_errors():
            layer = TextLayer(
                type="text",
                content=content,
                font=font,
                size=size,
                color=color,
                position=position,
                align=align,
                stroke=stroke,
                bold=bold,
                italic=italic,
            )
        self._layers.append(layer)
        return self

    def outline(self, width: int, color: str, offset: int = 0) -> Self:
        with convert_pydantic_errors():
            layer = OutlineLayer(
                type="outline",
                width=width,
                color=color,
                offset=offset,
            )
        self._layers.append(layer)
        return self

    def render(self, output_path: str, quality: int | None = None):
        self._validate_image_paths()
        image = self._create_canvas()

        for layer in self._layers:
            if isinstance(layer, BackgroundLayer):
                self._render_background_layer(image, layer)
            elif isinstance(layer, TextLayer):
                self._render_text_layer(image, layer)

        self._save_to_file(image, output_path, quality)

    def _create_canvas(self) -> Image.Image:
        return Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))

    def _save_to_file(self, image: Image.Image, output_path: str, quality: int | None = None):
        file_format = self._detect_format(output_path)
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
                and not os.path.exists(layer.image)
            ):
                raise FileNotFoundError(f"{layer.image}")

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
        if layer.color:
            color = self._apply_opacity_to_color(self._parse_color(layer.color), layer.opacity)
            layer_image = Image.new("RGBA", image.size, color)
            image.paste(layer_image, (0, 0), layer_image)

    def _apply_opacity_to_color(self, color: tuple[int, ...], opacity: float) -> tuple[int, ...]:
        r, g, b = color[:3]

        if len(color) == 3:
            alpha = int(FULL_OPACITY * opacity)
            return (r, g, b, alpha)

        existing_alpha = color[3]
        alpha = int(existing_alpha * opacity)
        return (r, g, b, alpha)

    def _render_text_layer(self, image: Image.Image, layer: TextLayer):
        draw = ImageDraw.Draw(image)
        font = self._load_font(layer)
        color = self._parse_color(layer.color) if layer.color else DEFAULT_TEXT_COLOR
        position = self._calculate_text_position(layer, font)
        draw.text(position, layer.content, font=font, fill=color)

    def _load_font(self, layer: TextLayer) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        size = layer.size or DEFAULT_TEXT_SIZE

        if layer.font:
            return ImageFont.truetype(layer.font, size)

        font_style = self._determine_font_style(layer)
        system_font_path = self._find_system_font(font_style)

        if system_font_path:
            return ImageFont.truetype(system_font_path, size)

        return ImageFont.load_default()

    def _determine_font_style(self, layer: TextLayer) -> str:
        if layer.bold and layer.italic:
            return "Bold Italic"
        if layer.bold:
            return "Bold"
        if layer.italic:
            return "Italic"
        return ""

    def _find_system_font(self, font_style: str) -> str | None:
        font_map = {
            "": [
                "/System/Library/Fonts/Supplemental/Arial.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            ],
            "Bold": [
                "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            ],
            "Italic": [
                "/System/Library/Fonts/Supplemental/Arial Italic.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf",
            ],
            "Bold Italic": [
                "/System/Library/Fonts/Supplemental/Arial Bold Italic.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-BoldOblique.ttf",
            ],
        }

        for candidate in font_map.get(font_style, []):
            if os.path.exists(candidate):
                return candidate

        return None

    def _calculate_text_position(self, layer: TextLayer, font) -> tuple[int, int]:
        text_dimensions = self._get_text_dimensions(layer.content, font)
        base_x, base_y = layer.position if layer.position else (0, 0)

        if not layer.align:
            return base_x, base_y

        return self._apply_alignment(base_x, base_y, text_dimensions, layer.align)

    def _get_text_dimensions(self, text: str, font) -> tuple[int, int]:
        temp_image = Image.new("RGBA", (1, 1))
        draw = ImageDraw.Draw(temp_image)
        bbox = draw.textbbox((0, 0), text, font=font)
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        return width, height

    def _apply_alignment(
        self,
        base_x: int,
        base_y: int,
        text_dimensions: tuple[int, int],
        align: tuple[str, str],
    ) -> tuple[int, int]:
        text_width, text_height = text_dimensions
        horizontal, vertical = align

        aligned_x = base_x
        if horizontal == "center":
            aligned_x = base_x - text_width // 2
        elif horizontal == "right":
            aligned_x = base_x - text_width

        aligned_y = base_y
        if vertical == "middle":
            aligned_y = base_y - text_height // 2
        elif vertical == "bottom":
            aligned_y = base_y - text_height

        return aligned_x, aligned_y

    def to_json(self) -> str:
        return CanvasModel(
            width=self.width, height=self.height, layers=self._layers
        ).model_dump_json()

    @classmethod
    def from_json(cls, data: str) -> Self:
        with convert_pydantic_errors():
            canvas_model = CanvasModel.model_validate_json(data)
        return cls(width=canvas_model.width, height=canvas_model.height, layers=canvas_model.layers)
