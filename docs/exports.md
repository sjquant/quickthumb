---
description: Export quickthumb canvases to SVG, editable PowerPoint (PPTX), and PDF documents alongside PNG/JPEG/WEBP.
---

# Exporting to SVG, PPTX & PDF

Beyond raster images, a canvas can render to vector and document formats. The output format is detected from the file extension:

```python
canvas.render("thumbnail.png")   # raster (PNG/JPEG/WEBP)
canvas.render("thumbnail.svg")   # vector SVG
canvas.render("thumbnail.pptx")  # editable PowerPoint slide
canvas.render("thumbnail.pdf")   # single-page PDF
```

Each format also has a direct method when you want the content in memory:

```python
svg_markup = canvas.to_svg()
pptx_bytes = canvas.to_pptx()
pdf_bytes = canvas.to_pdf()
```

## How export works

Exporters keep layers **native** wherever the target format can express them, and embed **pixel-exact PNG fragments** (rendered by the regular pipeline) everywhere else. Positions, wrapping, and alignment are computed with the same layout math as the raster renderer, so output matches the PNG render closely.

| Layer | SVG | PPTX | PDF |
| --- | --- | --- | --- |
| Background color / gradient | Native `rect` + gradient defs | Native shape fill (linear gradients native, radial embedded) | Native fill; opaque gradients native, translucent gradients embedded |
| Outline | Native `rect` stroke | Native bordered rectangle | Native rectangle stroke |
| Shapes (all primitives) | Native elements, incl. rotation and stroke/shadow/glow | Native autoshapes; polygons become freeforms | Native paths incl. rotation; shapes with effects embedded |
| Text (simple & rich) | Native `<text>` per line/run, incl. wrapping, letter spacing, gradient fills, effects | Editable text boxes with per-run styling | Native selectable text with embedded fonts; runs with gradient/image fills or blur effects embedded |
| Groups (auto-layout) | Children exported natively at their layout positions | Same | Same |
| Images & image-filled text | Embedded PNG fragment | Embedded picture | Embedded picture |
| SVG layers | Embedded as vector data URL (raster when effects are applied) | Embedded picture | Embedded picture |
| Blend modes & custom layers | Everything below the last blend/custom layer is flattened into one PNG | Same | Same |

## SVG

```python
svg = canvas.to_svg()
svg = canvas.to_svg(embed_fonts=True)
```

By default the SVG references fonts by family name (`font-family="Roboto"`), which keeps files small but requires the font on the viewing machine. With `embed_fonts=True` the used font files are inlined as `@font-face` data URLs so text renders identically everywhere.

!!! note "Viewer support"
    Shadow and glow effects use SVG filters (`feGaussianBlur`). Browsers render them faithfully; some minimal SVG rasterizers apply filters only partially.

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

## PDF

PDF export requires the optional dependency:

```bash
uv pip install "quickthumb[pdf]"
```

The canvas becomes a single PDF page sized to the canvas pixels (one point per pixel). Backgrounds, outlines, shapes, and text are drawn as native PDF vector primitives using the same layout math as the raster renderer, and the fonts used for text are subset and embedded into the document, so it is self-contained and renders correctly in any reader.

```python
canvas.render("promo.pdf")
# or
with open("promo.pdf", "wb") as f:
    f.write(canvas.to_pdf())
```

!!! note "Fidelity"
    PDF shadings cannot express transparency, so translucent gradients (and gradients with translucent stops) are embedded as pictures. Blur effects (shadow, glow), strokes on shapes, and gradient/image glyph fills have no faithful PDF vector form and are likewise embedded as pixel-exact PNG fragments.

## Decks (multiple images and slides)

A `Deck` is an ordered collection of canvases. Each slide is a full `Canvas` and renders exactly as it would on its own, so a deck is just a multi-output container on top of the same pipeline. See the [Deck API reference](api/deck.md) for the full method list.

Give the deck a size once and each slide can be a bare `Canvas()` that inherits it:

```python
from quickthumb import Canvas, Deck

deck = (
    Deck(1280, 720)   # default slide size; Deck.from_aspect_ratio("16:9", 1280) also works
    .slide(Canvas().background(color="#101820").text(content="Cover", ...))
    .slide(Canvas().background(color="#1A1A2E").text(content="Body", ...))
)
# pre-built canvases work too: Deck(slides=[cover, body])

deck.render("deck.pdf")     # one multi-page PDF (a page per slide)
deck.render("deck.pptx")    # one multi-slide PPTX (a slide per slide)
deck.render("slides.png")   # numbered sequence: slides_01.png, slides_02.png, …

pdf_bytes = deck.to_pdf()
pptx_bytes = deck.to_pptx()
```

`render()` dispatches on the output extension: `.pdf` and `.pptx` produce a single document, while raster extensions have no native multi-page container, so the deck writes one file per slide as a zero-padded numbered sequence and returns the written paths.

Slides may have different dimensions. `deck.diagnose()` aggregates each slide's [diagnostics](diagnostics.md) (each tagged with its `slide_index`) and adds a `mixed-slide-size` warning when they differ. The PDF path sizes each page to its slide, but PPTX has a single presentation size taken from the first slide, so slides larger than the first are clipped by PowerPoint — keep slides a uniform size when targeting `.pptx`. Decks round-trip through JSON with `deck.to_json()` / `Deck.from_json(...)`, reusing the per-canvas serialization.

## CLI

The CLI picks the format from the output extension too:

```bash
quickthumb render spec.json -o card.svg
quickthumb render spec.json -o card.pptx
quickthumb render spec.json -o card.pdf
```
