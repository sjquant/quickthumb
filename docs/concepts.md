---
description: Learn quickthumb's core model for canvases, ordered layers, coordinates, alignment, effects, fonts, rendering, and JSON specs.
---

# Core Concepts

## The canvas

A `Canvas` is the root object. It holds a width, height, and an ordered list of layers.

```python
from quickthumb import Canvas

canvas = Canvas(1280, 720)
```

All layer builder methods mutate the canvas and return `self`, so calls chain together naturally:

```python
canvas = (
    Canvas(1280, 720)
    .background(color="#0F172A")
    .text(content="Hello", size=64, color="#FFFFFF", align="center")
    .outline(width=8, color="#22d3ee")
)
```

## Layer order

Layers render in call order. The first layer added is drawn at the back; each subsequent layer is drawn on top.

```
canvas.background(...)   ← backmost
canvas.shape(...)
canvas.image(...)
canvas.text(...)
canvas.outline(...)      ← frontmost
```

This is intentional — you build up the composition the same way you would describe it: background first, foreground last.

## Layer types

| Method | What it adds |
| --- | --- |
| `.background(...)` | Full-canvas background: solid color, gradient, or image |
| `.text(...)` | Text with optional rich-text parts and effects |
| `.image(...)` | Positioned overlay image or cutout |
| `.shape(...)` | Positioned rectangle or ellipse |
| `.outline(...)` | Border drawn around the full canvas edge |
| `.custom(fn)` | Callback that receives and returns a Pillow `Image` |

## Positioning

Image and shape layers require a `position` argument — a 2-tuple of `(x, y)`.

Values can be integers (pixels) or percentage strings:

```python
# Pixels
canvas.shape(shape="rectangle", position=(64, 64), width=200, height=80, color="#CC0000")

# Percentages
canvas.image(path="portrait.png", position=("75%", "55%"), width=420, height=520)

# Mix
canvas.text(content="Hello", size=72, color="#fff", position=("8%", 360))
```

The `align` parameter controls which point of the layer the position refers to:

```python
# Position refers to the top-left corner of the element
canvas.shape(..., position=(64, 64), align=("left", "top"))

# Position refers to the center of the element
canvas.image(..., position=("75%", "55%"), align=("center", "middle"))
```

## Alignment

`align` accepts several forms:

```python
align="center"                  # shorthand string
align="top-left"                # compound string
align=("center", "middle")      # (horizontal, vertical) tuple
align=Align.BOTTOM_RIGHT        # enum value
```

Horizontal values: `left`, `center`, `right`
Vertical values: `top`, `middle`, `bottom`

For text, `align` without a `position` centers the text on the canvas.

## Effects

Effects are modifiers applied to a layer. Each layer type accepts a specific set:

| Layer | Available effects |
| --- | --- |
| Background | `Filter` |
| Text | `Stroke`, `Shadow`, `Glow`, `Background` |
| Image | `Stroke`, `Shadow`, `Glow`, `Filter` |
| Shape | `Stroke`, `Shadow`, `Glow` |

Pass effects as a list:

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

### Stroke

Draws an outline around text, images, or shapes.

```python
Stroke(width=4, color="#000000")
```

### Shadow

Adds a drop shadow.

```python
Shadow(offset_x=4, offset_y=8, color="#000000", blur_radius=12)
```

### Glow

Adds a colored halo effect.

```python
Glow(color="#B8FF00", radius=16, opacity=0.35)
```

### Filter

Applies image processing to backgrounds or image layers.

```python
Filter(blur=4, brightness=0.75, contrast=1.1, saturation=0.9)
```

All `Filter` parameters default to neutral (no effect) — only set what you want to adjust.

### Background (text effect)

Draws a filled rectangle behind a text block.

```python
from quickthumb import Background

canvas.text(
    content="BREAKING",
    size=64,
    color="#FFFFFF",
    effects=[Background(color="#CC000099", padding=(12, 20), border_radius=8)],
)
```

## Rich text

Plain strings work fine for uniform text. Use `TextPart` for per-segment styling:

```python
from quickthumb import TextPart

canvas.text(
    content=[
        TextPart(text="5 ", color="#FBBF24", weight=900),
        TextPart(text="WAYS TO WIN", color="#FFFFFF", weight=900),
    ],
    size=80,
    position=("8%", "55%"),
    align=("left", "middle"),
)
```

Each `TextPart` can override `color`, `size`, `font`, `weight`, `bold`, `italic`, `letter_spacing`, `line_height`, and `effects`.

## Blend modes

Background and image layers support blend modes for compositing:

```python
canvas.background(
    image="texture.jpg",
    blend_mode="multiply",   # or: overlay, screen, darken, lighten, normal
)
```

The blend is applied when compositing this layer over the layers drawn before it.

## Gradients

```python
from quickthumb import LinearGradient, RadialGradient

# Linear: angle in degrees, stops as (color, position) tuples
LinearGradient(
    angle=135,
    stops=[("#FF5733", 0.0), ("#3333FF", 1.0)],
)

# Radial: center as (x, y) fractions (0.0–1.0)
RadialGradient(
    stops=[("#FF5733", 0.0), ("#3333FF", 1.0)],
    center=(0.5, 0.5),
)
```

Pass a gradient to `.background(gradient=...)`.

## Fit modes

When an image or background image has explicit width and height dimensions set, `fit` controls how the image is scaled into that box:

| Value | Behavior |
| --- | --- |
| `cover` | Fill the box, cropping if needed (default for backgrounds) |
| `contain` | Fit entirely inside the box, leaving empty space |
| `fill` | Stretch to fill exactly, ignoring aspect ratio |

## JSON round-trip

Any canvas that uses only built-in layer types can be serialized and deserialized:

```python
json_str = canvas.to_json()
canvas2  = Canvas.from_json(json_str)
```

`canvas.custom(fn)` layers are intentionally excluded — callbacks cannot be represented in JSON.

## Validation

quickthumb validates all inputs at construction time using Pydantic. Invalid values raise `ValidationError` immediately, before any rendering occurs.

```python
from quickthumb import ValidationError

try:
    canvas.text(content="", size=64, color="#fff")  # empty content
except ValidationError as e:
    print(e)
```

Rendering errors (bad file paths, failed downloads, unsupported formats) raise `RenderingError` when `.render()`, `.to_base64()`, or `.to_data_url()` is called.
