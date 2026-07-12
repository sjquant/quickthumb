---
description: Answers to common quickthumb questions about installation, fonts, images, rendering behavior, JSON specs, and supported Python versions.
---

# FAQ

## Installation

### Which Python versions are supported?

Python 3.10, 3.11, and 3.12.

### Do I need to install anything else for background removal?

Yes. Install the `rembg` extra:

```bash
pip install "quickthumb[rembg]"
```

The first call to `remove_background=True` will download the ONNX model (~170 MB) and cache it locally.

### Why does my `svg` layer raise `RenderingError`?

SVG layers need the `svg` extra (cairosvg):

```bash
pip install "quickthumb[svg]"
```

### The `quickthumb` command isn't found. How do I install the CLI?

The CLI is an optional extra:

```bash
pip install "quickthumb[cli]"
```

---

## Canvas and layers

### What order are layers drawn in?

Layers render in the order you call them. The first layer added is drawn at the back; each subsequent layer is drawn on top.

### Can I reuse a canvas?

Each builder method returns `self`, so you can chain calls on one canvas object. There is no built-in "clone" method — just create a new canvas if you need a separate composition.

### What happens if I call `.render()` on a canvas with no layers?

It produces a transparent PNG of the specified dimensions. No error is raised.

### Why does my group child raise "group children must not set position"?

Auto-layout groups assign positions themselves — that's the point. Remove `position` from the child and anchor the whole group instead:

```python
canvas.group(
    children=[{"type": "text", "content": "TITLE", "size": 96, "color": "#fff"}],
    position=("8%", "50%"),
    align=("left", "middle"),
)
```

A child's `align` is also ignored; use the group's `item_align` for cross-axis placement.

### How do I check a composition for problems before rendering?

Call `canvas.diagnose()` (or run `quickthumb lint spec.json`). It reports off-canvas layers, tiny text, unwrappable words, and low text contrast. See [Diagnostics & CLI](diagnostics.md).

---

## Text

### Why is my text getting cut off?

Use `max_width` to enable wrapping:

```python
canvas.text(content="Long title here", size=72, color="#fff", max_width="60%")
```

Or use `auto_scale=True` with `max_width` and/or `max_height` to shrink the text until it fits the declared bounds.

### Can I mix fonts and colors in a single text block?

Yes — use `TextPart` for per-segment control:

```python
from quickthumb import TextPart

canvas.text(
    content=[
        TextPart(text="HOT ", color="#FF3B30", weight=900),
        TextPart(text="TAKE", color="#FFFFFF", weight=900),
    ],
    size=80,
    position=("8%", "50%"),
    align=("left", "middle"),
)
```

### I set `bold=True` and `weight=900` and got an error. Why?

`bold` and `weight` are mutually exclusive. Use one or the other:

```python
# Preferred
TextPart(text="STRONG", weight=900)

# Also valid
TextPart(text="STRONG", bold=True)
```

### How do I use a Google Font or custom web font?

Pass a URL directly as the `font` parameter:

```python
canvas.text(
    content="Hello",
    font="https://fonts.gstatic.com/s/inter/v13/UcCO3FwrK3iLTeHuS_fvQtMwCp50KnMw2boKoduKmMEVuLyfAZ9hiA.woff2",
    size=72,
    color="#FFFFFF",
)
```

quickthumb downloads and caches the font file. Note: when using a webfont URL, `bold`, `italic`, and `weight` are ignored — download separate URLs for bold/italic variants.

---

## Images

### Can I use remote images?

Yes, both `canvas.background(image=...)` and `canvas.image(path=...)` accept `http://` and `https://` URLs. quickthumb downloads and caches them during rendering.

### My image has a white background I want to remove. How?

Use `remove_background=True` on an image layer (requires the `rembg` extra):

```python
canvas.image(
    path="portrait.jpg",
    position=("75%", "55%"),
    width=420,
    height=520,
    remove_background=True,
)
```

### What's the difference between `cover`, `contain`, and `fill`?

| Mode | Behavior |
| --- | --- |
| `cover` | Fills the box, cropping if needed |
| `contain` | Fits entirely inside the box with letterboxing |
| `fill` | Stretches to fill exactly, ignoring aspect ratio |

---

## Export

### Which output formats are supported?

`PNG`, `JPEG`, and `WEBP`.

### Can I use `quality` with PNG?

No — `quality` is only valid for `JPEG` and `WEBP`. Passing it with `PNG` raises `RenderingError`.

### How do I get the image as a base64 string or data URL?

```python
b64  = canvas.to_base64(format="PNG")
url  = canvas.to_data_url(format="JPEG", quality=90)
```

---

## JSON

### Does `Canvas.from_json()` accept a dict?

No — it expects a JSON **string**. Use `json.dumps()` first if you have a dict:

```python
import json
from quickthumb import Canvas

data = {"width": 1280, "height": 720, "layers": [...]}
canvas = Canvas.from_json(json.dumps(data))
```

### Why does `canvas.to_json()` raise a `ValidationError`?

Your canvas contains a `.custom(fn)` layer. Custom layers cannot be serialized because they hold arbitrary Python callables. Remove or replace it before calling `to_json()`.

### Where did my `theme` block go after `to_json()`?

`$theme.*` tokens are resolved when the spec is parsed. `to_json()` emits the resolved values, so the round-tripped spec has no `theme` block. Keep the original spec file if you want to keep editing tokens.

---

## Errors

### What's the difference between `ValidationError` and `RenderingError`?

- `ValidationError` — raised immediately when you pass invalid arguments to a layer builder (wrong types, out-of-range values, conflicting options).
- `RenderingError` — raised when `.render()`, `.to_base64()`, or `.to_data_url()` is called and something fails at render time (bad file path, failed download, unsupported format).
