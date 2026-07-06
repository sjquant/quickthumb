"""Shared infrastructure for the document exporters (SVG, HTML, PPTX).

The exporters keep layers as native vector/text primitives where the target
format can express them, and fall back to embedding pixel-exact PNG fragments
rendered by the regular PIL pipeline everywhere else. This module hosts the
pieces they share: layer flattening, backdrop-dependency splitting, per-layer
rasterization, font-face resolution/embedding, and a text block layout that
mirrors TextEngine's positioning math run for run.
"""

from __future__ import annotations

import base64
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from io import BytesIO
from typing import TYPE_CHECKING

from PIL import Image, ImageFont

from quickthumb._base import (
    DEFAULT_LINE_HEIGHT_MULTIPLIER,
    DEFAULT_TEXT_COLOR,
    FontType,
    apply_alignment,
    expanded_rotation_size,
    parse_coordinate,
)
from quickthumb._composition import has_layer_composition
from quickthumb.errors import RenderingError
from quickthumb.models import (
    Align,
    Background,
    Glow,
    GroupLayer,
    LinearGradient,
    RadialGradient,
    Shadow,
    ShapeLayer,
    Stroke,
    SvgLayer,
    TextFillImage,
    TextLayer,
)

if TYPE_CHECKING:
    from quickthumb.canvas import Canvas, RenderableLayer

Box = tuple[float, float, float, float]  # left, top, right, bottom


def _fmt(value: float) -> str:
    """Format a coordinate compactly: integers stay integers, floats keep 2 dp."""
    if isinstance(value, int) or float(value).is_integer():
        return str(int(value))
    return f"{value:.2f}"


def flatten_layers(canvas: Canvas) -> list[RenderableLayer]:
    """Resolve group layers into placed children so exporters see a flat list."""
    flat: list[RenderableLayer] = []
    for layer in canvas.layers:
        if isinstance(layer, GroupLayer) and not has_layer_composition(layer):
            flat.extend(_flatten_group(canvas, layer))
        else:
            flat.append(layer)
    return flat


def _flatten_group(
    canvas: Canvas,
    group: GroupLayer,
    origin: tuple[int, int] | None = None,
    inherited_animation=None,
) -> list[RenderableLayer]:
    # An enclosing animated group wins over this group's own animation, so the
    # outermost animation drives everything beneath it. Every flattened child
    # carries the *same* animation object; the PPTX exporter recognises that
    # shared identity to animate the whole group as one effect.
    animation = inherited_animation or group.animation
    placements, _ = canvas._groups.layout_group(group, origin)
    placed: list[RenderableLayer] = []
    for child, position, size in placements:
        if isinstance(child, GroupLayer):
            if has_layer_composition(child):
                placed.append(
                    _with_group_animation(
                        child.model_copy(update={"position": position, "align": None}),
                        animation,
                    )
                )
            else:
                placed.extend(
                    _flatten_group(canvas, child, position, inherited_animation=animation)
                )
        elif isinstance(child, TextLayer):
            placed.append(
                _with_group_animation(
                    canvas._groups.place_text_child(child, position, size), animation
                )
            )
        elif isinstance(child, ShapeLayer):
            placed.append(
                _with_group_animation(
                    child.model_copy(update={"position": position, "align": None}), animation
                )
            )
        else:  # ImageLayer | SvgLayer
            placed.append(
                _with_group_animation(
                    child.model_copy(update={"position": position, "align": Align.TOP_LEFT}),
                    animation,
                )
            )
    return placed


def _with_group_animation(layer, animation):
    """Stamp a group's animation onto one of its flattened children.

    A group animation drives all of the group's children as one effect and takes
    precedence over any animation set on a child. When the group has none, the
    child keeps whatever animation it set itself.
    """
    if animation is None:
        return layer
    return layer.model_copy(update={"animation": animation})


def is_backdrop_dependent(layer: RenderableLayer) -> bool:
    """True for layers whose pixels depend on the already-composited content below."""
    from quickthumb.canvas import CustomLayer

    if isinstance(layer, CustomLayer):
        return True
    return getattr(layer, "blend_mode", None) is not None


def split_backdrop_prefix(
    layers: list[RenderableLayer],
) -> tuple[list[RenderableLayer], list[RenderableLayer]]:
    """Split layers at the last backdrop-dependent layer.

    Everything up to and including that layer must be rasterized as one composite
    so blend modes and custom callbacks see the backdrop they blend against.
    """
    last = -1
    for index, layer in enumerate(layers):
        if is_backdrop_dependent(layer):
            last = index
    return layers[: last + 1], layers[last + 1 :]


@dataclass
class RasterFragment:
    """A PNG-encoded patch of one or more layers, cropped to its visible bounds."""

    png_bytes: bytes
    x: int
    y: int
    width: int
    height: int


def rasterize_layers(canvas: Canvas, layers: list[RenderableLayer]) -> RasterFragment | None:
    """Render layers through the PIL pipeline and crop the result to its bounds."""
    image = Image.new("RGBA", (canvas.width, canvas.height), (0, 0, 0, 0))
    for layer in layers:
        canvas._render_layer(image, layer)
    bbox = image.getbbox()
    if bbox is None:
        return None
    cropped = image.crop(bbox)
    buffer = BytesIO()
    cropped.save(buffer, format="PNG")
    return RasterFragment(buffer.getvalue(), bbox[0], bbox[1], cropped.width, cropped.height)


def color_to_rgba(canvas: Canvas, color: str | tuple, opacity: float = 1.0) -> tuple:
    """Parse any supported color into an (r, g, b, a) tuple with opacity applied."""
    parsed = canvas._effects.parse_color(color)
    if len(parsed) == 3:
        parsed = (*parsed, 255)
    if opacity < 1.0:
        parsed = canvas._effects.apply_opacity_to_color(parsed, opacity)
    return parsed


def rgb_hex(rgba: tuple) -> str:
    return "#{:02X}{:02X}{:02X}".format(*rgba[:3])


def read_svg_layer_bytes_and_size(layer: SvgLayer) -> tuple[bytes, tuple[int, int]]:
    """Read an SVG layer and resolve its rendered dimensions."""
    with open(layer.path, "rb") as svg_file:
        svg_bytes = svg_file.read()

    intrinsic = intrinsic_svg_size(svg_bytes, layer.path)
    width, height = layer.width, layer.height
    if width and height:
        return svg_bytes, (width, height)
    if width:
        return svg_bytes, (width, round(width * intrinsic[1] / intrinsic[0]))
    if height:
        return svg_bytes, (round(height * intrinsic[0] / intrinsic[1]), height)
    return svg_bytes, (round(intrinsic[0]), round(intrinsic[1]))


def intrinsic_svg_size(svg_bytes: bytes, path: str) -> tuple[float, float]:
    """Resolve SVG intrinsic size from width/height or viewBox metadata."""
    try:
        root = ET.fromstring(svg_bytes)
    except ET.ParseError as e:
        raise RenderingError(f"Cannot read SVG dimensions for '{path}': {e}") from e

    width = _parse_svg_length(root.get("width"))
    height = _parse_svg_length(root.get("height"))
    if width and height:
        return width, height

    view_box = root.get("viewBox")
    if view_box:
        parts = view_box.replace(",", " ").split()
        if len(parts) == 4:
            try:
                view_width = float(parts[2])
                view_height = float(parts[3])
            except ValueError:
                view_width = view_height = 0
            if view_width > 0 and view_height > 0:
                return view_width, view_height

    raise RenderingError(
        f"Cannot determine dimensions for SVG '{path}'. "
        "Set width and height or include width/height/viewBox in the SVG."
    )


def _parse_svg_length(value: str | None) -> float | None:
    if value is None:
        return None
    match = re.fullmatch(r"\s*([0-9]+(?:\.[0-9]+)?)(?:px)?\s*", value)
    if not match:
        return None
    return float(match.group(1))


def resolve_font_face(run: TextRunLayout) -> tuple[str, str, str, str | None]:
    """Resolve (family, css weight, css style, embeddable font path) for a run.

    Shared by the SVG and HTML exporters so a run maps to the same font face
    rules in every vector export. ``path`` is the local font file to pass to
    ``font_face_declarations`` for embedding, or ``None`` when Pillow has no
    file to embed for this run's font (e.g. the built-in bitmap default).
    """
    font = run.font
    if isinstance(font, ImageFont.FreeTypeFont):
        family = font.getname()[0] or "sans-serif"
        path = getattr(font, "path", None)
    else:
        family = "sans-serif"
        path = None

    if isinstance(run.weight, int):
        weight = str(run.weight)
    elif isinstance(run.weight, str) and run.weight.isdigit():
        weight = run.weight
    elif run.bold or (isinstance(run.weight, str) and run.weight.lower() == "bold"):
        weight = "700"
    else:
        weight = "400"
    style = "italic" if run.italic else "normal"

    return family, weight, style, path if isinstance(path, str) else None


def font_face_declarations(font_faces: dict[str, tuple[str, str, str]]) -> str:
    """Build ``@font-face`` rules embedding each font file as a base64 data URL.

    Shared by the SVG and HTML exporters; each wraps the result for its own
    document (SVG in a ``<style>`` element, HTML inline in its own stylesheet).
    """
    faces = []
    for path, (family, weight, style) in font_faces.items():
        try:
            with open(path, "rb") as font_file:
                encoded = base64.b64encode(font_file.read()).decode("ascii")
        except OSError:
            continue
        faces.append(
            "@font-face{"
            f"font-family:{_css_string(family)};"
            f"src:url(data:font/ttf;base64,{encoded}) format('truetype');"
            f"font-weight:{weight};font-style:{style};}}"
        )
    return "".join(faces)


def _css_string(value: str) -> str:
    escaped = (
        value.replace("\\", "\\\\")
        .replace("&", "\\26 ")
        .replace('"', "\\22 ")
        .replace("'", "\\'")
        .replace("\r", "")
        .replace("\n", "\\A ")
        .replace("<", "\\3C ")
        .replace(">", "\\3E ")
    )
    return f"'{escaped}'"


def union_boxes(boxes: list[Box]) -> Box | None:
    if not boxes:
        return None
    return (
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        max(box[3] for box in boxes),
    )


def uses_image_fill(layer: TextLayer) -> bool:
    """True when the layer or any rich part fills glyphs with an image texture."""
    if isinstance(layer.fill, TextFillImage):
        return True
    if isinstance(layer.content, list):
        return any(isinstance(part.fill, TextFillImage) for part in layer.content)
    return False


def uses_radial_fill(layer: TextLayer) -> bool:
    """True when the layer or any rich part fills glyphs with a radial gradient."""
    if isinstance(layer.fill, RadialGradient):
        return True
    if isinstance(layer.content, list):
        return any(isinstance(part.fill, RadialGradient) for part in layer.content)
    return False


@dataclass
class TextRunLayout:
    """One styled run of text placed at absolute (pre-rotation) canvas coordinates."""

    text: str
    font: FontType
    pen_x: float
    baseline_y: float
    ink_box: Box
    color: tuple
    fill: LinearGradient | RadialGradient | TextFillImage | None
    fill_box: Box | None
    letter_spacing: int
    char_xs: list[float] | None
    font_name: str | None
    size: int
    bold: bool
    italic: bool
    weight: int | str | None
    strokes: list[Stroke] = field(default_factory=list)
    shadows: list[Shadow] = field(default_factory=list)
    glows: list[Glow] = field(default_factory=list)
    backgrounds: list[Background] = field(default_factory=list)
    bg_box: Box | None = None  # content box the Background effect pads around


@dataclass
class TextBlockLayout:
    """A text layer resolved into positioned runs, mirroring TextEngine output."""

    lines: list[list[TextRunLayout]]
    line_heights: list[int]
    block_box: Box | None
    block_backgrounds: list[Background]
    block_bg_box: Box | None
    opacity: float
    rotation: float = 0.0
    # For rotated layers, run coordinates are local to a padded staging box that
    # is placed at `origin` and rotated about `rot_center_local` (clockwise).
    origin: tuple[float, float] | None = None
    rot_center_local: tuple[float, float] | None = None


def compute_text_layout(canvas: Canvas, layer: TextLayer) -> TextBlockLayout:
    """Resolve a text layer into positioned runs using the engine's own math."""
    text = canvas._text
    layer = text.effective_layer(layer)

    if layer.rotation != 0:
        return _compute_rotated_layout(canvas, layer)

    if isinstance(layer.content, list):
        lines, line_heights = _layout_rich(canvas, layer)
        block_backgrounds: list[Background] = []
        block_bg_box: Box | None = None
    else:
        lines, line_heights, block_backgrounds, block_bg_box = _layout_simple(canvas, layer)

    block_box = union_boxes([run.ink_box for line in lines for run in line])
    return TextBlockLayout(
        lines=lines,
        line_heights=line_heights,
        block_box=block_box,
        block_backgrounds=block_backgrounds,
        block_bg_box=block_bg_box,
        opacity=layer.opacity,
    )


def _compute_rotated_layout(canvas: Canvas, layer: TextLayer) -> TextBlockLayout:
    """Mirror the engine's rotate-a-staging-image path as a transform description."""
    text = canvas._text

    text_w, text_h = text.measure_text_size(layer)
    if isinstance(layer.content, list):
        padding = text._calculate_rich_text_effects_padding(layer)
    else:
        padding = text._calculate_text_effects_padding(
            text._get_stroke_effects(layer.effects),
            text._get_shadow_effects(layer.effects),
            text._get_glow_effects(layer.effects),
        )

    temp_w, temp_h = text_w + padding * 2, text_h + padding * 2
    rotated_size = expanded_rotation_size((temp_w, temp_h), layer.rotation, scale=1)

    base_x, base_y = text.get_text_base_position(layer)
    if layer.align:
        base_x, base_y = apply_alignment(base_x, base_y, rotated_size, layer.align)

    origin = (
        base_x + (rotated_size[0] - temp_w) / 2,
        base_y + (rotated_size[1] - temp_h) / 2,
    )

    inner_layer = layer.model_copy(
        update={
            "position": (padding, padding),
            "align": None,
            "rotation": 0.0,
            "auto_scale": False,
        }
    )
    inner = compute_text_layout(canvas, inner_layer)
    return TextBlockLayout(
        lines=inner.lines,
        line_heights=inner.line_heights,
        block_box=inner.block_box,
        block_backgrounds=inner.block_backgrounds,
        block_bg_box=inner.block_bg_box,
        opacity=layer.opacity,
        rotation=layer.rotation,
        origin=origin,
        rot_center_local=(temp_w / 2, temp_h / 2),
    )


def _layout_simple(
    canvas: Canvas, layer: TextLayer
) -> tuple[list[list[TextRunLayout]], list[int], list[Background], Box | None]:
    text = canvas._text
    font = canvas._fonts.load_font(layer)
    color = color_to_rgba(canvas, layer.color) if layer.color else (*DEFAULT_TEXT_COLOR, 255)
    content = layer.content if isinstance(layer.content, str) else ""

    if not content:
        return [], [], [], None

    if layer.max_width:
        max_width_px = parse_coordinate(layer.max_width, canvas._ctx.width)
        lines_text = text._wrap_text(content, font, max_width_px, layer.letter_spacing)
        return _layout_simple_multiline(canvas, layer, lines_text, font, color)
    if "\n" in content:
        return _layout_simple_multiline(canvas, layer, content.split("\n"), font, color)
    if layer.letter_spacing:
        return _layout_simple_letter_spaced(canvas, layer, content, font, color)
    return _layout_simple_anchor(canvas, layer, content, font, color)


def _make_simple_run(
    layer: TextLayer,
    text_value: str,
    font: FontType,
    color: tuple,
    pen_x: float,
    baseline_y: float,
    ink_box: Box,
    char_xs: list[float] | None,
    bg_box: Box | None,
    fill_box: Box | None,
    backgrounds: list[Background],
    text_engine,
) -> TextRunLayout:
    from quickthumb._base import DEFAULT_TEXT_SIZE

    return TextRunLayout(
        text=text_value,
        font=font,
        pen_x=pen_x,
        baseline_y=baseline_y,
        ink_box=ink_box,
        color=color,
        fill=layer.fill,
        fill_box=fill_box,
        letter_spacing=layer.letter_spacing or 0,
        char_xs=char_xs,
        font_name=layer.font,
        size=layer.size or DEFAULT_TEXT_SIZE,
        bold=layer.bold,
        italic=layer.italic,
        weight=layer.weight,
        strokes=text_engine._get_stroke_effects(layer.effects),
        shadows=text_engine._get_shadow_effects(layer.effects),
        glows=text_engine._get_glow_effects(layer.effects),
        backgrounds=backgrounds,
        bg_box=bg_box,
    )


def _layout_simple_anchor(canvas, layer, content, font, color):
    """Single line, no wrapping or spacing: anchor-positioned like draw.text()."""
    text = canvas._text
    x, y = text.get_text_base_position(layer)
    anchor = text._get_text_anchor(layer.align)
    bbox_anchor = font.getbbox(content, anchor=anchor)
    bbox_baseline = font.getbbox(content, anchor="ls")

    pen_x = x + bbox_anchor[0] - bbox_baseline[0]
    baseline_y = y + bbox_anchor[1] - bbox_baseline[1]
    ink_box = (x + bbox_anchor[0], y + bbox_anchor[1], x + bbox_anchor[2], y + bbox_anchor[3])

    backgrounds = text._get_background_effects(layer.effects)
    run = _make_simple_run(
        layer,
        content,
        font,
        color,
        pen_x,
        baseline_y,
        ink_box,
        None,
        ink_box,
        ink_box if layer.fill else None,
        backgrounds,
        text,
    )
    return [[run]], [], [], None


def _layout_simple_letter_spaced(canvas, layer, content, font, color):
    """Single line with letter spacing: per-character pen positions."""
    text = canvas._text
    letter_spacing = layer.letter_spacing or 0
    total_width, char_widths = text._calculate_spaced_text_width(content, font, letter_spacing)
    bbox = font.getbbox(content)
    text_height = int(bbox[3] - bbox[1])

    base_x, base_y = text.get_text_base_position(layer)
    x = text.get_horizontal_start_x(base_x, total_width, layer.align)
    y = text.get_vertical_start_y(base_y, text_height, layer.align)

    bbox_top = font.getbbox(content, anchor="lt")
    bbox_baseline = font.getbbox(content, anchor="ls")
    baseline_y = y - bbox_baseline[1]
    char_xs = [
        char_x
        for _, char_x in text._iterate_letter_spaced_positions(
            content, letter_spacing, char_widths, x
        )
    ]
    ink_box = (x, y, x + total_width, y + text_height)
    bg_box = (
        x + bbox_top[0],
        y + bbox_top[1],
        x + bbox_top[0] + total_width,
        y + bbox_top[1] + text_height,
    )

    backgrounds = text._get_background_effects(layer.effects)
    run = _make_simple_run(
        layer,
        content,
        font,
        color,
        x,
        baseline_y,
        ink_box,
        char_xs,
        bg_box,
        ink_box if layer.fill else None,
        backgrounds,
        text,
    )
    return [[run]], [], [], None


def _layout_simple_multiline(canvas, layer, lines_text, font, color):
    """Wrapped or explicit multi-line text: mirrors _render_multiline_text."""
    text = canvas._text
    multiplier = layer.line_height or DEFAULT_LINE_HEIGHT_MULTIPLIER
    line_height = text._calculate_line_height(font, multiplier)
    total_height = line_height * len(lines_text)

    base_x, base_y = text.get_text_base_position(layer)
    start_y = text.get_vertical_start_y(base_y, total_height, layer.align)
    letter_spacing = layer.letter_spacing or 0

    line_layouts: list[tuple[str, float, float, tuple]] = []
    for index, line in enumerate(lines_text):
        line_width, _ = text.measure_text_bounds(line, font, letter_spacing, multiplier)
        y = start_y + index * line_height
        x = text.get_horizontal_start_x(base_x, line_width, layer.align)
        bbox = font.getbbox(line, anchor="lt")
        line_layouts.append((line, x, y, bbox))

    # Background and fill boxes span the whole block, exactly as the engine computes.
    content_box = union_boxes(
        [(x + bbox[0], y + bbox[1], x + bbox[2], y + bbox[3]) for _, x, y, bbox in line_layouts]
    )
    assert content_box is not None  # lines_text is never empty here
    if layer.fill and letter_spacing:
        spaced_widths = {
            line: text._calculate_spaced_text_width(line, font, letter_spacing)[0]
            for line, _, _, _ in line_layouts
        }
        fill_box = (
            min(x for _, x, _, _ in line_layouts),
            content_box[1],
            max(x + spaced_widths[line] for line, x, _, _ in line_layouts),
            content_box[3],
        )
    else:
        fill_box = content_box

    backgrounds = text._get_background_effects(layer.effects)
    lines: list[list[TextRunLayout]] = []
    for line, x, y, bbox in line_layouts:
        if not line:
            lines.append([])
            continue
        bbox_baseline = font.getbbox(line, anchor="ls")
        if letter_spacing:
            total_width, char_widths = text._calculate_spaced_text_width(line, font, letter_spacing)
            char_xs = [
                char_x
                for _, char_x in text._iterate_letter_spaced_positions(
                    line, letter_spacing, char_widths, int(x)
                )
            ]
            pen_x = x
            baseline_y = y - bbox_baseline[1]
            ink_box = (x, y + bbox[1], x + total_width, y + bbox[3])
        else:
            char_xs = None
            pen_x = x + bbox[0] - bbox_baseline[0]
            baseline_y = y + bbox[1] - bbox_baseline[1]
            ink_box = (x + bbox[0], y + bbox[1], x + bbox[2], y + bbox[3])
        run = _make_simple_run(
            layer,
            line,
            font,
            color,
            pen_x,
            baseline_y,
            ink_box,
            char_xs,
            None,
            fill_box if layer.fill else None,
            [],
            text,
        )
        lines.append([run])

    line_heights = [line_height] * len(lines_text)
    return lines, line_heights, backgrounds, content_box


def _layout_rich(canvas, layer) -> tuple[list[list[TextRunLayout]], list[int]]:
    """Rich (multi-part) text: mirrors _render_rich_text / _draw_rich_text_lines."""
    text = canvas._text
    fonts = canvas._fonts

    lines_data = text._prepare_rich_text_lines(layer, apply_wrapping=not layer.auto_scale)
    line_heights, total_height = text._calculate_rich_text_dimensions(layer, lines_data)
    base_x, start_y = text._calculate_start_position(layer, total_height)

    lines: list[list[TextRunLayout]] = []
    current_y = start_y
    for index, line_parts in enumerate(lines_data):
        line_height = line_heights[index]

        metadata = []
        line_width = 0
        for part in line_parts:
            font = fonts.load_font_variant(
                part["font_name"], part["size"], part["bold"], part["italic"], part["weight"]
            )
            width, _ = text.measure_text_bounds(part["text"], font, part["letter_spacing"])
            metadata.append((font, width))
            line_width += width

        current_x = text.get_horizontal_start_x(base_x, line_width, layer.align)
        runs: list[TextRunLayout] = []
        for part, (font, width) in zip(line_parts, metadata, strict=True):
            bbox_default = font.getbbox(part["text"])
            text_height = int(bbox_default[3] - bbox_default[1])
            vertical_offset = (line_height - text_height) // 2
            adjusted_y = current_y + vertical_offset

            bbox_top = font.getbbox(part["text"], anchor="lt")
            bbox_baseline = font.getbbox(part["text"], anchor="ls")
            letter_spacing = part["letter_spacing"]
            if letter_spacing:
                total_width, char_widths = text._calculate_spaced_text_width(
                    part["text"], font, letter_spacing
                )
                char_xs = [
                    char_x
                    for _, char_x in text._iterate_letter_spaced_positions(
                        part["text"], letter_spacing, char_widths, current_x
                    )
                ]
                pen_x: float = current_x
                baseline_y = adjusted_y - bbox_baseline[1]
                ink_box: Box = (
                    current_x,
                    adjusted_y,
                    current_x + total_width,
                    adjusted_y + text_height,
                )
            else:
                char_xs = None
                pen_x = current_x + bbox_top[0] - bbox_baseline[0]
                baseline_y = adjusted_y + bbox_top[1] - bbox_baseline[1]
                ink_box = (
                    current_x + bbox_top[0],
                    adjusted_y + bbox_top[1],
                    current_x + bbox_top[2],
                    adjusted_y + bbox_top[3],
                )

            bg_box = (
                current_x + bbox_top[0],
                adjusted_y + bbox_top[1],
                current_x + bbox_top[2],
                adjusted_y + bbox_top[3],
            )
            color = part["color"]
            if len(color) == 3:
                color = (*color, 255)
            runs.append(
                TextRunLayout(
                    text=part["text"],
                    font=font,
                    pen_x=pen_x,
                    baseline_y=baseline_y,
                    ink_box=ink_box,
                    color=color,
                    fill=part["fill"],
                    fill_box=ink_box if part["fill"] else None,
                    letter_spacing=letter_spacing,
                    char_xs=char_xs,
                    font_name=part["font_name"],
                    size=part["size"],
                    bold=bool(part["bold"]),
                    italic=bool(part["italic"]),
                    weight=part["weight"],
                    strokes=part["stroke_effects"],
                    shadows=part["shadow_effects"],
                    glows=part["glow_effects"],
                    backgrounds=part["background_effects"],
                    bg_box=bg_box,
                )
            )
            current_x += width

        lines.append(runs)
        current_y += line_height

    return lines, line_heights
