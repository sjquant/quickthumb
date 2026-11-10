---
description: Create animated vector logos, self-drawing outlines, and reusable intros.
---

<a id="lottie-vectors"></a>

# Lottie animations

[Export reference](../exports.md) · [Choose an output format](../output-guide.md)

Create a logo that changes shape, an outline that draws itself, or an intro with
a title and moving badge. Export a Canvas to `.lot` and play its vector artwork
with a Lottie player, without shipping rendered video frames or viewer-side fonts.

## Create a shape-changing logo

```python
from quickthumb import (
    AnimationSpec,
    Canvas,
    KeyframeSpec,
    LottieOptions,
    PathMorphTrack,
    TimingSpec,
)

square = "M20 20 H80 V80 H20 Z"
diamond = "M50 10 L90 50 L50 90 L10 50 Z"
morph = AnimationSpec.timeline(
    PathMorphTrack(keyframes=[
        KeyframeSpec(time=0, value=square),
        KeyframeSpec(time=1, value=diamond),
    ]),
    timing=TimingSpec(duration=1),
    easing="ease_in_out",
)
Canvas(120, 120).path(
    square, (10, 10), 100, 100, "#159A8C",
    view_box=(0, 0, 100, 100), animation=morph,
).export("logo.lot", animation=LottieOptions(fps=24, hold=0.5))
```

The square becomes a diamond over one second, then pauses for half a second.
Change the two paths, color, size, or easing to make your own logo.

<a id="playback-verification"></a>

## Play it on the web

Install `lottie-web@5.13.0` in your web project, add a container such as
`<div id="logo" style="width:120px;height:120px"></div>`, and serve `logo.lot`
from your public assets directory:

```javascript
import lottie from "lottie-web";

lottie.loadAnimation({
  container: document.getElementById("logo"),
  renderer: "svg",
  loop: true,
  autoplay: true,
  path: "/logo.lot",
});
```

Use `renderer: "svg"` to keep fill, stroke, and layer opacity consistent.
Canvas playback in lottie-web 5.12.2/5.13.0 has a combined-opacity defect.
Preview your file in the player used by your site or app. See the
[developer player checks](export-validation.md#lottie-reference-player) for
reference versions and repeatable comparisons.

## Reuse a complete intro

From the repository root, generate a two-second intro with an outlined title,
a self-drawing logo that becomes a circle, and a rotating badge:

```bash
pip install 'quickthumb[lottie]'
python -m examples.lottie_intro /tmp/intro.lot
```

The intro ends with a half-second pause. Edit the title, colors, paths, and
rotation in the [intro example](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_intro.py)
to reuse it; the exported title needs no font files on the viewer’s device.

## Choose artwork and timing

Use solid backgrounds and shapes, SVG Paths with fill/stroke and holes, and
position, scale, rotation, or opacity tracks. Start with the
[static shapes](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_static.py),
[curved Paths](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_paths.py), or
[motion example](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_motion.py).

Set `LottieOptions(fps=24, hold=0.5)` to sample motion at 24 fps and add a
half-second final pause. The default is 30 fps; up to 120 is available for finer
motion at the cost of larger files. Poses stay fixed until the next sample.
The export receipt reports the resulting frame count and duration.

## Lottie path morph

Combine `PathMorphTrack` with fill, stroke, opacity, transforms, and trim.
For curved artwork, adapt the [logo morph example](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_morph.py).

Keep the same contour count and open/closed states across your paths. Leave room
in `view_box` for curves, control points, and the stroke; use uniform scaling for
stroked paths. If export reports a geometry or work limit, enlarge the view box,
simplify the path, or lower fps as directed. See [Path morphing](../api/path.md#path-morphing).

## Lottie stroke trim

Use `TrimEndTrack` to reveal an outline. This continues the logo example above:

```python
from quickthumb import TrimEndTrack

outline = AnimationSpec.timeline(
    TrimEndTrack(keyframes=[
        KeyframeSpec(time=0, value=0),
        KeyframeSpec(time=1, value=1),
    ]),
    timing=TimingSpec(duration=1),
    easing="ease_in_out",
)
Canvas(120, 120).path(
    square, (10, 10), 100, 100, None,
    view_box=(0, 0, 100, 100), stroke="#159A8C", stroke_width=3,
    animation=outline,
).export("outline.lot", animation=LottieOptions(fps=24, hold=0.5))
```

Move a visible segment with `TrimStartTrack` and `TrimOffsetTrack`, or set static
`trim_start`, `trim_end`, and `trim_offset`. Positions run from 0 to 1 over total
path length in contour order, including while morphing; offsets wrap in either
direction. Full 0→1 draws the whole stroke; equal endpoints and 1→0 hide it.
Fill stays complete underneath. Use solid strokes and choose `line_cap` for cut
ends. If a very short interval triggers a precision error, widen the interval.
See the [trim example](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_trim.py).

## Move shapes together

Attach Shape layers to a Null with `parent` to rotate or move them as a group;
use the [parenting example](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_parenting.py)
as a starting point. Children keep their drawing order and independent opacity.
To fade the group, animate each visible child’s opacity. Percentage positions
use Canvas dimensions. Keep animated shapes without a parent inside the Canvas at
their authored pose; parented shapes can enter from outside. Parenting is
available for Shape and Null layers.

## Lottie outlined text

Install `quickthumb[lottie]` to add static, single-line printable ASCII titles
as vector outlines. Viewers need no fonts; edit the source title and re-export
to change it. Adapt the [text example](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_text.py)
with a local outline font, an opaque text color, and explicit nonzero
`letter_spacing` for multi-character text. Use layer `opacity` for translucency.
Keep the title unrotated and without a parent. For animated or multilingual typography,
choose a [video output](../output-guide.md) instead.

## Check compatibility before exporting

Call `canvas.validate_export("lottie")` before integrating an existing design.
It lists layers and fields to change, such as gradients, images, effects, or text
animation. Export also checks sampled geometry and precision before writing, so
a rejected export preserves an existing destination.

For vector Lottie, use the artwork and tracks shown above. To keep raster
images, effects, or other unsupported content, choose a [video output](../output-guide.md);
Lottie export does not silently replace them with images.

For a still version, use `ExportPolicy(reduced_motion=True)` with a positive
`hold`. This exports the authored artwork rather than the animation’s final pose.
