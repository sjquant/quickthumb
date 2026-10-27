---
description: Draw filled and stroked SVG paths with a fixed local viewport and explicit document-format fallbacks.
---

# Path

`Canvas.path()` draws static, filled or stroked SVG path data without an SVG
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
| `d` | SVG `M/L/H/V/C/S/Q/T/A/Z` commands, absolute or relative. Repeated coordinate sets, compact arc flags and implicit closing for fills are supported. |
| `position` | Required frame position in canvas pixels or percentages. |
| `width`, `height` | Required positive frame dimensions in pixels. |
| `view_box` | Optional `(x, y, width, height)` local coordinate window; defaults to `(0, 0, width, height)`. Its width and height must be positive. |
| `color` | Flat fill color, default black; `None` disables fill. |
| `stroke`, `stroke_width` | Optional solid stroke color and positive width in local units; width defaults to `1`. |
| `line_cap` | `"butt"` (default), `"round"` or `"square"` for open endpoints. |
| `line_join` | `"miter"` (default), `"bevel"` or `"round"` for joined segments. |
| `miter_limit` | Maximum vertex-to-tip distance divided by half the stroke width; defaults to `4`, must be at least `1`. Longer miters become bevels. |
| `id`, `motion_key` | Optional scene identity and cross-scene matching key, using the common layer identity rules. |

The local window maps independently onto the frame's width and height and is
clipped at its edges. The frame does not fit itself to changing path bounds.
Inspection reports that fixed frame. The fill uses the **even-odd** rule: an odd
number of boundary crossings paints, so nested contours make holes regardless
of their direction. Raster drawing supersamples only the visible painted bounds
at 4× and downsamples with antialiasing.

`C/S` draw cubic Béziers and `Q/T` draw quadratic Béziers. Smooth commands reflect
the preceding control point only within their own curve family, following SVG
rules. Curves are adaptively flattened after mapping to the frame, with a 1/8-pixel
chord tolerance before supersampling. Excessive plans raise `RenderingError`
(`path_subdivision_limit`) instead of silently reducing precision; simplify the
path or reduce its mapped scale.

`A/a` draw rotated elliptical arcs with SVG radius correction. Radii use their
absolute values; a zero radius draws a line, and identical endpoints omit the
arc. Large-arc and sweep flags must each be `0` or `1`. Arc subdivision uses the
same mapped chord tolerance and work limits. Unrepresentable numerical geometry
raises `RenderingError` (`path_arc_range_limit`) rather than producing invalid pixels.

Strokes are centered on the path and scale with the viewBox, including independent
horizontal and vertical scaling. `Z` joins the closing seam; returning to the
start with a line leaves two capped endpoints. Stroke coverage is unioned before
color is applied, so translucent intersections do not darken. Fill is painted
first and stroke above it, both clipped to the fixed viewport. Round geometry
uses the same 1/8-pixel chord tolerance. Excessive stroke geometry raises
`RenderingError` (`path_stroke_limit`) before output is written.

```python
canvas.path("M10 50C30 0 70 100 90 50", (20, 10), 120, 100, None,
            stroke="#42CEB7", stroke_width=8, line_cap="round",
            view_box=(0, 0, 100, 100))
```

Dashes, gradients, layer animation, parent links, grouping and composition controls are
not accepted yet. JSON uses `type="path"` and round-trips through `PathLayer`.

PNG and canonical samples draw the path directly. SVG, HTML, PDF and PPTX currently
embed a static raster image; `validate_export()` and `ExportResult` report the
fallback. A strict `ExportPolicy(unsupported_motion="error")` rejects that output
before writing.
