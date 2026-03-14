# Enums & Gradients

## Align

Controls which point of a layer the `position` coordinate refers to, and the horizontal alignment of text.

```python
from quickthumb import Align
```

### Values

| Enum | String alias | Horizontal | Vertical |
| --- | --- | --- | --- |
| `Align.CENTER` | `"center"` | center | middle |
| `Align.LEFT` | `"left"` | left | middle |
| `Align.RIGHT` | `"right"` | right | middle |
| `Align.TOP_LEFT` | `"top-left"` | left | top |
| `Align.TOP_CENTER` | `"top-center"` | center | top |
| `Align.TOP_RIGHT` | `"top-right"` | right | top |
| `Align.BOTTOM_LEFT` | `"bottom-left"` | left | bottom |
| `Align.BOTTOM_CENTER` | `"bottom-center"` | center | bottom |
| `Align.BOTTOM_RIGHT` | `"bottom-right"` | right | bottom |

### Usage

```python
# Enum value
canvas.image(..., align=Align.TOP_LEFT)

# String alias
canvas.image(..., align="center")

# (horizontal, vertical) tuple
canvas.image(..., align=("center", "middle"))
```

Horizontal tuple values: `"left"`, `"center"`, `"right"`
Vertical tuple values: `"top"`, `"middle"`, `"bottom"`

---

## BlendMode

Controls how a layer composites over the layers drawn before it.

```python
from quickthumb import BlendMode
```

### Values

| Enum | String alias | Effect |
| --- | --- | --- |
| `BlendMode.NORMAL` | `"normal"` | No blending — layer drawn on top |
| `BlendMode.MULTIPLY` | `"multiply"` | Darkens by multiplying color values |
| `BlendMode.OVERLAY` | `"overlay"` | Combines multiply and screen |
| `BlendMode.SCREEN` | `"screen"` | Lightens by inverting, multiplying, and inverting again |
| `BlendMode.DARKEN` | `"darken"` | Takes the darker of each pixel |
| `BlendMode.LIGHTEN` | `"lighten"` | Takes the lighter of each pixel |

### Usage

```python
# Enum value
canvas.background(image="texture.jpg", blend_mode=BlendMode.MULTIPLY)

# String alias
canvas.background(image="texture.jpg", blend_mode="multiply")
```

Available on: `.background()` and `.image()`.

---

## FitMode

Controls how an image is scaled when a target size box is defined.

```python
from quickthumb import FitMode
```

### Values

| Enum | String alias | Behavior |
| --- | --- | --- |
| `FitMode.COVER` | `"cover"` | Fill the box, cropping any overflow |
| `FitMode.CONTAIN` | `"contain"` | Fit entirely inside the box; letterbox the rest |
| `FitMode.FILL` | `"fill"` | Stretch to fill the box exactly (ignores aspect ratio) |

### Usage

```python
# Enum value
canvas.image(path="portrait.png", position=("75%", "55%"), width=420, height=520, fit=FitMode.COVER)

# String alias
canvas.image(path="portrait.png", position=("75%", "55%"), width=420, height=520, fit="cover")
```

Available on: `.background(image=...)` and `.image()`. Only applies when both `width` and `height` define a target box (or for background layers, the full canvas).

---

## LinearGradient

A linear color gradient defined by an angle and color stops.

```python
from quickthumb import LinearGradient

LinearGradient(
    angle=135,
    stops=[("#FF5733", 0.0), ("#3333FF", 1.0)],
)
```

| Parameter | Type | Description |
| --- | --- | --- |
| `angle` | `float` | Gradient direction in degrees. `0` = top to bottom, `90` = left to right. |
| `stops` | `list[tuple[str, float]]` | List of `(color, position)` tuples. Position is a float from `0.0` to `1.0`. |

### Examples

```python
# Top-to-bottom dark fade
LinearGradient(angle=0, stops=[("#000000", 0.0), ("#00000000", 1.0)])

# Diagonal blue-to-purple
LinearGradient(angle=135, stops=[("#3B82F6", 0.0), ("#8B5CF6", 1.0)])

# Three-stop gradient
LinearGradient(
    angle=90,
    stops=[("#FF0000", 0.0), ("#00FF00", 0.5), ("#0000FF", 1.0)],
)
```

Pass to `.background(gradient=...)`:

```python
canvas.background(
    gradient=LinearGradient(angle=120, stops=[("#0F172A", 0.0), ("#0F172A00", 1.0)]),
    opacity=0.8,
)
```

---

## RadialGradient

A radial color gradient emanating from a center point.

```python
from quickthumb import RadialGradient

RadialGradient(
    stops=[("#FF5733", 0.0), ("#3333FF", 1.0)],
    center=(0.5, 0.5),
)
```

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `stops` | `list[tuple[str, float]]` | **required** | List of `(color, position)` tuples. Position is a float from `0.0` to `1.0`. |
| `center` | `tuple[float, float]` | `(0.5, 0.5)` | Center of the gradient as `(x, y)` fractions of the canvas size. |

### Examples

```python
# Vignette (dark edges, bright center)
RadialGradient(
    stops=[("#00000000", 0.0), ("#000000CC", 1.0)],
    center=(0.5, 0.5),
)

# Off-center spotlight
RadialGradient(
    stops=[("#FFFFFF33", 0.0), ("#FFFFFF00", 1.0)],
    center=(0.25, 0.3),
)
```

Pass to `.background(gradient=...)`:

```python
canvas.background(
    gradient=RadialGradient(
        stops=[("#22d3ee33", 0.0), ("#22d3ee00", 1.0)],
        center=(0.5, 0.5),
    ),
)
```
