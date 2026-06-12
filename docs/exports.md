---
description: Export quickthumb canvases to SVG, standalone HTML, and editable PowerPoint (PPTX) documents alongside PNG/JPEG/WEBP.
---

# Exporting to SVG, HTML & PPTX

Beyond raster images, a canvas can render to vector and document formats. The output format is detected from the file extension:

```python
canvas.render("thumbnail.png")   # raster (PNG/JPEG/WEBP)
canvas.render("thumbnail.svg")   # vector SVG
canvas.render("thumbnail.html")  # standalone HTML page
canvas.render("thumbnail.pptx")  # editable PowerPoint slide
```

Each format also has a direct method when you want the content in memory:

```python
svg_markup = canvas.to_svg()
html_page = canvas.to_html(title="Launch card")
pptx_bytes = canvas.to_pptx()
```

## How export works

Exporters keep layers **native** wherever the target format can express them, and embed **pixel-exact PNG fragments** (rendered by the regular pipeline) everywhere else. Positions, wrapping, and alignment are computed with the same layout math as the raster renderer, so output matches the PNG render closely.

| Layer | SVG / HTML | PPTX |
| --- | --- | --- |
| Background color / gradient | Native `rect` + gradient defs | Native shape fill (linear gradients native, radial embedded) |
| Outline | Native `rect` stroke | Native bordered rectangle |
| Shapes (all primitives) | Native elements, incl. rotation and stroke/shadow/glow | Native autoshapes; polygons become freeforms |
| Text (simple & rich) | Native `<text>` per line/run, incl. wrapping, letter spacing, gradient fills, effects | Editable text boxes with per-run styling |
| Groups (auto-layout) | Children exported natively at their layout positions | Same |
| Images & image-filled text | Embedded PNG fragment | Embedded picture |
| SVG layers | Embedded as vector data URL (raster when effects are applied) | Embedded picture |
| Blend modes & custom layers | Everything below the last blend/custom layer is flattened into one PNG | Same |

## SVG

```python
svg = canvas.to_svg()
svg = canvas.to_svg(embed_fonts=True)
```

By default the SVG references fonts by family name (`font-family="Roboto"`), which keeps files small but requires the font on the viewing machine. With `embed_fonts=True` the used font files are inlined as `@font-face` data URLs so text renders identically everywhere.

!!! note "Viewer support"
    Shadow and glow effects use SVG filters (`feGaussianBlur`). Browsers render them faithfully; some minimal SVG rasterizers apply filters only partially.

## HTML

```python
html = canvas.to_html(title="My thumbnail")
```

The HTML export wraps the SVG render in a standalone, self-contained page. Fonts are embedded by default (`embed_fonts=True`) so the file can be shared as-is, like an image file that stays selectable and editable.

## PPTX

PPTX export requires the optional dependency:

```bash
uv pip install "quickthumb[pptx]"
```

The canvas becomes a single slide sized to the canvas pixels (at 96 dpi). Text stays fully editable — font family, size, weight, color, alignment, and line wrapping are carried over run by run, and stroke/shadow/glow effects map to PowerPoint text outline and effect properties.

```python
canvas.render("promo.pptx")
# or
with open("promo.pptx", "wb") as f:
    f.write(canvas.to_pptx())
```

!!! note "Fidelity"
    PowerPoint lays text out with its own font metrics, so text placement is a close approximation rather than pixel-identical. Radial background gradients and multi-stop text gradients beyond what DrawingML supports are embedded as pictures or approximated.

## CLI

The CLI picks the format from the output extension too:

```bash
quickthumb render spec.json -o card.svg
quickthumb render spec.json -o card.html
quickthumb render spec.json -o card.pptx
```
