---
description: Build your first quickthumb image by creating a canvas, layering backgrounds, text, shapes, and images, then exporting the rendered thumbnail.
---

# Getting Started

This guide walks through the core workflow: create a canvas, add layers, and export an image.

## Your first thumbnail

```python
from quickthumb import Canvas, Filter, Shadow, Stroke, TextPart

canvas = (
    Canvas.from_aspect_ratio("16:9", base_width=1280)
    .background(
        image="https://images.unsplash.com/photo-1516321318423-f06f85e504b3",
        effects=[Filter(brightness=0.65)],
    )
    .background(color="#000000", opacity=0.45)
    .text(
        content=[
            TextPart(
                text="BUILD THUMBNAILS\nFAST\n",
                color="#B8FF00",
                effects=[Stroke(width=8, color="#000000")],
            ),
            TextPart(
                text="With Python or JSON specs",
                color="#F5F5F5",
                size=44,
                effects=[Shadow(offset_x=2, offset_y=2, color="#000000", blur_radius=4)],
            ),
        ],
        size=112,
        position=("8%", "50%"),
        align=("left", "middle"),
        weight=900,
    )
    .outline(width=14, color="#B8FF00")
)

canvas.render("thumbnail.png")
```

## Step by step

### 1. Create a canvas

```python
from quickthumb import Canvas

# Explicit size
canvas = Canvas(1280, 720)

# Or from an aspect ratio
canvas = Canvas.from_aspect_ratio("16:9", base_width=1280)
canvas = Canvas.from_aspect_ratio("1:1", base_width=1080)
canvas = Canvas.from_aspect_ratio("9:16", base_width=1080)
```

### 2. Add a background

```python
from quickthumb import Canvas, Filter, LinearGradient

canvas = (
    Canvas(1280, 720)
    # Solid color
    .background(color="#0F172A")
    # Gradient overlay
    .background(
        gradient=LinearGradient(
            angle=120,
            stops=[("#111827", 0.0), ("#11182700", 1.0)],
        ),
        opacity=0.7,
    )
    # Remote image with effects
    .background(
        image="https://images.unsplash.com/photo-1516321318423-f06f85e504b3",
        fit="cover",
        blend_mode="multiply",
        effects=[Filter(blur=4, brightness=0.75)],
    )
)
```

Layers stack in call order — the first `.background()` is drawn first (backmost).

### 3. Add text

```python
from quickthumb import Background, Glow, Shadow, Stroke, TextPart

canvas.text(
    content=[
        TextPart(text="5 ", color="#FBBF24", weight=900),
        TextPart(text="WARNING SIGNS", color="#FFFFFF", weight=900),
    ],
    size=72,
    position=(80, 540),
    effects=[
        Background(color="#111827CC", padding=(16, 22), border_radius=12),
        Stroke(width=2, color="#000000"),
        Shadow(offset_x=4, offset_y=4, color="#000000", blur_radius=8),
        Glow(color="#F59E0B", radius=14, opacity=0.35),
    ],
)
```

`content` can also be a plain string for simple cases:

```python
canvas.text(content="Hello World", size=64, color="#FFFFFF", align="center")
```

### 4. Add an image

```python
from quickthumb import Filter, Shadow

canvas.image(
    path="portrait.png",
    position=("73%", "52%"),
    width=420,
    height=520,
    fit="cover",
    align=("center", "middle"),
    border_radius=24,
    effects=[
        Filter(contrast=1.1, saturation=1.05),
        Shadow(offset_x=0, offset_y=12, color="#000000", blur_radius=24),
    ],
)
```

### 5. Add shapes

```python
from quickthumb import Shadow, Stroke

canvas.shape(
    shape="rectangle",
    position=(64, 60),
    width=320,
    height=88,
    color="#CC0000",
    border_radius=10,
    effects=[
        Stroke(width=2, color="#FFFFFF"),
        Shadow(offset_x=0, offset_y=6, color="#000000", blur_radius=12),
    ],
)
```

### 6. Check your work

`diagnose()` flags common problems — off-canvas layers, illegibly small text, words that can't wrap, low text contrast — before you render:

```python
for finding in canvas.diagnose().findings:
    print(finding.severity, finding.code, finding.message)
```

An empty `findings` list means the composition is clean. See [Diagnostics & CLI](diagnostics.md).

### 7. Export

```python
# PNG file
canvas.render("output.png")

# JPEG or WebP with quality
canvas.render("output.webp", format="WEBP", quality=90)
canvas.render("output.jpg", format="JPEG", quality=85)

# Base64 string
png_b64 = canvas.to_base64(format="PNG")

# Data URL (e.g. for HTML src=)
data_url = canvas.to_data_url(format="JPEG", quality=90)
```

## JSON workflow

You can also drive quickthumb from a JSON config instead of Python code:

```python
from quickthumb import Canvas

config = """
{
  "kind": "canvas",
  "width": 1280,
  "height": 720,
  "layers": [
    { "type": "background", "color": "#111827" },
    {
      "type": "text",
      "content": "Hello quickthumb",
      "size": 72,
      "color": "#FFFFFF",
      "align": "center",
      "position": ["50%", "50%"]
    },
    { "type": "outline", "width": 10, "color": "#22C55E" }
  ]
}
"""

canvas = Canvas.from_json(config)
canvas.render("hello.png")
```

This is particularly useful for AI-generated specs. See [JSON Schema & AI Workflow](json-schema.md) for details.

## Next steps

- [Core Concepts](concepts.md) — understand how layers, effects, and positioning work
- [Group (Auto Layout)](api/group.md) — stack layers in rows and columns without hand-placed coordinates
- [API Reference](api/index.md) — full parameter reference for every layer type
- [Diagnostics & CLI](diagnostics.md) — lint specs and render from the terminal
- [Cookbook](cookbook/index.md) — complete real-world examples
