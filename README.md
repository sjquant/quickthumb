# QuickThumb

QuickThumb is a Python library for programmatic thumbnail, social card, and promo image generation.
It is designed for code-first and JSON-first workflows, with a layer-based API that works well for human-authored scripts and AI-generated specs.

## Gallery

| YouTube Thumbnail | Burnout Thumbnail | Instagram News Card |
| --- | --- | --- |
| ![YouTube thumbnail example](examples/youtube_thumbnail_01.png) | ![Burnout thumbnail example](examples/youtube_thumbnail_02.png) | ![Instagram news card example](examples/instagram_news_card.png) |

| Talking Head | Reaction / Commentary | Tutorial / Explainer |
| --- | --- | --- |
| ![Talking head thumbnail example](examples/youtube_talking_head.png) | ![Reaction thumbnail example](examples/youtube_reaction.png) | ![Tutorial thumbnail example](examples/youtube_tutorial_explainer.png) |

## Why QuickThumb

- Built for thumbnails and social graphics, not just generic image composition
- Works with Python method chaining and JSON serialization/deserialization
- Handles gradients, remote images, rich text, shapes, blend modes, and export helpers
- Good fit for AI-assisted workflows that need deterministic image specs

## Installation

```bash
uv pip install quickthumb
```

Optional background removal support:

```bash
uv pip install "quickthumb[rembg]"
```

## Quick Start

```python
from quickthumb import Background, Canvas, Filter, Shadow, Stroke, TextPart

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

## Core API

### Create a canvas

```python
from quickthumb import Canvas

canvas = Canvas(1280, 720)
square = Canvas.from_aspect_ratio("1:1", base_width=1080)
vertical = Canvas.from_aspect_ratio("9:16", base_width=1080)
```

### Background layers

```python
from quickthumb import Canvas, Filter, FitMode, LinearGradient

canvas = (
    Canvas(1280, 720)
    .background(color="#101828")
    .background(
        gradient=LinearGradient(
            angle=120,
            stops=[("#0F172A", 0.0), ("#0F172A00", 1.0)],
        ),
    )
    .background(
        image="hero.jpg",
        fit=FitMode.COVER,
        blend_mode="multiply",
        effects=[Filter(blur=4, brightness=0.75, contrast=1.1, saturation=0.9)],
    )
)
```

### Text layers and rich text

```python
from quickthumb import Background, Canvas, Glow, Shadow, Stroke, TextPart

canvas = Canvas(1280, 720).text(
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

### Gradient and image-filled text

Fill text with a gradient or image instead of a flat color. Works on the whole text layer or per `TextPart`.

```python
from quickthumb import Canvas, LinearGradient, RadialGradient, TextFillImage, TextPart

# Gradient headline
canvas = Canvas(1280, 720).text(
    content="GRADIENT TITLE",
    size=120,
    fill=LinearGradient(
        angle=90,
        stops=[("#FF6B6B", 0.0), ("#FFE66D", 0.5), ("#4ECDC4", 1.0)],
    ),
    position=("50%", "50%"),
    align="center",
)

# Image-filled text
canvas = Canvas(1280, 720).text(
    content="TEXTURE",
    size=140,
    fill=TextFillImage(path="fire_texture.jpg", fit="cover"),
    position=("50%", "50%"),
    align="center",
)

# Per-segment fills using TextPart
canvas = Canvas(1280, 720).text(
    content=[
        TextPart(
            text="HOT ",
            fill=LinearGradient(angle=45, stops=[("#FF4500", 0.0), ("#FFD700", 1.0)]),
            weight=900,
        ),
        TextPart(
            text="COLD",
            fill=LinearGradient(angle=45, stops=[("#00BFFF", 0.0), ("#8A2BE2", 1.0)]),
            weight=900,
        ),
    ],
    size=110,
    position=("50%", "50%"),
    align="center",
)
```

`fill` accepts `LinearGradient`, `RadialGradient`, or `TextFillImage`. It is mutually independent of `color` — when `fill` is set it takes visual precedence. A `fill` on a `TextPart` overrides the layer-level `fill` for that segment only.

### Image layers

```python
from quickthumb import Canvas, Filter

canvas = Canvas(1280, 720).image(
    path="portrait.png",
    position=("73%", "52%"),
    width=420,
    height=520,
    fit="cover",
    align=("center", "middle"),
    border_radius=24,
    remove_background=True,
    blend_mode="normal",
    effects=[Filter(contrast=1.1, saturation=1.05)],
)
```

### Shape layers

```python
from quickthumb import Canvas, Shadow, Stroke

canvas = Canvas(1280, 720).shape(
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

### Export helpers

```python
png_base64 = canvas.to_base64(format="PNG")
jpeg_data_url = canvas.to_data_url(format="JPEG", quality=90)
canvas.render("output.webp", format="WEBP", quality=90)
```

## JSON-First Workflow

QuickThumb can round-trip most canvases through JSON:

```python
from quickthumb import Canvas

config = """
{
  "width": 1280,
  "height": 720,
  "layers": [
    {
      "type": "background",
      "color": "#111827"
    },
    {
      "type": "text",
      "content": "Hello QuickThumb",
      "size": 72,
      "color": "#FFFFFF",
      "align": "center",
      "position": ["50%", "50%"]
    },
    {
      "type": "outline",
      "width": 10,
      "color": "#22C55E"
    }
  ]
}
"""

canvas = Canvas.from_json(config)
canvas.render("hello.png")

serialized = canvas.to_json()
```

Notes:

- JSON uses top-level `width`, `height`, and `layers`
- Named custom layers added with `canvas.custom(fn, name="...", kwargs={...})` are JSON-serializable via the registry; unnamed custom layers are not
- Enum-like values such as `blend_mode`, `fit`, and `align` can be passed as strings

## AI-Friendly Workflows

QuickThumb is a good target when you want an LLM to generate image specs that are deterministic and easy to validate.

Prompt pattern for Python generation:

```text
Generate QuickThumb Python code for a 1280x720 YouTube thumbnail.
Use layered composition only.
Keep text on the left, subject image on the right, and use high-contrast typography.
Return runnable code that ends with canvas.render("thumbnail.png").
```

Prompt pattern for JSON generation:

```text
Generate a QuickThumb JSON config with top-level width, height, and layers.
Use one background image layer, one dark overlay background layer, two text layers, and one outline layer.
Only use valid QuickThumb layer types and effect names.
```

Recommended workflow:

1. Have the model produce QuickThumb Python or JSON.
2. Validate or render it locally.
3. Adjust only the content, colors, and assets instead of rewriting layout logic from scratch.

## Environment Variables

QuickThumb looks for fonts using these environment variables:

- `QUICKTHUMB_FONT_DIR`: directory that contains font files
- `QUICKTHUMB_DEFAULT_FONT`: default font family/name to use when `font` is omitted

Example:

```python
import os

os.environ["QUICKTHUMB_FONT_DIR"] = "assets/fonts"
os.environ["QUICKTHUMB_DEFAULT_FONT"] = "Roboto"
```

## Feature Matrix

| Area | Supported |
| --- | --- |
| Canvas sizing | Explicit width/height, `from_aspect_ratio()` |
| Backgrounds | Solid colors, linear gradients, radial gradients, local/remote images |
| Background controls | Opacity, blend modes, fit modes, blur, brightness, contrast, saturation |
| Text | Positioning, alignment, wrapping, letter spacing, line height, rotation, auto-scale |
| Rich text | Per-segment `TextPart` styling |
| Text fills | Gradient (`LinearGradient`, `RadialGradient`) and image (`TextFillImage`) fills; per-`TextPart` override |
| Text effects | Stroke, shadow, glow, background fill |
| Fonts | Local fonts, CSS-style weights, italic/bold flags, webfont URLs, fallback mapping |
| Images | Local/remote images, sizing, fit modes, alignment, opacity, rotation |
| Image effects | Stroke, shadow, glow, filter effects, border radius, background removal |
| Shapes | Rectangle and ellipse primitives with stroke/shadow/glow support |
| Export | PNG, JPEG, WebP, file output, base64, data URLs |
| Serialization | `to_json()` / `from_json()` for built-in layer types and named custom layers |

## Real Example Scripts

See the shipped examples in [`examples/README.md`](examples/README.md):

- `examples/youtube_thumbnail_01.py`
- `examples/youtube_thumbnail_02.py`
- `examples/instagram_news_card.py`

## Gotchas

- `weight` and `bold=True` are mutually exclusive on text layers and `TextPart`
- `auto_scale=True` requires `max_width`
- `position` percentage values must be strings like `"50%"`
- `fill` and `color` are independent fields; when `fill` is set it takes visual precedence over `color`
- `canvas.custom(fn)` without a `name` runs during render order but cannot be serialized to JSON; pass `name=` and register the function with `Canvas.register_layer_fn()` to enable serialization

## Development

```bash
uv sync
uv run pytest
uv run ruff check .
uv run ty quickthumb/
```

## Reference

- License: [LICENSE](LICENSE)
