import os
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from io import BytesIO
from typing import Any, Literal, cast

from PIL import Image, ImageDraw
from typing_extensions import Self

from quickthumb._base import FileFormat, RenderContext, aspect_ratio_dimensions, is_url
from quickthumb._diagnostics import DiagnosticsEngine
from quickthumb._effects import EffectsEngine
from quickthumb._fonts import FontEngine
from quickthumb._groups import GroupEngine
from quickthumb._images import ImageEngine
from quickthumb._measurements import BBox, LayerMeasurement, measure_layers
from quickthumb._shapes import ShapeEngine
from quickthumb._text import TextEngine
from quickthumb.errors import RenderingError, ValidationError
from quickthumb.models import (
    Align,
    AnimationInput,
    BackgroundEffect,
    BackgroundLayer,
    BlendMode,
    CanvasInspection,
    FitMode,
    Grain,
    GroupLayer,
    ImageEffect,
    ImageLayer,
    InspectionBBox,
    LayerInspection,
    LayerType,
    LinearGradient,
    OutlineLayer,
    RadialGradient,
    ShapeEffect,
    ShapeLayer,
    SvgLayer,
    TextFillImage,
    TextInspection,
    TextLayer,
    TextPart,
)


@dataclass
class CustomLayer:
    fn: Callable[..., Image.Image | None]
    name: str | None = None
    kwargs: dict = field(default_factory=dict)


RenderableLayer = LayerType | CustomLayer
TextContentInput = str | list[TextPart | dict[str, Any]]

_THEME_REF_RE = re.compile(r"\$theme\.([A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)*)")
_VAR_RE = re.compile(r"\$\{(\w+)\}|\$(\w+)")


def _is_theme_reference(match: re.Match) -> bool:
    """True when a $var match is really a $theme.* token, resolved later by from_json."""
    return match.group(2) == "theme" and match.string[match.end() : match.end() + 1] == "."


def _lookup_theme_token(path: str, theme: dict, seen: frozenset = frozenset()):
    if path in seen:
        raise ValidationError(f"Theme token '$theme.{path}' is part of a circular reference.")
    node = theme
    for key in path.split("."):
        if not isinstance(node, dict) or key not in node:
            raise ValidationError(
                f"Theme token '$theme.{path}' is not defined in the spec's theme block."
            )
        node = node[key]
    # Theme values may themselves reference other theme tokens (aliases).
    return _resolve_theme_tokens(node, theme, seen | {path})


def _resolve_theme_tokens(value, theme: dict, seen: frozenset = frozenset()):
    """Recursively replace $theme.path references in a parsed JSON structure."""
    if isinstance(value, str):
        full_match = _THEME_REF_RE.fullmatch(value)
        if full_match:
            return _lookup_theme_token(full_match.group(1), theme, seen)

        def replace(match: re.Match) -> str:
            token = _lookup_theme_token(match.group(1), theme, seen)
            if isinstance(token, bool) or not isinstance(token, (str, int, float)):
                raise ValidationError(
                    f"Theme token '$theme.{match.group(1)}' must be a string or number "
                    "to be embedded inside a longer string."
                )
            return str(token)

        return _THEME_REF_RE.sub(replace, value)
    if isinstance(value, list):
        return [_resolve_theme_tokens(item, theme, seen) for item in value]
    if isinstance(value, dict):
        return {key: _resolve_theme_tokens(item, theme, seen) for key, item in value.items()}
    return value


class Canvas:
    _custom_layer_registry: dict[str, Callable[..., Image.Image | None]] = {}
    _template_registry: dict[str, str] = {}

    _BUILTIN_TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")

    _UNSIZED_MESSAGE = (
        "This Canvas has no size yet. Construct it as Canvas(width, height), "
        "or add it to a Deck created with a size (Deck(width, height))."
    )

    @classmethod
    def register_layer_fn(cls, name: str, fn: Callable[..., Image.Image | None]) -> None:
        cls._custom_layer_registry[name] = fn

    @classmethod
    def unregister_layer_fn(cls, name: str) -> None:
        cls._custom_layer_registry.pop(name, None)

    @classmethod
    def register_template(cls, name: str, path: str) -> None:
        cls._template_registry[name] = path

    @classmethod
    def unregister_template(cls, name: str) -> None:
        cls._template_registry.pop(name, None)

    def __init__(
        self,
        width: int | None = None,
        height: int | None = None,
        layers: list[RenderableLayer] | None = None,
    ):
        if (width is None) != (height is None):
            raise ValidationError("Provide both width and height, or neither.")
        if width is not None and width <= 0:
            raise ValidationError("width must be > 0")
        if height is not None and height <= 0:
            raise ValidationError("height must be > 0")

        # An unsized canvas defers its dimensions until a Deck injects them. Layer
        # builders never need a size (coordinates resolve at render time), so the
        # placeholder ctx stays valid; render/diagnose/serialize guard on _has_size.
        self._has_size = width is not None
        self._ctx = RenderContext(width or 0, height or 0)
        self._layers: list[RenderableLayer] = layers or []

        self._effects = EffectsEngine()
        self._fonts = FontEngine()
        self._images = ImageEngine(self._ctx, self._effects)
        self._text = TextEngine(self._ctx, self._fonts, self._effects, self._images)
        self._shapes = ShapeEngine(self._ctx, self._effects, self._images)
        self._groups = GroupEngine(self._ctx, self._fonts, self._images, self._shapes, self._text)
        self._diagnostics = DiagnosticsEngine(
            self._ctx, self, self._effects, self._fonts, self._text, self._groups
        )

    @property
    def has_size(self) -> bool:
        """Whether the canvas has concrete dimensions (False until a Deck assigns them)."""
        return self._has_size

    def _inherit_size(self, width: int, height: int) -> None:
        """Assign a size to an unsized canvas; no-op if it already has one.

        Used by Deck so an unsized slide picks up the deck's default size while an
        explicitly sized canvas keeps its own dimensions.
        """
        if self._has_size:
            return
        self._ctx.width = width
        self._ctx.height = height
        self._has_size = True

    @property
    def width(self) -> int:
        if not self._has_size:
            raise ValidationError(self._UNSIZED_MESSAGE)
        return self._ctx.width

    @width.setter
    def width(self, value: int):
        if value <= 0:
            raise ValidationError("width must be > 0")
        self._ctx.width = value
        self._has_size = self._ctx.height > 0

    @property
    def height(self) -> int:
        if not self._has_size:
            raise ValidationError(self._UNSIZED_MESSAGE)
        return self._ctx.height

    @height.setter
    def height(self, value: int):
        if value <= 0:
            raise ValidationError("height must be > 0")
        self._ctx.height = value
        self._has_size = self._ctx.width > 0

    @property
    def layers(self) -> list[RenderableLayer]:
        return self._layers

    @layers.setter
    def layers(self, value: list[RenderableLayer]):
        self._layers = value

    def diagnose(self) -> list:
        """Check layers for layout and legibility issues without producing an output file.

        Returns structured findings (off-canvas, tiny-text, text-overflow, low-contrast)
        that an agent or human can act on before rendering.
        """
        return self._diagnostics.diagnose()

    def inspect(self):
        """Return a deterministic layout report for this canvas without rendering output."""
        self._validate_image_paths()
        self._ctx.begin_render_pass()
        return CanvasInspection(
            width=self.width,
            height=self.height,
            layers=[self._inspect_layer(measured) for measured in measure_layers(self)],
        )

    def _inspect_layer(self, measured: LayerMeasurement) -> LayerInspection:
        return LayerInspection(
            id=measured.layer_id,
            index=measured.index,
            order=measured.order,
            z_order=measured.z_order,
            type=self._inspect_layer_type(measured),
            name=measured.name,
            visible=measured.visible,
            bbox=self._inspect_bbox(measured.bbox),
            text=self._inspect_text(measured),
            children=[self._inspect_layer(child) for child in measured.children],
        )

    @staticmethod
    def _inspect_layer_type(measured: LayerMeasurement) -> str:
        raw_type = getattr(measured.raw_layer, "type", None)
        if raw_type:
            return str(raw_type)
        if isinstance(measured.raw_layer, CustomLayer):
            return "custom"
        return measured.layer_type

    @staticmethod
    def _inspect_bbox(box: BBox | None) -> InspectionBBox | None:
        if box is None:
            return None
        return InspectionBBox(x=box.x, y=box.y, width=box.width, height=box.height)

    def _inspect_text(self, measured: LayerMeasurement) -> TextInspection | None:
        if measured.layer_type != "text":
            return None
        layer = measured.effective_text_layer
        if layer is None:
            return None
        layout = self._text.measure_text_layout(layer)
        return TextInspection(
            wrapped_lines=list(layout["wrapped_lines"]),
            effective_font_size=layout["effective_font_size"],
            effective_font_sizes=list(layout["effective_font_sizes"]),
            max_width=layer.max_width,
            auto_scaled=bool(measured.metadata.get("auto_scaled", False)),
        )

    @classmethod
    def from_aspect_ratio(cls, ratio: str, base_width: int) -> Self:
        width, height = aspect_ratio_dimensions(ratio, base_width)
        return cls(width, height)

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
        if color is None and gradient is None and image is None:
            raise ValidationError(
                "background() requires at least one of: color, gradient, or image"
            )
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
        content: TextContentInput | None = None,
        font: str | None = None,
        size: int | None = None,
        color: str | None = None,
        fill: "LinearGradient | RadialGradient | TextFillImage | None" = None,
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
        animation: AnimationInput | None = None,
    ) -> Self:
        if content is None:
            raise ValidationError("content is required")

        layer = TextLayer(
            type="text",
            content=cast(str | list[TextPart], content),
            font=font,
            size=size,
            color=color,
            fill=fill,
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
            animation=animation,
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
        shape: Literal["rectangle", "ellipse", "pill", "triangle", "star", "polygon"],
        position: tuple,
        width: int,
        height: int,
        color: str,
        border_radius: int = 0,
        opacity: float = 1.0,
        rotation: float = 0.0,
        align: Align | str | tuple[str, str] | None = None,
        points: list[tuple[float, float]] | None = None,
        star_points: int = 5,
        inner_radius: float = 0.5,
        effects: list[ShapeEffect] | None = None,
        animation: AnimationInput | None = None,
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
            points=points,
            star_points=star_points,
            inner_radius=inner_radius,
            effects=effects or [],
            animation=animation,
        )
        self._layers.append(layer)
        return self

    def image(
        self,
        path: str,
        position: tuple[int, int] | tuple[str, str] | tuple[int, str] | tuple[str, int],
        width: int | None = None,
        height: int | None = None,
        fit: FitMode | str | None = None,
        opacity: float = 1.0,
        rotation: float = 0.0,
        align: Align | str | tuple[str, str] = Align.TOP_LEFT,
        remove_background: bool = False,
        border_radius: int = 0,
        effects: list[ImageEffect] | None = None,
        blend_mode: BlendMode | str | None = None,
        animation: AnimationInput | None = None,
    ) -> Self:
        """Add an image overlay layer to the canvas.

        Args:
            path: Local file path or URL to the image
            position: (x, y) position in pixels or percentages (e.g., (50, 100) or ("50%", "50%"))
            width: Image width in pixels (preserves aspect ratio if height is None)
            height: Image height in pixels (preserves aspect ratio if width is None)
            fit: Fit mode when width and height define a target box: "fill", "contain", or "cover"
            opacity: Image opacity from 0.0 (transparent) to 1.0 (opaque)
            rotation: Rotation angle in degrees
            align: Image alignment, accepts:
                   - Align enum (e.g., Align.CENTER, Align.TOP_LEFT)
                   - String shortcut (e.g., "center", "top-left", "bottom-right")
                   - Tuple (horizontal, vertical) (e.g., ("center", "middle"))
            blend_mode: Blend mode for compositing this image onto prior layers
            animation: Optional entrance/exit Animation applied in PPTX and HTML export
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
            fit=fit,  # type: ignore[arg-type]  # Pydantic validator handles conversion
            blend_mode=blend_mode,  # type: ignore[arg-type]  # Pydantic validator handles conversion
            effects=effects or [],
            animation=animation,
        )
        self._layers.append(layer)
        return self

    def svg(
        self,
        path: str,
        position: tuple[int, int] | tuple[str, str] | tuple[int, str] | tuple[str, int],
        width: int | None = None,
        height: int | None = None,
        opacity: float = 1.0,
        rotation: float = 0.0,
        align: Align | str | tuple[str, str] = Align.TOP_LEFT,
        effects: list[ImageEffect] | None = None,
        blend_mode: BlendMode | str | None = None,
        animation: AnimationInput | None = None,
    ) -> Self:
        """Add an SVG overlay layer, rasterized at render time (requires quickthumb[svg]).

        Args:
            path: Local file path or URL to the SVG document
            position: (x, y) position in pixels or percentages
            width: Output raster width in pixels (preserves aspect ratio if height is None)
            height: Output raster height in pixels (preserves aspect ratio if width is None)
            opacity: Layer opacity from 0.0 (transparent) to 1.0 (opaque)
            rotation: Rotation angle in degrees
            align: Layer alignment relative to position
            blend_mode: Blend mode for compositing onto prior layers
            animation: Optional entrance/exit Animation applied in PPTX and HTML export
        Returns:
            Self for method chaining
        """
        layer = SvgLayer(
            type="svg",
            path=path,
            position=position,  # Pydantic validator handles conversion
            width=width,
            height=height,
            opacity=opacity,
            rotation=rotation,
            align=align,  # type: ignore[arg-type]  # Pydantic validator handles conversion
            blend_mode=blend_mode,  # type: ignore[arg-type]  # Pydantic validator handles conversion
            effects=effects or [],
            animation=animation,
        )
        self._layers.append(layer)
        return self

    def group(
        self,
        children: list,
        direction: Literal["row", "column"] = "column",
        gap: int = 0,
        padding: int | tuple[int, int] | tuple[int, int, int, int] = 0,
        position: (
            tuple[int, int] | tuple[str, str] | tuple[int, str] | tuple[str, int] | None
        ) = None,
        align: Align | str | tuple[str, str] | None = None,
        item_align: Literal["start", "center", "end"] = "start",
        animation: AnimationInput | None = None,
    ) -> Self:
        """Add an auto-layout group that stacks child layers along a row or column.

        Children are measured at their natural size and positioned by the group:
        they must not set their own position. Children may be dicts or layer models
        of type text, image, shape, svg, or nested group.

        Args:
            children: Child layer dicts or models, in stacking order
            direction: Main axis: "column" stacks top-to-bottom, "row" left-to-right
            gap: Pixels between adjacent children along the main axis
            padding: Inner padding (int, (vertical, horizontal), or (top, right, bottom, left))
            position: Anchor point of the group box in pixels or percentages
            align: How the group box anchors to position (like image layers)
            item_align: Cross-axis placement of each child: "start", "center", or "end"
            animation: Optional Animation applied to the whole group in PPTX and HTML export
        Returns:
            Self for method chaining
        """
        layer = GroupLayer(
            type="group",
            direction=direction,
            gap=gap,
            padding=padding,
            position=position,  # Pydantic validator handles conversion
            align=align,  # type: ignore[arg-type]  # Pydantic validator handles conversion
            item_align=item_align,
            animation=animation,
            children=children,
        )
        self._layers.append(layer)
        return self

    def custom(
        self,
        fn: Callable[..., Image.Image | None],
        name: str | None = None,
        kwargs: dict | None = None,
    ) -> Self:
        """Add a custom callback layer that can draw directly onto the canvas image."""
        if not callable(fn):
            raise ValidationError("fn must be callable")

        self._layers.append(CustomLayer(fn=fn, name=name, kwargs=kwargs or {}))
        return self

    def render(
        self,
        output_path: str,
        format: FileFormat | None = None,
        quality: int | None = None,
    ):
        """Render the canvas to a file.

        The output format is detected from the file extension: PNG, JPEG, and
        WEBP render through the raster pipeline, while .svg, .pptx, and .pdf
        produce vector/document output (see to_svg, to_pptx, and to_pdf).
        """
        if format is None:
            extension = os.path.splitext(output_path)[1].lower()
            if extension in (".svg", ".pptx", ".pdf", ".html", ".htm"):
                if quality is not None:
                    raise RenderingError(
                        "Quality parameter is only supported for JPEG and WEBP formats, "
                        f"not {extension} output."
                    )
                self._render_document(output_path, extension)
                return

        self._validate_image_paths()
        image = self._render_to_image()
        self._save_to_file(image, output_path, quality, format=format)

    def _render_document(self, output_path: str, extension: str):
        if extension == ".svg":
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(self.to_svg())
            return

        if extension in (".html", ".htm"):
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(self.to_html())
            return

        if extension == ".pdf":
            from quickthumb._export_pdf import PdfExporter

            PdfExporter(self).save(output_path)
            return

        from quickthumb._export_pptx import PptxExporter

        PptxExporter(self).save(output_path)

    def to_svg(self, embed_fonts: bool = False) -> str:
        """Render the canvas to an SVG document string.

        Backgrounds, gradients, outlines, shapes, and text become native SVG
        elements positioned with the same layout math as the raster renderer;
        raster images, blend modes, image glyph fills, and custom layers are
        embedded as pixel-exact PNG fragments. Set embed_fonts=True to inline
        the used font files as @font-face data URLs so text renders identically
        on machines without the fonts installed.
        """
        from quickthumb._export_svg import SvgExporter

        return SvgExporter(self, embed_fonts=embed_fonts).export()

    def to_html(self, responsive: bool = True, embed_fonts: bool = True) -> str:
        """Render the canvas to a standalone, self-contained HTML document string.

        Backgrounds, gradients, outlines, shapes, and text become native
        HTML/CSS positioned with the same layout math as the raster renderer;
        raster images, blend modes, image glyph fills, and custom layers are
        embedded as pixel-exact PNG fragments. Per-layer ``animation`` effects
        play via a small inline JS runtime (click to advance), so unlike the
        other formats HTML actually animates.

        The composition is a fixed-size stage that never reflows, keeping it a
        faithful twin of the PNG/SVG/PDF/PPTX output. With ``responsive=True``
        (default) the whole stage is scaled as one unit to fill the viewport;
        pass ``responsive=False`` to emit the bare fixed-size stage. ``embed_fonts``
        defaults to ``True`` so the used fonts are inlined as ``@font-face`` data
        URLs and text renders identically everywhere; pass ``False`` to drop them
        and rely on the viewer's system fonts for a smaller file.
        """
        from quickthumb._export_html import HtmlExporter

        return HtmlExporter(self, embed_fonts=embed_fonts, responsive=responsive).export()

    def to_pptx(self) -> bytes:
        """Render the canvas to a PowerPoint file as bytes (requires quickthumb[pptx]).

        The canvas becomes a single slide: text stays editable text boxes,
        shapes become autoshapes, and everything else is embedded as pictures.
        """
        from quickthumb._export_pptx import PptxExporter

        return PptxExporter(self).export_bytes()

    def to_pdf(self) -> bytes:
        """Render the canvas to a single-page PDF as bytes (requires quickthumb[pdf]).

        The page is sized to the canvas pixels (one point per pixel).
        Backgrounds, outlines, shapes, and text are drawn as native PDF vector
        primitives, while raster images, blend modes, blur effects, gradient or
        image glyph fills, translucent gradients, and custom layers are embedded
        as pixel-exact PNG fragments. The fonts used for text are subset and
        embedded into the PDF, so the document is self-contained and renders
        correctly in any reader without the fonts installed.
        """
        from quickthumb._export_pdf import PdfExporter

        return PdfExporter(self).export_bytes()

    def to_json(self) -> str:
        import json as _json

        layers_json = []
        for layer in self._layers:
            if isinstance(layer, CustomLayer):
                if layer.name is None:
                    raise ValidationError("Custom layers cannot be serialized to JSON")
                try:
                    _json.dumps(layer.kwargs)
                except (TypeError, ValueError) as e:
                    raise ValidationError(
                        f"Custom layer '{layer.name}' has kwargs that are not JSON-serializable:"
                        f" {e}"
                    ) from e
                layers_json.append({"type": "custom", "name": layer.name, "kwargs": layer.kwargs})
            else:
                layers_json.append(_json.loads(layer.model_dump_json()))

        return _json.dumps({"width": self.width, "height": self.height, "layers": layers_json})

    @classmethod
    def from_json(cls, data: str) -> Self:
        import json as _json

        from pydantic import TypeAdapter

        from quickthumb.models import CanvasModel, LayerType

        raw = _json.loads(data)
        if not isinstance(raw, dict):
            CanvasModel.model_validate_json(data)  # raises ValidationError with good message
        raw = cast(dict[str, Any], raw)

        theme = raw.pop("theme", {})
        if not isinstance(theme, dict):
            raise ValidationError("'theme' must be a JSON object of token groups")
        raw = _resolve_theme_tokens(raw, theme)
        raw = cast(dict[str, Any], raw)

        layers_raw = raw.get("layers", [])

        if not isinstance(layers_raw, list):
            CanvasModel.model_validate_json(data)  # raises ValidationError with good message

        layer_adapter: TypeAdapter[LayerType] = TypeAdapter(LayerType)
        renderable_layers: list[RenderableLayer] = []
        for layer_dict in layers_raw:
            if isinstance(layer_dict, dict) and layer_dict.get("type") == "custom":
                name = layer_dict.get("name")
                if not isinstance(name, str):
                    raise ValidationError("Custom layer 'name' must be a string.")
                fn = cls._custom_layer_registry.get(name)
                if fn is None:
                    raise ValidationError(
                        f"Custom layer '{name}' is not registered. "
                        f"Call Canvas.register_layer_fn('{name}', fn) before deserializing."
                    )
                kwargs = layer_dict.get("kwargs") or {}
                if not isinstance(kwargs, dict):
                    raise ValidationError(f"Custom layer '{name}' kwargs must be a JSON object.")
                renderable_layers.append(CustomLayer(fn=fn, name=name, kwargs=kwargs))
            else:
                renderable_layers.append(layer_adapter.validate_python(layer_dict))

        width = raw.get("width")
        height = raw.get("height")
        if not isinstance(width, int) or not isinstance(height, int):
            CanvasModel.model_validate(raw)  # raises ValidationError with good message
            raise ValidationError("'width' and 'height' must be integers.")

        return cls(width=width, height=height, layers=renderable_layers)

    @classmethod
    def _read_template_file(cls, path: str) -> str:
        try:
            with open(path) as f:
                return f.read()
        except OSError as e:
            raise ValidationError(f"Cannot read template file '{path}': {e}") from e

    @classmethod
    def _resolve_template_string(cls, spec_or_path: str) -> str:
        if spec_or_path.lstrip().startswith("{"):
            return spec_or_path
        if spec_or_path in cls._template_registry:
            return cls._read_template_file(cls._template_registry[spec_or_path])
        builtin_path = os.path.join(cls._BUILTIN_TEMPLATES_DIR, f"{spec_or_path}.json")
        if os.path.exists(builtin_path):
            return cls._read_template_file(builtin_path)
        if os.path.exists(spec_or_path):
            return cls._read_template_file(spec_or_path)
        raise ValidationError(
            f"Template '{spec_or_path}' is not a registered template name, "
            f"built-in template name, or valid file path."
        )

    @classmethod
    def from_template(
        cls, spec_or_path: str, variables: Mapping[str, object] | None = None
    ) -> Self:
        import json as _json

        variables = variables or {}
        raw_spec = cls._resolve_template_string(spec_or_path)

        def substitute(match: re.Match) -> str:
            if _is_theme_reference(match):
                return match.group(0)
            key = match.group(1) or match.group(2)
            assert key is not None
            if key not in variables:
                raise ValidationError(
                    f"Template placeholder '${key}' has no matching variable. "
                    f"Provide variables={{'{key}': ...}} to Canvas.from_template()."
                )
            value = variables[key]
            dumped = _json.dumps(value)
            return dumped[1:-1] if isinstance(value, str) else dumped

        return cls.from_json(_VAR_RE.sub(substitute, raw_spec))

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
        self._ctx.begin_render_pass()
        image = self._create_canvas()

        for layer in self._layers:
            self._render_layer(image, layer)

        return image

    def _render_layer(self, image: Image.Image, layer: RenderableLayer):
        if isinstance(layer, BackgroundLayer):
            self._render_background_layer(image, layer)
        elif isinstance(layer, TextLayer):
            self._text.render_text_layer(image, layer)
        elif isinstance(layer, OutlineLayer):
            self._render_outline_layer(image, layer)
        elif isinstance(layer, ImageLayer):
            self._images.render_image_layer(image, layer)
        elif isinstance(layer, ShapeLayer):
            self._shapes.render_shape_layer(image, layer)
        elif isinstance(layer, SvgLayer):
            self._images.render_svg_layer(image, layer)
        elif isinstance(layer, GroupLayer):
            self._groups.render_group_layer(image, layer)
        elif isinstance(layer, CustomLayer):
            self._render_custom_layer(image, layer)

    def _render_custom_layer(self, image: Image.Image, layer: CustomLayer):
        try:
            result = layer.fn(image, **layer.kwargs)
        except Exception as e:
            raise RenderingError(f"Custom layer callback failed: {e}") from e

        if result is None:
            return

        if not isinstance(result, Image.Image):
            raise RenderingError("Custom layer callback must return PIL.Image.Image or None")

        if result.size != image.size:
            raise RenderingError("Custom layer callback returned an image with different size")

        image.paste(result)

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

    def _iter_layers_deep(self):
        """Yield all layers including group children, depth-first."""

        def walk(layers):
            for layer in layers:
                yield layer
                if isinstance(layer, GroupLayer):
                    yield from walk(layer.children)

        yield from walk(self._layers)

    def _validate_image_paths(self):
        for layer in self._iter_layers_deep():
            if (
                isinstance(layer, BackgroundLayer)
                and layer.image
                and not is_url(layer.image)
                and not os.path.exists(layer.image)
            ):
                raise FileNotFoundError(f"{layer.image}")
            elif (
                isinstance(layer, (ImageLayer, SvgLayer))
                and not is_url(layer.path)
                and not os.path.exists(layer.path)
            ):
                raise FileNotFoundError(f"{layer.path}")
            elif isinstance(layer, TextLayer):
                fills_to_check: list[TextFillImage] = []
                if isinstance(layer.fill, TextFillImage):
                    fills_to_check.append(layer.fill)
                if isinstance(layer.content, list):
                    for part in layer.content:
                        if isinstance(part.fill, TextFillImage):
                            fills_to_check.append(part.fill)
                for fill in fills_to_check:
                    if not is_url(fill.path) and not os.path.exists(fill.path):
                        raise FileNotFoundError(f"{fill.path}")

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

    def _render_background_layer(self, image: Image.Image, layer: BackgroundLayer):
        layer_image = self._create_layer_image(image.size, layer)
        if not layer_image:
            return

        for effect in layer.effects:
            if isinstance(effect, Grain):
                layer_image = self._effects.apply_grain(layer_image, effect)
            else:
                layer_image = self._effects.apply_filter(layer_image, effect)

        if layer.opacity < 1.0 and not layer.color:
            layer_image = self._effects.apply_opacity(layer_image, layer.opacity)

        if layer.blend_mode:
            blended = self._effects.apply_blend_mode(image, layer_image, layer.blend_mode)
            image.paste(blended, (0, 0))
        else:
            image.alpha_composite(layer_image)

    def _create_layer_image(
        self, size: tuple[int, int], layer: BackgroundLayer
    ) -> Image.Image | None:
        if layer.color:
            color = self._effects.parse_color(layer.color)
            if layer.opacity < 1.0:
                color = self._effects.apply_opacity_to_color(color, layer.opacity)
            return Image.new("RGBA", size, color)

        if layer.gradient:
            if isinstance(layer.gradient, LinearGradient):
                return self._effects.create_linear_gradient(
                    size, layer.gradient.angle, layer.gradient.stops
                )
            if isinstance(layer.gradient, RadialGradient):
                return self._effects.create_radial_gradient(
                    size, layer.gradient.stops, layer.gradient.center
                )

        if layer.image:
            return self._images.load_and_fit_image(layer.image, size, layer.fit)

        return None

    def _render_outline_layer(self, image: Image.Image, layer: OutlineLayer):
        draw = ImageDraw.Draw(image)
        color = self._effects.parse_color(layer.color)
        if layer.opacity < 1.0:
            color = self._effects.apply_opacity_to_color(color, layer.opacity)

        x1 = layer.offset
        y1 = layer.offset
        x2 = self.width - layer.offset - 1
        y2 = self.height - layer.offset - 1

        for i in range(layer.width):
            draw.rectangle([x1 + i, y1 + i, x2 - i, y2 - i], outline=color)
