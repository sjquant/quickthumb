---
description: Reference for deterministic bar chart, line chart, and QR code layers.
---

# Data visualizations

quickthumb includes three compact, deterministic visualization layers for dashboards,
cards, and generated social graphics. They share `ChartData` and `ChartStyle` primitives;
they are intentionally not a general-purpose plotting system.

```python
from quickthumb import Canvas, ChartStyle

canvas = (
    Canvas(800, 400)
    .bar_chart(
        [-4, 8, 12, 6],
        position=(40, 40),
        width=220,
        height=120,
        style=ChartStyle(color="#2563EB", negative_color="#DC2626"),
    )
    .line_chart(
        [2, 5, 3, 7],
        position=(40, 200),
        width=440,
        height=120,
        color="#7C3AED",
        fill="#DDD6FE",
    )
    .qr_code("https://example.com", position=(620, 40), size=140)
)
```

## Shared chart data and style

`ChartData(values=[...])` is useful when a generated spec wants a named data
object; builders and JSON also accept a plain numeric list. Empty, constant, and
negative series are valid. Values must be finite numbers, so `NaN`, infinity, and
non-numeric values raise `ValidationError`.

`ChartStyle` accepts `color`, `padding`, and `opacity` as shared options. Bar charts
also accept `negative_color` and `bar_gap`; line charts accept `fill`, `fill_opacity`,
`stroke_width`, `point_radius`, and `show_points`. Passing an option that has no
meaning for the selected chart type raises `ValidationError` instead of silently
changing nothing. The same supported fields can be passed directly to a builder.

Line chart values are scaled to the plot box. Constant series sit on the
vertical midpoint. Bar charts always include zero in their range, so positive and
negative values render on opposite sides of the baseline. Empty series render no
pixels.

## Layer builders

| Builder | JSON type | Purpose |
| --- | --- | --- |
| `.bar_chart(data, position, width, height)` | `bar_chart` | Vertical bars with a zero-aware baseline |
| `.line_chart(data, position, width, height)` | `line_chart` | Line chart with point markers by default |
| `.qr_code(data, position, size)` | `qr_code` | Square QR code with explicit error correction and quiet zone |

All chart builders accept pixel or percentage positions, `align`, `opacity`,
and the existing `clip` and `mask` composition primitives. Chart layers can also
be used as group children; the group assigns their positions automatically. QR codes accept
`foreground`, `background`, `error_correction` (`L`, `M`, `Q`, or `H`), and
`quiet_zone`. QR rendering raises `RenderingError` when the requested square is
too small to preserve the generated QR module matrix. Charts and QR codes also
accept the existing layer-level `animation` contract for PPTX and GIF/video
exports; omitting it keeps the deterministic static behavior.

Chart and QR layers serialize through `Canvas.to_json()`, validate through
`Canvas.from_json()`, and appear in `quickthumb schema`. SVG, HTML, PDF, and
PPTX exports preserve them through the standard pixel-exact raster fallback.
