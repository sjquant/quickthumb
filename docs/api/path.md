---
description: Draw filled polygonal SVG paths with a fixed local viewport and explicit document-format fallbacks.
---

# Path

`Canvas.path()` draws static, filled polygonal SVG path data without an SVG
file or an optional rendering dependency:

```python
from quickthumb import Canvas

canvas = Canvas(160, 120).path(
    "M 0 0 H 100 V 100 H 0 Z M 25 25 H 75 V 75 H 25 Z",
    position=(20, 10), width=120, height=100,
    view_box=(0, 0, 100, 100), color="#42CEB7", id="frame",
)
canvas.export("path.png")
```

| Parameter | Meaning |
| --- | --- |
| `d` | SVG `M/L/H/V/Z` commands, absolute or relative. Repeated coordinate pairs and implicit closing for fills are supported. Other commands are rejected. |
| `position` | Required frame position in canvas pixels or percentages. |
| `width`, `height` | Required positive frame dimensions in pixels. |
| `view_box` | Optional `(x, y, width, height)` local coordinate window; defaults to `(0, 0, width, height)`. Its width and height must be positive. |
| `color` | Flat fill color, default black; `None` paints nothing. |
| `id`, `motion_key` | Optional scene identity and cross-scene matching key, using the common layer identity rules. |

The local window maps independently onto the frame's width and height and is
clipped at its edges. The frame does not fit itself to changing path bounds.
Inspection reports that fixed frame. The fill uses the **even-odd** rule: an odd
number of boundary crossings paints, so nested contours make holes regardless
of their direction. Raster drawing supersamples only the visible painted bounds
at 4× and downsamples with antialiasing.

This initial path surface supports flat filled polygons. Curves, strokes,
gradients, layer animation, parent links, grouping and composition controls are
not accepted yet. JSON uses `type="path"` and round-trips through `PathLayer`.

PNG and canonical samples draw the path directly. SVG, HTML, PDF and PPTX currently
embed a static raster image; `validate_export()` and `ExportResult` report the
fallback. A strict `ExportPolicy(unsupported_motion="error")` rejects that output
before writing.
