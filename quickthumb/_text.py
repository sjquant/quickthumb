import warnings
from collections.abc import Callable
from typing import TypedDict, cast

from PIL import Image, ImageDraw, ImageFilter

from quickthumb._base import (
    DEFAULT_LINE_HEIGHT_MULTIPLIER,
    DEFAULT_TEXT_COLOR,
    DEFAULT_TEXT_SIZE,
    LINE_HEIGHT_REFERENCE,
    FontType,
    RenderContext,
    apply_alignment,
    parse_coordinate,
    parse_padding,
)
from quickthumb._effects import EffectsEngine
from quickthumb._fonts import FontEngine
from quickthumb._images import ImageEngine
from quickthumb.errors import RenderingError
from quickthumb.models import (
    Align,
    Background,
    Glow,
    LinearGradient,
    RadialGradient,
    Shadow,
    Stroke,
    TextEffect,
    TextFillImage,
    TextLayer,
    TextPart,
)


class TextPartData(TypedDict):
    color: tuple[int, ...]
    fill: "LinearGradient | RadialGradient | TextFillImage | None"
    font_name: str | None
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


class TextLayoutMetadata(TypedDict):
    size: tuple[int, int]
    wrapped_lines: tuple[str, ...]
    effective_font_size: int
    effective_font_sizes: tuple[int, ...]


class TextEngine:
    """Text layout, measurement, wrapping, effects, and rendering."""

    def __init__(
        self,
        ctx: RenderContext,
        fonts: FontEngine,
        effects: EffectsEngine,
        images: ImageEngine,
    ):
        self._ctx = ctx
        self._fonts = fonts
        self._effects = effects
        self._images = images

    def render_text_layer(self, image: Image.Image, layer: TextLayer):
        if layer.opacity < 1.0:
            temp = Image.new("RGBA", image.size, (0, 0, 0, 0))
            if isinstance(layer.content, list):
                self._render_rich_text(temp, layer)
            else:
                self._render_simple_text(temp, layer)
            self._effects.apply_opacity(temp, layer.opacity)
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
        max_width_px = parse_coordinate(layer.max_width, self._ctx.width)
        base_size = layer.size or DEFAULT_TEXT_SIZE
        content = layer.content if isinstance(layer.content, str) else ""

        def fits(size: int) -> bool:
            font = self._fonts.load_font_variant(
                layer.font, size, layer.bold, layer.italic, layer.weight
            )
            lines = self._wrap_text(content, font, max_width_px, layer.letter_spacing)
            return all(
                self.measure_text_bounds(line, font, layer.letter_spacing or 0)[0] <= max_width_px
                for line in lines
            )

        best_size = self._find_max_fitting_size(base_size, fits)
        return layer.model_copy(update={"size": best_size})

    def _scale_rich_text_parts(self, layer: TextLayer, scale_factor: float) -> list[TextPart]:
        return [
            part.model_copy(
                update={"size": max(1, int(self.resolve_size(part, layer) * scale_factor))}
            )
            for part in cast(list[TextPart], layer.content)
        ]

    def _measure_rich_line_width(self, line_parts: list[TextPartData]) -> int:
        width = 0
        for part in line_parts:
            font = self._fonts.load_font_variant(
                part["font_name"], part["size"], part["bold"], part["italic"], part["weight"]
            )
            w, _ = self.measure_text_bounds(part["text"], font, part["letter_spacing"])
            width += w
        return width

    def _auto_scale_rich_text(self, layer: TextLayer) -> TextLayer:
        assert layer.max_width is not None
        max_width_px = parse_coordinate(layer.max_width, self._ctx.width)
        base_size = layer.size or DEFAULT_TEXT_SIZE

        def fits(size: int) -> bool:
            scaled_parts = self._scale_rich_text_parts(layer, size / base_size)
            temp_layer = layer.model_copy(update={"content": scaled_parts, "size": size})
            lines = self._prepare_rich_text_lines(temp_layer, apply_wrapping=False)
            return all(
                self._measure_rich_line_width(line_parts) <= max_width_px for line_parts in lines
            )

        best_size = self._find_max_fitting_size(base_size, fits)
        final_parts = self._scale_rich_text_parts(layer, best_size / base_size)
        return layer.model_copy(update={"content": final_parts, "size": best_size})

    def effective_layer(self, layer: TextLayer) -> TextLayer:
        """Return the layer as it will actually render, with auto-scaling applied."""
        if not (layer.auto_scale and layer.max_width):
            return layer
        if isinstance(layer.content, list):
            return self._auto_scale_rich_text(layer)
        return self._auto_scale_simple_text(layer)

    def measure_text_layout(self, layer: TextLayer) -> TextLayoutMetadata:
        """Return rendered text line and font-size metadata for inspection."""
        if isinstance(layer.content, list):
            return self._measure_rich_text_layout(layer)
        return self._measure_simple_text_layout(layer)

    def _measure_simple_text_layout(self, layer: TextLayer) -> TextLayoutMetadata:
        font = self._fonts.load_font(layer)
        content = layer.content if isinstance(layer.content, str) else ""
        if layer.max_width:
            max_width_px = parse_coordinate(layer.max_width, self._ctx.width)
            lines = self._wrap_text(content, font, max_width_px, layer.letter_spacing)
        elif "\n" in content:
            lines = content.split("\n")
        else:
            lines = [content]
        size = self.measure_text_bounds(
            "\n".join(lines),
            font,
            layer.letter_spacing or 0,
            layer.line_height or DEFAULT_LINE_HEIGHT_MULTIPLIER,
        )

        return {
            "size": size,
            "wrapped_lines": tuple(lines),
            "effective_font_size": layer.size or DEFAULT_TEXT_SIZE,
            "effective_font_sizes": (layer.size or DEFAULT_TEXT_SIZE,),
        }

    def _measure_rich_text_layout(self, layer: TextLayer) -> TextLayoutMetadata:
        lines = self._prepare_rich_text_lines(layer, apply_wrapping=not layer.auto_scale)
        line_text = tuple("".join(part["text"] for part in line) for line in lines)
        sizes = tuple(sorted({part["size"] for line in lines for part in line}))
        effective_size = min(sizes) if sizes else layer.size or DEFAULT_TEXT_SIZE
        _, total_height = self._calculate_rich_text_dimensions(layer, lines)
        size = (
            max((self._measure_rich_line_width(line_parts) for line_parts in lines), default=0),
            total_height,
        )
        return {
            "size": size,
            "wrapped_lines": line_text,
            "effective_font_size": effective_size,
            "effective_font_sizes": sizes or (effective_size,),
        }

    def _render_simple_text(self, image: Image.Image, layer: TextLayer):
        # Apply auto-scaling if enabled
        if layer.auto_scale and layer.max_width:
            layer = self._auto_scale_simple_text(layer)

        # If rotation is needed, render to temporary image first
        if layer.rotation != 0:
            self._render_rotated_simple_text(image, layer)
            return

        draw = ImageDraw.Draw(image)
        font = self._fonts.load_font(layer)
        color = self._effects.parse_color(layer.color) if layer.color else DEFAULT_TEXT_COLOR
        content = layer.content if isinstance(layer.content, str) else ""

        stroke_effects = self._get_stroke_effects(layer.effects)
        shadow_effects = self._get_shadow_effects(layer.effects)
        glow_effects = self._get_glow_effects(layer.effects)
        background_effects = self._get_background_effects(layer.effects)

        if layer.max_width:
            max_width_px = parse_coordinate(layer.max_width, self._ctx.width)
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
        lines = self._prepare_rich_text_lines(layer, apply_wrapping=not layer.auto_scale)
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
                ref_font = self._fonts.load_font(layer)
                lh_mult = layer.line_height or DEFAULT_LINE_HEIGHT_MULTIPLIER
                max_line_height = self._calculate_line_height(ref_font, lh_mult)
            else:
                for part in line_parts:
                    font = self._fonts.load_font_variant(
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
        base_x, base_y = self.get_text_base_position(layer)
        start_y = self.get_vertical_start_y(base_y, total_height, layer.align)
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
                font = self._fonts.load_font_variant(
                    part["font_name"],
                    part["size"],
                    part["bold"],
                    part["italic"],
                    part["weight"],
                )

                w, _ = self.measure_text_bounds(part["text"], font, part["letter_spacing"])
                part_metadata.append({"font": font, "width": w})
                line_width += w

            current_x = self.get_horizontal_start_x(base_x, line_width, layer.align)

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

    def _prepare_rich_text_lines(
        self, layer: TextLayer, apply_wrapping: bool = True
    ) -> list[list[TextPartData]]:
        if apply_wrapping and layer.max_width:
            return self._prepare_wrapped_rich_text_lines(layer)

        lines: list[list[TextPartData]] = [[]]

        for part in cast(list[TextPart], layer.content):
            color = self.resolve_color(part, layer)
            size = self.resolve_size(part, layer)
            bold = self.resolve_bold(part, layer)
            italic = self.resolve_italic(part, layer)
            weight = self.resolve_weight(part, layer)
            font_name = self._resolve_font_name(part, layer)
            lh_mult = self._resolve_line_height(part, layer)
            letter_spacing = self.resolve_letter_spacing(part, layer)

            combined_effects = list(layer.effects) + list(part.effects)

            part_data: TextPartData = {
                "color": color,
                "fill": self._resolve_fill(part, layer),
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

    def _prepare_wrapped_rich_text_lines(self, layer: TextLayer) -> list[list[TextPartData]]:
        max_width_px = parse_coordinate(layer.max_width, self._ctx.width)  # type: ignore[arg-type]
        lines: list[list[TextPartData]] = [[]]
        current_width = 0

        for part in cast(list[TextPart], layer.content):
            color = self.resolve_color(part, layer)
            size = self.resolve_size(part, layer)
            bold = self.resolve_bold(part, layer)
            italic = self.resolve_italic(part, layer)
            weight = self.resolve_weight(part, layer)
            font_name = self._resolve_font_name(part, layer)
            lh_mult = self._resolve_line_height(part, layer)
            letter_spacing = self.resolve_letter_spacing(part, layer)
            combined_effects = list(layer.effects) + list(part.effects)
            font = self._fonts.load_font_variant(font_name, size, bold, italic, weight)
            part_template: TextPartData = {
                "color": color,
                "fill": self._resolve_fill(part, layer),
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
                "text": "",
            }

            for seg_idx, segment in enumerate(part.text.split("\n")):
                if seg_idx > 0:
                    lines.append([])
                    current_width = 0

                words = segment.split()
                if not words:
                    continue

                pending_words: list[str] = []
                space_prefix = False  # leading space before first word of this batch
                for word in words:
                    has_content = bool(lines[-1] or pending_words)
                    test_text = (" " if has_content else "") + word
                    word_w, _ = self.measure_text_bounds(test_text, font, letter_spacing)

                    if current_width + word_w <= max_width_px:
                        if not pending_words:
                            space_prefix = bool(lines[-1])
                        pending_words.append(word)
                        current_width += word_w
                    else:
                        if pending_words:
                            flushed = (" " if space_prefix else "") + " ".join(pending_words)
                            entry = part_template.copy()
                            entry["text"] = flushed
                            lines[-1].append(entry)
                            pending_words = []
                        if lines[-1]:
                            lines.append([])
                        bare_w, _ = self.measure_text_bounds(word, font, letter_spacing)
                        pending_words = [word]
                        space_prefix = False
                        current_width = bare_w

                if pending_words:
                    flushed = (" " if space_prefix else "") + " ".join(pending_words)
                    entry = part_template.copy()
                    entry["text"] = flushed
                    lines[-1].append(entry)

        return lines

    def resolve_color(self, part: TextPart, layer: TextLayer):
        if part.color:
            return self._effects.parse_color(part.color)
        if layer.color:
            return self._effects.parse_color(layer.color)
        return DEFAULT_TEXT_COLOR

    def resolve_size(self, part: TextPart, layer: TextLayer):
        if part.size is not None:
            return part.size
        if layer.size:
            return layer.size
        return DEFAULT_TEXT_SIZE

    def resolve_bold(self, part: TextPart, layer: TextLayer):
        if part.bold is not None:
            return part.bold
        return layer.bold

    def resolve_italic(self, part: TextPart, layer: TextLayer):
        if part.italic is not None:
            return part.italic
        return layer.italic

    def resolve_weight(self, part: TextPart, layer: TextLayer):
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

    def resolve_letter_spacing(self, part: TextPart, layer: TextLayer):
        if part.letter_spacing is not None:
            return part.letter_spacing
        if layer.letter_spacing:
            return layer.letter_spacing
        return 0

    def _resolve_fill(self, part: TextPart, layer: TextLayer):
        if part.fill is not None:
            return part.fill
        return layer.fill

    def _create_text_fill_image(
        self,
        size: tuple[int, int],
        fill: "LinearGradient | RadialGradient | TextFillImage",
    ) -> Image.Image:
        """Create a fill image (gradient or texture) at the given size."""
        if isinstance(fill, LinearGradient):
            return self._effects.create_linear_gradient(size, fill.angle, fill.stops)
        if isinstance(fill, RadialGradient):
            return self._effects.create_radial_gradient(size, fill.stops, fill.center)
        if isinstance(fill, TextFillImage):
            return self._images.load_and_fit_image(fill.path, size, fill.fit)
        raise RenderingError(f"Unsupported fill type: {type(fill).__name__}")

    def _draw_filled_text(
        self,
        image: Image.Image,
        text: str,
        position: tuple[int, int],
        font: FontType,
        fill: "LinearGradient | RadialGradient | TextFillImage",
        stroke_effects: list[Stroke],
        anchor: str = "lt",
    ) -> None:
        """Render text with a gradient or image fill.

        Renders stroke first (in stroke color), then overlays the fill on the
        text body, leaving the stroke ring visible around the glyph.
        """
        temp_draw = ImageDraw.Draw(image)
        bbox = temp_draw.textbbox((0, 0), text, font=font, anchor=anchor)
        text_w = int(bbox[2] - bbox[0])
        text_h = int(bbox[3] - bbox[1])
        if text_w <= 0 or text_h <= 0:
            return

        draw_x = -bbox[0]
        draw_y = -bbox[1]

        # Draw stroke under fill: use stroke color for both fill and stroke areas
        # so the outer stroke ring stays visible after fill is composited on top.
        if stroke_effects:
            for stroke in stroke_effects:
                stroke_color = self._effects.parse_color(stroke.color)
                temp_draw.text(
                    position,
                    text,
                    font=font,
                    fill=stroke_color,
                    stroke_width=stroke.width,
                    stroke_fill=stroke_color,
                    anchor=anchor,
                )

        # Create fill image sized to the text bounding box
        fill_img = self._create_text_fill_image((text_w, text_h), fill)

        # Create a white-on-black mask from the text glyphs (no stroke expansion)
        mask = Image.new("L", (text_w, text_h), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.text((draw_x, draw_y), text, font=font, fill=255, anchor=anchor)

        fill_img.putalpha(mask)

        paste_x = int(position[0] + bbox[0])
        paste_y = int(position[1] + bbox[1])
        image.alpha_composite(fill_img, (paste_x, paste_y))

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
        part_fill = part_data["fill"]
        letter_spacing = part_data["letter_spacing"]
        if part_fill is not None and letter_spacing:
            total_width, char_widths = self._calculate_spaced_text_width(text, font, letter_spacing)
            bbox = font.getbbox(text)
            text_height = int(bbox[3] - bbox[1])
            if stroke_effects := part_data["stroke_effects"]:
                for stroke in stroke_effects:
                    stroke_color = self._effects.parse_color(stroke.color)
                    self._draw_text_with_letter_spacing(
                        draw,
                        text,
                        (x, y),
                        font,
                        stroke_color,
                        letter_spacing,
                        [stroke],
                        char_widths,
                    )
            fill_img = self._create_text_fill_image((total_width, text_height), part_fill)
            bbox_ls = font.getbbox(text, anchor="ls")
            baseline_y_in_mask = int(-bbox_ls[1])
            mask = Image.new("L", (total_width, text_height), 0)
            mask_draw = ImageDraw.Draw(mask)
            for char, char_x in self._iterate_letter_spaced_positions(
                text, letter_spacing, char_widths, 0
            ):
                mask_draw.text((char_x, baseline_y_in_mask), char, font=font, fill=255, anchor="ls")
            fill_img.putalpha(mask)
            image.alpha_composite(fill_img, (x, y))
        elif part_fill is not None:
            self._draw_filled_text(
                image, text, (x, y), font, part_fill, part_data["stroke_effects"]
            )
        elif letter_spacing:
            self._draw_text_with_letter_spacing(
                draw,
                text,
                (x, y),
                font,
                part_data["color"],
                letter_spacing,
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

        base_x, base_y = self.get_text_base_position(layer)

        start_y = self.get_vertical_start_y(base_y, total_height, layer.align)

        glow_effects = self._get_glow_effects(layer.effects)
        shadow_effects = self._get_shadow_effects(layer.effects)
        stroke_effects = self._get_stroke_effects(layer.effects)
        background_effects = self._get_background_effects(layer.effects)
        line_layouts: list[tuple[str, int, int, tuple[int, int, int, int]]] = []
        for i, line in enumerate(lines):
            line_width, _ = self.measure_text_bounds(
                line, font, layer.letter_spacing or 0, line_height_multiplier
            )
            y = start_y + i * line_height
            x = self.get_horizontal_start_x(base_x, line_width, layer.align)
            bbox = cast(tuple[int, int, int, int], font.getbbox(line, anchor="lt"))
            line_layouts.append((line, x, y, bbox))

        if background_effects and line_layouts:
            content_left = min(x + bbox[0] for _, x, _, bbox in line_layouts)
            content_top = min(y + bbox[1] for _, _, y, bbox in line_layouts)
            content_right = max(x + bbox[2] for _, x, _, bbox in line_layouts)
            content_bottom = max(y + bbox[3] for _, _, y, bbox in line_layouts)

            for bg in background_effects:
                self._render_background_box(
                    image,
                    content_left,
                    content_top,
                    content_right - content_left,
                    content_bottom - content_top,
                    bg,
                )

        text_fill = layer.fill
        letter_spacing = layer.letter_spacing or 0
        if text_fill is not None and line_layouts:
            # Pre-compute letter-spaced widths when needed so block bounds are accurate.
            if letter_spacing:
                spaced_data = {
                    line: self._calculate_spaced_text_width(line, font, letter_spacing)
                    for line, _, _, _ in line_layouts
                }
                block_left = min(x for _, x, _, _ in line_layouts)
                block_right = max(x + spaced_data[line][0] for line, x, _, _ in line_layouts)
            else:
                spaced_data = {}
                block_left = min(x + bbox[0] for _, x, _, bbox in line_layouts)
                block_right = max(x + bbox[2] for _, x, _, bbox in line_layouts)

            # Build a block-level fill image spanning all lines so gradients and
            # images map to the full text block rather than repeating per line.
            block_top = min(y + bbox[1] for _, _, y, bbox in line_layouts)
            block_bottom = max(y + bbox[3] for _, _, y, bbox in line_layouts)
            block_w = max(1, block_right - block_left)
            block_h = max(1, block_bottom - block_top)
            fill_image = self._create_text_fill_image((block_w, block_h), text_fill)

            for line, x, y, bbox in line_layouts:
                for glow in glow_effects:
                    self._render_glow(image, line, font, (x, y), glow)
                for shadow in shadow_effects:
                    self._render_shadow(image, line, font, (x, y), shadow)

                if letter_spacing:
                    spaced_width, char_widths = spaced_data[line]
                    line_pixel_left = x
                    line_pixel_top = y + bbox[1]
                    line_pixel_w = spaced_width
                else:
                    char_widths = None
                    line_pixel_left = x + bbox[0]
                    line_pixel_top = y + bbox[1]
                    line_pixel_w = int(bbox[2] - bbox[0])

                line_pixel_h = int(bbox[3] - bbox[1])
                if line_pixel_w <= 0 or line_pixel_h <= 0:
                    continue

                # Draw stroke first (stroke color covers both body and ring)
                if stroke_effects:
                    for stroke in stroke_effects:
                        stroke_color = self._effects.parse_color(stroke.color)
                        if letter_spacing:
                            self._draw_text_with_letter_spacing(
                                draw,
                                line,
                                (x, y),
                                font,
                                stroke_color,
                                letter_spacing,
                                [stroke],
                                char_widths,
                            )
                        else:
                            draw.text(
                                (x, y),
                                line,
                                font=font,
                                fill=stroke_color,
                                stroke_width=stroke.width,
                                stroke_fill=stroke_color,
                                anchor="lt",
                            )

                # Clip fill to this line's portion of the block
                offset_x = line_pixel_left - block_left
                offset_y = line_pixel_top - block_top
                fill_clip = fill_image.crop(
                    (offset_x, offset_y, offset_x + line_pixel_w, offset_y + line_pixel_h)
                )

                # Text body mask
                mask = Image.new("L", (line_pixel_w, line_pixel_h), 0)
                mask_draw = ImageDraw.Draw(mask)
                if letter_spacing and char_widths:
                    bbox_ls = font.getbbox(line, anchor="ls")
                    baseline_y_in_mask = int(-bbox_ls[1]) + bbox[1]
                    for char, char_x in self._iterate_letter_spaced_positions(
                        line, letter_spacing, char_widths, 0
                    ):
                        mask_draw.text(
                            (char_x, baseline_y_in_mask), char, font=font, fill=255, anchor="ls"
                        )
                else:
                    mask_draw.text((-bbox[0], -bbox[1]), line, font=font, fill=255, anchor="lt")
                fill_clip.putalpha(mask)

                image.alpha_composite(fill_clip, (line_pixel_left, line_pixel_top))
        else:
            for line, x, y, _ in line_layouts:
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

    def get_text_base_position(self, layer: TextLayer) -> tuple[int, int]:
        """Return base (x, y) for text, deriving from alignment when position is not set."""
        if layer.position is not None:
            return (
                parse_coordinate(layer.position[0], self._ctx.width),
                parse_coordinate(layer.position[1], self._ctx.height),
            )
        if layer.align:
            h_map = {"left": 0, "center": self._ctx.width // 2, "right": self._ctx.width}
            v_map = {"top": 0, "middle": self._ctx.height // 2, "bottom": self._ctx.height}
            return h_map[layer.align.horizontal], v_map[layer.align.vertical]
        return 0, 0

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

        base_x, base_y = self.get_text_base_position(layer)
        x = self.get_horizontal_start_x(base_x, total_width, layer.align)
        y = self.get_vertical_start_y(base_y, text_height, layer.align)
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

        if layer.fill is not None:
            # Build fill image over the letter-spaced text bounding box and mask with glyphs.
            bbox_ls = font.getbbox(content, anchor="ls")
            baseline_y_in_mask = int(-bbox_ls[1])
            fill_img = self._create_text_fill_image((total_width, text_height), layer.fill)

            # Draw stroke first so the stroke ring stays visible after fill compositing.
            if stroke_effects:
                for stroke in stroke_effects:
                    stroke_color = self._effects.parse_color(stroke.color)
                    self._draw_text_with_letter_spacing(
                        draw,
                        content,
                        position,
                        font,
                        stroke_color,
                        letter_spacing,
                        [stroke],
                        char_widths,
                    )

            mask = Image.new("L", (total_width, text_height), 0)
            mask_draw = ImageDraw.Draw(mask)
            for char, char_x in self._iterate_letter_spaced_positions(
                content, letter_spacing, char_widths, 0
            ):
                mask_draw.text((char_x, baseline_y_in_mask), char, font=font, fill=255, anchor="ls")

            fill_img.putalpha(mask)
            image.alpha_composite(fill_img, (x, y))
        else:
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
        position = self.get_text_base_position(layer)
        anchor = self._get_text_anchor(layer.align)

        for bg in background_effects:
            self._render_background(image, content, font, position, bg, anchor)

        self._render_text_effects(
            image, content, font, position, glow_effects, shadow_effects, anchor
        )

        if layer.fill is not None:
            self._draw_filled_text(
                image, content, position, font, layer.fill, stroke_effects, anchor
            )
        else:
            self._draw_text(draw, content, position, font, color, stroke_effects, anchor)

    def _render_rotated_simple_text(self, image: Image.Image, layer: TextLayer):
        """Render simple text with rotation applied.

        Rotation is performed by rendering text to a temporary image, rotating it,
        then compositing the result onto the main canvas. This approach preserves
        all text effects during rotation.
        """
        stroke_effects = self._get_stroke_effects(layer.effects)
        shadow_effects = self._get_shadow_effects(layer.effects)
        glow_effects = self._get_glow_effects(layer.effects)

        text_width, text_height = self.measure_text_size(layer)
        padding = self._calculate_text_effects_padding(stroke_effects, shadow_effects, glow_effects)
        temp_image, _ = self._create_temp_image_for_text(text_width, text_height, padding)

        # Re-render through the one dispatcher, unrotated, anchored inside the padding.
        temp_layer = layer.model_copy(
            update={
                "position": (padding, padding),
                "align": None,
                "rotation": 0.0,
                "auto_scale": False,
            }
        )
        self._render_simple_text(temp_image, temp_layer)
        self._rotate_and_composite_text(image, temp_image, layer)

    def measure_text_size(self, layer: TextLayer) -> tuple[int, int]:
        """Calculate rendered text bounding box size accounting for wrapping."""
        return self.measure_text_layout(layer)["size"]

    def _render_rotated_rich_text(self, image: Image.Image, layer: TextLayer):
        """Render rich text with rotation applied.

        Rotation is performed by rendering to a temporary image, rotating it,
        then compositing the result. This preserves all text effects and handles
        per-part styling correctly.
        """
        if not isinstance(layer.content, list):
            return

        text_width, text_height = self.measure_text_size(layer)
        padding = self._calculate_rich_text_effects_padding(layer)
        temp_image, _ = self._create_temp_image_for_text(text_width, text_height, padding)

        # Re-render through the one dispatcher, unrotated, anchored inside the padding.
        temp_layer = layer.model_copy(
            update={
                "position": (padding, padding),
                "align": None,
                "rotation": 0.0,
                "auto_scale": False,
            }
        )
        self._render_rich_text(temp_image, temp_layer)
        self._rotate_and_composite_text(image, temp_image, layer)

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

        base_x, base_y = self.get_text_base_position(layer)

        if layer.align:
            base_x, base_y = apply_alignment(base_x, base_y, rotated.size, layer.align)

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
        wrapped_lines: list[str] = []

        for paragraph in text.split("\n"):
            words = paragraph.split()

            if not words:
                wrapped_lines.append("")
                continue

            current_line: list[str] = []
            for word in words:
                test_line = " ".join(current_line + [word])

                width, _ = self.measure_text_bounds(test_line, font, letter_spacing or 0)

                if width <= max_width:
                    current_line.append(word)
                else:
                    if current_line:
                        wrapped_lines.append(" ".join(current_line))
                        current_line = [word]
                    else:
                        warnings.warn(
                            f"Word '{word}' exceeds max_width and cannot be wrapped.",
                            UserWarning,
                            stacklevel=2,
                        )
                        wrapped_lines.append(word)

            if current_line:
                wrapped_lines.append(" ".join(current_line))

        return wrapped_lines

    def measure_text_bounds(
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

    def get_vertical_start_y(self, base_y: int, total_height: int, align: Align | None) -> int:
        if not align:
            return base_y

        vertical_align = align.vertical
        if vertical_align == "middle":
            return base_y - total_height // 2
        elif vertical_align == "bottom":
            return base_y - total_height
        return base_y

    def get_horizontal_start_x(self, base_x: int, line_width: int, align: Align | None) -> int:
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
                    stroke_fill=self._effects.parse_color(stroke.color),
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

        glow_color = self._effects.parse_color(glow.color)
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

        glow_color = self._effects.parse_color(glow.color)
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

        shadow_color = self._effects.parse_color(shadow.color)
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
        shadow_color = self._effects.parse_color(shadow.color)

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

        self._render_background_box(
            image,
            position[0] + int(bbox[0]),
            position[1] + int(bbox[1]),
            text_width,
            text_height,
            background,
        )

    def _render_background_box(
        self,
        image: Image.Image,
        content_left: int,
        content_top: int,
        content_width: int,
        content_height: int,
        background: Background,
    ) -> None:
        """Render a background box around a measured content rectangle."""
        pad_top, pad_right, pad_bottom, pad_left = parse_padding(background.padding)

        bg_width = content_width + pad_left + pad_right
        bg_height = content_height + pad_top + pad_bottom

        bg_color = self._effects.apply_opacity_to_color(
            self._effects.parse_color(background.color), background.opacity
        )

        # Draw background shape; supersample rounded corners for anti-aliased edges.
        if background.border_radius > 0:
            scale = 4
            bg_big = Image.new("RGBA", (bg_width * scale, bg_height * scale), (0, 0, 0, 0))
            bg_draw_big = ImageDraw.Draw(bg_big)
            bg_draw_big.rounded_rectangle(
                [0, 0, bg_width * scale - 1, bg_height * scale - 1],
                radius=background.border_radius * scale,
                fill=bg_color,
            )
            bg_layer = bg_big.resize((bg_width, bg_height), Image.Resampling.LANCZOS)
        else:
            bg_layer = Image.new("RGBA", (bg_width, bg_height), (0, 0, 0, 0))
            bg_draw = ImageDraw.Draw(bg_layer)
            bg_draw.rectangle([(0, 0), (bg_width - 1, bg_height - 1)], fill=bg_color)

        paste_x = content_left - pad_left
        paste_y = content_top - pad_top

        image.paste(bg_layer, (paste_x, paste_y), bg_layer)

    def _get_stroke_effects(self, effects: list[TextEffect]) -> list[Stroke]:
        return [e for e in effects if isinstance(e, Stroke)]

    def _get_shadow_effects(self, effects: list[TextEffect]) -> list[Shadow]:
        return [e for e in effects if isinstance(e, Shadow)]

    def _get_glow_effects(self, effects: list[TextEffect]) -> list[Glow]:
        return [e for e in effects if isinstance(e, Glow)]

    def _get_background_effects(self, effects: list[TextEffect]) -> list[Background]:
        return [e for e in effects if isinstance(e, Background)]
