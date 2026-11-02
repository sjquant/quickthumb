"""Canonical glow pictures behind editable PowerPoint objects."""

from io import BytesIO

from PIL import Image

from quickthumb._export_base import RasterFragment, rasterize_layers
from quickthumb.models import (
    ExportDiagnostic,
    Glow,
    LinearGradient,
    RadialGradient,
    Shadow,
    ShapeLayer,
    Stroke,
    TextLayer,
)


def effect_diagnostic(layer, layer_id: str) -> ExportDiagnostic | None:
    """Report whether PPTX effects preserve editable content."""
    if not isinstance(layer, (ShapeLayer, TextLayer)):
        return None
    effects = list(layer.effects)
    if isinstance(layer, TextLayer) and isinstance(layer.content, list):
        for part in layer.content:
            effects.extend(part.effects)
    reason = effect_fallback_reason(layer)
    glows = any(isinstance(effect, Glow) for effect in effects)
    if not glows and reason is None:
        return None
    return ExportDiagnostic(
        layer_id=layer_id,
        feature="glow" if glows else "effects",
        target="pptx",
        support="fallback" if reason else "partial",
        fallback="rasterize",
        message=reason
        or (
            "Glow uses a fixed canonical PNG underlay behind editable opaque text/geometry; "
            "re-export after editing the foreground. Translucent or rich-text glow "
            "requires a complete PNG fallback."
        ),
    )


def effect_fallback_reason(layer) -> str | None:
    """Explain when effects require the complete layer to become an image."""
    if not isinstance(layer, (ShapeLayer, TextLayer)):
        return None
    styles = [layer]
    if isinstance(layer, TextLayer) and isinstance(layer.content, list):
        styles.extend(layer.content)
    effects = [effect for style in styles for effect in style.effects]
    glows = any(isinstance(effect, Glow) for effect in effects)
    strokes = [effect for effect in effects if isinstance(effect, Stroke)]
    if not (strokes or glows):
        return None
    translucent = layer.opacity != 1 or any(not _opaque(stroke.color) for stroke in strokes)
    if isinstance(layer, ShapeLayer):
        if translucent or not _opaque(layer.color) or layer.fill is not None:
            return "Translucent or gradient shape effects require a canonical PNG composite"
    else:
        paints = [(layer.color, layer.fill)]
        if isinstance(layer.content, list):
            paints = [
                (part.color or layer.color, part.fill or layer.fill) for part in layer.content
            ]
        for color, fill in paints:
            if fill is None:
                translucent |= not _opaque(color)
            elif not isinstance(fill, (LinearGradient, RadialGradient)) or any(
                not _opaque(color) for color, _ in fill.stops
            ):
                translucent = True
        if translucent or glows and isinstance(layer.content, list):
            return "Translucent text effects or rich-text glow require a canonical PNG composite"
    if glows and any(isinstance(effect, Shadow) for effect in effects):
        return "Interleaved glow and shadow require a canonical PNG composite"
    return None


def glow_fragment(canvas, layer, layout=None) -> RasterFragment | None:
    """Render only glow in the canonical layer coordinate system."""
    surface = Image.new("RGBA", (canvas.width, canvas.height))
    if isinstance(layer, ShapeLayer):
        source = rasterize_layers(canvas, [layer.model_copy(update={"effects": []})])
        if source is None:
            return None
        ink = Image.open(BytesIO(source.png_bytes)).convert("RGBA")
        for glow in layer.effects:
            if isinstance(glow, Glow):
                canvas._images.apply_image_glow(surface, ink, source.x, source.y, glow)
    else:
        assert layout is not None
        stage = surface
        if layout.rot_center_local is not None:
            cx, cy = layout.rot_center_local
            stage = Image.new("RGBA", (round(cx * 2), round(cy * 2)))
        for line in layout.lines:
            for run in line:
                for glow in run.glows:
                    if run.char_xs is not None and isinstance(layer.content, str):
                        top = run.baseline_y + run.font.getbbox(run.text, anchor="ls")[1]
                        canvas._text._render_letter_spaced_glow(
                            stage,
                            run.text,
                            run.font,
                            (round(run.pen_x), round(top)),
                            glow,
                            run.letter_spacing,
                            canvas._text._calculate_char_widths(run.text, run.font),
                        )
                    else:
                        canvas._text._render_glow(
                            stage,
                            run.text,
                            run.font,
                            (round(run.pen_x), round(run.baseline_y)),
                            glow,
                            anchor="ls",
                        )
        if stage is not surface:
            canvas._text._rotate_and_composite_text(
                surface, stage, canvas._text.effective_layer(layer)
            )
    bounds = surface.getbbox()
    if bounds is None:
        return None
    patch = surface.crop(bounds)
    encoded = BytesIO()
    patch.save(encoded, format="PNG")
    return RasterFragment(encoded.getvalue(), bounds[0], bounds[1], patch.width, patch.height)


def _opaque(color: str | None) -> bool:
    return color is None or len(color) == 7 or color[-2:].lower() == "ff"
