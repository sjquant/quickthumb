---
description: How quickthumb works: a canvas of ordered layers, positions and alignment, effects, rich text, auto layout, JSON specs, and validation.
---

# Core Concepts

## A canvas is a list of layers

A `Canvas` has a size and an ordered list of layers. Each layer method adds one
layer and returns the canvas, so calls chain:

```python
from quickthumb import Canvas

canvas = (
    Canvas(1280, 720)
    .background(color="#0F172A")
    .text(content="Hello", size=64, color="#FFFFFF", align="center")
    .outline(width=8, color="#22D3EE")
)
canvas.render("hello.png")
```

Layers are drawn in the order you add them. The first one is at the back and
the last one is on top, so you describe an image the way you would paint it:
background first, details last.

## Layer types

| Method | Adds | Reference |
| --- | --- | --- |
| `.background()` | A full-canvas color, gradient, or image | [Background](api/background.md) |
| `.text()` | Text, plain or as styled `TextPart`s | [Text](api/text.md) |
| `.image()` | A placed image, optionally cut out of its background | [Image](api/image.md) |
| `.shape()` | A rectangle, ellipse, pill, triangle, star, or polygon | [Shape](api/shape.md) |
| `.svg()` | An SVG file such as an icon or logo (needs the `svg` extra) | [SVG](api/svg.md) |
| `.video()` | A video clip, for animated exports | [Video](api/video.md) |
| `.chart()`, `.qr_code()` | A bar or line chart, or a QR code | [Data visualizations](api/data-visualizations.md) |
| `.counter()` | A number that counts from one value to another | [Canvas](api/canvas.md) |
| `.group()` | A row or column that positions its children for you | [Group](api/group.md) |
| `.outline()` | A border around the edge of the canvas | [Outline](api/outline.md) |
| `.custom(fn)` | Your own function that draws on the Pillow image | [Canvas](api/canvas.md) |

## Position and alignment

`position` is an `(x, y)` pair. Each value is pixels or a percentage of the
canvas, and you can mix them:

```python
canvas.shape(shape="rectangle", position=(64, 64), width=200, height=80, color="#CC0000")
canvas.text(content="Hello", size=72, color="#FFFFFF", position=("8%", 360))
```

`align` says which point of the layer sits at that position. By default it is
the top-left corner. `align=("center", "middle")` puts the layer's center
there instead, and `align=("right", "bottom")` with `position=(1280, 720)`
pins a layer to the bottom-right corner of a 1280×720 canvas whatever its
size.

`align` accepts several spellings of the same thing:

```python
align=("center", "middle")      # (horizontal, vertical)
align="center"                  # same as ("center", "middle")
align="bottom-right"
align=Align.BOTTOM_RIGHT
```

Horizontal values are `left`, `center`, and `right`; vertical values are
`top`, `middle`, and `bottom`. A text layer with `align` but no `position` is
placed on the canvas by its alignment, so `align="center"` centers it.

## Effects

Effects change how one layer is drawn. Pass them as a list:

```python
from quickthumb import Shadow, Stroke

canvas.text(
    content="CLICK NOW",
    size=96,
    color="#FFFFFF",
    effects=[
        Stroke(width=4, color="#000000"),
        Shadow(offset_x=4, offset_y=4, color="#000000", blur_radius=8),
    ],
)
```

Not every effect makes sense on every layer:

| Layer | Effects |
| --- | --- |
| Background | `Filter`, `Grain` |
| Text | `Stroke`, `Shadow`, `Glow`, `Background` (a box behind the text) |
| Shape | `Stroke`, `Shadow`, `Glow`, `InnerShadow`, `BackdropBlur` |
| Image, SVG, video | `Stroke`, `Shadow`, `Glow`, `Filter`, `Grain`, `Duotone`, `InnerShadow`, `BackdropBlur` |

Passing an effect a layer doesn't support raises `ValidationError`. The
[Effects reference](api/effects.md) lists every parameter.

## Rich text

A plain string is enough when all the text looks the same. To style parts of
it differently, pass a list of `TextPart`s:

```python
from quickthumb import TextPart

canvas.text(
    content=[
        TextPart(text="5 ", color="#FBBF24"),
        TextPart(text="WAYS TO WIN", color="#FFFFFF"),
    ],
    size=80,
    weight=900,
    position=("8%", "55%"),
    align=("left", "middle"),
)
```

Settings on the layer (`size`, `weight` here) apply to every part unless the
part sets its own. A part can override `color`, `size`, `font`, `weight`,
`bold`, `italic`, `letter_spacing`, `line_height`, and `effects`.

## Gradients, blend modes, and fit

Backgrounds take a `gradient` as well as a color or an image:

```python
from quickthumb import LinearGradient, RadialGradient

canvas.background(gradient=LinearGradient(angle=135, stops=[("#FF5733", 0.0), ("#3333FF", 1.0)]))
canvas.background(gradient=RadialGradient(center=(0.5, 0.5), stops=[("#FF5733", 0.0), ("#3333FF", 1.0)]))
```

Colors in stops can include alpha (`"#00000080"`), which is how you darken
part of a photo behind text.

`blend_mode` on a background or image layer sets how it combines with what is
underneath: `normal`, `multiply`, `screen`, `overlay`, `darken`, or `lighten`.

`fit` sets how an image fills its box: `cover` fills it and crops the excess
(the default for backgrounds), `contain` fits the whole image inside, and
`fill` stretches it.

## Auto layout

Text that is placed by hand breaks when the copy gets longer. A `group`
measures its children and stacks them in a row or column; you place the group
once and it places the children:

```python
canvas.group(
    children=[
        {"type": "shape", "shape": "pill", "width": 120, "height": 36, "color": "#E94560"},
        {"type": "text", "content": "AUTO LAYOUT", "size": 96, "color": "#FFFFFF", "weight": 900},
        {"type": "text", "content": "Longer copy pushes the rest down", "size": 40, "color": "#A2A8D3"},
    ],
    direction="column",
    gap=24,
    position=("8%", "50%"),
    align=("left", "middle"),
)
```

Children don't set a `position`, and groups can contain groups. See
[Group](api/group.md).

## JSON specs

Everything above can be written as JSON instead of Python, and a canvas
converts both ways:

```python
spec = canvas.to_json()
same_canvas = Canvas.from_json(spec)
```

The only exception is `.custom(fn)`, because a Python function can't be stored
as JSON.

JSON specs can also define colors and sizes once in a `theme` block and refer
to them as `$theme.<path>`:

```json
{
  "kind": "canvas",
  "width": 1280,
  "height": 720,
  "theme": { "colors": { "primary": "#B8FF00" }, "sizes": { "title": 96 } },
  "layers": [
    { "type": "text", "content": "Hello", "size": "$theme.sizes.title", "color": "$theme.colors.primary" }
  ]
}
```

See [JSON Schema & AI Workflow](json-schema.md).

## Errors and checks

Arguments are validated when you add a layer, before anything is drawn:

```python
from quickthumb import ValidationError

try:
    canvas.text(content="Hello", size=64, color="#FFF")
except ValidationError as error:
    print(error)  # /color: invalid hex color: #FFF
```

Problems that only show up while drawing, such as a failed download, raise
`RenderingError`, and a local file that doesn't exist raises
`MissingAssetError`. Every error carries structured `details`; see
[Structured Errors](errors.md).

A canvas can be valid and still look wrong. `canvas.diagnose()` looks for
text that is too small or runs off the canvas, low contrast, layers hidden by
other layers, and similar problems, without rendering a file. See
[Diagnostics & CLI](diagnostics.md).
