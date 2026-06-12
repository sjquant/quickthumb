---
description: Reference for quickthumb SVG layers — rasterize icons and logos at render time with sizing, alignment, blend modes, and effects.
---

# SVG

`.svg()` adds an SVG overlay layer, rasterized at render time. Use it for icons, logos, and vector decorations that should stay crisp at any output size.

!!! note "Optional dependency"
    SVG layers require the `svg` extra ([cairosvg](https://cairosvg.org/)):

    ```bash
    pip install "quickthumb[svg]"
    ```

    Rendering a canvas with an `svg` layer without it raises `RenderingError`.

## Signature

```python
canvas.svg(
    path,
    position,
    width=None,
    height=None,
    opacity=1.0,
    rotation=0.0,
    align=Align.TOP_LEFT,
    effects=None,
    blend_mode=None,
)
```

## Parameters

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `path` | `str` | **required** | Local file path or URL to the SVG document. |
| `position` | `tuple` | **required** | `(x, y)` position. Values can be integers (px) or percentage strings (`"50%"`). |
| `width` | `int \| None` | `None` | Output raster width in pixels. Aspect ratio is preserved if `height` is omitted. |
| `height` | `int \| None` | `None` | Output raster height in pixels. Aspect ratio is preserved if `width` is omitted. |
| `opacity` | `float` | `1.0` | Layer opacity from `0.0` to `1.0`. |
| `rotation` | `float` | `0.0` | Rotation in degrees. |
| `align` | `str \| Align \| tuple` | `Align.TOP_LEFT` | Which point of the layer the `position` refers to. See [Align](enums.md#align). |
| `effects` | `list \| None` | `[]` | Same effects as image layers: `Stroke`, `Shadow`, `Glow`, `Filter`. |
| `blend_mode` | `str \| BlendMode \| None` | `None` | Blend mode for compositing onto prior layers. |

The SVG is rasterized at the requested size — not scaled from a fixed-size bitmap — so logos stay sharp even when rendered large.

## Examples

### Logo in a corner

```python
canvas.svg(
    path="logo.svg",
    position=("95%", "6%"),
    width=120,
    align=("right", "top"),
)
```

### Decorative element with rotation and opacity

```python
canvas.svg(
    path="assets/images/spark.svg",
    position=("70%", "20%"),
    width=44,
    align=("center", "middle"),
    rotation=20,
    opacity=0.8,
)
```

### Remote SVG with a shadow

```python
from quickthumb import Shadow

canvas.svg(
    path="https://example.com/badge.svg",
    position=("50%", "85%"),
    width=200,
    align=("center", "middle"),
    effects=[Shadow(offset_x=0, offset_y=8, color="#000000", blur_radius=16)],
)
```

## Validation rules

- `path` and `position` are required.
- `position` must be a 2-item tuple. Percentage strings must match `-?N%`.
- `opacity` must be between `0.0` and `1.0`.
- Rendering without `quickthumb[svg]` installed raises `RenderingError`.
