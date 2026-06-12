---
description: Reference for quickthumb shape layers, including rectangles, ellipses, pills, triangles, stars, polygons, strokes, shadows, and positioning.
---

# Shape

`.shape()` adds a positioned shape primitive: rectangle, ellipse, pill, triangle, star, or polygon.

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
    points=None,
    star_points=5,
    inner_radius=0.5,
    effects=None,
)
```

## Parameters

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `shape` | `str` | **required** | Shape type: `"rectangle"`, `"ellipse"`, `"pill"`, `"triangle"`, `"star"`, or `"polygon"`. |
| `position` | `tuple` | **required** | `(x, y)` position. Values can be integers (px) or percentage strings (`"50%"`). |
| `width` | `int` | **required** | Shape width in pixels. Positive integer. |
| `height` | `int` | **required** | Shape height in pixels. Positive integer. |
| `color` | `str` | **required** | Fill color. Hex string (`"#RRGGBB"` or `"#RRGGBBAA"`). |
| `border_radius` | `int` | `0` | Corner rounding in pixels. Only applies to `"rectangle"`. Non-negative integer. |
| `opacity` | `float` | `1.0` | Layer opacity from `0.0` to `1.0`. |
| `rotation` | `float` | `0.0` | Rotation in degrees. |
| `align` | `str \| Align \| tuple \| None` | `None` | Which point of the shape the `position` refers to. See [Align](enums.md#align). |
| `points` | `list[tuple[float, float]] \| None` | `None` | Vertices for `"polygon"` shapes, normalized `0.0`–`1.0` within the shape box. At least 3 points. |
| `star_points` | `int` | `5` | Number of star spikes. Only applies to `"star"`. Minimum 3. |
| `inner_radius` | `float` | `0.5` | Inner-to-outer radius ratio for `"star"`, strictly between `0.0` and `1.0`. |
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

### Pill

A capsule shape — a rectangle with fully rounded ends. No `border_radius` needed.

```python
canvas.shape(
    shape="pill",
    position=(64, 60),
    width=220,
    height=56,
    color="#B8FF00",
)
```

### Triangle

An isosceles triangle pointing up, inscribed in the `width` × `height` box. Use `rotation` to point it another way.

```python
canvas.shape(
    shape="triangle",
    position=("50%", "20%"),
    width=140,
    height=120,
    color="#F59E0B",
    align=("center", "middle"),
    rotation=180,   # point down
)
```

### Star

`star_points` sets the number of spikes; `inner_radius` controls how sharp they are (smaller = pointier).

```python
from quickthumb import Glow

canvas.shape(
    shape="star",
    position=("80%", "50%"),
    width=280,
    height=280,
    color="#7C5CFF",
    align=("center", "middle"),
    rotation=12,
    star_points=5,
    inner_radius=0.45,
    effects=[Glow(color="#7C5CFF", radius=40, opacity=0.5)],
)
```

### Polygon

Arbitrary vertices, normalized to the shape box: `(0.0, 0.0)` is the box's top-left corner and `(1.0, 1.0)` its bottom-right.

```python
# A right-pointing arrow
canvas.shape(
    shape="polygon",
    position=(600, 60),
    width=160,
    height=100,
    color="#53BF9D",
    points=[
        (0.0, 0.25), (0.6, 0.25), (0.6, 0.0),
        (1.0, 0.5),
        (0.6, 1.0), (0.6, 0.75), (0.0, 0.75),
    ],
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
- `points` is required for `"polygon"` and rejected for any other shape. It needs at least 3 entries, each normalized between `0.0` and `1.0`.
- `star_points` must be at least 3; `inner_radius` must be strictly between `0.0` and `1.0`.
