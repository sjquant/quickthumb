---
description: Reference for QuickThumb outline layers that draw canvas borders with configurable width, color, opacity, and corner radius.
---

# Outline

`.outline()` draws a border around the entire canvas edge. It is typically added as the last layer so it sits on top of all content.

## Signature

```python
canvas.outline(
    width,
    color,
    offset=0,
    opacity=1.0,
)
```

## Parameters

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `width` | `int` | **required** | Border thickness in pixels. Positive integer. |
| `color` | `str` | **required** | Border color. Hex string (`"#RRGGBB"` or `"#RRGGBBAA"`). |
| `offset` | `int` | `0` | Inset distance from the canvas edge in pixels. Non-negative integer. |
| `opacity` | `float` | `1.0` | Layer opacity from `0.0` to `1.0`. |

## Examples

### Basic outline

```python
canvas.outline(width=12, color="#B8FF00")
```

### Inset outline

```python
# Drawn 8px inside the canvas edge
canvas.outline(width=4, color="#FFFFFF", offset=8)
```

### Semi-transparent outline

```python
canvas.outline(width=8, color="#FFFFFF", opacity=0.5)
```

### Typical usage in a full composition

```python
canvas = (
    Canvas(1280, 720)
    .background(color="#0F172A")
    .text(content="TITLE", size=96, color="#FFFFFF", align="center")
    .outline(width=12, color="#22d3ee")  # always last
)
```

## Notes

- The outline is drawn inward from the canvas edge by default (`offset=0`).
- Using a large `offset` with a thin `width` can create a floating frame effect.
- `opacity` must be between `0.0` and `1.0`.
