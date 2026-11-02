---
description: Reference for svg, html, powerpoint, and pdf in quickthumb.
---

# SVG, HTML, PowerPoint, and PDF

[Export reference](../exports.md) · [Choose an output format](../output-guide.md)

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
html = canvas.to_html()
canvas.render("card.html")
```

The result is one self-contained HTML file. Backgrounds, shapes, outlines, and
text become HTML and CSS; images and anything else without a CSS equivalent
are embedded as PNG fragments. Unlike SVG, PDF, and PPTX, the page plays layer
`animation` effects, advancing on click.

The design is a fixed-size stage that never reflows. By default
(`responsive=True`) the whole stage scales to fit the browser window; pass
`responsive=False` to get it at its exact pixel size. Fonts are embedded by
default (`embed_fonts=True`), so the page looks the same on any machine.

A deck exports to an HTML slideshow the same way, with a presenter view; see
[Deck](../api/deck.md).

## PPTX

Create slides you can refine in PowerPoint or Keynote, with editable text and
supported shapes. Install the `pptx` extra:

```bash
pip install "quickthumb[pptx]"
```

```python
from quickthumb import Canvas

canvas = Canvas(640, 360).background(color="#101826").text(
    "Ready to share", font="Arial", size=36, color="#FFFFFF", position=(60, 120)
)
canvas.export("promo.pptx")
```

Open `promo.pptx` in your slide editor. A Canvas becomes one slide; use
`deck.export("promo.pptx")` for several slides.

!!! note "Editing styled content"
    Glow is saved as a fixed image, and outlines may use separate objects.
    After changing styled text or shapes, re-export from Python to keep their
    glow and border aligned. Some effect combinations become pictures, so the
    affected content cannot be edited as individual text or shapes. See
    [PPTX compatibility](export-validation.md#pptx-compatibility) for details.

!!! note "Fonts and layout"
    Fonts are not embedded. Choose a font available both to quickthumb and in
    the slide editor. Font substitution, mixed-size rich text and rotation can
    change spacing or placement; check the result in the app you will use.

## PDF

PDF export needs the `pdf` extra:

```bash
pip install "quickthumb[pdf]"
```

The canvas becomes a single PDF page sized to the canvas pixels (one point per pixel). Backgrounds, outlines, shapes, and eligible text are drawn as native PDF vector primitives using the same layout math as the raster renderer. Fonts that can be safely embedded are subset when their text does not need complex shaping; unsupported text is embedded as a pixel-exact PNG fragment so its visual result remains faithful.

```python
canvas.render("promo.pdf")
# or
with open("promo.pdf", "wb") as f:
    f.write(canvas.to_pdf())
```

!!! note "Fidelity"
    PDF shadings cannot express transparency, so translucent gradients (and gradients with translucent stops) are embedded as pictures. Blur effects (shadow, glow), strokes on shapes, and gradient/image glyph fills have no faithful PDF vector form and are likewise embedded as pixel-exact PNG fragments.
