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

Optional PDF export support:

```bash
uv pip install "quickthumb[pdf]"
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

### SVG, HTML, PPTX, and PDF renderers

The same canvas renders to vector and document formats, detected from the file extension:

```python
canvas.render("card.svg")    # vector SVG with native shapes, gradients, and selectable text
canvas.render("card.html")   # self-contained, animated HTML/CSS page
canvas.render("card.pptx")   # PowerPoint slide with editable text boxes and autoshapes
canvas.render("card.pdf")    # single-page PDF with native vectors and eligible embedded fonts
canvas.render("card.gif")    # animated GIF playing the layer animations
canvas.render("card.mp4")    # H.264 video (needs the ffmpeg binary); .webm for VP9

svg_markup = canvas.to_svg(embed_fonts=True)   # inline @font-face for portable text
html_doc = canvas.to_html(embed_fonts=True)    # standalone document string
pptx_bytes = canvas.to_pptx()                  # requires quickthumb[pptx]
pdf_bytes = canvas.to_pdf()                    # requires quickthumb[pdf]
gif_bytes = canvas.to_gif(fps=20, hold=3.0)    # and to_mp4() / to_webm()
```

Layers the target format can express (backgrounds, gradients, outlines, shapes, text — including wrapping, rich parts, letter spacing, and effects) are exported natively and stay editable; everything else (raster images, blend modes, custom layers) is embedded as pixel-exact PNG fragments rendered by the regular pipeline. See the [export docs](https://sjquant.github.io/quickthumb/exports/) for the full mapping.

### HTML renderer

`canvas.to_html()` produces one **self-contained** HTML document (inline CSS, JS,
fonts, and images — no external files), built on the same layout math as every
other renderer. No optional extra is required.

```python
canvas.render("card.html")                            # responsive, scale-to-fit page
html_doc = canvas.to_html(responsive=False)           # bare fixed-size stage to embed
html_doc = canvas.to_html(embed_fonts=True)           # inline @font-face for exact text
```

The composition is a **fixed-size stage that never reflows**, so an HTML export
stays a faithful twin of its PNG/SVG/PDF/PPTX counterpart. With
`responsive=True` (the default) the whole stage is scaled as one unit to fill
the viewport — it adapts to any screen size without rearranging the layout (set
`responsive=False` to emit the bare stage for embedding). Because browsers
rasterize fonts differently from PIL, text placement is a close approximation
rather than pixel-identical (like the PPTX exporter); `embed_fonts=True` inlines
the used fonts for the closest match.

Unlike the other document formats, HTML actually **plays** per-layer
`animation`s: each effect maps to a CSS keyframe driven by a tiny inline JS
runtime that honours the same `on_click` / `with_previous` / `after_previous`
sequencing as PowerPoint (click to advance). A `Deck` renders to a standalone
**slideshow** — `deck.render("slides.html")` — that advances per-layer
animations and then slides with a click or the arrow keys, applying slide
transitions between stages.

```python
deck.render("slides.html")          # one self-contained, navigable slideshow
html_doc = deck.to_html()           # the document as a string
```

### Decks: multiple images and slides

A `Deck` is an ordered collection of canvases ("slides"). Give the deck a size
once and each slide can be written as a bare `Canvas()` that inherits it — no
need to repeat the dimensions per slide:

```python
from quickthumb import Canvas, Deck

deck = (
    Deck(1280, 720)   # default slide size; Deck.from_aspect_ratio("16:9", 1280) also works
    .slide(Canvas().background(color="#101820").text(
        content="Episode 12", size=120, color="#B8FF00", position=("50%", "50%"), align="center"
    ))
    .slide(Canvas().background(color="#101820").text(
        content="Show notes", size=96, color="#FFFFFF", position=("50%", "50%"), align="center"
    ))
)

deck.render("deck.pdf")        # one multi-page PDF (a page per slide)
deck.render("deck.pptx")       # one multi-slide PPTX (a slide per slide)
deck.render("deck.html")       # one self-contained, navigable HTML slideshow
deck.render("deck.gif")        # one animation playing slide transitions (.webm too)
deck.render("deck.mp4")        # static slides with each slide's optional narration
deck.render("slides.png")      # numbered sequence: slides_01.png, slides_02.png, …

pdf_bytes = deck.to_pdf()      # requires quickthumb[pdf]
pptx_bytes = deck.to_pptx()    # requires quickthumb[pptx]
gif_bytes = deck.to_gif()
webm_bytes = deck.to_webm()    # requires ffmpeg; plays the animated timeline
mp4_bytes = deck.to_mp4()      # requires ffmpeg/ffprobe; static, per-slide narration
```

An unsized `Canvas()` inherits the deck's size when added; a canvas built with an
explicit size (`Canvas(1080, 1080)`) keeps its own. You can also seed a deck with
fully built canvases up front — `Deck(slides=[cover, body])`. A bare `Canvas()`
cannot be rendered until it is given a size (directly or by a deck).

Raster formats have no native multi-page container, so `render()` writes one
file per slide as a zero-padded numbered sequence and returns the written
paths. `.pdf` and `.pptx` produce a single document. Slides may have different
dimensions; `deck.diagnose()` aggregates each slide's
[diagnostics](#diagnostics) (tagged with `slide_index`) and adds a
`mixed-slide-size` warning when they differ. The PDF path sizes each page to its
slide, but PPTX has a single presentation size taken from the first slide, so
slides larger than the first are clipped by PowerPoint — keep deck slides a
uniform size when targeting `.pptx`. Decks round-trip through JSON with
`deck.to_json()` / `Deck.from_json(...)`, reusing the per-canvas serialization.

### Slide effects (PPTX and HTML transitions and animations)

When you export to PowerPoint or HTML, slides can carry a **transition** (the
animation played as the slide appears) and individual layers can carry
**entrance/exit animations**. Raster, SVG, and PDF outputs ignore these effects,
so the same spec still renders identically there.

```python
from quickthumb import Box, Canvas, Deck, Fade, Wipe
from quickthumb.transitions import Fade as FadeTransition
from quickthumb.transitions import Push

cover = (
    Canvas(1280, 720)
    .background(color="#101820")
    .text(
        "Quarterly Review",
        size=110,
        color="#B8FF00",
        position=("50%", "40%"),
        align="center",
        animation=Fade(),  # fades in on first click
    )
    .text(
        "FY25 · Q3",
        size=56,
        color="#FFFFFF",
        position=("50%", "62%"),
        align="center",
        # a list plays in order: zoom in, then wipe back out
        animation=[
            Box(direction="in", trigger="after_previous"),
            Wipe(direction="up", animate="exit", trigger="after_previous"),
        ],
    )
)

deck = (
    Deck(1280, 720)
    .transition(FadeTransition())     # default transition for every slide
    .slide(cover, transition=Push(direction="left", duration=0.6))
    .slide(Canvas().background(color="#101820"), transition="wipe")  # string shorthand
)

deck.render("review.pptx")
```

**Transitions** are a deck concern. Set a deck-wide default with
`Deck.transition(...)` and override a single slide with
`Deck.slide(canvas, transition=...)`; the per-slide override always wins. Like
animations, each transition is its own typed class in `quickthumb.transitions`,
exposing only the options it supports — `Push(direction="left")`,
`Wipe(direction="up")`, `Cover`/`Uncover`, `Zoom(direction="in")`,
`Split(orientation="vertical", direction="out")`, `Blinds`/`Checker`/`Comb`
(`orientation=...`), `Wheel(spokes=4)`, and `Fade`/`Cut`/`Dissolve`/`Wedge`/
`Circle`/`Diamond`/`Newsflash`/`Random` (no extra options):

```python
from quickthumb.transitions import Cover, Fade, Push, Split, Wheel, Wipe, Zoom
```

You can also pass a dict (`{"effect": "push", "direction": "left"}`) or an effect
string (`"push"`, which uses that effect's defaults). Every transition shares the
timing fields `duration` (seconds, default `1.0`), `advance_on_click` (default
`True`), and `advance_after` (auto-advance after N seconds, default `None`).

**Animations** attach to a `text`, `shape`, `image`, `svg`, or `group` layer via
`animation=`, which takes a single effect or a list of effects played in order.
Each effect is its own class, so it only exposes the options it actually
supports — `Wipe(direction="up")`, `Box(direction="in")`, `Blinds(orientation="vertical")`,
`Checkerboard(direction="down")`, `Wheel(spokes=3)`, and `Appear`/`Fade`/`Circle`/
`Diamond`/`Dissolve` (no extra options):

```python
from quickthumb import Appear, Blinds, Box, Checkerboard, Circle, Diamond, Dissolve, Fade, Wheel, Wipe
```

Every effect shares the same timing fields:

| Field | Description |
| --- | --- |
| `animate` | `entrance` (default) or `exit` |
| `duration` | Seconds the animation runs (default `0.5`) |
| `delay` | Seconds to wait before it starts (default `0.0`) |
| `trigger` | `on_click` (default), `with_previous`, or `after_previous` |

`trigger` controls sequencing: `on_click` waits for a click, `with_previous`
runs alongside the previous animation, and `after_previous` starts automatically
when the previous one finishes. A layer that maps to several PowerPoint shapes
(e.g. text with a background fill) animates them together, and a `group`
animation drives all of the group's children as one effect — taking precedence
over any animation set on an individual child. Animations and transitions
round-trip through JSON with the rest of the spec (an effect serializes with its
`effect` tag, e.g. `{"effect": "wipe", "direction": "up"}`).

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
- `quickthumb schema` emits the current JSON Schema for constrained generation and editor autocomplete

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

For constrained generation, first run `quickthumb schema > quickthumb.schema.json` and pass that schema to the model or editor. Prefer concrete field values in schema-constrained calls; `$theme.*` tokens are resolved by quickthumb before model validation and may not satisfy generic JSON Schema validators by themselves.

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
| Document renderers | SVG (`to_svg()`), self-contained animated HTML (`to_html()`), editable PPTX via `quickthumb[pptx]`, PDF via `quickthumb[pdf]` |
| Decks | `Deck` of multiple slides: multi-page PDF, multi-slide PPTX, numbered image sequences, per-slide diagnostics |
| Slide effects | PPTX/HTML slide `Transition`s (per-slide or deck default) and per-layer entrance/exit `Animation`s |
| Serialization | `to_json()` / `from_json()` for built-in layer types and named custom layers |

## Real Example Scripts

See the shipped examples in [`examples/README.md`](examples/README.md):

- `examples/youtube_thumbnail_01.py`
- `examples/youtube_thumbnail_02.py`
- `examples/instagram_news_card.py`
- `examples/launch_announcement.py` — the 0.5 feature set (groups, theme tokens, shapes, SVG, diagnostics) in one JSON spec
- `examples/investor_deck.py` — an animated investor-style deck exported to both HTML and PPTX

## Gotchas

- `weight` and `bold=True` are mutually exclusive on text layers and `TextPart`
- `auto_scale=True` requires `max_width` or `max_height`
- `position` percentage values must be strings like `"50%"`
- `fill` and `color` are independent fields; when `fill` is set it takes visual precedence over `color`
- `canvas.custom(fn)` without a `name` runs during render order but cannot be serialized to JSON; pass `name=` and register the function with `Canvas.register_layer_fn()` to enable serialization
- `Grain` is valid only on background and image layer `effects`; it is not a valid text or shape effect
- `Grain(intensity=0.0)` is a no-op (no noise is generated or composited)
- Group children must not set `position`; the group assigns positions (their `align` is also ignored — use `item_align`)
- `svg` layers raise `RenderingError` unless `quickthumb[svg]` (cairosvg) is installed
- `theme` blocks are resolved at parse time; `to_json()` emits resolved values without the `theme` block
- Slide `Transition`s and layer `Animation`s affect PPTX, HTML, GIF, and Deck WebM output; Deck MP4 currently renders static slides with per-slide narration
- Transitions live on the `Deck` (default plus per-slide override), not on `Canvas`; a per-slide override wins over the deck default
- Animations are valid on `text`, `shape`, `image`, `svg`, and `group` layers; pass one effect or a list of effects played in order
- HTML export needs no optional extra; the document is fixed-layout and scaled to fit (`responsive=True` by default), never reflowed, so it stays a faithful twin of the PNG/SVG/PDF/PPTX output
- HTML text placement is a close approximation (browsers rasterize fonts differently than PIL); use `embed_fonts=True` for the closest match, available when text uses local font files
- HTML, GIF, and Deck WebM play per-layer `animation`s and `Deck` slide transitions; HTML approximates a few exotic effects (blinds, checkerboard, wheel, dissolve) in CSS
- HTML cannot animate a layer that must be rasterized together with earlier backdrop-dependent content, such as blend-mode or custom layers; move animated layers after that content or remove the backdrop dependency
- Deck MP4 can attach `audio=` and `duration=` to each `slide()`: it requires FFmpeg/FFprobe, always writes H.264/AAC, and currently exports static slides without transitions or layer animations

## Development

```bash
uv sync
uv run pytest
uv run ruff check .
uv run ty quickthumb/
```

## Reference

- License: [LICENSE](LICENSE)
