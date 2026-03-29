# API Reference

Complete reference for every class, method, and parameter in QuickThumb.

## Public imports

```python
from quickthumb import (
    Align,
    Background,
    BlendMode,
    Canvas,
    Filter,
    FitMode,
    Glow,
    Grain,
    LinearGradient,
    RadialGradient,
    Shadow,
    Stroke,
    TextFillImage,
    TextPart,
    ValidationError,
)
```

## Pages

| Page | What it covers |
| --- | --- |
| [Canvas](canvas.md) | `Canvas` creation, layer builders, and export methods |
| [Background](background.md) | `.background()` — solid colors, gradients, and images |
| [Text](text.md) | `.text()` and `TextPart` — text layers and rich text |
| [Image](image.md) | `.image()` — overlay images and cutouts |
| [Shape](shape.md) | `.shape()` — rectangles and ellipses |
| [Outline](outline.md) | `.outline()` — canvas border |
| [Effects](effects.md) | `Stroke`, `Shadow`, `Glow`, `Filter`, `Background`, `Grain` |
| [Enums & Gradients](enums.md) | `Align`, `BlendMode`, `FitMode`, `LinearGradient`, `RadialGradient`, `TextFillImage` |

## Error types

| Exception | When raised |
| --- | --- |
| `ValidationError` | Invalid arguments passed to a layer builder (raised immediately) |
| `RenderingError` | Failure during `.render()`, `.to_base64()`, or `.to_data_url()` |
