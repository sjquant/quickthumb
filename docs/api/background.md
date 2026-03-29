# Background

`.background()` adds a full-canvas background layer. Multiple background calls stack in render order — first call is backmost.

## Signature

```python
canvas.background(
    color=None,
    gradient=None,
    image=None,
    opacity=1.0,
    blend_mode=None,
    fit=None,
    effects=None,
)
```

## Parameters

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `color` | `str \| tuple \| None` | `None` | Solid fill color. Hex string (`"#RRGGBB"` or `"#RRGGBBAA"`) or RGB/RGBA tuple. |
| `gradient` | `LinearGradient \| RadialGradient \| None` | `None` | Gradient fill. See [Enums & Gradients](enums.md). |
| `image` | `str \| None` | `None` | Local file path or remote URL. |
| `opacity` | `float` | `1.0` | Layer opacity from `0.0` (transparent) to `1.0` (opaque). |
| `blend_mode` | `str \| BlendMode \| None` | `None` | How this layer composites over previous layers. See [BlendMode](enums.md#blendmode). |
| `fit` | `str \| FitMode \| None` | `None` | How an image fills the canvas. See [FitMode](enums.md#fitmode). |
| `effects` | `list \| None` | `[]` | Background effects. Accepts `Filter` and `Grain`. |

## Examples

### Solid color

```python
canvas.background(color="#0F172A")
```

### Gradient overlay

```python
from quickthumb import LinearGradient

canvas.background(
    gradient=LinearGradient(
        angle=120,
        stops=[("#111827", 0.0), ("#11182700", 1.0)],
    ),
    opacity=0.7,
)
```

### Remote image with effects

```python
from quickthumb import Filter

canvas.background(
    image="https://images.unsplash.com/photo-1516321318423-f06f85e504b3",
    fit="cover",
    blend_mode="multiply",
    effects=[Filter(blur=4, brightness=0.75, contrast=1.1, saturation=0.9)],
)
```

### Dark overlay

```python
canvas.background(color="#000000", opacity=0.4)
```

## Notes

- Background layers always cover the entire canvas.
- `color`, `gradient`, and `image` can each be used independently or together within one layer.
- `blend_mode` applies when compositing this layer over previous layers.
- Supports both local file paths and remote URLs for `image`.
- For available effects, see [Filter](effects.md#filter) and [Grain](effects.md#grain).
