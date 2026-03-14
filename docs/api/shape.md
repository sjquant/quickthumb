# Shape

`.shape()` adds a positioned rectangle or ellipse.

## Signature

```python
canvas.shape(
    shape,
    position,
    width,
    height,
    color,
    border_radius=0,
    opacity=1.0,
    rotation=0.0,
    align=None,
    effects=None,
)
```

## Parameters

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `shape` | `str` | **required** | Shape type: `"rectangle"` or `"ellipse"`. |
| `position` | `tuple` | **required** | `(x, y)` position. Values can be integers (px) or percentage strings (`"50%"`). |
| `width` | `int` | **required** | Shape width in pixels. Positive integer. |
| `height` | `int` | **required** | Shape height in pixels. Positive integer. |
| `color` | `str` | **required** | Fill color. Hex string (`"#RRGGBB"` or `"#RRGGBBAA"`). |
| `border_radius` | `int` | `0` | Corner rounding in pixels. Only applies to `"rectangle"`. Non-negative integer. |
| `opacity` | `float` | `1.0` | Layer opacity from `0.0` to `1.0`. |
| `rotation` | `float` | `0.0` | Rotation in degrees. |
| `align` | `str \| Align \| tuple \| None` | `None` | Which point of the shape the `position` refers to. See [Align](enums.md#align). |
| `effects` | `list \| None` | `[]` | List of effects: `Stroke`, `Shadow`, `Glow`. |

## Examples

### Label rectangle

```python
from quickthumb import Shadow, Stroke

canvas.shape(
    shape="rectangle",
    position=(64, 64),
    width=320,
    height=96,
    color="#CC0000",
    border_radius=14,
    effects=[
        Stroke(width=3, color="#FFFFFF"),
        Shadow(offset_x=0, offset_y=10, color="#000000", blur_radius=18),
    ],
)
```

### Rotated badge

```python
canvas.shape(
    shape="rectangle",
    position=(64, 64),
    width=360,
    height=120,
    color="#CC0000",
    border_radius=16,
    opacity=0.95,
    rotation=-4,
    align=("left", "top"),
)
```

### Ellipse / circle

```python
# Circle: set width == height
canvas.shape(
    shape="ellipse",
    position=("50%", "50%"),
    width=200,
    height=200,
    color="#22d3ee",
    align=("center", "middle"),
)
```

### Centered shape with glow

```python
from quickthumb import Glow

canvas.shape(
    shape="rectangle",
    position=("50%", "80%"),
    width=480,
    height=72,
    color="#111827",
    border_radius=36,
    align=("center", "middle"),
    effects=[Glow(color="#22d3ee", radius=24, opacity=0.4)],
)
```

## Validation rules

- `shape`, `position`, `width`, `height`, and `color` are required.
- `position` must be a 2-item tuple. Percentage strings must match `-?N%`.
- `border_radius` cannot be negative.
- `opacity` must be between `0.0` and `1.0`.
