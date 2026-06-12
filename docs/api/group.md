---
description: Reference for quickthumb group layers — auto-layout rows and columns with gap, padding, item alignment, and nesting.
---

# Group (Auto Layout)

`.group()` adds an auto-layout container that measures its children and stacks them along a row or column — no hand-placed coordinates. Because the group recomputes positions from each child's natural size, the same spec keeps working when headline copy gets longer or a badge is added, which makes groups especially reliable for LLM-generated layouts.

## Signature

```python
canvas.group(
    children,
    direction="column",
    gap=0,
    padding=0,
    position=None,
    align=None,
    item_align="start",
)
```

## Parameters

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `children` | `list` | **required** | Child layers in stacking order. Dicts or layer models of type `text`, `image`, `shape`, `svg`, or nested `group`. |
| `direction` | `str` | `"column"` | Main axis: `"column"` stacks top-to-bottom, `"row"` left-to-right. |
| `gap` | `int` | `0` | Pixels between adjacent children along the main axis. Non-negative. |
| `padding` | `int \| tuple` | `0` | Inner padding: a single int, `(vertical, horizontal)`, or `(top, right, bottom, left)`. |
| `position` | `tuple \| None` | `None` | Anchor point of the group box, in pixels or percentage strings. |
| `align` | `str \| Align \| tuple \| None` | `None` | Which point of the group box the `position` refers to, like image layers. See [Align](enums.md#align). |
| `item_align` | `str` | `"start"` | Cross-axis placement of each child: `"start"`, `"center"`, or `"end"`. |

!!! warning "Children must not set `position`"
    The group assigns positions. A child that sets its own `position` raises `ValidationError`, and a child's `align` is ignored — use `item_align` on the group instead.

## Examples

### Stacked headline block

```python
canvas = Canvas(1280, 720).background(color="#16213E").group(
    children=[
        {"type": "shape", "shape": "pill", "width": 120, "height": 36, "color": "#E94560"},
        {"type": "text", "content": "AUTO LAYOUT", "size": 96, "color": "#FFFFFF", "weight": 900},
        {"type": "text", "content": "No coordinates were harmed", "size": 40, "color": "#A2A8D3"},
    ],
    direction="column",
    gap=24,
    position=("8%", "50%"),
    align=("left", "middle"),
)
```

### Horizontal badge row

```python
def chip(label):
    return {
        "type": "text",
        "content": label,
        "size": 24,
        "color": "#22D3EE",
        "weight": 700,
        "effects": [
            {"type": "background", "color": "#1D2547", "padding": [8, 14], "border_radius": 18},
        ],
    }

canvas.group(
    children=[chip("GROUPS"), chip("TOKENS"), chip("LINT")],
    direction="row",
    gap=14,
    position=("50%", "88%"),
    align=("center", "middle"),
)
```

### Nested groups

Groups can nest, so a column can contain a row (and vice versa):

```python
canvas.group(
    children=[
        {"type": "text", "content": "RELEASE 0.5", "size": 96, "color": "#FFFFFF", "weight": 900},
        {
            "type": "group",
            "direction": "row",
            "gap": 14,
            "children": [chip("GROUPS"), chip("TOKENS"), chip("LINT")],
        },
    ],
    direction="column",
    gap=28,
    position=("7%", "50%"),
    align=("left", "middle"),
)
```

### Cross-axis alignment

```python
canvas.group(
    children=[
        {"type": "text", "content": "CENTERED", "size": 80, "color": "#FFFFFF", "weight": 900},
        {"type": "text", "content": "Both children share a center line", "size": 36, "color": "#A2A8D3"},
    ],
    direction="column",
    gap=18,
    item_align="center",            # cross-axis: center each child horizontally
    position=("50%", "50%"),
    align=("center", "middle"),
)
```

## How sizing works

1. Each child is measured at its natural size (text bounds, image dimensions, shape `width`/`height`).
2. Children are placed one after another along the main axis, separated by `gap`.
3. The group box is the union of the children plus `padding`.
4. The whole box is anchored to `position` according to `align`.

## JSON form

Groups serialize like any other layer. See the [JSON Schema page](../json-schema.md#group-layer) for the full schema:

```json
{
  "type": "group",
  "direction": "column",
  "gap": 24,
  "position": ["8%", "50%"],
  "align": ["left", "middle"],
  "item_align": "start",
  "children": [
    { "type": "text", "content": "AUTO LAYOUT", "size": 96, "color": "#FFFFFF", "weight": 900 }
  ]
}
```

## Validation rules

- `children` must be a non-empty list.
- Children must not set `position` (the group assigns positions).
- Valid child types: `text`, `image`, `shape`, `svg`, `group`.
- `gap` cannot be negative; `padding` values cannot be negative, and a padding tuple must have 2 or 4 elements.
