from collections.abc import Iterable
from itertools import islice
from math import ceil
from typing import TYPE_CHECKING
from unicodedata import category

from PIL import Image, ImageChops

from quickthumb._base import DEFAULT_TEXT_SIZE, RenderContext, parse_coordinate
from quickthumb._diagnostic_rules import (
    PLATFORM_SAFE_MARGIN_PRESETS,
    LayerAlphaCache,
    OverlapMeasurement,
    SafeMarginPreset,
    TiledContrastMeasurement,
    average_visible_background,
    bbox_payload,
    clear_overlap_suggestion,
    diagnostic_context,
    edge_distances,
    layer_label,
    mask_area,
    move_inside_canvas_suggestion,
    move_inside_safe_area_suggestion,
    overlap_pairs,
    require_bbox,
    resolve_overlay_bbox,
    resolve_safe_margins,
    safe_area_bbox,
    visible_leaf_layers,
    worst_tile_contrast,
)
from quickthumb._effects import EffectsEngine
from quickthumb._groups import GroupEngine
from quickthumb._images import ImageEngine
from quickthumb._measurements import BBox, LayerMeasurement, measure_layers
from quickthumb._shapes import ShapeEngine
from quickthumb._text import TextEngine

if TYPE_CHECKING:
    from quickthumb.canvas import Canvas
from quickthumb.models import (
    BackgroundLayer,
    Diagnostic,
    DiagnosticBBox,
    GroupLayer,
    ImageLayer,
    ShapeLayer,
    SvgLayer,
    TextLayer,
)

TINY_TEXT_RATIO = 0.025
LOW_CONTRAST_THRESHOLD = 2.0
CONTRAST_TILE_SIZE = 32
MIN_PARTIAL_OVERLAP_RATIO = 0.2
BACKDROP_COVERAGE_RATIO = 0.95
OVERLAP_CLEARANCE_PX = 8


class DiagnosticsEngine:
    """Pre-render legibility and layout checks over a canvas's layers."""

    def __init__(
        self,
        ctx: RenderContext,
        canvas: "Canvas",
        effects: EffectsEngine,
        images: ImageEngine,
        shapes: ShapeEngine,
        text: TextEngine,
        groups: GroupEngine,
    ):
        self._ctx = ctx
        self._canvas = canvas
        self._effects = effects
        self._images = images
        self._shapes = shapes
        self._text = text
        self._groups = groups
        self._alpha_cache = LayerAlphaCache(
            self._has_opaque_rectangle_mask, self._render_layer_alpha_mask
        )

    def diagnose(self) -> list[Diagnostic]:
        """Check layers for layout and legibility issues without producing an output file.

        Returns structured findings (off-canvas, tiny-text, text-overflow,
        low-contrast, layer-overlap) that an agent or human can act on before
        rendering.
        """
        self._alpha_cache.clear()
        self._canvas._validate_image_paths()
        self._ctx.begin_render_pass()

        diagnostics: list[Diagnostic] = []
        measurements = measure_layers(self._canvas)
        running = self._canvas._create_canvas()
        for measured in measurements:
            if measured.visible:
                layer = measured.raw_layer
                if isinstance(layer, TextLayer):
                    diagnostics.extend(self._diagnose_text_layer(running, measured))
                elif isinstance(layer, GroupLayer):
                    for child in measured.text_descendants():
                        if child.visible:
                            diagnostics.extend(self._diagnose_text_layer(running, child))

                if measured.bbox is not None:
                    finding = self._diagnose_off_canvas(measured)
                    if finding is not None:
                        diagnostics.append(finding)

            self._canvas._render_layer(running, measured.raw_layer)

        diagnostics.extend(self._diagnose_layer_overlaps(measurements))
        diagnostics.extend(self._diagnose_hidden_layers(measurements))
        edge_ignored_layer_ids = set()
        for finding in diagnostics:
            if finding.code == "off-canvas" and finding.layer_id is not None:
                edge_ignored_layer_ids.add(finding.layer_id)
            elif finding.code == "layer-hidden":
                edge_ignored_layer_ids.update(finding.related_layers)
        diagnostics.extend(
            self._diagnose_edge_crowding(measurements, ignored_layer_ids=edge_ignored_layer_ids)
        )

        return diagnostics

    def _diagnose_layer_overlaps(self, measurements: list[LayerMeasurement]) -> list[Diagnostic]:
        findings: list[Diagnostic] = []
        candidates = list(visible_leaf_layers(measurements))
        for lower, upper in overlap_pairs(candidates):
            finding = self._diagnose_candidate_overlap(lower, upper)
            if finding is not None:
                findings.append(finding)
        return findings

    def _diagnose_candidate_overlap(
        self, lower: LayerMeasurement, upper: LayerMeasurement
    ) -> Diagnostic | None:
        lower_box = require_bbox(lower)
        upper_box = require_bbox(upper)
        overlap = lower_box.intersection(upper_box)
        if overlap is None:
            return None

        measured_overlap = self._alpha_cache.measure(lower, upper, overlap)
        if measured_overlap is None:
            return None

        if not self._is_suspicious_overlap(lower, upper, measured_overlap):
            return None

        suggestion = clear_overlap_suggestion(
            upper,
            lower,
            canvas_width=self._ctx.width,
            canvas_height=self._ctx.height,
            clearance=OVERLAP_CLEARANCE_PX,
        )
        return Diagnostic(
            code="layer-overlap",
            severity="warning",
            layer_index=upper.index,
            message=(
                f"{layer_label(upper)} (order {upper.order}) "
                f"overlaps {layer_label(lower)} "
                f"(order {lower.order}); bbox_overlap={measured_overlap.bbox_area}px "
                f"(bbox_overlap_pct={measured_overlap.upper_bbox_pct:.0%} of upper, "
                f"{measured_overlap.lower_bbox_pct:.0%} of lower), "
                f"visible_overlap={measured_overlap.visible_area}px "
                f"(visible_overlap_pct={measured_overlap.upper_visible_pct:.0%} of upper, "
                f"{measured_overlap.lower_visible_pct:.0%} of lower); {suggestion}"
            ),
            layer_id=upper.layer_id,
            layer_name=upper.name,
            bbox=DiagnosticBBox(**bbox_payload(overlap)),
            related_layers=[upper.layer_id, lower.layer_id],
            measured={
                "lower_layer_id": lower.layer_id,
                "upper_layer_id": upper.layer_id,
                "lower_bbox": bbox_payload(lower_box),
                "upper_bbox": bbox_payload(upper_box),
                "overlap_bbox": bbox_payload(overlap),
                "bbox_overlap": measured_overlap.bbox_area,
                "bbox_overlap_pct_lower": measured_overlap.lower_bbox_pct,
                "bbox_overlap_pct_upper": measured_overlap.upper_bbox_pct,
                "visible_overlap": measured_overlap.visible_area,
                "visible_overlap_pct_lower": measured_overlap.lower_visible_pct,
                "visible_overlap_pct_upper": measured_overlap.upper_visible_pct,
            },
            suggestion=suggestion,
        )

    def _is_suspicious_overlap(
        self, lower: LayerMeasurement, upper: LayerMeasurement, overlap: OverlapMeasurement
    ) -> bool:
        if lower.layer_type == "text" and upper.layer_type == "text":
            return True

        if lower.layer_type == "text":
            return overlap.lower_visible_pct >= MIN_PARTIAL_OVERLAP_RATIO

        if self._is_text_on_backdrop(lower, upper, overlap):
            return False

        if max(overlap.lower_visible_pct, overlap.upper_visible_pct) >= BACKDROP_COVERAGE_RATIO:
            return True

        overlap_ratio = min(overlap.lower_visible_pct, overlap.upper_visible_pct)
        return overlap_ratio >= MIN_PARTIAL_OVERLAP_RATIO

    def _is_text_on_backdrop(
        self, lower: LayerMeasurement, upper: LayerMeasurement, overlap: OverlapMeasurement
    ) -> bool:
        if lower.layer_type == "text" or upper.layer_type != "text":
            return False
        return overlap.upper_visible_pct >= BACKDROP_COVERAGE_RATIO

    def _diagnose_hidden_layers(self, measurements: list[LayerMeasurement]) -> list[Diagnostic]:
        findings: list[Diagnostic] = []
        candidates = list(visible_leaf_layers(measurements))
        opaque_backgrounds = [
            measured
            for measured in measurements
            if measured.visible
            and isinstance(measured.raw_layer, BackgroundLayer)
            and self._is_opaque_background(measured.raw_layer)
        ]
        for lower_index, lower in enumerate(candidates):
            finding = self._diagnose_hidden_layer(
                lower,
                islice(candidates, lower_index + 1, None),
                [
                    background.layer_id
                    for background in opaque_backgrounds
                    if background.order > lower.order
                ],
            )
            if finding is not None:
                findings.append(finding)
        return findings

    def _diagnose_hidden_layer(
        self,
        lower: LayerMeasurement,
        later_layers: Iterable[LayerMeasurement],
        later_background_ids: list[str],
    ) -> Diagnostic | None:
        lower_alpha = self._alpha_cache.get(lower)
        if lower_alpha.visible_area == 0:
            return None

        lower_box = require_bbox(lower)
        lower_mask = self._alpha_cache.region_mask(lower, lower_box)
        coverage = Image.new("L", (lower_box.width, lower_box.height), 0)
        covering_layer_ids = list(later_background_ids)
        covered_visible_area = 0
        if covering_layer_ids:
            coverage.paste(255, (0, 0, lower_box.width, lower_box.height))
            covered_visible_area = lower_alpha.visible_area
        if covered_visible_area >= lower_alpha.visible_area:
            return self._hidden_layer_diagnostic(lower, covering_layer_ids)

        for upper in later_layers:
            if not self._can_hide_lower_layer(upper):
                continue
            overlap = lower_box.intersection(require_bbox(upper))
            if overlap is None:
                continue

            newly_covered = self._add_layer_coverage(
                coverage, lower_box, lower_mask, upper, overlap
            )
            if newly_covered > 0:
                covered_visible_area += newly_covered
                covering_layer_ids.append(upper.layer_id)

            if covered_visible_area >= lower_alpha.visible_area:
                return self._hidden_layer_diagnostic(lower, covering_layer_ids)

        return None

    def _add_layer_coverage(
        self,
        coverage: Image.Image,
        lower_box: BBox,
        lower_mask: Image.Image,
        upper: LayerMeasurement,
        overlap: BBox,
    ) -> int:
        local_box = (
            overlap.x - lower_box.x,
            overlap.y - lower_box.y,
            overlap.right - lower_box.x,
            overlap.bottom - lower_box.y,
        )
        upper_mask = self._opaque_region_mask(upper, overlap)
        existing = coverage.crop(local_box)
        lower_region = lower_mask.crop(local_box)
        newly_covered = ImageChops.multiply(ImageChops.subtract(upper_mask, existing), lower_region)
        combined = ImageChops.lighter(existing, upper_mask)
        coverage.paste(combined, local_box)
        return mask_area(newly_covered)

    def _hidden_layer_diagnostic(
        self, lower: LayerMeasurement, covering_layer_ids: list[str]
    ) -> Diagnostic:
        lower_box = require_bbox(lower)
        suggestion = (
            f"remove layer {lower.index}, move it above the covering layers, "
            "or move the covering layers"
        )
        return Diagnostic(
            code="layer-hidden",
            severity="warning",
            layer_index=lower.index,
            message=(
                f"{layer_label(lower)} (order {lower.order}) is fully hidden by later "
                f"opaque visible layers; {suggestion}"
            ),
            layer_id=lower.layer_id,
            layer_name=lower.name,
            bbox=DiagnosticBBox(**bbox_payload(lower_box)),
            related_layers=[lower.layer_id, *covering_layer_ids],
            measured={
                "layer_type": lower.layer_type,
                "visible_area": self._alpha_cache.get(lower).visible_area,
                "hidden_visible_pct": 1.0,
                "covering_layer_ids": covering_layer_ids,
            },
            suggestion=suggestion,
        )

    def _can_hide_lower_layer(self, measured: LayerMeasurement) -> bool:
        layer = measured.raw_layer
        if not measured.visible or measured.bbox is None:
            return False
        if float(getattr(layer, "opacity", 1.0)) < 1.0:
            return False
        blend_mode = getattr(layer, "blend_mode", None)
        blend_value = getattr(blend_mode, "value", blend_mode)
        return blend_value in (None, "normal")

    def _is_opaque_background(self, layer: BackgroundLayer) -> bool:
        if layer.blend_mode is not None:
            return False
        image = self._canvas._create_canvas()
        self._canvas._render_background_layer(image, layer)
        return (
            mask_area(self._opaque_mask(image.getchannel("A")))
            == self._ctx.width * self._ctx.height
        )

    def _diagnose_edge_crowding(
        self, measurements: list[LayerMeasurement], *, ignored_layer_ids: set[str]
    ) -> list[Diagnostic]:
        findings: list[Diagnostic] = []
        platform = getattr(self._canvas, "platform", None)
        preset = PLATFORM_SAFE_MARGIN_PRESETS.get(platform) if platform is not None else None
        margins = resolve_safe_margins(
            preset, canvas_width=self._ctx.width, canvas_height=self._ctx.height
        )
        safe_area = safe_area_bbox(
            canvas_width=self._ctx.width, canvas_height=self._ctx.height, margins=margins
        )
        for measured in visible_leaf_layers(measurements):
            if measured.layer_id in ignored_layer_ids:
                continue
            finding = self._diagnose_margin_crowding(measured, preset, margins, safe_area)
            if finding is not None:
                findings.append(finding)
            findings.extend(self._diagnose_overlay_crowding(measured, preset))
        return findings

    def _diagnose_margin_crowding(
        self,
        measured: LayerMeasurement,
        preset: SafeMarginPreset | None,
        margins: tuple[int, int, int, int],
        safe_area: BBox,
    ) -> Diagnostic | None:
        box = require_bbox(measured)
        if box.is_partially_outside(self._ctx.width, self._ctx.height):
            return None
        distances = edge_distances(
            box, canvas_width=self._ctx.width, canvas_height=self._ctx.height
        )
        top, right, bottom, left = margins
        thresholds = {"top": top, "right": right, "bottom": bottom, "left": left}
        crowded_edges = [
            edge for edge, distance in distances.items() if distance < thresholds[edge]
        ]
        if not crowded_edges:
            return None

        platform = preset.name if preset is not None else None
        suggestion = move_inside_safe_area_suggestion(measured, safe_area, platform=platform)
        target = f"{platform} safe area" if platform else "safe area"
        return Diagnostic(
            code="edge-crowding",
            severity="warning",
            layer_index=measured.index,
            message=(
                f"{layer_label(measured)} is too close to the "
                f"{', '.join(crowded_edges)} edge(s) of the {target}; {suggestion}"
            ),
            measured={
                "layer_type": measured.layer_type,
                "platform": platform,
                "edges": crowded_edges,
                "distances": distances,
                "margins": {
                    "top": top,
                    "right": right,
                    "bottom": bottom,
                    "left": left,
                },
                "safe_bbox": bbox_payload(safe_area),
            },
            suggestion=suggestion,
            **diagnostic_context(measured),
        )

    def _diagnose_overlay_crowding(
        self, measured: LayerMeasurement, preset: SafeMarginPreset | None
    ) -> list[Diagnostic]:
        if preset is None:
            return []

        box = require_bbox(measured)
        findings: list[Diagnostic] = []
        for overlay in preset.overlays:
            overlay_box = resolve_overlay_bbox(
                overlay, canvas_width=self._ctx.width, canvas_height=self._ctx.height
            )
            overlap = box.intersection(overlay_box)
            if overlap is None:
                continue

            suggestion = (
                f"move layer {measured.index} away from the {preset.name} {overlay.label} overlay"
            )
            findings.append(
                Diagnostic(
                    code="edge-crowding",
                    severity="warning",
                    layer_index=measured.index,
                    message=(
                        f"{layer_label(measured)} intersects the {preset.name} "
                        f"{overlay.label} overlay; {suggestion}"
                    ),
                    layer_id=measured.layer_id,
                    layer_name=measured.name,
                    bbox=DiagnosticBBox(**bbox_payload(overlap)),
                    related_layers=[measured.layer_id],
                    measured={
                        "layer_type": measured.layer_type,
                        "platform": preset.name,
                        "overlay": overlay.name,
                        "overlay_label": overlay.label,
                        "overlay_bbox": bbox_payload(overlay_box),
                        "overlap_bbox": bbox_payload(overlap),
                    },
                    suggestion=suggestion,
                )
            )
        return findings

    def _has_opaque_rectangle_mask(self, measured: LayerMeasurement) -> bool:
        layer = measured.raw_layer
        if not (
            isinstance(layer, ShapeLayer)
            and layer.shape == "rectangle"
            and layer.border_radius == 0
            and layer.rotation == 0
            and layer.opacity == 1.0
            and not layer.effects
        ):
            return False
        color = self._effects.parse_color(layer.color)
        return len(color) < 4 or color[3] == 255

    def _render_layer_alpha_mask(self, measured: LayerMeasurement) -> Image.Image:
        return self._render_layer_alpha_channel(measured).point(lambda value: 255 if value else 0)

    def _opaque_region_mask(self, measured: LayerMeasurement, region: BBox) -> Image.Image:
        if self._has_opaque_rectangle_mask(measured):
            return Image.new("L", (region.width, region.height), 255)

        box = require_bbox(measured)
        left, top = region.x - box.x, region.y - box.y
        return self._opaque_mask(
            self._render_layer_alpha_channel(measured).crop(
                (left, top, left + region.width, top + region.height)
            )
        )

    def _render_layer_alpha_channel(self, measured: LayerMeasurement) -> Image.Image:
        box = require_bbox(measured)
        image = Image.new("RGBA", (self._ctx.width, self._ctx.height), (0, 0, 0, 0))
        layer = measured.raw_layer
        if isinstance(layer, TextLayer):
            self._text.render_text_layer(image, layer)
        elif isinstance(layer, ImageLayer):
            self._images.render_image_layer(image, layer)
        elif isinstance(layer, SvgLayer):
            self._images.render_svg_layer(image, layer)
        elif isinstance(layer, ShapeLayer):
            self._shapes.render_shape_layer(image, layer)
        else:
            return Image.new("L", (box.width, box.height), 0)
        return image.getchannel("A").crop((box.x, box.y, box.right, box.bottom))

    def _opaque_mask(self, alpha: Image.Image) -> Image.Image:
        return alpha.point(lambda value: 255 if value == 255 else 0)

    def _diagnose_off_canvas(self, measured: LayerMeasurement) -> Diagnostic | None:
        box = measured.bbox
        if box is None or box.is_empty:
            return None
        x, y, w, h = box.as_tuple()
        layer_type = measured.layer_type

        if box.is_fully_outside(self._ctx.width, self._ctx.height):
            return Diagnostic(
                code="off-canvas",
                severity="error",
                layer_index=measured.index,
                message=(
                    f"{layer_type} layer at ({x}, {y}) size {w}x{h} is entirely outside "
                    f"the {self._ctx.width}x{self._ctx.height} canvas"
                ),
                measured={
                    "layer_type": layer_type,
                    "canvas_width": self._ctx.width,
                    "canvas_height": self._ctx.height,
                    "outside": "fully",
                },
                suggestion=move_inside_canvas_suggestion(
                    measured,
                    canvas_width=self._ctx.width,
                    canvas_height=self._ctx.height,
                ),
                **diagnostic_context(measured),
            )
        if box.is_partially_outside(self._ctx.width, self._ctx.height):
            return Diagnostic(
                code="off-canvas",
                severity="warning",
                layer_index=measured.index,
                message=(
                    f"{layer_type} layer at ({x}, {y}) size {w}x{h} extends past the edge "
                    f"of the {self._ctx.width}x{self._ctx.height} canvas"
                ),
                measured={
                    "layer_type": layer_type,
                    "canvas_width": self._ctx.width,
                    "canvas_height": self._ctx.height,
                    "outside": "partially",
                },
                suggestion=move_inside_canvas_suggestion(
                    measured,
                    canvas_width=self._ctx.width,
                    canvas_height=self._ctx.height,
                ),
                **diagnostic_context(measured),
            )
        return None

    def _diagnose_text_layer(
        self, running: Image.Image, measured: LayerMeasurement
    ) -> list[Diagnostic]:
        findings: list[Diagnostic] = []
        layer = measured.effective_text_layer
        if layer is None:
            return findings

        size = self._minimum_text_size(layer)
        tiny_threshold = self._ctx.height * TINY_TEXT_RATIO
        if size < tiny_threshold:
            findings.append(
                Diagnostic(
                    code="tiny-text",
                    severity="warning",
                    layer_index=measured.index,
                    message=(
                        f"text size {size}px is below {tiny_threshold:.0f}px "
                        f"({TINY_TEXT_RATIO:.1%} of canvas height) and may be illegible "
                        "at thumbnail display sizes"
                    ),
                    measured={
                        "font_size": size,
                        "threshold": tiny_threshold,
                        "threshold_ratio": TINY_TEXT_RATIO,
                        "canvas_height": self._ctx.height,
                    },
                    suggestion=f"increase text size to at least {ceil(tiny_threshold)}px",
                    **diagnostic_context(measured),
                )
            )

        overflow = self._find_overflowing_word(layer)
        if overflow is not None:
            word, word_width, max_width = overflow
            findings.append(
                Diagnostic(
                    code="text-overflow",
                    severity="warning",
                    layer_index=measured.index,
                    message=(
                        f"word '{word}' is wider than max_width={layer.max_width} "
                        "and cannot be wrapped"
                    ),
                    measured={
                        "word": word,
                        "word_width": word_width,
                        "max_width": max_width,
                    },
                    suggestion=(
                        f"increase max_width to at least {word_width}px or enable auto_scale"
                    ),
                    **diagnostic_context(measured),
                )
            )

        clipping = self._find_text_clipping(measured, has_overflow=overflow is not None)
        if clipping is not None:
            findings.append(
                Diagnostic(
                    code="text-clipped",
                    severity="warning",
                    layer_index=measured.index,
                    message=(
                        f"wrapped text block at ({clipping['text_bbox']['x']}, "
                        f"{clipping['text_bbox']['y']}) size "
                        f"{clipping['text_bbox']['width']}x{clipping['text_bbox']['height']} "
                        f"exceeds {clipping['clipped_by']} and may be clipped"
                    ),
                    measured=clipping,
                    suggestion=(
                        "move the text fully inside the canvas, reduce text size, "
                        "increase max_width, or enable auto_scale"
                    ),
                    **diagnostic_context(measured),
                )
            )

        missing_glyphs = self._find_missing_glyphs(layer)
        if missing_glyphs:
            display = ", ".join(repr(char) for char in missing_glyphs)
            findings.append(
                Diagnostic(
                    code="missing-glyph",
                    severity="warning",
                    layer_index=measured.index,
                    message=(
                        f"text contains glyphs that render as the font replacement glyph: {display}"
                    ),
                    measured={
                        "characters": missing_glyphs,
                        "character_count": len(missing_glyphs),
                    },
                    suggestion=f"use a font that supports {display}",
                    **diagnostic_context(measured),
                )
            )

        contrast = self._text_background_contrast(running, measured)
        if contrast is not None and contrast.contrast < LOW_CONTRAST_THRESHOLD:
            findings.append(
                Diagnostic(
                    code="low-contrast",
                    severity="warning",
                    layer_index=measured.index,
                    message=(
                        f"text worst-tile contrast ratio {contrast.contrast:.2f} "
                        "against the layers below it "
                        f"is under {LOW_CONTRAST_THRESHOLD}; the text may be hard to read"
                    ),
                    measured={
                        "contrast": contrast.contrast,
                        "threshold": LOW_CONTRAST_THRESHOLD,
                        "method": "worst-tile",
                        "tile_bbox": bbox_payload(contrast.tile),
                        "tile_count": contrast.tile_count,
                        "tile_size": CONTRAST_TILE_SIZE,
                        "foreground_rgb": contrast.foreground,
                        "background_rgb": contrast.background,
                    },
                    suggestion=(
                        f"increase foreground/background contrast to at least "
                        f"{LOW_CONTRAST_THRESHOLD}:1"
                    ),
                    **diagnostic_context(measured),
                )
            )

        return findings

    def _minimum_text_size(self, layer: TextLayer) -> int:
        if isinstance(layer.content, list):
            return min(self._text.resolve_size(part, layer) for part in layer.content)
        return layer.size or DEFAULT_TEXT_SIZE

    def _find_overflowing_word(self, layer: TextLayer) -> tuple[str, int, int] | None:
        if not layer.max_width:
            return None

        max_width_px = parse_coordinate(layer.max_width, self._ctx.width)

        for text, font, letter_spacing in self._text.iter_text_runs(layer):
            word = self._first_word_wider_than(text, font, letter_spacing, max_width_px)
            if word is not None:
                return word
        return None

    def _first_word_wider_than(
        self, text: str, font, letter_spacing: int, max_width_px: int
    ) -> tuple[str, int, int] | None:
        for word in text.split():
            width, _ = self._text.measure_text_bounds(word, font, letter_spacing)
            if width > max_width_px:
                return word, width, max_width_px
        return None

    def _find_text_clipping(
        self, measured: LayerMeasurement, *, has_overflow: bool = False
    ) -> dict | None:
        layer = measured.effective_text_layer
        box = measured.bbox
        if layer is None or box is None or not layer.max_width:
            return None

        wrapped_lines = tuple(measured.metadata.get("wrapped_lines", ()))
        if len(wrapped_lines) < 2:
            return None

        max_width_px = parse_coordinate(layer.max_width, self._ctx.width)
        text_bbox = bbox_payload(box)
        base = {
            "text_bbox": text_bbox,
            "wrapped_line_count": len(wrapped_lines),
            "max_width": max_width_px,
            "text_width": box.width,
            "text_height": box.height,
            "canvas_width": self._ctx.width,
            "canvas_height": self._ctx.height,
        }

        canvas_overflow = self._canvas_overflow(box)
        if canvas_overflow:
            if has_overflow and "top" not in canvas_overflow and "bottom" not in canvas_overflow:
                return None
            return {
                **base,
                "clipped_by": "canvas",
                "overflow": canvas_overflow,
            }

        if box.width > max_width_px:
            return {
                **base,
                "clipped_by": "max_width",
                "overflow_width": box.width - max_width_px,
            }

        return None

    def _canvas_overflow(self, box) -> dict[str, int]:
        overflow = {
            "left": max(0, -box.x),
            "top": max(0, -box.y),
            "right": max(0, box.right - self._ctx.width),
            "bottom": max(0, box.bottom - self._ctx.height),
        }
        return {edge: amount for edge, amount in overflow.items() if amount > 0}

    def _find_missing_glyphs(self, layer: TextLayer) -> list[str]:
        missing: list[str] = []
        reported_missing: set[str] = set()
        checked: set[tuple[object, str]] = set()
        for text, font, _letter_spacing in self._text.iter_text_runs(layer):
            missing_signatures = self._missing_glyph_signatures(font)
            for char in text:
                if (
                    char in reported_missing
                    or char in {"\u25a1", "\ufffd"}
                    or char.isspace()
                    or category(char)[0] == "C"
                ):
                    continue

                checked_key = (font, char)
                if checked_key in checked:
                    continue
                checked.add(checked_key)

                signature = self._glyph_signature(font, char)
                if signature is not None and signature in missing_signatures:
                    missing.append(char)
                    reported_missing.add(char)
        return missing

    def _missing_glyph_signatures(self, font) -> set:
        return {
            signature
            for probe in ("\ufffd", "\uffff", "\u0378")
            if (signature := self._glyph_signature(font, probe)) is not None
        }

    def _glyph_signature(self, font, char: str):
        try:
            mask = font.getmask(char)
            data = bytes(mask)
            if not data or not any(data):
                return None
            return font.getbbox(char), mask.size, data
        except (OSError, UnicodeError, ValueError):
            return None

    def _text_background_contrast(
        self, running: Image.Image, measured: LayerMeasurement
    ) -> TiledContrastMeasurement | None:
        """Worst contrast ratio between the layer's visible text pixels and the area below."""
        layer = measured.effective_text_layer
        if layer is None:
            return None

        box = measured.bbox
        if box is None:
            return None
        clamped = box.clamped_to(self._ctx.width, self._ctx.height)
        if clamped is None:
            return None

        content = layer.content
        if isinstance(content, list):
            content = [part.model_copy(update={"effects": []}) for part in content]
        foreground_layer = layer.model_copy(update={"content": content, "effects": []})
        foreground = Image.new("RGBA", (self._ctx.width, self._ctx.height), (0, 0, 0, 0))
        self._text.render_text_layer(foreground, foreground_layer)
        return worst_tile_contrast(
            running,
            foreground,
            clamped,
            tile_size=CONTRAST_TILE_SIZE,
        )
