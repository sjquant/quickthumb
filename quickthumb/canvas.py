import math
import os
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from io import BytesIO
from typing import Any, Literal, cast

from PIL import Image, ImageDraw, ImageFont
from pydantic import TypeAdapter
from pydantic import ValidationError as PydanticValidationError
from typing_extensions import Self

from quickthumb._base import FileFormat, RenderContext, aspect_ratio_dimensions, is_url
from quickthumb._composition import composite_layer_with_boundary, has_layer_composition
from quickthumb._diagnostic_rules import PLATFORM_SAFE_MARGIN_PRESETS
from quickthumb._diagnostics import DiagnosticsEngine
from quickthumb._effects import EffectsEngine
from quickthumb._fonts import FontEngine
from quickthumb._groups import GroupEngine
from quickthumb._images import ImageEngine
from quickthumb._measurements import BBox, LayerMeasurement, measure_layers
from quickthumb._shapes import ShapeEngine
from quickthumb._text import TextEngine
from quickthumb._validation import validate_dimensions
from quickthumb._video import (
    iter_video_layers,
    probe_video,
    render_video_captions,
    render_video_layer,
)
from quickthumb._visualizations import VisualizationEngine
from quickthumb.errors import RenderingError, ValidationError
from quickthumb.models import (
    Align,
    AnimatedTextValue,
    AnimationInput,
    AudioTrack,
    BackdropBlur,
    BackgroundEffect,
    BackgroundLayer,
    BlendMode,
    CanonicalFrame,
    CanvasInspection,
    ChartLayer,
    ChartSpec,
    DiagnosticReport,
    ExportPolicy,
    ExportResult,
    FaceRegion,
    FitMode,
    GifOptions,
    Grain,
    GroupLayer,
    ImageEffect,
    ImageLayer,
    InspectionBBox,
    LayerClip,
    LayerInspection,
    LayerMask,
    LayerType,
    LinearGradient,
    OutlineLayer,
    PluginLayer,
    QRCodeLayer,
    RadialGradient,
    ResolvedDocument,
    ShapeEffect,
    ShapeLayer,
    SvgLayer,
    TextFillImage,
    TextInspection,
    TextLayer,
    TextPart,
    ValidationReport,
    VideoCaption,
    VideoLayer,
    VideoOptions,
)
from quickthumb.plugins import PluginRegistry, plugin_registry


@dataclass
class CustomLayer:
    fn: Callable[..., Image.Image | None]
    name: str | None = None
    kwargs: dict = field(default_factory=dict)


RenderableLayer = LayerType | CustomLayer
TextContentInput = str | list[TextPart | dict[str, Any]]

_THEME_REF_RE = re.compile(r"\$theme\.([A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)*)")
_VAR_RE = re.compile(r"\$\{(\w+)\}|\$(\w+)")
_LAYER_ADAPTER: TypeAdapter[LayerType] = TypeAdapter(LayerType)
_LAYER_SCHEMA: dict[str, Any] = _LAYER_ADAPTER.json_schema()


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
        platform: str | None = None,
        *,
        registry: PluginRegistry | None = None,
    ):
        validate_dimensions(width, height)
        if platform is not None:
            try:
                platform = PLATFORM_SAFE_MARGIN_PRESETS[platform].name
            except KeyError:
                supported = ", ".join(sorted(PLATFORM_SAFE_MARGIN_PRESETS))
                raise ValidationError(
                    f"Unsupported platform preset '{platform}'. Supported: {supported}"
                ) from None
        # An unsized canvas defers its dimensions until a Deck injects them. Layer
        # builders never need a size (coordinates resolve at render time), so the
        # placeholder ctx stays valid; render/diagnose/serialize guard on _has_size.
        self._has_size = width is not None
        self._ctx = RenderContext(width or 0, height or 0)
        self._layers: list[RenderableLayer] = layers or []
        if registry is not None and not isinstance(registry, PluginRegistry):
            raise ValidationError("registry must be a PluginRegistry instance")
        self._plugin_registry = plugin_registry if registry is None else registry
        self._validate_layer_identities()
        self._platform = platform

        self._effects = EffectsEngine()
        self._fonts = FontEngine(self._ctx.asset_resolver)
        self._images = ImageEngine(self._ctx, self._effects)
        self._text = TextEngine(self._ctx, self._fonts, self._effects, self._images)
        self._shapes = ShapeEngine(self._ctx, self._effects, self._images)
        self._visualizations = VisualizationEngine(self._ctx, self._effects)
        self._groups = GroupEngine(
            self._ctx,
            self._fonts,
            self._effects,
            self._images,
            self._shapes,
            self._text,
            self._visualizations,
        )
        self._diagnostics = DiagnosticsEngine(
            self._ctx,
            self,
            self._effects,
            self._images,
            self._shapes,
            self._text,
            self._groups,
        )

    @property
    def has_size(self) -> bool:
        """Whether the canvas has concrete dimensions (False until a Deck assigns them)."""
        return self._has_size

    @property
    def platform(self) -> str | None:
        """Optional publishing platform preset used by diagnostic safe-margin rules."""
        return self._platform

    @classmethod
    def for_platform(cls, platform: str) -> Self:
        """Create a canvas sized for a platform and enable its diagnostic overlays."""
        try:
            preset = PLATFORM_SAFE_MARGIN_PRESETS[platform]
        except KeyError:
            supported = ", ".join(sorted(PLATFORM_SAFE_MARGIN_PRESETS))
            raise ValidationError(
                f"Unsupported platform preset '{platform}'. Supported: {supported}"
            ) from None
        return cls(width=preset.width, height=preset.height, platform=preset.name)

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
        return list(self._layers)

    @layers.setter
    def layers(self, value: list[RenderableLayer]):
        previous = self._layers
        self._layers = list(value)
        try:
            self._validate_layer_identities()
        except Exception:
            self._layers = previous
            raise

    def _append_layer(self, layer: RenderableLayer) -> None:
        """Append a layer while preserving scene-local id uniqueness."""
        self._layers.append(layer)
        try:
            self._validate_layer_identities()
        except Exception:
            self._layers.pop()
            raise

    def _validate_layer_identities(self) -> None:
        seen: set[str] = set()

        def visit(layer: object) -> None:
            layer_id = getattr(layer, "id", None)
            if layer_id is not None:
                if layer_id in seen:
                    raise ValidationError(f"duplicate layer id: {layer_id}")
                seen.add(layer_id)
            for child in getattr(layer, "children", ()):
                visit(child)

        for layer in self._layers:
            visit(layer)

    def validate(self) -> ValidationReport:
        """Return a structured validation report for this document."""
        from quickthumb._document import Document, validation_report

        return validation_report(cast(Document, self), kind="canvas")

    def _contract_kind(self) -> Literal["canvas"]:
        return "canvas"

    def _contract_canvases(self) -> list["Canvas"]:
        return [self]

    def _contract_layers(self):
        return self._iter_layers_deep()

    def _contract_audio_paths(self) -> tuple[str | None, ...]:
        return ()

    def _contract_validate_assets(self) -> None:
        self._validate_image_paths()

    def _contract_resolve_assets(self) -> None:
        """Resolve remote image and font references before building a manifest."""
        self._validate_image_paths()
        for asset_type, source in self._remote_asset_references():
            self._images.resolve_remote_reference(source, asset_type=asset_type)
        self._fonts.resolve_remote_references(self._iter_layers_deep())

    def _contract_asset_record(self, asset_type: str, source: str):
        return self._ctx.asset_resolver.record_for(source, asset_type)

    def _remote_asset_references(self):
        for layer in self._iter_layers_deep():
            if isinstance(layer, BackgroundLayer) and layer.image and is_url(layer.image):
                yield "image", layer.image
            elif isinstance(layer, ImageLayer) and is_url(layer.path):
                yield "image", layer.path
            elif isinstance(layer, SvgLayer) and is_url(layer.path):
                yield "svg", layer.path

            if isinstance(layer, TextLayer):
                fills = []
                if isinstance(layer.fill, TextFillImage):
                    fills.append(layer.fill)
                if isinstance(layer.content, list):
                    for part in layer.content:
                        if isinstance(part.fill, TextFillImage):
                            fills.append(part.fill)
                for fill in fills:
                    if is_url(fill.path):
                        yield "text-fill", fill.path

    def _contract_validate_structure(self) -> None:
        if not self.has_size:
            raise ValidationError("canvas has no size")
        self._validate_layer_identities()
        for layer in self._layers:
            self._validate_plugin_layer_tree(layer, self._plugin_registry)

    def _contract_motion_report(self, target: str, policy, fps: float):
        return self.inspect_motion(target=target, policy=policy, fps=fps)

    def _contract_static_timing(self) -> None:
        return None

    def resolve_assets(self) -> ResolvedDocument:
        """Check referenced assets and return their manifest metadata."""
        from quickthumb._document import AssetPort, Document, resolved_document

        return resolved_document(
            cast(Document, self),
            kind="canvas",
            assets=AssetPort(
                resolve=self._contract_resolve_assets,
                record_for=self._contract_asset_record,
            ),
        )

    def sample(self, time: float = 0.0) -> CanonicalFrame:
        """Return one canonical RGBA frame without exposing motion internals."""
        self._validate_image_paths()
        return CanonicalFrame.from_image(self.render_frame(time), time=float(time))

    def diagnose(self) -> DiagnosticReport:
        """Check layers for layout and legibility issues without producing an output file.

        Returns structured findings for layout, legibility, visibility, and safe-area
        checks that an agent or human can act on before rendering.
        """
        from quickthumb._document import DiagnosticReport

        return DiagnosticReport(findings=self._diagnostics.diagnose())

    def inspect(self) -> CanvasInspection:
        """Return a deterministic layout report for this canvas without rendering output."""
        self._validate_image_paths()
        self._ctx.begin_render_pass()
        return CanvasInspection(
            width=self.width,
            height=self.height,
            layers=[self._inspect_layer(measured) for measured in measure_layers(self)],
        )

    def validate_export(self, target: str, policy=None):
        """Return renderer-independent motion diagnostics for an export target."""
        from quickthumb.motion import validate_export

        return validate_export(self, target, policy)

    def inspect_motion(
        self, target=None, policy=None, fps: float = 30.0, max_samples: int = 10_000
    ):
        """Return a serializable report of this canvas's resolved motion."""
        from quickthumb.motion import inspect_motion

        return inspect_motion(self, target=target, policy=policy, fps=fps, max_samples=max_samples)

    def _inspect_layer(
        self, measured: LayerMeasurement, index: int | None = None, order: int | None = None
    ) -> LayerInspection:
        box = measured.bbox
        return LayerInspection(
            id=measured.layer_id,
            index=measured.index if index is None else index,
            order=measured.order if order is None else order,
            z_order=measured.z_order if order is None else order,
            type=self._inspect_layer_type(measured),
            name=measured.name,
            visible=measured.visible,
            bbox=None
            if box is None
            else InspectionBBox(x=box.x, y=box.y, width=box.width, height=box.height),
            text=self._inspect_text(measured),
            children=[
                self._inspect_layer(child, index=child_index, order=child_index)
                for child_index, child in enumerate(measured.children)
            ],
        )

    @staticmethod
    def _inspect_layer_type(measured: LayerMeasurement) -> str:
        raw_type = getattr(measured.raw_layer, "type", None)
        if raw_type:
            return str(raw_type)
        if isinstance(measured.raw_layer, CustomLayer):
            return "custom"
        return measured.layer_type

    def _inspect_text(self, measured: LayerMeasurement) -> TextInspection | None:
        if measured.layer_type != "text":
            return None
        layer = measured.effective_text_layer
        if layer is None:
            return None
        return TextInspection(
            wrapped_lines=list(measured.metadata["wrapped_lines"]),
            effective_font_size=measured.metadata["effective_font_size"],
            effective_font_sizes=list(measured.metadata["effective_font_sizes"]),
            max_width=layer.max_width,
            max_height=layer.max_height,
            min_size=layer.min_size,
            balance_lines=layer.balance_lines,
            font_source=layer.font_source,
            font_variations=layer.font_variations,
            emoji_style=layer.emoji_style,
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
        focal_point: tuple[float, float] | None = None,
        faces: list[FaceRegion | dict[str, float]] | None = None,
        effects: list[BackgroundEffect] | None = None,
        *,
        id: str | None = None,
        motion_key: str | None = None,
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
            focal_point=focal_point,
            faces=faces or [],  # type: ignore[arg-type]
            effects=effects or [],
            id=id,
            motion_key=motion_key,
        )
        self._append_layer(layer)
        return self

    def counter(
        self,
        from_: float,
        to: float,
        duration: float,
        *,
        delay: float = 0.0,
        decimals: int = 0,
        minimum_integer_digits: int = 1,
        prefix: str = "",
        suffix: str = "",
        grouping: bool = False,
        style: Literal["plain", "odometer", "flip"] = "odometer",
        easing: Literal["linear", "ease_in", "ease_out", "ease_in_out"] = "ease_out",
        **text_options: Any,
    ) -> Self:
        """Add a deterministic animated numeric TextLayer."""
        # `from` is a keyword, so the alias can only be supplied through validation.
        value = AnimatedTextValue.model_validate(
            {
                "from": from_,
                "to": to,
                "duration": duration,
                "delay": delay,
                "decimals": decimals,
                "minimum_integer_digits": minimum_integer_digits,
                "prefix": prefix,
                "suffix": suffix,
                "grouping": grouping,
                "style": style,
                "easing": easing,
            }
        )
        return self.text(content=value.settled_text(), value=value, **text_options)

    def text(
        self,
        content: TextContentInput | None = None,
        font: str | None = None,
        font_source: Literal["auto", "system", "google"] = "auto",
        font_variations: dict[str, float] | None = None,
        emoji_style: Literal["monochrome", "color"] = "monochrome",
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
        max_height: int | str | None = None,
        min_size: int = 1,
        balance_lines: bool = False,
        effects: list | None = None,
        line_height: float | None = None,
        letter_spacing: int | None = None,
        auto_scale: bool = False,
        rotation: float = 0,
        opacity: float = 1.0,
        clip: LayerClip | dict[str, Any] | None = None,
        mask: LayerMask | dict[str, Any] | None = None,
        animation: AnimationInput | None = None,
        value: "AnimatedTextValue | dict[str, Any] | None" = None,
        *,
        id: str | None = None,
        motion_key: str | None = None,
    ) -> Self:
        if content is None:
            raise ValidationError("content is required")

        layer = TextLayer(
            type="text",
            content=cast(str | list[TextPart], content),
            value=cast(Any, value),
            font=font,
            font_source=font_source,
            font_variations=font_variations or {},
            emoji_style=emoji_style,
            size=size,
            color=color,
            fill=fill,
            position=position,
            align=align,  # type: ignore[arg-type]  # Pydantic validator handles conversion
            bold=bold,
            italic=italic,
            weight=weight,
            max_width=max_width,
            max_height=max_height,
            min_size=min_size,
            balance_lines=balance_lines,
            effects=effects or [],
            line_height=line_height,
            letter_spacing=letter_spacing,
            auto_scale=auto_scale,
            rotation=rotation,
            opacity=opacity,
            clip=cast(Any, clip),
            mask=cast(Any, mask),
            animation=animation,
            id=id,
            motion_key=motion_key,
        )
        self._append_layer(layer)
        return self

    def outline(
        self,
        width: int,
        color: str,
        offset: int = 0,
        opacity: float = 1.0,
        *,
        id: str | None = None,
        motion_key: str | None = None,
    ) -> Self:
        layer = OutlineLayer(
            type="outline",
            width=width,
            color=color,
            offset=offset,
            opacity=opacity,
            id=id,
            motion_key=motion_key,
        )
        self._append_layer(layer)
        return self

    def shape(
        self,
        shape: Literal["rectangle", "ellipse", "pill", "triangle", "star", "polygon"],
        position: tuple,
        width: int,
        height: int,
        color: str,
        fill: "LinearGradient | RadialGradient | None" = None,
        border_radius: int = 0,
        opacity: float = 1.0,
        rotation: float = 0.0,
        align: Align | str | tuple[str, str] | None = None,
        points: list[tuple[float, float]] | None = None,
        star_points: int = 5,
        inner_radius: float = 0.5,
        effects: list[ShapeEffect] | None = None,
        clip: LayerClip | dict[str, Any] | None = None,
        mask: LayerMask | dict[str, Any] | None = None,
        animation: AnimationInput | None = None,
        *,
        id: str | None = None,
        motion_key: str | None = None,
    ) -> Self:
        layer = ShapeLayer(
            type="shape",
            shape=shape,
            position=position,
            width=width,
            height=height,
            color=color,
            fill=fill,
            border_radius=border_radius,
            opacity=opacity,
            rotation=rotation,
            align=align,  # type: ignore[arg-type]  # Pydantic validator handles conversion
            points=points,
            star_points=star_points,
            inner_radius=inner_radius,
            clip=cast(Any, clip),
            mask=cast(Any, mask),
            effects=effects or [],
            animation=animation,
            id=id,
            motion_key=motion_key,
        )
        self._append_layer(layer)
        return self

    def image(
        self,
        path: str,
        position: tuple[int, int] | tuple[str, str] | tuple[int, str] | tuple[str, int],
        width: int | None = None,
        height: int | None = None,
        fit: FitMode | str | None = None,
        focal_point: tuple[float, float] | None = None,
        faces: list[FaceRegion | dict[str, float]] | None = None,
        opacity: float = 1.0,
        rotation: float = 0.0,
        align: Align | str | tuple[str, str] = Align.TOP_LEFT,
        remove_background: bool = False,
        border_radius: int = 0,
        effects: list[ImageEffect] | None = None,
        blend_mode: BlendMode | str | None = None,
        clip: LayerClip | dict[str, Any] | None = None,
        mask: LayerMask | dict[str, Any] | None = None,
        animation: AnimationInput | None = None,
        *,
        id: str | None = None,
        motion_key: str | None = None,
    ) -> Self:
        """Add an image overlay layer to the canvas.

        Args:
            path: Local file path or URL to the image
            position: (x, y) position in pixels or percentages (e.g., (50, 100) or ("50%", "50%"))
            width: Image width in pixels (preserves aspect ratio if height is None)
            height: Image height in pixels (preserves aspect ratio if width is None)
            fit: Fit mode when width and height define a target box: "fill", "contain", or "cover"
            focal_point: Normalized (x, y) source-image point to keep visible for fit="cover"
            faces: Normalized source-image face boxes that guide fit="cover" crops
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
            focal_point=focal_point,
            faces=faces or [],  # type: ignore[arg-type]
            blend_mode=blend_mode,  # type: ignore[arg-type]  # Pydantic validator handles conversion
            clip=cast(Any, clip),
            mask=cast(Any, mask),
            effects=effects or [],
            animation=animation,
            id=id,
            motion_key=motion_key,
        )
        self._append_layer(layer)
        return self

    def video(
        self,
        source: str,
        position: tuple[int, int] | tuple[str, str] | tuple[int, str] | tuple[str, int],
        width: int,
        height: int,
        fit: FitMode | str = FitMode.CONTAIN,
        trim_start: float = 0.0,
        trim_end: float | None = None,
        start: float = 0.0,
        duration: float | None = None,
        speed: float = 1.0,
        volume: float = 1.0,
        captions: list[VideoCaption | dict[str, Any]] | None = None,
        border_radius: int = 0,
        opacity: float = 1.0,
        rotation: float = 0.0,
        align: Align | str | tuple[str, str] | None = None,
        blend_mode: BlendMode | str | None = None,
        effects: list[ImageEffect] | None = None,
        clip: LayerClip | dict[str, Any] | None = None,
        mask: LayerMask | dict[str, Any] | None = None,
        animation: AnimationInput | None = None,
        *,
        id: str | None = None,
        motion_key: str | None = None,
    ) -> Self:
        """Add a constrained video clip layer for GIF, MP4, and WebM export."""
        layer = VideoLayer(
            type="video",
            source=source,
            position=position,
            width=width,
            height=height,
            fit=FitMode(fit),
            trim_start=trim_start,
            trim_end=trim_end,
            start=start,
            duration=duration,
            speed=speed,
            volume=volume,
            captions=cast(list[VideoCaption], captions or []),
            border_radius=border_radius,
            opacity=opacity,
            rotation=rotation,
            align=align,  # type: ignore[arg-type]  # Pydantic validator handles conversion
            blend_mode=blend_mode,  # type: ignore[arg-type]
            effects=effects or [],
            clip=cast(Any, clip),
            mask=cast(Any, mask),
            animation=animation,
            id=id,
            motion_key=motion_key,
        )
        self._append_layer(layer)
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
        clip: LayerClip | dict[str, Any] | None = None,
        mask: LayerMask | dict[str, Any] | None = None,
        animation: AnimationInput | None = None,
        *,
        id: str | None = None,
        motion_key: str | None = None,
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
            clip=cast(Any, clip),
            mask=cast(Any, mask),
            effects=effects or [],
            animation=animation,
            id=id,
            motion_key=motion_key,
        )
        self._append_layer(layer)
        return self

    def chart(
        self,
        spec: ChartSpec,
        position: tuple[int | str, int | str],
        width: int,
        height: int,
        opacity: float = 1.0,
        align: Align | str | tuple[str, str] = Align.TOP_LEFT,
        clip: LayerClip | dict[str, Any] | None = None,
        mask: LayerMask | dict[str, Any] | None = None,
        animation: AnimationInput | None = None,
        *,
        id: str | None = None,
        motion_key: str | None = None,
    ) -> Self:
        """Add a chart layer using a validated bar or line specification."""
        layer = ChartLayer(
            position=position,
            width=width,
            height=height,
            opacity=opacity,
            animation=animation,
            align=align,  # type: ignore[arg-type]
            clip=cast(Any, clip),
            mask=cast(Any, mask),
            spec=spec,
            id=id,
            motion_key=motion_key,
        )
        self._append_layer(layer)
        return self

    def qr_code(
        self,
        data: str,
        position: tuple[int | str, int | str] = (0, 0),
        size: int = 128,
        foreground: str = "#000000",
        background: str | None = "#FFFFFF",
        error_correction: Literal["L", "M", "Q", "H"] = "M",
        quiet_zone: int = 4,
        align: Align | str | tuple[str, str] = Align.TOP_LEFT,
        opacity: float = 1.0,
        clip: LayerClip | dict[str, Any] | None = None,
        mask: LayerMask | dict[str, Any] | None = None,
        animation: AnimationInput | None = None,
        *,
        id: str | None = None,
        motion_key: str | None = None,
    ) -> Self:
        """Add a square QR code layer."""
        layer = QRCodeLayer(
            data=data,
            position=position,
            size=size,
            foreground=foreground,
            background=background,
            error_correction=error_correction,
            quiet_zone=quiet_zone,
            align=align,  # type: ignore[arg-type]
            opacity=opacity,
            animation=animation,
            clip=cast(Any, clip),
            mask=cast(Any, mask),
            id=id,
            motion_key=motion_key,
        )
        self._append_layer(layer)
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
        clip: LayerClip | dict[str, Any] | None = None,
        mask: LayerMask | dict[str, Any] | None = None,
        animation: AnimationInput | None = None,
        *,
        id: str | None = None,
        motion_key: str | None = None,
    ) -> Self:
        """Add an auto-layout group that stacks child layers along a row or column.

        Children are measured at their natural size and positioned by the group:
        they must not set their own position. Children may be dicts or layer models
        of type text, image, shape, svg, chart, qr_code, or nested group.

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
            clip=cast(Any, clip),
            mask=cast(Any, mask),
            animation=animation,
            children=children,
            id=id,
            motion_key=motion_key,
        )
        self._append_layer(layer)
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

        self._append_layer(CustomLayer(fn=fn, name=name, kwargs=kwargs or {}))
        return self

    def render(
        self,
        output_path: str,
        format: FileFormat | None = None,
        quality: int | None = None,
        debug: bool = False,
        animation: GifOptions | VideoOptions | None = None,
        policy: ExportPolicy | None = None,
    ):
        """Render the canvas to a file.

        The output format is detected from the file extension: PNG, JPEG, and
        WEBP render through the raster pipeline; .svg, .pptx, and .pdf produce
        vector/document output (see to_svg, to_pptx, and to_pdf); .gif, .mp4,
        and .webm produce an animation that plays the canvas's layer
        ``animation`` effects. Pass ``GifOptions`` for GIF or ``VideoOptions``
        for MP4/WebM to tune animated output.
        Set debug=True for raster output annotated with public layer-id bboxes.
        """
        extension = os.path.splitext(output_path)[1].lower()
        if format is not None and extension in (".gif", ".mp4", ".webm"):
            raise RenderingError(
                "format override is only supported for raster output, not animated output."
            )
        if format is None and extension in (
            ".svg",
            ".pptx",
            ".pdf",
            ".html",
            ".htm",
            ".gif",
            ".mp4",
            ".webm",
        ):
            if animation is not None and extension not in (".gif", ".mp4", ".webm"):
                raise RenderingError(
                    "animation options are only supported for GIF, MP4, and WebM output."
                )
            if debug:
                raise RenderingError(
                    "Debug render is only supported for PNG, JPEG, and WEBP output."
                )
            if quality is not None:
                raise RenderingError(
                    "Quality parameter is only supported for JPEG and WEBP formats, "
                    f"not {extension} output."
                )
            if extension in (".gif", ".mp4", ".webm"):
                from quickthumb._export_video import write_animation

                write_animation(
                    [self],
                    [None],
                    output_path,
                    format=extension[1:],  # type: ignore[arg-type]
                    animation=animation,
                    reduced_motion=bool(policy and policy.reduced_motion),
                )
                return
            self._render_document(output_path, extension, policy=policy)
            return

        if animation is not None:
            raise RenderingError(
                "animation options require an animated output extension (.gif, .mp4, or .webm)."
            )
        self._validate_image_paths()
        image = self._render_to_image(debug=debug)
        self._save_to_file(image, output_path, quality, format=format)

    def export(
        self,
        output_path: str | os.PathLike[str],
        policy: ExportPolicy | None = None,
        *,
        format: FileFormat | None = None,
        quality: int | None = None,
        animation: GifOptions | VideoOptions | None = None,
    ) -> ExportResult:
        """Export through the existing renderer and return the shared result envelope."""
        from quickthumb._document import AssetPort, Document, build_export_result, preflight_export

        normalized_path = os.fspath(output_path)
        preflight_export(cast(Document, self), normalized_path, policy, format=format)
        written = self.render(
            normalized_path,
            format=format,
            quality=quality,
            animation=animation,
            policy=policy,
        )
        paths = [normalized_path] if written is None else [os.fspath(path) for path in written]
        return build_export_result(
            cast(Document, self),
            normalized_path,
            paths,
            policy,
            format=format,
            animation=animation,
            assets=AssetPort(
                resolve=self._contract_resolve_assets,
                record_for=self._contract_asset_record,
            ),
        )

    def _render_document(
        self, output_path: str, extension: str, policy: ExportPolicy | None = None
    ):
        if extension == ".svg":
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(self.to_svg())
            return

        if extension in (".html", ".htm"):
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(self.to_html(policy=policy))
            return

        if extension == ".pdf":
            from quickthumb._export_pdf import PdfExporter

            PdfExporter(self).save(output_path)
            return

        from quickthumb._export_pptx import PptxExporter

        PptxExporter(self, reduced_motion=bool(policy and policy.reduced_motion)).save(output_path)

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

    def to_html(
        self,
        responsive: bool = True,
        embed_fonts: bool = True,
        *,
        policy: ExportPolicy | None = None,
    ) -> str:
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

        return HtmlExporter(
            self,
            embed_fonts=embed_fonts,
            responsive=responsive,
            reduced_motion=bool(policy and policy.reduced_motion),
        ).export()

    def to_pptx(self, *, policy: ExportPolicy | None = None) -> bytes:
        """Render the canvas to a PowerPoint file as bytes (requires quickthumb[pptx]).

        The canvas becomes a single slide: text stays editable text boxes,
        shapes become autoshapes, and everything else is embedded as pictures.
        """
        from quickthumb._export_pptx import PptxExporter

        return PptxExporter(
            self, reduced_motion=bool(policy and policy.reduced_motion)
        ).export_bytes()

    def to_pdf(self) -> bytes:
        """Render the canvas to a single-page PDF as bytes (requires quickthumb[pdf]).

        The page is sized to the canvas pixels (one point per pixel).
        Backgrounds, outlines, shapes, and eligible text are drawn as native PDF
        vector primitives. Raster images, blend modes, blur effects, gradient or
        image glyph fills, translucent gradients, custom layers, and text whose
        font cannot be safely embedded or whose script needs complex shaping are
        embedded as pixel-exact PNG fragments. Vector text fonts are subset and
        embedded, so eligible text is selectable and self-contained in readers
        without those fonts installed.
        """
        from quickthumb._export_pdf import PdfExporter

        return PdfExporter(self).export_bytes()

    def to_gif(
        self,
        fps: float = 20.0,
        hold: float = 3.0,
        loop: int = 0,
        matte: str = "#000000",
        *,
        policy: ExportPolicy | None = None,
    ) -> bytes:
        """Render the canvas to animated GIF bytes that play its layer animations.

        Layer ``animation`` effects play in sequence (``on_click`` effects run
        automatically -- there are no clicks in a video), then the settled
        composition holds for ``hold`` seconds. A canvas with no animations
        yields a single-frame GIF. ``loop`` is the GIF repeat count (0 =
        forever). Frames are composited onto the opaque ``matte`` color since
        GIF cannot carry the canvas's alpha.
        """
        from quickthumb._export_video import export_animation_bytes

        return export_animation_bytes(
            [self],
            [None],
            format="gif",
            fps=fps,
            slide_duration=hold,
            loop=loop,
            matte=matte,
            reduced_motion=bool(policy and policy.reduced_motion),
        )

    def to_mp4(
        self,
        fps: float = 30.0,
        hold: float = 3.0,
        matte: str = "#000000",
        soundtrack: AudioTrack | str | dict | None = None,
        loop_audio: bool | None = None,
        *,
        policy: ExportPolicy | None = None,
    ) -> bytes:
        """Render the canvas to MP4 (H.264) bytes; timing model as in ``to_gif``.

        Requires the ``ffmpeg`` binary on PATH (or ``QUICKTHUMB_FFMPEG``).
        An odd-sized canvas loses its last pixel row/column (H.264 4:2:0
        output needs even dimensions). ``soundtrack`` muxes an audio file
        (any format ffmpeg decodes) as AAC, trimmed to the video length;
        ``loop_audio`` overrides `AudioTrack.loop`; legacy path strings loop by default.
        """
        from quickthumb._export_video import export_animation_bytes

        return export_animation_bytes(
            [self],
            [None],
            format="mp4",
            fps=fps,
            slide_duration=hold,
            matte=matte,
            soundtrack=soundtrack,
            loop_audio=loop_audio,
            reduced_motion=bool(policy and policy.reduced_motion),
        )

    def to_webm(
        self,
        fps: float = 30.0,
        hold: float = 3.0,
        matte: str = "#000000",
        soundtrack: AudioTrack | str | dict | None = None,
        loop_audio: bool | None = None,
        *,
        policy: ExportPolicy | None = None,
    ) -> bytes:
        """Render the canvas to WebM (VP9) bytes; timing model as in ``to_gif``.

        Requires the ``ffmpeg`` binary on PATH (or ``QUICKTHUMB_FFMPEG``).
        An odd-sized canvas loses its last pixel row/column (VP9 4:2:0 output
        needs even dimensions). ``soundtrack`` muxes an audio file (any
        format ffmpeg decodes) as Opus, trimmed to the video length;
        ``loop_audio`` overrides `AudioTrack.loop`; legacy path strings loop by default.
        """
        from quickthumb._export_video import export_animation_bytes

        return export_animation_bytes(
            [self],
            [None],
            format="webm",
            fps=fps,
            slide_duration=hold,
            matte=matte,
            soundtrack=soundtrack,
            loop_audio=loop_audio,
            reduced_motion=bool(policy and policy.reduced_motion),
        )

    def to_json(self) -> str:
        from quickthumb._document import canonical_json

        layers_json = []
        for layer in self._layers:
            if isinstance(layer, CustomLayer):
                if layer.name is None:
                    raise ValidationError("Custom layers cannot be serialized to JSON")
                try:
                    canonical_json(layer.kwargs)
                except ValidationError as e:
                    raise ValidationError(
                        f"Custom layer '{layer.name}' has kwargs that are not JSON-serializable:"
                        f" {e}"
                    ) from e
                layers_json.append({"type": "custom", "name": layer.name, "kwargs": layer.kwargs})
            else:
                layer_json = layer.model_dump(mode="json", by_alias=True)
                layers_json.append(self._omit_unset_composition_fields(layer_json))

        payload: dict[str, Any] = {
            "kind": "canvas",
            "width": self.width,
            "height": self.height,
            "layers": layers_json,
        }
        if self.platform is not None:
            payload["platform"] = self.platform
        return canonical_json(payload)

    @classmethod
    def _omit_unset_composition_fields(cls, value):
        if isinstance(value, dict):
            if value.get("id") is None:
                value.pop("id", None)
            if value.get("motion_key") is None:
                value.pop("motion_key", None)
            if value.get("clip") is None:
                value.pop("clip", None)
            if value.get("mask") is None:
                value.pop("mask", None)
            if value.get("focal_point") is None:
                value.pop("focal_point", None)
            if value.get("faces") == []:
                value.pop("faces", None)
            return {key: cls._omit_unset_composition_fields(item) for key, item in value.items()}
        if isinstance(value, list):
            return [cls._omit_unset_composition_fields(item) for item in value]
        return value

    @classmethod
    def from_json(cls, data: str, *, registry: PluginRegistry | None = None) -> Self:
        try:
            return cls._from_json(data, registry=registry)
        except PydanticValidationError as error:
            messages = []
            for detail in error.errors():
                field = " -> ".join(map(str, detail["loc"]))
                messages.append(f"Field '{field}': {detail['msg']}")
            raise ValidationError(" | ".join(messages), original_error=error) from error

    @classmethod
    def _from_json(cls, data: str, *, registry: PluginRegistry | None = None) -> Self:
        from quickthumb._document import decode_json_object, require_document_kind
        from quickthumb.models import CanvasModel

        parser_registry = plugin_registry if registry is None else registry
        if not isinstance(parser_registry, PluginRegistry):
            raise ValidationError("registry must be a PluginRegistry instance")
        raw = decode_json_object(data)
        require_document_kind(raw, expected="canvas")
        raw = dict(raw)
        raw.pop("kind")

        theme = raw.pop("theme", {})
        if not isinstance(theme, dict):
            raise ValidationError("'theme' must be a JSON object of token groups")
        unknown = sorted(set(raw) - {"width", "height", "platform", "layers"})
        if unknown:
            raise ValidationError(f"Canvas JSON contains unknown field(s): {', '.join(unknown)}")
        if "layers" not in raw:
            raise ValidationError("Canvas JSON must contain a 'layers' list.")
        raw = _resolve_theme_tokens(raw, theme)
        raw = cast(dict[str, Any], raw)

        layers_raw = raw["layers"]

        if not isinstance(layers_raw, list):
            CanvasModel.model_validate_json(data)  # raises ValidationError with good message

        layer_defs = cast(dict[str, dict[str, Any]], _LAYER_SCHEMA.get("$defs", {}))

        def resolve_json_schema(node: dict[str, Any], value: object) -> dict[str, Any]:
            reference = node.get("$ref")
            if isinstance(reference, str) and reference.startswith("#/$defs/"):
                return resolve_json_schema(layer_defs[reference.rsplit("/", 1)[-1]], value)

            if isinstance(value, dict):
                value = cast(dict[str, Any], value)
                discriminator = cast(dict[str, Any], node.get("discriminator", {}))
                property_name = discriminator.get("propertyName")
                mapping = discriminator.get("mapping", {})
                if isinstance(property_name, str) and isinstance(mapping, dict):
                    discriminator_value = value.get(property_name)
                    variant = (
                        mapping.get(discriminator_value)
                        if isinstance(discriminator_value, str)
                        else None
                    )
                    if isinstance(variant, str):
                        return resolve_json_schema(node={"$ref": variant}, value=value)
                    return node

            choices = node.get("oneOf") or node.get("anyOf")
            if isinstance(choices, list):
                candidates: list[tuple[int, dict[str, Any]]] = []
                for choice in choices:
                    if not isinstance(choice, dict):
                        continue
                    resolved = resolve_json_schema(choice, value)
                    if not _schema_matches_value(resolved, value):
                        continue
                    required = resolved.get("required", [])
                    if isinstance(value, dict) and not all(key in value for key in required):
                        continue
                    candidates.append((len(required), resolved))
                if candidates:
                    return max(candidates, key=lambda candidate: candidate[0])[1]
            return node

        def _schema_matches_value(node: dict[str, Any], value: object) -> bool:
            if node.get("oneOf") or node.get("anyOf"):
                return False
            if "const" in node and value != node["const"]:
                return False
            enum = node.get("enum")
            if isinstance(enum, list) and value not in enum:
                return False
            schema_type = node.get("type")
            if schema_type == "object":
                return isinstance(value, dict)
            if schema_type == "array":
                return isinstance(value, list)
            if schema_type == "string":
                return isinstance(value, str)
            if schema_type == "boolean":
                return isinstance(value, bool)
            if schema_type == "integer":
                return isinstance(value, int) and not isinstance(value, bool)
            if schema_type == "number":
                return isinstance(value, (int, float)) and not isinstance(value, bool)
            if schema_type == "null":
                return value is None
            if "properties" in node or "required" in node:
                return isinstance(value, dict)
            if "items" in node or "prefixItems" in node:
                return isinstance(value, list)
            return True

        def reject_unknown_json_fields(value: object, node: dict[str, Any], path: str) -> None:
            if isinstance(value, list):
                resolved = resolve_json_schema(node, value)
                item_schema = resolved.get("items")
                if isinstance(item_schema, dict):
                    for index, item in enumerate(value):
                        reject_unknown_json_fields(item, item_schema, f"{path}/{index}")
                return
            if not isinstance(value, dict):
                return

            resolved = resolve_json_schema(node, value)
            properties = resolved.get("properties")
            if not isinstance(properties, dict):
                return
            unknown = sorted(str(key) for key in set(value) - set(properties))
            if unknown:
                raise ValidationError(
                    f"JSON object at {path} contains unknown field(s): {', '.join(unknown)}"
                )
            for key, child in value.items():
                child_schema = properties.get(key)
                if isinstance(child_schema, dict):
                    reject_unknown_json_fields(child, child_schema, f"{path}/{key}")
                elif isinstance(resolved.get("additionalProperties"), dict):
                    reject_unknown_json_fields(
                        child,
                        cast(dict[str, Any], resolved["additionalProperties"]),
                        f"{path}/{key}",
                    )

        renderable_layers: list[RenderableLayer] = []
        for layer_index, layer_dict in enumerate(layers_raw):
            if isinstance(layer_dict, dict) and layer_dict.get("type") == "custom":
                unknown = sorted(set(layer_dict) - {"type", "name", "kwargs"})
                if unknown:
                    raise ValidationError(
                        f"Custom layer at /layers/{layer_index} contains unknown field(s): "
                        f"{', '.join(unknown)}"
                    )
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
                reject_unknown_json_fields(layer_dict, _LAYER_SCHEMA, f"/layers/{layer_index}")
                parsed_layer = _LAYER_ADAPTER.validate_python(layer_dict)
                cls._validate_plugin_layer_tree(parsed_layer, parser_registry)
                renderable_layers.append(parsed_layer)

        platform = raw.get("platform")
        if platform is not None and not isinstance(platform, str):
            CanvasModel.model_validate(raw)  # raises ValidationError with good message
            raise ValidationError("'platform' must be a string.")

        width = raw.get("width")
        height = raw.get("height")
        if platform is not None and width is None and height is None:
            try:
                preset = PLATFORM_SAFE_MARGIN_PRESETS[platform]
            except KeyError:
                supported = ", ".join(sorted(PLATFORM_SAFE_MARGIN_PRESETS))
                raise ValidationError(
                    f"Unsupported platform preset '{platform}'. Supported: {supported}"
                ) from None
            width = preset.width
            height = preset.height

        if not isinstance(width, int) or not isinstance(height, int):
            CanvasModel.model_validate(raw)  # raises ValidationError with good message
            raise ValidationError("'width' and 'height' must be integers.")

        return cls(
            width=width,
            height=height,
            layers=renderable_layers,
            platform=platform,
            registry=parser_registry,
        )

    @classmethod
    def _validate_plugin_layer_tree(cls, layer: RenderableLayer, registry: PluginRegistry) -> None:
        """Resolve every plugin in a parsed layer tree before it enters a Canvas."""
        if isinstance(layer, PluginLayer):
            registry.validate(layer)
            return
        if isinstance(layer, GroupLayer):
            for child in layer.children:
                cls._validate_plugin_layer_tree(child, registry)

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
        cls,
        spec_or_path: str,
        variables: Mapping[str, object] | None = None,
        *,
        registry: PluginRegistry | None = None,
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

        return cls.from_json(_VAR_RE.sub(substitute, raw_spec), registry=registry)

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

    def render_frame(self, time: float = 0.0) -> Image.Image:
        """Render one deterministic sampled frame of canonical layer motion."""
        if not isinstance(time, (int, float)) or not math.isfinite(time) or time < 0:
            raise ValidationError("motion frame time must be a finite non-negative number")
        return self._render_to_image(time=float(time))

    def _render_to_image(self, debug: bool = False, time: float | None = None) -> Image.Image:
        self._ctx.begin_render_pass()
        self._ctx.motion_time = time
        try:
            image = self._create_canvas()
            for layer in self._layers:
                self._render_moving_layer(image, layer, time)
            render_video_captions(
                image,
                iter_video_layers(self._layers),
                0.0 if time is None else time,
                self._ctx.video_info_cache,
                self._fonts.load_font_variant,
            )
            if debug:
                self._draw_debug_overlay(image)
            return image
        finally:
            self._ctx.motion_time = None
            self._ctx.close_video_decoders()

    def _draw_debug_overlay(self, image: Image.Image) -> None:
        draw = ImageDraw.Draw(image, "RGBA")
        font = self._fonts.load_font_variant(None, 10, False, False)

        measurements = list(reversed(measure_layers(self)))
        while measurements:
            measured = measurements.pop()
            measurements.extend(reversed(measured.children))

            if measured.bbox is None or not measured.visible or measured.bbox.is_empty:
                continue

            bbox = measured.bbox.clamped_to(self.width, self.height)
            if bbox is None:
                continue

            self._draw_debug_box(
                draw,
                bbox,
                measured.layer_id,
                (255, 45, 85, 255),
                font,
                image.size,
            )

    @staticmethod
    def _draw_debug_box(
        draw: ImageDraw.ImageDraw,
        bbox: BBox,
        label: str,
        color: tuple[int, int, int, int],
        font: ImageFont.ImageFont | ImageFont.FreeTypeFont,
        canvas_size: tuple[int, int],
    ) -> None:
        draw.rectangle((bbox.x, bbox.y, bbox.right - 1, bbox.bottom - 1), outline=color, width=2)

        label_bbox = draw.textbbox((0, 0), label, font=font)
        label_width = label_bbox[2] - label_bbox[0] + 6
        label_height = label_bbox[3] - label_bbox[1] + 4
        label_left = min(max(bbox.x, 0), max(0, canvas_size[0] - label_width))
        label_top = min(max(bbox.y, 0), max(0, canvas_size[1] - label_height))
        draw.rectangle(
            (label_left, label_top, label_left + label_width, label_top + label_height),
            fill=color,
        )
        draw.text((label_left + 3, label_top + 2), label, fill=(255, 255, 255, 255), font=font)

    def _staggered_target_count(self, layer: RenderableLayer) -> int:
        """Return how many semantic targets a layer's stagger addresses."""
        animation = getattr(layer, "animation", None)
        if animation is None:
            return 0
        from quickthumb.models import AnimationSpec

        animations = animation if isinstance(animation, list) else [animation]
        staggers = [
            item.stagger
            for item in animations
            if isinstance(item, AnimationSpec) and item.stagger is not None
        ]
        if not staggers or not isinstance(layer, TextLayer):
            return 0
        target = staggers[0].target
        if target not in {"lines", "words", "characters"}:
            return 0
        return len(self._text.resolve_animation_targets(layer, target))

    def _render_staggered_targets(
        self,
        image: Image.Image,
        surface: Image.Image,
        layer: RenderableLayer,
        time: float | None,
    ) -> bool:
        """Move each staggered target on its own, returning whether it applied.

        The layer is sliced out of its own finished render, so every target keeps
        the layout it was drawn with. Targets that cannot be told apart — lines
        set tight enough to touch, or a target kind with no visual band — fall
        back to moving the layer as a whole.
        """
        from quickthumb._export_base import composite_motion_targets, split_into_bands
        from quickthumb.motion import sample_canonical_targets

        count = self._staggered_target_count(layer)
        states = sample_canonical_targets(layer, time, count)
        if states is None:
            return False
        fragments = split_into_bands(surface, count)
        if fragments is None:
            return False
        composite_motion_targets(image, fragments, states)
        return True

    def _render_moving_layer(
        self, image: Image.Image, layer: RenderableLayer, time: float | None = None
    ):
        """Render one layer, moving it when canonical motion is being sampled.

        Geometry is applied to the layer's own rendered pixels rather than by
        each renderer, so every layer type moves the same way. Only this timed
        pass transforms; the exporters render layers untimed and apply the same
        geometry once per animation unit.
        """
        from quickthumb._export_base import apply_canonical_alpha, apply_canonical_geometry
        from quickthumb.motion import sample_canonical_state

        state = sample_canonical_state(layer, time)
        if state is None:
            self._render_layer(image, layer, time)
            return
        surface = Image.new("RGBA", image.size, (0, 0, 0, 0))
        self._render_layer(surface, layer, time)
        if self._render_staggered_targets(image, surface, layer, time):
            return
        bounds = surface.getbbox()
        if bounds is None:
            return
        fragment, position = apply_canonical_geometry(
            surface.crop(bounds),
            state,
            (bounds[0], bounds[1]),
            # Image layers fold scale into their source crop already.
            include_scale=not isinstance(layer, ImageLayer),
        )
        # Charts and QR codes reveal their own bars, points, and modules from the
        # same track, so a second generic clip on top would reveal twice.
        self_revealing = isinstance(layer, (ChartLayer, QRCodeLayer))
        fragment = apply_canonical_alpha(
            fragment, state, clip_progress=1.0 if self_revealing else state.clip_progress
        )
        if fragment is None:
            return
        image.alpha_composite(fragment, position)

    def _render_layer(self, image: Image.Image, layer: RenderableLayer, time: float | None = None):
        if has_layer_composition(layer):
            self._render_composed_layer(image, layer, time)
            return

        self._render_layer_direct(image, layer, time)

    def _render_composed_layer(
        self, image: Image.Image, layer: RenderableLayer, time: float | None = None
    ):
        isolated = self._layer_without_boundary_blend(layer)
        composite_layer_with_boundary(
            self._ctx,
            self._effects,
            image,
            layer,
            lambda layer_surface: self._render_layer_direct(layer_surface, isolated, time),
        )

    @staticmethod
    def _layer_without_boundary_blend(layer: RenderableLayer) -> RenderableLayer:
        updates: dict[str, Any] = {}
        if isinstance(layer, (ImageLayer, SvgLayer)) and layer.blend_mode is not None:
            updates["blend_mode"] = None
        effects = getattr(layer, "effects", None)
        if effects is not None:
            filtered = [effect for effect in effects if not isinstance(effect, BackdropBlur)]
            if len(filtered) != len(effects):
                updates["effects"] = filtered
        if updates and isinstance(layer, (ImageLayer, ShapeLayer, SvgLayer)):
            return layer.model_copy(update=updates)
        return layer

    def _render_layer_direct(
        self, image: Image.Image, layer: RenderableLayer, time: float | None = None
    ):
        if isinstance(layer, BackgroundLayer):
            self._render_background_layer(image, layer)
        elif isinstance(layer, TextLayer):
            self._text.render_text_layer(image, layer, time)
        elif isinstance(layer, OutlineLayer):
            self._render_outline_layer(image, layer)
        elif isinstance(layer, ImageLayer):
            self._images.render_image_layer(image, layer, time)
        elif isinstance(layer, ShapeLayer):
            self._shapes.render_shape_layer(image, layer)
        elif isinstance(layer, SvgLayer):
            self._images.render_svg_layer(image, layer)
        elif isinstance(layer, ChartLayer):
            self._visualizations.render_chart(image, layer, time)
        elif isinstance(layer, QRCodeLayer):
            self._visualizations.render_qr_code(image, layer, time)
        elif isinstance(layer, GroupLayer):
            self._groups.render_group_layer(image, layer, time=time)
        elif isinstance(layer, VideoLayer):
            info = self._ctx.video_info_cache.get(layer.source)
            if info is None:
                info = probe_video(layer.source)
                self._ctx.video_info_cache[layer.source] = info
            render_video_layer(
                image,
                layer,
                0.0 if time is None else time,
                info,
                self._ctx.video_frame_cache,
                self._ctx.video_decoder_cache,
                self._fonts.load_font_variant,
                self._images,
            )
        elif isinstance(layer, PluginLayer):
            raise RenderingError("Plugin layer rendering is not available until the D2 runtime.")
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
            elif (
                isinstance(layer, VideoLayer)
                and not is_url(layer.source)
                and not os.path.exists(layer.source)
            ):
                raise FileNotFoundError(f"{layer.source}")
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
            return self._images.load_and_fit_image(
                layer.image,
                size,
                layer.fit,
                focal_point=layer.focal_point,
                faces=layer.faces,
            )

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
