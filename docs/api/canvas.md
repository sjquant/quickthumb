---
description: Reference for quickthumb Canvas creation, aspect ratios, layer composition, rendering, JSON loading, and image output.
---

# Canvas

The `Canvas` is the root object. It holds dimensions and an ordered list of layers.

## Creation

### `Canvas(width, height)`

```python
from quickthumb import Canvas

canvas = Canvas(1280, 720)
```

| Parameter | Type | Description |
| --- | --- | --- |
| `width` | `int` | Canvas width in pixels. Must be a positive integer. |
| `height` | `int` | Canvas height in pixels. Must be a positive integer. |

### `Canvas.from_aspect_ratio(ratio, base_width)`

Creates a canvas from an aspect ratio string and a base width. Height is calculated automatically.

```python
wide     = Canvas.from_aspect_ratio("16:9", base_width=1280)   # 1280×720
square   = Canvas.from_aspect_ratio("1:1",  base_width=1080)   # 1080×1080
vertical = Canvas.from_aspect_ratio("9:16", base_width=1080)   # 1080×1920
```

| Parameter | Type | Description |
| --- | --- | --- |
| `ratio` | `str` | Aspect ratio string in `"W:H"` format, e.g. `"16:9"` |
| `base_width` | `int` | Canvas width in pixels |

## Layer builders

All builder methods mutate the canvas and return `self`, enabling method chaining.

| Method | Description |
| --- | --- |
| `.background(...)` | Add a full-canvas background layer |
| `.text(...)` | Add a text layer |
| `.image(...)` | Add an overlay image layer |
| `.shape(...)` | Add a shape layer |
| `.svg(...)` | Add an SVG layer, rasterized at render time |
| `.group(...)` | Add an auto-layout group of child layers |
| `.outline(...)` | Add a canvas border |
| `.custom(fn)` | Add a Pillow callback layer |

See the individual reference pages for full parameter details.

## `.diagnose()`

Checks the composition for layout and legibility issues without writing a file. Returns a list of `Diagnostic` findings (empty when clean):

```python
for finding in canvas.diagnose():
    print(finding.severity, finding.code, finding.message)
```

Finding codes: `off-canvas`, `tiny-text`, `text-overflow`, `low-contrast`. See [Diagnostics & CLI](../diagnostics.md) for details and the `quickthumb lint` equivalent.

## Export methods

### `.render(path, format="PNG", quality=None)`

Renders the canvas and writes the result to a file. The format is detected from the file extension; `.svg`, `.html`, and `.pptx` produce vector/document output (see [Exporting to SVG, HTML & PPTX](../exports.md)).

```python
canvas.render("output.png")
canvas.render("output.jpg", format="JPEG", quality=85)
canvas.render("output.webp", format="WEBP", quality=90)
canvas.render("output.svg")
canvas.render("output.html")
canvas.render("output.pptx")  # requires quickthumb[pptx]
```

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `path` | `str` | — | Output file path |
| `format` | `str` | `"PNG"` | Raster output format: `"PNG"`, `"JPEG"`, or `"WEBP"` |
| `quality` | `int \| None` | `None` | Compression quality (1–95). Only valid for `JPEG` and `WEBP`. |

!!! warning
    Passing `quality` with `format="PNG"` raises `RenderingError`.

### `.to_svg(embed_fonts=False)`

Returns the canvas as an SVG document string. Set `embed_fonts=True` to inline the used font files as `@font-face` data URLs.

```python
svg = canvas.to_svg(embed_fonts=True)
```

### `.to_html(embed_fonts=True, title="quickthumb")`

Returns a standalone HTML page with the canvas embedded as inline SVG. Fonts are embedded by default so the document is self-contained.

```python
html = canvas.to_html(title="Launch card")
```

### `.to_pptx()`

Returns the canvas as PowerPoint file bytes — a single slide with editable text boxes and autoshapes. Requires the `pptx` extra.

```python
with open("deck.pptx", "wb") as f:
    f.write(canvas.to_pptx())
```

### `.to_base64(format="PNG", quality=None)`

Returns the rendered image as a base64-encoded string.

```python
b64 = canvas.to_base64(format="PNG")
b64 = canvas.to_base64(format="WEBP", quality=90)
```

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `format` | `str` | `"PNG"` | Output format: `"PNG"`, `"JPEG"`, or `"WEBP"` |
| `quality` | `int \| None` | `None` | Compression quality. Only valid for `JPEG` and `WEBP`. |

### `.to_data_url(format="PNG", quality=None)`

Returns the rendered image as a data URL (`data:<mime>;base64,...`).

```python
url = canvas.to_data_url(format="JPEG", quality=90)
# → "data:image/jpeg;base64,..."
```

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `format` | `str` | `"PNG"` | Output format: `"PNG"`, `"JPEG"`, or `"WEBP"` |
| `quality` | `int \| None` | `None` | Compression quality. Only valid for `JPEG` and `WEBP`. |

### `.to_json()`

Serializes the canvas to a JSON string.

```python
json_str = canvas.to_json()
```

Raises `ValidationError` if the canvas contains `.custom(fn)` layers (callbacks cannot be serialized).

### `Canvas.from_json(json_str)`

Deserializes a canvas from a JSON string.

```python
canvas = Canvas.from_json(json_str)
```

!!! note
    `from_json()` expects a **JSON string**, not a Python dict. Use `json.dumps(data)` first if you have a dict.

## `.custom(fn)`

Adds a callback that receives and returns a Pillow `Image`.

```python
from PIL import ImageDraw
from quickthumb import Canvas

def draw_badge(image):
    d = ImageDraw.Draw(image)
    d.polygon([(70, 70), (240, 70), (155, 180)], fill="#FF3B30")
    return image

canvas = Canvas(512, 512).custom(draw_badge)
```

| Rule | Detail |
| --- | --- |
| `fn` must be callable | Receives a `PIL.Image.Image` |
| Return value | May return the same image (mutated), a new image of the same size, or `None` |
| Errors | Exceptions from the callback are wrapped as `RenderingError` |
| Serialization | Custom layers are **not** JSON-serializable |
