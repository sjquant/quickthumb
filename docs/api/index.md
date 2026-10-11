---
description: Explore the quickthumb API reference for Canvas, layers, backgrounds, text, images, shapes, outlines, effects, enums, and gradients.
---

# API Reference

Every class, method, and parameter in quickthumb, one page per layer type.

## Public imports

```python
from quickthumb import (
    Align,
    Background,
    BlendMode,
    Canvas,
    ChartData,
    BarChartStyle,
    LineChartStyle,
    Deck,
    Diagnostic,
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
| [Canvas](canvas.md) | Creating a canvas, every layer method, checks, and export methods |
| [Deck](deck.md) | Several canvases as one PDF, PPTX, HTML slideshow, video, or image sequence |
| [Background](background.md) | `.background()`: colors, gradients, and images |
| [Text](text.md) | `.text()` and `TextPart`: text and rich text |
| [Image](image.md) | `.image()`: placed images and cut-outs |
| [Shape](shape.md) | `.shape()`: rectangles, ellipses, pills, triangles, stars, polygons |
| [SVG](svg.md) | `.svg()`: icons and logos from SVG files |
| [Video](video.md) | `.video()`: video clips, captions, and audio |
| [Group](group.md) | `.group()`: auto-layout rows and columns |
| [Outline](outline.md) | `.outline()`: a border around the canvas |
| [Data visualizations](data-visualizations.md) | `.chart()` and `.qr_code()` |
| [Effects](effects.md) | `Stroke`, `Shadow`, `Glow`, `Filter`, `Background`, `Grain`, `Duotone`, `InnerShadow`, `BackdropBlur` |
| [Enums & Gradients](enums.md) | `Align`, `BlendMode`, `FitMode`, `LinearGradient`, `RadialGradient`, `TextFillImage` |

## Error types

| Exception | When raised |
| --- | --- |
| `ValidationError` | Invalid arguments passed to a layer builder (raised immediately) |
| `RenderingError` | Failure during `.render()`, `.to_base64()`, or `.to_data_url()` |
