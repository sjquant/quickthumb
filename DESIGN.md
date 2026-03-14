# QuickThumb API Reference

This document reflects the current implemented API in this repository.
It is intended to be the reliable reference for writing QuickThumb code, generating QuickThumb JSON, and validating what the library actually supports today.

## Core Model

- A `Canvas` is an ordered list of layers.
- Layers render in call order: first added is the backmost layer.
- All layer builder methods mutate the canvas and return `self`.
- Most canvases can round-trip through JSON with `to_json()` and `from_json()`.
- Named custom callback layers can round-trip through JSON via a registry. Unnamed custom layers cannot be serialized.

## Public Imports

```python
from quickthumb import (
    Align,
    Background,
    BlendMode,
    Canvas,
    Filter,
    FitMode,
    Glow,
    LinearGradient,
    RadialGradient,
    Shadow,
    Stroke,
    TextPart,
    ValidationError,
)
```

## Canvas API

### Creation

```python
from quickthumb import Canvas

canvas = Canvas(1280, 720)
wide = Canvas.from_aspect_ratio("16:9", base_width=1280)
square = Canvas.from_aspect_ratio("1:1", base_width=1080)
vertical = Canvas.from_aspect_ratio("9:16", base_width=1080)
```

Rules:

- `width` and `height` must be positive integers.
- `from_aspect_ratio()` expects a string like `"16:9"` plus `base_width`.

### Layer Builders

```python
canvas.background(...)
canvas.text(...)
canvas.outline(...)
canvas.shape(...)
canvas.image(...)
canvas.custom(fn)
canvas.custom(fn, name="...", kwargs={...})
Canvas.register_layer_fn(name, fn)
Canvas.unregister_layer_fn(name)
```

### Export Methods

```python
canvas.render("output.png")
canvas.render("output.webp", format="WEBP", quality=90)

png_base64 = canvas.to_base64(format="PNG")
jpeg_data_url = canvas.to_data_url(format="JPEG", quality=90)

json_data = canvas.to_json()
canvas = Canvas.from_json(json_data)
```

Rules:

- Supported output formats are `PNG`, `JPEG`, and `WEBP`.
- `quality` is only valid for `JPEG` and `WEBP`.
- `Canvas.from_json()` accepts a JSON string, not a Python dict.

## Layer Reference

### Background Layer

Adds a full-canvas background layer.

```python
from quickthumb import Canvas, Filter, LinearGradient

canvas = (
    Canvas(1280, 720)
    .background(color="#0F172A")
    .background(
        gradient=LinearGradient(
            angle=120,
            stops=[("#111827", 0.0), ("#11182700", 1.0)],
        ),
        opacity=0.7,
    )
    .background(
        image="https://images.unsplash.com/photo-1516321318423-f06f85e504b3",
        fit="cover",
        blend_mode="multiply",
        effects=[Filter(blur=4, brightness=0.75, contrast=1.1, saturation=0.9)],
    )
)
```

Parameters:

- `color`: hex string (`"#RRGGBB"` or `"#RRGGBBAA"`) or RGB/RGBA tuple
- `gradient`: `LinearGradient` or `RadialGradient`
- `image`: local file path or remote URL
- `opacity`: float from `0.0` to `1.0`
- `blend_mode`: `multiply`, `overlay`, `screen`, `darken`, `lighten`, or `normal`
- `fit`: `cover`, `contain`, or `fill`
- `effects`: background effects list, currently `Filter` only

Notes:

- Background layers cover the full canvas.
- Background blend modes apply when compositing over previous layers.
- Backgrounds support local images and remote URLs.

### Text Layer

Adds a text layer using either a plain string or rich text parts.

```python
from quickthumb import Background, Canvas, Glow, Shadow, Stroke, TextPart

canvas = Canvas(1280, 720).text(
    content=[
        TextPart(text="BUILD ", color="#B8FF00", weight=900),
        TextPart(text="FASTER", color="#FFFFFF", effects=[Stroke(width=4, color="#000000")]),
    ],
    font="Impact",
    size=110,
    color="#FFFFFF",
    position=("8%", "50%"),
    align=("left", "middle"),
    max_width="60%",
    line_height=1.0,
    letter_spacing=1,
    effects=[
        Background(color="#111827CC", padding=(16, 24), border_radius=14),
        Shadow(offset_x=4, offset_y=4, color="#000000", blur_radius=8),
        Glow(color="#B8FF00", radius=16, opacity=0.25),
    ],
    rotation=0,
    opacity=1.0,
)
```

Parameters:

- `content`: required; either a string or `list[TextPart]`
- `font`: font family name, font file path, or webfont URL
- `size`: positive integer font size
- `color`: default text color for the layer
- `position`: optional `(x, y)` tuple using pixels or percentage strings
- `align`: optional `Align`, string alias, or `(horizontal, vertical)` tuple
- `bold`: legacy bold flag
- `italic`: italic flag
- `weight`: CSS-style font weight as int or name
- `max_width`: wrap width in pixels or percentage string
- `effects`: any mix of `Stroke`, `Shadow`, `Glow`, and text `Background`
- `line_height`: positive float
- `letter_spacing`: integer tracking adjustment
- `auto_scale`: shrink text until it fits `max_width`
- `rotation`: degrees
- `opacity`: float from `0.0` to `1.0`

Notes:

- `content` is required.
- `align` accepts values like `"center"`, `"top-left"`, `"bottom-right"`, or tuples like `("left", "middle")`.
- `font` may be a remote URL; QuickThumb downloads and caches it.
- `weight` is supported on both full text layers and individual `TextPart` entries.

### Outline Layer

Adds a border around the full canvas.

```python
canvas.outline(width=12, color="#B8FF00", offset=0, opacity=1.0)
```

Parameters:

- `width`: positive integer
- `color`: hex string
- `offset`: non-negative integer inset/outset offset
- `opacity`: float from `0.0` to `1.0`

### Shape Layer

Adds a positioned rectangle or ellipse.

```python
from quickthumb import Canvas, Shadow, Stroke

canvas = Canvas(1280, 720).shape(
    shape="rectangle",
    position=(64, 64),
    width=360,
    height=120,
    color="#CC0000",
    border_radius=16,
    opacity=0.95,
    rotation=-4,
    align=("left", "top"),
    effects=[
        Stroke(width=3, color="#FFFFFF"),
        Shadow(offset_x=0, offset_y=10, color="#000000", blur_radius=18),
    ],
)
```

Parameters:

- `shape`: `"rectangle"` or `"ellipse"`
- `position`: required `(x, y)` tuple using pixels or percentage strings
- `width`: positive integer
- `height`: positive integer
- `color`: hex string
- `border_radius`: non-negative integer
- `opacity`: float from `0.0` to `1.0`
- `rotation`: degrees
- `align`: optional `Align`, string alias, or `(horizontal, vertical)` tuple
- `effects`: any mix of `Stroke`, `Shadow`, and `Glow`

### Image Layer

Adds an overlay image or cutout.

```python
from quickthumb import Canvas, Filter, Shadow

canvas = Canvas(1280, 720).image(
    path="portrait.png",
    position=("74%", "54%"),
    width=420,
    height=520,
    fit="cover",
    opacity=1.0,
    rotation=0,
    align=("center", "middle"),
    remove_background=True,
    border_radius=28,
    blend_mode="normal",
    effects=[
        Filter(contrast=1.1, saturation=1.05),
        Shadow(offset_x=0, offset_y=12, color="#000000", blur_radius=24),
    ],
)
```

Parameters:

- `path`: required local file path or remote URL
- `position`: required `(x, y)` tuple using pixels or percentage strings
- `width`: optional positive integer
- `height`: optional positive integer
- `fit`: `cover`, `contain`, or `fill` when width and height define a target box
- `opacity`: float from `0.0` to `1.0`
- `rotation`: degrees
- `align`: `Align`, string alias, or `(horizontal, vertical)` tuple
- `remove_background`: requires `quickthumb[rembg]`
- `border_radius`: non-negative integer
- `effects`: any mix of `Stroke`, `Shadow`, `Glow`, and `Filter`
- `blend_mode`: `multiply`, `overlay`, `screen`, `darken`, `lighten`, or `normal`

Notes:

- If only one of `width` or `height` is set, aspect ratio is preserved.
- `fit` matters when both `width` and `height` define a box.
- Image blend modes apply during compositing onto prior layers.

### Custom Layer

Adds a callback that can draw directly onto the rendered Pillow image.

```python
from PIL import ImageDraw
from quickthumb import Canvas

def add_badge(image):
    draw = ImageDraw.Draw(image)
    draw.polygon([(70, 70), (240, 70), (155, 180)], fill="#FF3B30")
    return image

canvas = Canvas(512, 512).custom(add_badge)
```

Named custom layers can be serialized to JSON by registering the function in a global registry:

```python
from PIL import ImageDraw
from quickthumb import Canvas

def draw_bar(image, *, color: str = "#000000", height: int = 40) -> None:
    ImageDraw.Draw(image).rectangle((0, 0, image.width, height), fill=color)

Canvas.register_layer_fn("draw_bar", draw_bar)

canvas = Canvas(512, 512).custom(draw_bar, name="draw_bar", kwargs={"color": "#E74C3C", "height": 60})

json_str = canvas.to_json()
# {"type": "custom", "name": "draw_bar", "kwargs": {"color": "#E74C3C", "height": 60}}

recreated = Canvas.from_json(json_str)  # register_layer_fn must be called first
```

Parameters:

- `fn`: required callable; receives a `PIL.Image.Image` as the first argument
- `name`: optional string; required for JSON serialization
- `kwargs`: optional dict of keyword arguments forwarded to `fn` at render time; must be JSON-serializable when `name` is set

Rules:

- `fn` must be callable.
- The callback receives a `PIL.Image.Image` as the first positional argument, followed by any `kwargs`.
- The callback may mutate and return the same image, return a new image of the same size, or return `None`.
- Exceptions from the callback are wrapped as `RenderingError`.
- Unnamed custom layers (`name=None`) cannot be serialized to JSON.
- `Canvas.register_layer_fn(name, fn)` must be called before `Canvas.from_json()` for any canvas containing a custom layer with that name.
- `Canvas.unregister_layer_fn(name)` removes a name from the registry.

## Helpers, Enums, and Effects

### Gradients

```python
from quickthumb import LinearGradient, RadialGradient

LinearGradient(
    angle=45,
    stops=[("#FF5733", 0.0), ("#3333FF", 1.0)],
)

RadialGradient(
    stops=[("#FF5733", 0.0), ("#3333FF", 1.0)],
    center=(0.5, 0.5),
)
```

### TextPart

`TextPart` supports per-segment overrides inside rich text content.

```python
from quickthumb import Stroke, TextPart

TextPart(
    text="HOT",
    color="#FF3B30",
    size=56,
    font="Impact",
    bold=None,
    italic=None,
    weight=900,
    line_height=None,
    letter_spacing=0,
    effects=[Stroke(width=3, color="#000000")],
)
```

Rules:

- `text` cannot be empty.
- `weight` and `bold=True` are mutually exclusive here too.

### Enums

Blend modes:

- `BlendMode.MULTIPLY`
- `BlendMode.OVERLAY`
- `BlendMode.SCREEN`
- `BlendMode.DARKEN`
- `BlendMode.LIGHTEN`
- `BlendMode.NORMAL`

Fit modes:

- `FitMode.COVER`
- `FitMode.CONTAIN`
- `FitMode.FILL`

Align values:

- `Align.CENTER`
- `Align.TOP_LEFT`
- `Align.TOP_CENTER`
- `Align.TOP_RIGHT`
- `Align.LEFT`
- `Align.RIGHT`
- `Align.BOTTOM_LEFT`
- `Align.BOTTOM_CENTER`
- `Align.BOTTOM_RIGHT`

### Effects by Layer Type

- Text layers: `Stroke`, `Shadow`, `Glow`, `Background`
- Image layers: `Stroke`, `Shadow`, `Glow`, `Filter`
- Shape layers: `Stroke`, `Shadow`, `Glow`
- Background layers: `Filter`

## JSON Schema

QuickThumb serializes canvases as a JSON object with top-level `width`, `height`, and `layers`.

```json
{
  "width": 1280,
  "height": 720,
  "layers": [
    {
      "type": "background",
      "color": "#0F172A",
      "opacity": 1.0,
      "blend_mode": null,
      "fit": null,
      "effects": []
    },
    {
      "type": "shape",
      "shape": "rectangle",
      "position": [48, 48],
      "width": 320,
      "height": 96,
      "color": "#CC0000",
      "border_radius": 14,
      "opacity": 1.0,
      "rotation": 0.0,
      "align": "top-left",
      "effects": [
        { "type": "stroke", "width": 2, "color": "#FFFFFF" }
      ]
    },
    {
      "type": "text",
      "content": [
        { "text": "HELLO ", "color": "#FFFFFF", "effects": [] },
        {
          "text": "WORLD",
          "color": "#B8FF00",
          "weight": 900,
          "effects": [
            { "type": "stroke", "width": 3, "color": "#000000" }
          ]
        }
      ],
      "size": 88,
      "position": ["8%", "50%"],
      "align": "left",
      "max_width": "60%",
      "auto_scale": false,
      "rotation": 0.0,
      "opacity": 1.0,
      "effects": [
        {
          "type": "shadow",
          "offset_x": 4,
          "offset_y": 4,
          "color": "#000000",
          "blur_radius": 8
        }
      ]
    },
    {
      "type": "image",
      "path": "portrait.png",
      "position": ["74%", "54%"],
      "width": 420,
      "height": 520,
      "opacity": 1.0,
      "rotation": 0.0,
      "remove_background": false,
      "align": "center",
      "border_radius": 24,
      "fit": "cover",
      "blend_mode": "normal",
      "effects": [
        { "type": "filter", "blur": 0, "brightness": 1.0, "contrast": 1.05, "saturation": 1.0 }
      ]
    },
    {
      "type": "outline",
      "width": 12,
      "color": "#B8FF00",
      "offset": 0,
      "opacity": 1.0
    }
  ]
}
```

Serialization notes:

- Every layer uses a `type` discriminator.
- Enum-like fields serialize to strings.
- Positions serialize as JSON arrays.
- `align` serializes to a single string such as `"center"` or `"top-left"`.
- Named custom layers serialize as `{"type": "custom", "name": "...", "kwargs": {...}}`.
- Unnamed custom layers are not serializable.

## Validation Rules and Gotchas

### Text

- `content` is required for `canvas.text(...)`.
- Rich text lists cannot be empty.
- `TextPart.text` cannot be empty.
- `weight` and `bold=True` are mutually exclusive on both `TextLayer` and `TextPart`.
- `auto_scale=True` requires `max_width`.
- `max_width` must be a positive integer or positive percentage string.
- Percentage strings are validated for `position` and `max_width`.

### Fonts

- `font` may be a font family name, font file path, or remote font URL.
- When `font` is a webfont URL, `bold`, `italic`, and `weight` flags are ignored.
- Provide separate font URLs for styled webfont variants.
- `QUICKTHUMB_FONT_DIR` can point QuickThumb to a custom font directory.
- `QUICKTHUMB_DEFAULT_FONT` can override the default fallback font.

### Images and Shapes

- `image.position` and `shape.position` are required.
- Positions must be 2-item tuples or lists.
- Percentage positions may be negative, for example `("-10%", "50%")`.
- `border_radius` cannot be negative.
- `opacity` must be between `0.0` and `1.0`.

### Rendering and Export

- `quality` is only supported for `JPEG` and `WEBP`; using it with `PNG` raises `RenderingError`.
- Unsupported file formats raise `RenderingError`.
- Invalid local paths or failed remote downloads raise rendering-time errors.

### JSON

- `Canvas.from_json()` expects a JSON string.
- `Canvas.to_json()` raises `ValidationError` when the canvas contains unnamed custom layers.
- Named custom layers round-trip through JSON; `Canvas.register_layer_fn(name, fn)` must be called before `Canvas.from_json()`.
- `Canvas.from_json()` raises `ValidationError` if a custom layer name is not in the registry.
- Round-trip JSON works for all built-in layer types, effects, and named custom layers.

## End-to-End Example

```python
from quickthumb import Background, Canvas, Filter, Shadow, Stroke, TextPart

canvas = (
    Canvas.from_aspect_ratio("16:9", base_width=1280)
    .background(
        image="https://images.unsplash.com/photo-1516321318423-f06f85e504b3",
        fit="cover",
        effects=[Filter(brightness=0.6)],
    )
    .background(color="#000000", opacity=0.35)
    .shape(
        shape="rectangle",
        position=(52, 52),
        width=360,
        height=96,
        color="#CC0000",
        border_radius=14,
    )
    .text(
        content=[
            TextPart(text="AI ", color="#B8FF00", weight=900),
            TextPart(text="THUMBNAILS", color="#FFFFFF", weight=900),
        ],
        size=108,
        position=("8%", "52%"),
        align=("left", "middle"),
        max_width="58%",
        effects=[
            Stroke(width=6, color="#000000"),
            Shadow(offset_x=4, offset_y=4, color="#000000", blur_radius=8),
            Background(color="#111827CC", padding=(16, 22), border_radius=12),
        ],
    )
    .image(
        path="portrait.png",
        position=("75%", "55%"),
        width=430,
        height=540,
        fit="cover",
        align=("center", "middle"),
        border_radius=24,
        effects=[Shadow(offset_x=0, offset_y=14, color="#000000", blur_radius=24)],
    )
    .outline(width=12, color="#B8FF00")
)

canvas.render("thumbnail.png")
```
