import math
import os
from collections.abc import Callable
from contextlib import contextmanager
from io import BytesIO
from typing import Literal, TypedDict, cast
from urllib.request import urlopen

import pydantic_core
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from typing_extensions import Self

from quickthumb.errors import RenderingError, ValidationError
from quickthumb.models import (
    BackgroundLayer,
    BlendMode,
    CanvasModel,
    FitMode,
    Glow,
    LayerType,
    LinearGradient,
    OutlineLayer,
    RadialGradient,
    Shadow,
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


@contextmanager
def convert_pydantic_errors():
    try:
        yield
    except pydantic_core.ValidationError as e:
        errors = e.errors()
        if errors:
            error_locs = ",".join(str(loc) for loc in errors[0].get("loc", []))
            error_msg = errors[0].get("msg", "validation error")
            final_msg = f"{error_locs}: {error_msg}" if error_locs else error_msg
            raise ValidationError(final_msg) from e
        raise ValidationError("validation error") from e


class TextPartData(TypedDict):
    color: tuple[int, int, int]
    font_name: str
    size: int
    bold: bool
    italic: bool
    line_height_multiplier: float
    letter_spacing: int
    stroke_effects: list[Stroke]
    shadow_effects: list[Shadow]
    glow_effects: list[Glow]
    text: str


class TextPartMetadata(TypedDict):
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont
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
    def from_aspect_ratio(cls, ratio: str, base_width: int):
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
        brightness: float = 1.0,
    ) -> Self:
        with convert_pydantic_errors():
            layer = BackgroundLayer(
                type="background",
                color=color,
                gradient=gradient,
                image=image,
                opacity=opacity,
                blend_mode=blend_mode,
                fit=fit,
                brightness=brightness,
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
        align: tuple[str, str] | None = None,
        bold: bool = False,
        italic: bool = False,
        max_width: int | str | None = None,
        effects: list | None = None,
        line_height: float | None = None,
        letter_spacing: int | None = None,
    ) -> Self:
        if content is None:
            raise ValidationError("content is required")

        with convert_pydantic_errors():
            layer = TextLayer(
                type="text",
                content=content,
                font=font,
                size=size,
                color=color,
                position=position,
                align=align,
                bold=bold,
                italic=italic,
                max_width=max_width,
                effects=effects or [],
                line_height=line_height,
                letter_spacing=letter_spacing,
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
            elif isinstance(layer, OutlineLayer):
                self._render_outline_layer(image, layer)

        self._save_to_file(image, output_path, quality)

    def to_json(self) -> str:
        return CanvasModel(
            width=self.width, height=self.height, layers=self._layers
        ).model_dump_json()

    @classmethod
    def from_json(cls, data: str) -> Self:
        with convert_pydantic_errors():
            canvas_model = CanvasModel.model_validate_json(data)
        return cls(width=canvas_model.width, height=canvas_model.height, layers=canvas_model.layers)

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
                and not self._is_url(layer.image)
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
        layer_image = self._create_layer_image(image.size, layer)
        if not layer_image:
            return

        if layer.brightness != 1.0:
            layer_image = self._apply_brightness(layer_image, layer.brightness)

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

        x1 = layer.offset
        y1 = layer.offset
        x2 = self.width - layer.offset - 1
        y2 = self.height - layer.offset - 1

        for i in range(layer.width):
            draw.rectangle([x1 + i, y1 + i, x2 - i, y2 - i], outline=color)

    def _render_text_layer(self, image: Image.Image, layer: TextLayer):
        if isinstance(layer.content, list):
            self._render_rich_text(image, layer)
        else:
            self._render_simple_text(image, layer)

    def _render_simple_text(self, image: Image.Image, layer: TextLayer):
        draw = ImageDraw.Draw(image)
        font = self._load_font(layer)
        color = self._parse_color(layer.color) if layer.color else DEFAULT_TEXT_COLOR
        content = layer.content if isinstance(layer.content, str) else ""

        stroke_effects = self._get_stroke_effects(layer.effects)
        shadow_effects = self._get_shadow_effects(layer.effects)
        glow_effects = self._get_glow_effects(layer.effects)

        if layer.max_width:
            max_width_px = self._parse_coordinate(layer.max_width, self.width)
            lines = self._wrap_text(content, font, max_width_px, layer.letter_spacing)
            self._render_multiline_text(draw, lines, font, color, layer, image)
        else:
            position = self._calculate_text_position(layer, font)

            for glow in glow_effects:
                self._render_glow(image, content, font, position, glow)

            for shadow in shadow_effects:
                self._render_shadow(image, content, font, position, shadow)

            if layer.letter_spacing:
                self._draw_text_with_letter_spacing(
                    draw, content, position, font, color, layer.letter_spacing, stroke_effects
                )
            else:
                self._draw_text(draw, content, position, font, color, stroke_effects)

    def _render_rich_text(self, image: Image.Image, layer: TextLayer):
        if not isinstance(layer.content, list):
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
                        part["font_name"], part["size"], part["bold"], part["italic"]
                    )
                    lh = self._calculate_line_height(font, part["line_height_multiplier"])
                    max_line_height = max(max_line_height, lh)

            line_heights.append(max_line_height)
            total_height += max_line_height

        return line_heights, total_height

    def _calculate_start_position(self, layer: TextLayer, total_height: int) -> tuple[int, int]:
        raw_x, raw_y = layer.position if layer.position else (0, 0)
        base_x = self._parse_coordinate(raw_x, self.width)
        base_y = self._parse_coordinate(raw_y, self.height)

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
                    part["font_name"], part["size"], part["bold"], part["italic"]
                )

                w, _ = self._measure_text_bounds(part["text"], font, part["letter_spacing"])
                part_metadata.append({"font": font, "width": w})
                line_width += w

            current_x = self._get_horizontal_start_x(base_x, line_width, layer.align)

            for j, part in enumerate(line_parts):
                meta = part_metadata[j]
                font = meta["font"]
                width = meta["width"]

                self._render_text_part(draw, image, part, font, (current_x, current_y))
                current_x += width

            current_y += line_height

    def _prepare_rich_text_lines(self, layer: TextLayer) -> list[list[TextPartData]]:
        lines: list[list[TextPartData]] = [[]]

        for part in cast(list[TextPart], layer.content):
            color = self._resolve_color(part, layer)
            size = self._resolve_size(part, layer)
            bold = self._resolve_bold(part, layer)
            italic = self._resolve_italic(part, layer)
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
                "line_height_multiplier": lh_mult,
                "letter_spacing": letter_spacing,
                "stroke_effects": self._get_stroke_effects(combined_effects),
                "shadow_effects": self._get_shadow_effects(combined_effects),
                "glow_effects": self._get_glow_effects(combined_effects),
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
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        position: tuple[int, int],
        width: int | None = None,
    ):
        text = part_data["text"]
        x, y = position

        # Render effects
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
        font,
        color: tuple[int, ...],
        layer: TextLayer,
        image: Image.Image,
    ):
        line_height_multiplier = layer.line_height or DEFAULT_LINE_HEIGHT_MULTIPLIER
        line_height = self._calculate_line_height(font, line_height_multiplier)
        total_height = line_height * len(lines)

        raw_x, raw_y = layer.position if layer.position else (0, 0)
        base_x = self._parse_coordinate(raw_x, self.width)
        base_y = self._parse_coordinate(raw_y, self.height)

        start_y = self._get_vertical_start_y(base_y, total_height, layer.align)

        glow_effects = self._get_glow_effects(layer.effects)
        shadow_effects = self._get_shadow_effects(layer.effects)
        stroke_effects = self._get_stroke_effects(layer.effects)

        for i, line in enumerate(lines):
            line_width, _ = self._measure_text_bounds(
                line, font, layer.letter_spacing or 0, line_height_multiplier
            )

            y = start_y + i * line_height
            x = self._get_horizontal_start_x(base_x, line_width, layer.align)

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

    def _calculate_text_position(self, layer: TextLayer, font) -> tuple[int, int]:
        content = layer.content if isinstance(layer.content, str) else ""
        line_height_multiplier = layer.line_height or DEFAULT_LINE_HEIGHT_MULTIPLIER

        text_width, text_height = self._measure_text_bounds(
            content, font, layer.letter_spacing or 0, line_height_multiplier
        )

        raw_x, raw_y = layer.position if layer.position else (0, 0)

        base_x = self._parse_coordinate(raw_x, self.width)
        base_y = self._parse_coordinate(raw_y, self.height)

        if not layer.align:
            return base_x, base_y

        x = self._get_horizontal_start_x(base_x, text_width, layer.align)
        y = self._get_vertical_start_y(base_y, text_height, layer.align)

        return x, y

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
        font,
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
                width = bbox[2] - bbox[0]

            bbox = font.getbbox(text)
            height = bbox[3] - bbox[1]
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
                line_width = bbox[2] - bbox[0]

            max_width = max(max_width, line_width)

        line_height = self._calculate_line_height(font, line_height_multiplier)
        total_height = line_height * len(lines)

        return max_width, total_height

    def _calculate_line_height(self, font, multiplier: float) -> int:
        bbox = font.getbbox(LINE_HEIGHT_REFERENCE)
        base_height = bbox[3] - bbox[1]
        return int(base_height * multiplier)

    def _calculate_char_widths(self, text: str, font) -> list[int]:
        widths = []
        for char in text:
            bbox = font.getbbox(char)
            widths.append(bbox[2] - bbox[0])
        return widths

    def _get_vertical_start_y(
        self, base_y: int, total_height: int, align: tuple[str, str] | None
    ) -> int:
        if not align:
            return base_y

        _, vertical_align = align
        if vertical_align == "middle":
            return base_y - total_height // 2
        elif vertical_align == "bottom":
            return base_y - total_height
        return base_y

    def _get_horizontal_start_x(
        self, base_x: int, line_width: int, align: tuple[str, str] | None
    ) -> int:
        if not align:
            return base_x

        horizontal_align, _ = align
        if horizontal_align == "center":
            return base_x - line_width // 2
        elif horizontal_align == "right":
            return base_x - line_width
        return base_x

    def _draw_text_with_letter_spacing(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        position: tuple[int, int],
        font,
        color: tuple[int, ...],
        letter_spacing: int,
        stroke_effects: list[Stroke] | None = None,
    ):
        x, y = position
        char_widths = self._calculate_char_widths(text, font)
        strokes = stroke_effects or []

        for i, char in enumerate(text):
            self._draw_text(draw, char, (x, y), font, color, strokes)
            x += char_widths[i] + letter_spacing

    def _draw_text(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        position: tuple[int, int],
        font,
        color: tuple[int, ...],
        stroke_effects: list[Stroke],
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
                )
        else:
            draw.text(position, text, font=font, fill=color)

    def _render_glow(
        self,
        image: Image.Image,
        text: str,
        font,
        position: tuple[int, int],
        glow: Glow,
    ):
        bbox = font.getbbox(text)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        expansion = max(1, glow.radius // 2)
        blur_padding = max(glow.radius * 3, 1)
        total_padding = blur_padding + expansion

        draw_x = total_padding - bbox[0]
        draw_y = total_padding - bbox[1]

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

    def _render_shadow(
        self,
        image: Image.Image,
        text: str,
        font,
        position: tuple[int, int],
        shadow: Shadow,
    ):
        bbox = font.getbbox(text)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        padding = max(shadow.blur_radius * 3, 1)

        draw_x = padding - bbox[0]
        draw_y = padding - bbox[1]

        temp_w = text_width + 2 * padding
        temp_h = text_height + 2 * padding

        shadow_layer = Image.new("RGBA", (temp_w, temp_h), (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow_layer)

        shadow_color = self._parse_color(shadow.color)
        shadow_draw.text((draw_x, draw_y), text, font=font, fill=shadow_color)

        if shadow.blur_radius > 0:
            shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=shadow.blur_radius))

        paste_x = position[0] + shadow.offset_x - draw_x
        paste_y = position[1] + shadow.offset_y - draw_y

        image.paste(shadow_layer, (paste_x, paste_y), shadow_layer)

    def _load_font(self, layer: TextLayer) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        return self._load_font_variant(
            layer.font, layer.size or DEFAULT_TEXT_SIZE, layer.bold, layer.italic
        )

    def _load_font_variant(
        self, font_name: str | None, size: int, bold: bool | None, italic: bool | None
    ) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        font_style = self._get_style_string(bold or False, italic or False)

        try:
            if font_name and font_style:
                try:
                    styled_font_name = f"{font_name} {font_style}"
                    return ImageFont.truetype(styled_font_name, size)
                except OSError:
                    # Fallback to the original font name if the styled one fails
                    pass

            if font_name:
                return ImageFont.truetype(font_name, size)

            system_font_path = self._find_system_font(font_style)
            if system_font_path:
                return ImageFont.truetype(system_font_path, size)

            return ImageFont.load_default()
        except OSError as e:
            font_name = font_name or "default"
            raise RenderingError(f"Could not load font '{font_name}'.") from e

    def _get_style_string(self, bold: bool, italic: bool) -> str:
        if bold and italic:
            return "Bold Italic"
        if bold:
            return "Bold"
        if italic:
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

    def _is_url(self, path: str) -> bool:
        return path.startswith("http://") or path.startswith("https://")

    def _load_image_from_url(self, url: str) -> Image.Image:
        with urlopen(url) as response:
            image_data = response.read()
        return Image.open(BytesIO(image_data))

    def _create_gradient_lut(
        self, stops: list[tuple[str, float]]
    ) -> tuple[list[int], list[int], list[int]]:
        r_lut, g_lut, b_lut = [], [], []

        parsed_stops = []
        for color, pos in stops:
            parsed_color = self._parse_color(color)
            parsed_stops.append((parsed_color, pos))

        for i in range(256):
            pos = i / 255.0

            color1, pos1 = parsed_stops[0]
            color2, pos2 = parsed_stops[-1]

            if pos <= pos1:
                r, g, b = color1[:3]
            elif pos >= pos2:
                r, g, b = color2[:3]
            else:
                for j in range(len(parsed_stops) - 1):
                    c1, p1 = parsed_stops[j]
                    c2, p2 = parsed_stops[j + 1]
                    if p1 <= pos <= p2:
                        ratio = (pos - p1) / (p2 - p1) if p2 != p1 else 0
                        r = int(c1[0] + (c2[0] - c1[0]) * ratio)
                        g = int(c1[1] + (c2[1] - c1[1]) * ratio)
                        b = int(c1[2] + (c2[2] - c1[2]) * ratio)
                        break

            r_lut.append(r)
            g_lut.append(g)
            b_lut.append(b)

        return r_lut, g_lut, b_lut

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

        r_lut, g_lut, b_lut = self._create_gradient_lut(stops)
        r = gradient_mask.point(r_lut)
        g = gradient_mask.point(g_lut)
        b = gradient_mask.point(b_lut)

        return Image.merge("RGB", (r, g, b)).convert("RGBA")

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

        r_lut, g_lut, b_lut = self._create_gradient_lut(stops)
        r = gradient_mask.point(r_lut)
        g = gradient_mask.point(g_lut)
        b = gradient_mask.point(b_lut)

        return Image.merge("RGB", (r, g, b)).convert("RGBA")

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
