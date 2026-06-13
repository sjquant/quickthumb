# quickthumb

quickthumb is a Python library for programmatic thumbnail, social card, and promo image generation.
It is designed for code-first and JSON-first workflows, with a layer-based API that works well for human-authored scripts and AI-generated specs.

## Gallery

| YouTube Thumbnail | Burnout Thumbnail | Instagram News Card |
| --- | --- | --- |
| ![YouTube thumbnail example](examples/youtube_thumbnail_01.png) | ![Burnout thumbnail example](examples/youtube_thumbnail_02.png) | ![Instagram news card example](examples/instagram_news_card.png) |

| Talking Head | Reaction / Commentary | Tutorial / Explainer |
| --- | --- | --- |
| ![Talking head thumbnail example](examples/youtube_talking_head.png) | ![Reaction thumbnail example](examples/youtube_reaction.png) | ![Tutorial thumbnail example](examples/youtube_tutorial_explainer.png) |

![Launch announcement example built with auto-layout groups, theme tokens, star shapes, and SVG layers](examples/launch_announcement.png)

*One JSON spec, zero hand-placed text coordinates: [`examples/launch_announcement.json`](examples/launch_announcement.json) combines auto-layout groups, theme tokens, star shapes, SVG layers, grain, and `diagnose()`.*

## Why quickthumb

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

Optional SVG layer support:

```bash
uv pip install "quickthumb[svg]"
```

Optional PowerPoint (PPTX) export support:

```bash
uv pip install "quickthumb[pptx]"
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

Beyond `rectangle` and `ellipse`, shape layers support `pill`, `triangle`, `star`, and `polygon`:

```python
canvas = (
    Canvas(1280, 720)
    .shape(shape="pill", position=(64, 60), width=200, height=56, color="#B8FF00")
    .shape(shape="star", position=(400, 60), width=120, height=120, color="#FFD700",
           star_points=6, inner_radius=0.4)
    .shape(
        shape="polygon",  # normalized 0..1 points inside the shape box
        position=(600, 60),
        width=160,
        height=100,
        color="#53BF9D",
        points=[(0.0, 0.25), (0.6, 0.25), (0.6, 0.0), (1.0, 0.5), (0.6, 1.0), (0.6, 0.75), (0.0, 0.75)],
    )
)
```

### SVG layers

Rasterize SVG icons and logos at render time (requires `quickthumb[svg]`):

```python
canvas = Canvas(1280, 720).svg(
    path="logo.svg",
    position=("90%", "8%"),
    width=120,
    align=("right", "top"),
)
```

`width`/`height` control the raster size (aspect ratio is preserved when only one is set). SVG layers support `opacity`, `rotation`, `align`, `blend_mode`, and the same `effects` as image layers.

### Group layers (auto layout)

Stop hand-placing coordinates: a `group` measures its children and stacks them along a row or column. Specs survive content-length changes, which makes them much more reliable for LLM-generated layouts.

```python
canvas = Canvas(1280, 720).background(color="#16213E").group(
    children=[
        {"type": "shape", "shape": "pill", "width": 120, "height": 36, "color": "#E94560"},
        {"type": "text", "content": "AUTO LAYOUT", "size": 96, "color": "#FFFFFF", "weight": 900},
        {"type": "text", "content": "No coordinates were harmed", "size": 40, "color": "#A2A8D3"},
    ],
    direction="column",
    gap=24,
    position=("8%", "50%"),
    align=("left", "middle"),
)
```

- `direction`: `"column"` (default) or `"row"`
- `gap`: pixels between children; `padding`: int, `(vertical, horizontal)`, or `(top, right, bottom, left)`
- `item_align`: cross-axis placement per child — `"start"`, `"center"`, or `"end"`
- `position` + `align` anchor the whole group box, like image layers
- Children may be `text`, `image`, `shape`, `svg`, or nested `group` layers; they must not set their own `position`

### Theme tokens

Define brand tokens once in a JSON spec and reference them anywhere with `$theme.path`:

```json
{
  "width": 1280,
  "height": 720,
  "theme": {
    "colors": {"primary": "#B8FF00", "ink": "#111111"},
    "sizes": {"title": 96}
  },
  "layers": [
    {"type": "background", "color": "$theme.colors.ink"},
    {"type": "text", "content": "Hello", "size": "$theme.sizes.title", "color": "$theme.colors.primary"}
  ]
}
```

Whole-string references keep their native JSON type (numbers, lists); scalar tokens can also be embedded inside longer strings. Unknown tokens raise `ValidationError`. Theme tokens work alongside `$var` template substitution.

### Diagnostics

`canvas.diagnose()` checks a composition for common problems without writing a file — ideal for agent loops (render → diagnose → fix):

```python
for finding in canvas.diagnose():
    print(finding.severity, finding.code, finding.message)
```

Findings: `off-canvas` (layer outside the canvas), `tiny-text` (under 2.5% of canvas height), `text-overflow` (a word wider than `max_width`), and `low-contrast` (text vs the composited layers below it). The CLI equivalent is `quickthumb lint spec.json` (exit codes: 0 clean, 1 invalid spec, 2 render failure, 3 findings).

### Grain / noise effect

Add film-grain noise to background or image layers via `effects=[Grain(...)]`.

```python
from quickthumb import Canvas, Grain

canvas = (
    Canvas(1280, 720)
    .background(
        color="#1A1A2E",
        effects=[Grain(intensity=0.12, monochrome=True)],
    )
    .image(
        path="portrait.png",
        position=("70%", "50%"),
        width=400,
        height=500,
        align=("center", "middle"),
        effects=[Grain(intensity=0.08, monochrome=False, blend_mode="overlay", opacity=0.6)],
    )
)
```

`Grain` parameters:

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `intensity` | `float` | required | Noise amplitude, `0.0`–`1.0` |
| `monochrome` | `bool` | `True` | `True` = luminance noise; `False` = per-channel color noise |
| `blend_mode` | `str` | `"overlay"` | `"overlay"`, `"screen"`, `"multiply"`, or `"normal"` |
| `opacity` | `float` | `1.0` | Overall grain strength, `0.0`–`1.0` |
| `seed` | `int \| None` | `None` | Optional RNG seed for deterministic output |

`Grain` is valid in `effects` on **background** and **image** layers. It is serialized with `"type": "grain"` in JSON.

### Export helpers

```python
png_base64 = canvas.to_base64(format="PNG")
jpeg_data_url = canvas.to_data_url(format="JPEG", quality=90)
canvas.render("output.webp", format="WEBP", quality=90)
```

### SVG and PPTX renderers

The same canvas renders to vector and document formats, detected from the file extension:

```python
canvas.render("card.svg")    # vector SVG with native shapes, gradients, and selectable text
canvas.render("card.pptx")   # PowerPoint slide with editable text boxes and autoshapes

svg_markup = canvas.to_svg(embed_fonts=True)  # inline @font-face for portable text
pptx_bytes = canvas.to_pptx()                 # requires quickthumb[pptx]
```

Layers the target format can express (backgrounds, gradients, outlines, shapes, text — including wrapping, rich parts, letter spacing, and effects) are exported natively and stay editable; everything else (raster images, blend modes, custom layers) is embedded as pixel-exact PNG fragments rendered by the regular pipeline. See the [export docs](https://sjquant.github.io/quickthumb/exports/) for the full mapping.

## JSON-First Workflow

quickthumb can round-trip most canvases through JSON:

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
      "content": "Hello quickthumb",
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

quickthumb is a good target when you want an LLM to generate image specs that are deterministic and easy to validate.

Prompt pattern for Python generation:

```text
Generate quickthumb Python code for a 1280x720 YouTube thumbnail.
Use layered composition only.
Keep text on the left, subject image on the right, and use high-contrast typography.
Return runnable code that ends with canvas.render("thumbnail.png").
```

Prompt pattern for JSON generation:

```text
Generate a quickthumb JSON config with top-level width, height, and layers.
Use one background image layer, one dark overlay background layer, two text layers, and one outline layer.
Only use valid quickthumb layer types and effect names.
```

Recommended workflow:

1. Have the model produce quickthumb Python or JSON.
2. Validate or render it locally.
3. Adjust only the content, colors, and assets instead of rewriting layout logic from scratch.

## Environment Variables

quickthumb looks for fonts using these environment variables:

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
| Grain / noise | Per-layer `Grain` effect on background and image layers; monochrome or color noise |
| Shapes | Rectangle, ellipse, pill, triangle, star, and polygon primitives with stroke/shadow/glow support |
| SVG | `svg` layers rasterized via optional `quickthumb[svg]` extra |
| Auto layout | `group` layers: row/column stacking, gap, padding, item alignment, nesting |
| Theme tokens | Top-level `theme` block with `$theme.path` references in JSON specs |
| Diagnostics | `canvas.diagnose()` and `quickthumb lint`: off-canvas, tiny text, overflow, low contrast |
| Export | PNG, JPEG, WebP, file output, base64, data URLs |
| Document renderers | SVG (`to_svg()`), editable PPTX via optional `quickthumb[pptx]` extra |
| Serialization | `to_json()` / `from_json()` for built-in layer types and named custom layers |

## Real Example Scripts

See the shipped examples in [`examples/README.md`](examples/README.md):

- `examples/youtube_thumbnail_01.py`
- `examples/youtube_thumbnail_02.py`
- `examples/instagram_news_card.py`
- `examples/launch_announcement.py` — the 0.5 feature set (groups, theme tokens, shapes, SVG, diagnostics) in one JSON spec

## Gotchas

- `weight` and `bold=True` are mutually exclusive on text layers and `TextPart`
- `auto_scale=True` requires `max_width`
- `position` percentage values must be strings like `"50%"`
- `fill` and `color` are independent fields; when `fill` is set it takes visual precedence over `color`
- `canvas.custom(fn)` without a `name` runs during render order but cannot be serialized to JSON; pass `name=` and register the function with `Canvas.register_layer_fn()` to enable serialization
- `Grain` is valid only on background and image layer `effects`; it is not a valid text or shape effect
- `Grain(intensity=0.0)` is a no-op (no noise is generated or composited)
- Group children must not set `position`; the group assigns positions (their `align` is also ignored — use `item_align`)
- `svg` layers raise `RenderingError` unless `quickthumb[svg]` (cairosvg) is installed
- `theme` blocks are resolved at parse time; `to_json()` emits resolved values without the `theme` block

## Development

```bash
uv sync
uv run pytest
uv run ruff check .
uv run ty quickthumb/
```

## Reference

- License: [LICENSE](LICENSE)
