# QuickThumb Feature Spec

This document specifies planned and exploratory features for QuickThumb. It is a forward-looking companion to README.md, which documents the **currently implemented** API.

### Status Legend

| Status        | Meaning                                       |
| ------------- | --------------------------------------------- |
| `planned`     | Committed for implementation; not yet shipped |
| `in progress` | Actively being developed                      |
| `done`        | Shipped; refer to README.md for the final API |
| `exploratory` | Under consideration; design not committed     |

### Feature Status

| #   | Feature                      | Status        |
| --- | ---------------------------- | ------------- |
| 1   | CLI (`quickthumb` command)   | `planned`     |
| 2   | Template System              | `planned`     |
| 3   | Gradient / Image-Filled Text | `done`        |
| 4   | Noise / Grain Effect         | `planned`     |
| 5   | Presentation & Video         | `exploratory` |

---

## 1. CLI — `planned`

A `quickthumb` command-line tool for rendering JSON specs without writing Python.

### Installation

The CLI is an optional extra to avoid pulling `typer` into the core dependency set.

```bash
uv pip install "quickthumb[cli]"
```

`pyproject.toml` entry point:

```toml
[project.scripts]
quickthumb = "quickthumb.cli:main"
```

### Subcommands

#### `render`

Render a JSON spec file to an image.

```bash
quickthumb render spec.json
quickthumb render spec.json -o thumbnail.png
quickthumb render spec.json -o output.webp --format WEBP --quality 85
```

Template variable substitution via `--var`:

```bash
quickthumb render template.json \
  --var title="10 Python Tips" \
  --var image=photo.png \
  -o out.png
```

Parameters:

- `spec`: required; path to a JSON spec file
- `-o` / `--output`: output file path; defaults to `output.png` in the current directory
- `--format`: `PNG`, `JPEG`, or `WEBP`; inferred from output extension when omitted
- `--quality`: integer quality for `JPEG` and `WEBP`
- `--var KEY=VALUE`: substitutes `$KEY` / `${KEY}` placeholders in the spec before parsing; repeatable

#### `watch` (stretch goal)

Re-render automatically when the spec file changes. Requires `watchfiles`.

```bash
quickthumb watch spec.json -o thumbnail.png
```

Install with:

```bash
uv pip install "quickthumb[cli]"
```

### Pipeline

1. Read the JSON spec file from disk.
2. Substitute `--var` placeholders (string-level, before JSON parsing).
3. Call `Canvas.from_json()` on the substituted string.
4. Call `canvas.render(output, format=..., quality=...)`.

### Exit Codes

| Code | Meaning                                                                 |
| ---- | ----------------------------------------------------------------------- |
| 0    | Success                                                                 |
| 1    | Validation error (bad spec, missing required field, unknown layer type) |
| 2    | Rendering error (missing file, download failure, unsupported format)    |

### Notes

- `typer` is only imported inside `quickthumb/cli.py`; the rest of the library does not depend on it.
- `quickthumb watch` exits with code 1 if `watchfiles` is not installed.
- Errors print to stderr; the rendered image path prints to stdout on success.

---

## 2. Template System — `planned`

Reusable JSON specs with variable placeholders. Useful for batch generation and AI-driven workflows.

### Placeholder Syntax

Templates use `$variable` and `${variable}` placeholders anywhere in the JSON text. Substitution happens at the string level before the JSON is parsed.

```json
{
  "width": 1280,
  "height": 720,
  "layers": [
    { "type": "background", "color": "${bg_color}" },
    {
      "type": "text",
      "content": "$title",
      "size": 88,
      "color": "#FFFFFF",
      "position": ["8%", "50%"]
    },
    {
      "type": "image",
      "path": "${subject_image}",
      "position": ["74%", "54%"],
      "width": 420,
      "height": 520,
      "align": ["center", "middle"]
    }
  ]
}
```

### Python API

```python
from quickthumb import Canvas

# From a template file path
canvas = Canvas.from_template(
    "templates/youtube-16x9.json",
    variables={
        "title": "10 Python Tips",
        "bg_color": "#0F172A",
        "subject_image": "portrait.png",
    },
)
canvas.render("thumbnail.png")

# From a template string
spec = open("template.json").read()
canvas = Canvas.from_template(spec, variables={"title": "Hello"})
```

Parameters:

- `spec_or_path`: required; a JSON string or a file path to a `.json` template
- `variables`: dict mapping placeholder names to string values; defaults to `{}`

### Built-in Templates

QuickThumb ships a small set of starter templates in `quickthumb/templates/`:

| Name               | Aspect Ratio      | Description                             |
| ------------------ | ----------------- | --------------------------------------- |
| `youtube-16x9`     | 16:9 (1280×720)   | Title left, subject image right         |
| `instagram-square` | 1:1 (1080×1080)   | Centered headline with background image |
| `twitter-card`     | 2:1 (1200×600)    | Logo + title + subtitle                 |
| `og-image`         | 1.91:1 (1200×630) | Open Graph social card                  |

Access by name:

```python
canvas = Canvas.from_template(
    "youtube-16x9",
    variables={"title": "My Video", "image": "thumb.jpg"},
)
```

### Template Registry

```python
from quickthumb import Canvas

# Register a custom template by name
Canvas.register_template("my-brand", "/path/to/brand-template.json")

# Use it by name
canvas = Canvas.from_template("my-brand", variables={"headline": "..."})

# Remove a registered template
Canvas.unregister_template("my-brand")
```

### Limitations

- Substitution is string-level. Variables cannot inject JSON structure (objects, arrays).
- Variable values are always treated as strings. To inject a number into JSON, use `"size": $font_size` without surrounding quotes in the template, but the substituted value must be a valid JSON token.
- Unresolved placeholders (no matching variable) raise `ValidationError` before JSON parsing.
- `Canvas.to_json()` does not produce a template; templates are authored separately.

### Notes

- `Canvas.from_template()` raises `ValidationError` if required variables are missing.
- Built-in template names take lower precedence than user-registered names with the same key.

---

## 3. Gradient / Image-Filled Text (Knockout Text) — `done`

Fill text with a gradient or image instead of a flat color. The text shape acts as a mask that reveals the fill behind it.

### Python API

```python
from quickthumb import Canvas, LinearGradient, RadialGradient, TextFillImage, TextPart

# Gradient-filled headline
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
    content="FIRE TEXT",
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

### `TextFillImage` Model

```python
from quickthumb import TextFillImage

fill = TextFillImage(
    path="texture.jpg",   # local path or remote URL
    fit="cover",           # "cover", "contain", or "fill"
)
```

Parameters:

- `path`: required; local file path or remote URL
- `fit`: how the image is scaled to the text bounding box; default `"cover"`

### Parameters (Text Layer and TextPart)

New `fill` parameter on both `canvas.text(...)` and `TextPart`:

- `fill`: `LinearGradient`, `RadialGradient`, or `TextFillImage`; mutually exclusive with `color` when set

Fallback rule: if `fill` is `None`, `color` is used as before.

### Implementation Notes

- Render a white-on-black alpha mask from the text glyphs.
- Render the fill (gradient or image) onto a same-size canvas.
- Composite fill through the mask to produce the filled text image.
- Composite the result onto the main canvas, applying any layer-level effects (Stroke, Shadow, Glow) as usual.
- Effects operate on the filled text shape, not on the fill content itself.

### JSON Serialization

`fill` uses a `type` discriminator:

```json
{
  "type": "text",
  "content": "GRADIENT",
  "size": 120,
  "fill": {
    "type": "linear_gradient",
    "angle": 90,
    "stops": [
      ["#FF6B6B", 0.0],
      ["#4ECDC4", 1.0]
    ]
  },
  "position": ["50%", "50%"],
  "align": "center",
  "effects": []
}
```

```json
{
  "type": "text",
  "content": "TEXTURE",
  "size": 140,
  "fill": {
    "type": "image",
    "path": "fire_texture.jpg",
    "fit": "cover"
  },
  "position": ["50%", "50%"],
  "align": "center",
  "effects": []
}
```

`TextFillImage` discriminator value: `"image"`.
`LinearGradient` discriminator value: `"linear_gradient"`.
`RadialGradient` discriminator value: `"radial_gradient"`.

### Rules

- `fill` and `color` are independent; `fill` takes visual precedence when set.
- `fill` on a `TextPart` overrides the layer-level `fill` for that segment only.
- `TextFillImage.path` supports remote URLs; the image is downloaded and cached at render time.
- `fit` on `TextFillImage` maps the image to the bounding box of the entire text block, not per-glyph.

---

## 4. Noise / Grain Effect — `planned`

Add film-grain noise to backgrounds, images, or the entire canvas.

### Per-Layer Effect

`Grain` can be added to `effects` on background and image layers.

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
        effects=[Grain(intensity=0.08, monochrome=False, opacity=0.6)],
    )
)
```

### Canvas-Level Grain

`canvas.grain()` appends a grain layer that composites noise over the entire rendered canvas.

```python
canvas = (
    Canvas(1280, 720)
    .background(color="#0F172A")
    .text(content="GRITTY", size=100, color="#FFFFFF", position=("50%", "50%"), align="center")
    .grain(intensity=0.15)
)
```

### `Grain` Model

```python
from quickthumb import Grain

effect = Grain(
    intensity=0.12,       # 0.0 to 1.0; controls noise amplitude
    monochrome=True,      # True = luminance noise; False = color noise (RGB channels independently)
    blend_mode="overlay", # blend mode for compositing noise onto the layer
    opacity=1.0,          # 0.0 to 1.0
)
```

Parameters:

- `intensity`: float from `0.0` to `1.0`; `0.0` produces no grain, `1.0` is maximum noise
- `monochrome`: bool; `True` generates identical noise across R/G/B channels (gray grain), `False` generates independent per-channel noise (color grain); default `True`
- `blend_mode`: how the noise layer is composited; `"overlay"`, `"screen"`, `"multiply"`, or `"normal"`; default `"overlay"`
- `opacity`: float from `0.0` to `1.0`; scales the grain strength; default `1.0`

### Canvas-Level `grain()` Builder

```python
canvas.grain(
    intensity=0.15,
    monochrome=True,
    blend_mode="overlay",
    opacity=1.0,
)
```

Internally appends a `GrainLayer` to the canvas layer list. `GrainLayer` renders a full-canvas noise image and composites it over everything rendered so far.

### JSON Serialization

Per-layer effect:

```json
{
  "type": "background",
  "color": "#1A1A2E",
  "effects": [
    {
      "type": "grain",
      "intensity": 0.12,
      "monochrome": true,
      "blend_mode": "overlay",
      "opacity": 1.0
    }
  ]
}
```

Canvas-level grain layer:

```json
{
  "type": "grain",
  "intensity": 0.15,
  "monochrome": true,
  "blend_mode": "overlay",
  "opacity": 1.0
}
```

### Implementation Notes

- Grain is generated using Pillow only; no NumPy dependency is introduced.
- Generate noise using `random.randint` into a raw bytes buffer and construct a Pillow `Image` from it, or use `ImageFilter` or point operations available in Pillow.
- Each render call generates a fresh noise sample (non-deterministic by default).
- Grain is generated at native canvas resolution; no supersampling.

### Rules

- `intensity` must be between `0.0` and `1.0`.
- `opacity` must be between `0.0` and `1.0`.
- `Grain` is valid in `effects` on background layers and image layers; it is not a valid text or shape effect.
- `canvas.grain()` is the only way to apply grain across the full composited canvas.

---

## 5. Presentation and Video — `exploratory`

**This section is exploratory. Nothing here is committed for implementation.**

These capabilities require significant additional dependencies and design work. They are documented here to capture direction and trade-offs, not as a near-term roadmap.

### Slide Decks

A `Deck` would be an ordered sequence of `Canvas` objects, each representing one slide.

```python
# Hypothetical API — not implemented
from quickthumb import Canvas
from quickthumb_slides import Deck

deck = Deck([
    Canvas(1280, 720).background(color="#0F172A").text(content="Slide 1", size=80, color="#FFF", position=("50%", "50%"), align="center"),
    Canvas(1280, 720).background(color="#1E3A5F").text(content="Slide 2", size=80, color="#FFF", position=("50%", "50%"), align="center"),
])

deck.export_html("presentation/")     # reveal.js bundle
deck.export_pptx("presentation.pptx") # requires python-pptx
```

Export targets:

- **HTML**: a self-contained reveal.js bundle; each canvas renders to a PNG embedded as a slide background
- **PPTX**: via `python-pptx`; each canvas renders to a PNG inserted as a slide image

### Video

A video sequence would be a list of `Canvas` objects with per-frame timing and optional transitions.

```python
# Hypothetical API — not implemented
from quickthumb_video import VideoSequence, Transition

seq = VideoSequence(fps=30)
seq.add_frame(canvas_a, duration=3.0)
seq.add_transition(Transition.CROSSFADE, duration=0.5)
seq.add_frame(canvas_b, duration=3.0)
seq.render("output.mp4")  # requires ffmpeg or moviepy
```

### Packaging Recommendation

Both capabilities should ship as **separate packages** that depend on `quickthumb` core:

- `quickthumb-slides` — slide deck export (HTML/PPTX)
- `quickthumb-video` — video sequence export (MP4)

Reasons:

- Avoids pulling large optional dependencies (`python-pptx`, `moviepy`, `ffmpeg` bindings) into `quickthumb` core.
- Keeps the core install fast and lightweight.
- Allows independent versioning and maintenance.
- Users who only need thumbnails pay no cost for video capabilities.

### Open Questions

- Transitions between canvases require interpolating layer states or blending rendered frames; which approach is tractable?
- PPTX export via rendered PNGs loses editability; is native PPTX shape generation worth the complexity?
- Should `Deck` support JSON serialization (a list of canvas JSON specs)?
- Audio tracks for video: out of scope for `quickthumb-video` or supported via ffmpeg passthrough?
