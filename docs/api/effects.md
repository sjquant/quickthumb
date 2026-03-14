# Effects

Effects are modifiers applied to layers. Each layer type accepts a specific set.

| Effect | Text | Image | Shape | Background |
| --- | :---: | :---: | :---: | :---: |
| `Stroke` | ✓ | ✓ | ✓ | — |
| `Shadow` | ✓ | ✓ | ✓ | — |
| `Glow` | ✓ | ✓ | ✓ | — |
| `Filter` | — | ✓ | — | ✓ |
| `Background` | ✓ | — | — | — |

Pass effects as a list to the `effects` parameter of any layer:

```python
from quickthumb import Shadow, Stroke

canvas.text(
    content="CLICK NOW",
    size=96,
    color="#FFFFFF",
    effects=[
        Stroke(width=4, color="#000000"),
        Shadow(offset_x=4, offset_y=4, color="#000000", blur_radius=8),
    ],
)
```

---

## Stroke

Draws an outline around text glyphs, image edges, or shape edges.

```python
from quickthumb import Stroke

Stroke(width=4, color="#000000")
```

| Parameter | Type | Description |
| --- | --- | --- |
| `width` | `int` | Stroke thickness in pixels. Positive integer. |
| `color` | `str` | Stroke color. Hex string (`"#RRGGBB"` or `"#RRGGBBAA"`). |

### Example

```python
from quickthumb import Stroke, TextPart

canvas.text(
    content=[
        TextPart(text="BIG TEXT", color="#FFFFFF", effects=[Stroke(width=6, color="#000000")]),
    ],
    size=108,
    position=("8%", "50%"),
    align=("left", "middle"),
)
```

---

## Shadow

Adds a drop shadow offset from the layer.

```python
from quickthumb import Shadow

Shadow(offset_x=4, offset_y=8, color="#000000", blur_radius=12)
```

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `offset_x` | `int` | **required** | Horizontal shadow offset in pixels. Can be negative. |
| `offset_y` | `int` | **required** | Vertical shadow offset in pixels. Can be negative. |
| `color` | `str` | **required** | Shadow color. Hex string. |
| `blur_radius` | `int` | `0` | Blur spread in pixels. Non-negative integer. |

### Example

```python
from quickthumb import Shadow

canvas.image(
    path="portrait.png",
    position=("74%", "54%"),
    width=420,
    height=520,
    effects=[Shadow(offset_x=0, offset_y=14, color="#000000", blur_radius=24)],
)
```

---

## Glow

Adds a soft colored halo around the layer.

```python
from quickthumb import Glow

Glow(color="#B8FF00", radius=16, opacity=0.35)
```

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `color` | `str` | **required** | Glow color. Hex string. |
| `radius` | `int` | **required** | Glow spread radius in pixels. Positive integer. |
| `opacity` | `float` | `1.0` | Glow intensity from `0.0` to `1.0`. |

### Example

```python
from quickthumb import Glow

canvas.text(
    content="ELECTRIC",
    size=96,
    color="#FFFFFF",
    effects=[Glow(color="#22d3ee", radius=24, opacity=0.5)],
)
```

---

## Filter

Applies image processing adjustments. Used on background layers and image layers.

```python
from quickthumb import Filter

Filter(blur=4, brightness=0.75, contrast=1.1, saturation=0.9)
```

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `blur` | `int` | `0` | Gaussian blur radius. Non-negative integer. |
| `brightness` | `float` | `1.0` | Brightness multiplier. Positive float. `1.0` = no change, `0.5` = half brightness. |
| `contrast` | `float` | `1.0` | Contrast multiplier. Positive float. `1.0` = no change. |
| `saturation` | `float` | `1.0` | Saturation multiplier. Non-negative float. `0.0` = grayscale, `1.0` = no change. |

All parameters default to neutral — only set the ones you want to change.

### Example

```python
from quickthumb import Filter

canvas.background(
    image="hero.jpg",
    fit="cover",
    effects=[Filter(blur=6, brightness=0.6, saturation=0.8)],
)
```

---

## Background (text fill)

Draws a filled rounded rectangle behind a text block. Only available on text layers.

```python
from quickthumb import Background

Background(color="#111827CC", padding=(16, 24), border_radius=14, opacity=1.0)
```

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `color` | `str` | **required** | Fill color. Hex string (`"#RRGGBB"` or `"#RRGGBBAA"`). |
| `padding` | `int \| tuple` | `0` | Inner padding. `int` for uniform, `(vertical, horizontal)`, or `(top, right, bottom, left)`. |
| `border_radius` | `int` | `0` | Corner rounding in pixels. Non-negative integer. |
| `opacity` | `float` | `1.0` | Fill opacity from `0.0` to `1.0`. |

### Example

```python
from quickthumb import Background

canvas.text(
    content="BREAKING NEWS",
    size=72,
    color="#FFFFFF",
    position=("8%", "50%"),
    align=("left", "middle"),
    effects=[
        Background(color="#CC0000", padding=(12, 20), border_radius=8),
    ],
)
```

!!! note
    `Background` as an effect is separate from the `.background()` layer builder. The effect applies behind a text block; the layer covers the full canvas.
