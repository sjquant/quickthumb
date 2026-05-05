---
description: Reference for quickthumb image layers, including local and remote images, fit modes, positioning, masking, effects, and background removal.
---

# Image

`.image()` adds a positioned overlay image. Supports local files, remote URLs, background removal, fit modes, blend modes, and effects.

## Signature

```python
canvas.image(
    path,
    position,
    width=None,
    height=None,
    fit=None,
    opacity=1.0,
    rotation=0.0,
    align=Align.TOP_LEFT,
    remove_background=False,
    border_radius=0,
    blend_mode=None,
    effects=None,
)
```

## Parameters

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `path` | `str` | **required** | Local file path or remote `http(s)://` URL. |
| `position` | `tuple` | **required** | `(x, y)` position. Values can be integers (px) or percentage strings (`"50%"`). |
| `width` | `int \| None` | `None` | Target width in pixels. If only one dimension is given, aspect ratio is preserved. |
| `height` | `int \| None` | `None` | Target height in pixels. If only one dimension is given, aspect ratio is preserved. |
| `fit` | `str \| FitMode \| None` | `None` | How the image is scaled when both `width` and `height` are set. See [FitMode](enums.md#fitmode). |
| `opacity` | `float` | `1.0` | Layer opacity from `0.0` to `1.0`. |
| `rotation` | `float` | `0.0` | Rotation in degrees. |
| `align` | `str \| Align \| tuple` | `Align.TOP_LEFT` | Which point of the image the `position` refers to. See [Align](enums.md#align). |
| `remove_background` | `bool` | `False` | Remove the image background using AI. Requires `quickthumb[rembg]`. |
| `border_radius` | `int` | `0` | Corner rounding in pixels. Non-negative integer. |
| `blend_mode` | `str \| BlendMode \| None` | `None` | Compositing blend mode. See [BlendMode](enums.md#blendmode). |
| `effects` | `list \| None` | `[]` | List of effects: `Stroke`, `Shadow`, `Glow`, `Filter`, `Grain`. |

## Examples

### Basic overlay

```python
canvas.image(
    path="portrait.png",
    position=("74%", "54%"),
    width=420,
    height=520,
    fit="cover",
    align=("center", "middle"),
)
```

### With effects

```python
from quickthumb import Filter, Shadow

canvas.image(
    path="portrait.png",
    position=("74%", "54%"),
    width=420,
    height=520,
    fit="cover",
    align=("center", "middle"),
    border_radius=28,
    effects=[
        Filter(contrast=1.1, saturation=1.05),
        Shadow(offset_x=0, offset_y=12, color="#000000", blur_radius=24),
    ],
)
```

### Background removal

```python
canvas.image(
    path="portrait.jpg",
    position=("75%", "55%"),
    width=430,
    height=540,
    align=("center", "middle"),
    remove_background=True,
)
```

!!! note
    `remove_background=True` requires `uv pip install "quickthumb[rembg]"`. The ONNX model (~170 MB) is downloaded and cached on first use.

### Remote image

```python
canvas.image(
    path="https://example.com/avatar.png",
    position=("50%", "50%"),
    width=300,
    height=300,
    align=("center", "middle"),
    border_radius=150,  # circle
)
```

### Preserve aspect ratio

```python
# Only set width — height is calculated to preserve ratio
canvas.image(path="logo.png", position=(40, 40), width=200)

# Only set height — width is calculated to preserve ratio
canvas.image(path="logo.png", position=(40, 40), height=80)
```

## Fit modes

`fit` applies when both `width` and `height` are set:

| Value | Behavior |
| --- | --- |
| `"cover"` | Fill the box, cropping if needed |
| `"contain"` | Fit entirely inside the box with empty space at edges |
| `"fill"` | Stretch to fill the box exactly, ignoring aspect ratio |

## Validation rules

- `path` and `position` are required.
- `position` must be a 2-item tuple. Percentage strings must match `-?N%`.
- `border_radius` cannot be negative.
- `opacity` must be between `0.0` and `1.0`.
- Invalid `path` values or failed remote downloads raise `RenderingError` at render time.
