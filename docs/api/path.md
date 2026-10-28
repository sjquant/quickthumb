---
description: Draw filled and stroked SVG paths with a local viewBox, gradients, dashes, and path animations.
---

# Path

`Canvas.path()` draws filled or stroked vector paths using standard SVG path data (`d`), without requiring an external SVG file or extra dependencies:

```python
from quickthumb import Canvas

canvas = Canvas(160, 120).path(
    "M 0 0 H 100 V 100 H 0 Z M 25 25 H 75 V 75 H 25 Z",
    position=(20, 10),
    width=120,
    height=100,
    view_box=(0, 0, 100, 100),
    color="#42CEB7",
)
canvas.export("path.png")
```

## Parameters

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `d` | `str` | **required** | SVG path commands (`M`, `L`, `H`, `V`, `C`, `S`, `Q`, `T`, `A`, `Z`). |
| `position` | `tuple` | **required** | `(x, y)` position in pixels or percentage strings (`"50%"`). |
| `width` | `int` | **required** | Frame width in pixels. |
| `height` | `int` | **required** | Frame height in pixels. |
| `view_box` | `tuple \| None` | `None` | Local coordinate window `(x, y, width, height)`. Defaults to `(0, 0, width, height)`. |
| `color` | `str \| None` | `"#000000"` | Flat fill color. Set to `None` for stroke-only paths. |
| `fill` | `LinearGradient \| RadialGradient \| None` | `None` | Gradient fill. Replaces `color` when provided. |
| `stroke` | `str \| None` | `None` | Stroke color (hex string). |
| `stroke_width` | `int \| float` | `1` | Stroke thickness in local units. |
| `line_cap` | `str` | `"butt"` | Endpoint style: `"butt"`, `"round"`, or `"square"`. |
| `line_join` | `str` | `"miter"` | Corner join style: `"miter"`, `"bevel"`, or `"round"`. |
| `miter_limit` | `float` | `4` | Maximum miter ratio before switching to bevel. |
| `dash_array` | `tuple \| None` | `None` | Dash pattern tuple of lengths `(dash, gap, ...)`. |
| `dash_offset` | `float` | `0` | Starting phase offset into the dash pattern. |
| `rotation` | `float` | `0.0` | Rotation in degrees. |
| `opacity` | `float` | `1.0` | Layer opacity from `0.0` to `1.0`. |
| `anchor` | `tuple` | `(0.5, 0.5)` | Normalized pivot point for rotation and scaling. |
| `animation` | `AnimationSpec \| None` | `None` | Timeline animation for motion, trim, dash phase, or morphing. |

## Examples

### Stroked curves with dashed outline

```python
canvas.path(
    "M10 50 C30 0 70 100 90 50",
    position=(20, 10),
    width=120,
    height=100,
    color=None,
    stroke="#42CEB7",
    stroke_width=6,
    line_cap="round",
    view_box=(0, 0, 100, 100),
    dash_array=(12, 6),
    dash_offset=3,
)
```

### Gradient fill with cutouts

Paths use the **even-odd fill rule**: overlapping internal contours naturally create cutouts or holes.

```python
from quickthumb import LinearGradient

canvas.path(
    "M10 10 H90 V90 H10 Z M30 30 H70 V70 H30 Z",
    position=(20, 10),
    width=120,
    height=100,
    color=None,
    fill=LinearGradient(angle=45, stops=[("#42CEB7", 0), ("#315D8E", 1)]),
    view_box=(0, 0, 100, 100),
)
```

## Path Animations

### Animated dash phase (Marching ants)

Animate `DashOffsetTrack` to create a crawling dashed-line effect:

```python
from quickthumb import AnimationSpec, DashOffsetTrack, KeyframeSpec, TimingSpec

phase_animation = AnimationSpec.timeline(
    DashOffsetTrack(keyframes=[
        KeyframeSpec(time=0, value=0),
        KeyframeSpec(time=1, value=20),
    ]),
    timing=TimingSpec(duration=1),
    easing="linear",
)

canvas.path(
    "M0 10 H100",
    position=(10, 10),
    width=200,
    height=20,
    color=None,
    stroke="#42CEB7",
    dash_array=(6, 4),
    animation=phase_animation,
)
```

### Stroke trim (Self-drawing line)

Use `TrimEndTrack` to progressively draw a line or outline from start to finish:

```python
from quickthumb import AnimationSpec, KeyframeSpec, TimingSpec, TrimEndTrack

draw_outline = AnimationSpec.timeline(
    TrimEndTrack(keyframes=[
        KeyframeSpec(time=0, value=0.0),
        KeyframeSpec(time=1.5, value=1.0),
    ]),
    timing=TimingSpec(duration=1.5),
    easing="ease_in_out",
)

canvas.path(
    "M0 20 Q50 -10 100 20",
    position=(20, 20),
    width=200,
    height=60,
    view_box=(0, -10, 100, 30),
    color=None,
    stroke="#42CEB7",
    stroke_width=4,
    animation=draw_outline,
)
```

- `TrimStartTrack` and `TrimEndTrack`: Normalized endpoints (`0.0` to `1.0`) along the path's total length.
- `TrimOffsetTrack`: Shifts the trimmed interval along the path.

### Path morphing

Smoothly transform one vector shape into another using `PathMorphTrack`:

```python
from quickthumb import AnimationSpec, KeyframeSpec, PathMorphTrack, TimingSpec

morph = AnimationSpec.timeline(
    PathMorphTrack(keyframes=[
        KeyframeSpec(time=0, value="M10 10 H50 V50 H10 Z"),
        KeyframeSpec(time=1, value="M20 20 H60 V60 H20 Z"),
    ]),
    timing=TimingSpec(duration=1),
    easing="ease_in_out",
)

canvas.path(
    "M10 10 H50 V50 H10 Z",
    position=(10, 10),
    width=100,
    height=100,
    color="#42CEB7",
    animation=morph,
)
```

For smooth morphing, both keyframes should have a matching number of non-intersecting contours.

## Export Support

- **Raster & Video (PNG, GIF, MP4, WebM)**: Render paths, dashes, trims, and morph animations.
- **Lottie**: Export supported [path morph animations](../reference/export-lottie.md#lottie-path-morph) as vectors.
- **HTML**: Native SVG rendering with CSS stroke animations for supported open paths. Morph animations use the authored still image.
- **PDF & PPTX**: Export supported paths as vectors; morph animations use the authored still image.
