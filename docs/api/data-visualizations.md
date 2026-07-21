---
description: Reference for deterministic sparkline, bar chart, line chart, and QR code layers.
---

# Data visualizations

quickthumb includes four compact, deterministic visualization layers for dashboards,
cards, and generated social graphics. They share `ChartData` and `ChartStyle` primitives;
they are intentionally not a general-purpose plotting system.

```python
from quickthumb import Canvas, ChartStyle

canvas = (
    Canvas(800, 400)
    .sparkline([12, 18, 15, 24], position=(40, 40), width=180, height=48)
    .bar_chart(
        [-4, 8, 12, 6],
        position=(260, 40),
        width=220,
        height=120,
        style=ChartStyle(color="#2563EB", negative_color="#DC2626"),
    )
    .line_chart(
        [2, 5, 3, 7],
        position=(40, 160),
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

`ChartStyle` accepts `color`, `negative_color`, `fill`, `fill_opacity`,
`stroke_width`, `point_radius`, `show_points`, `bar_gap`, `padding`, and `opacity`.
The same fields can be passed directly to a chart builder when convenient.

Line and sparkline values are scaled to the plot box. Constant series sit on the
vertical midpoint. Bar charts always include zero in their range, so positive and
negative values render on opposite sides of the baseline. Empty series render no
pixels.

## Layer builders

| Builder | JSON type | Purpose |
| --- | --- | --- |
| `.sparkline(data, position, width, height)` | `sparkline` | Small trend line without point markers by default |
| `.bar_chart(data, position, width, height)` | `bar_chart` | Vertical bars with a zero-aware baseline |
| `.line_chart(data, position, width, height)` | `line_chart` | Line chart with point markers by default |
| `.qr_code(data, position, size)` | `qr_code` | Square QR code with explicit error correction and quiet zone |

All chart builders accept pixel or percentage positions, `align`, `opacity`,
and the existing `clip` and `mask` composition primitives. QR codes accept
`foreground`, `background`, `error_correction` (`L`, `M`, `Q`, or `H`), and
`quiet_zone`.

Chart and QR layers serialize through `Canvas.to_json()`, validate through
`Canvas.from_json()`, and appear in `quickthumb schema`. SVG, HTML, PDF, and
PPTX exports preserve them through the standard pixel-exact raster fallback.
