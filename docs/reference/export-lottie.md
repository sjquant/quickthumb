---
description: Reference for lottie vectors in quickthumb.
---

# Lottie vectors

[Export reference](../exports.md) · [Choose an output format](../output-guide.md)

## Lottie vectors

```python
from quickthumb import Canvas, LottieOptions

canvas = Canvas(240, 160).shape("ellipse", (20, 20), 80, 60, "#159A8C")
result = canvas.export("scene.lot", animation=LottieOptions(fps=30, hold=3))
```

`.lot` contains ordinary Lottie JSON, not Quickthumb document JSON. The supported
subset is a single Canvas: one initial solid background, solid
rectangle/rounded rectangle, ellipse, pill, triangle, star and polygon shapes,
and Paths (`M/L/H/V/C/S/Q/T/A/Z`) with even-odd solid fill or solid stroke. Shape
alignment and percentage positions retain their authored layout. Path control hulls must
fit inside the viewport (strokes reserve a conservative miter-limit margin); stroked Paths require uniform view-box scaling.

`hold` is nonnegative seconds; `fps` defaults to 30 and supports up to 120.
Stroked degenerate contours are rejected rather than replaced with missing dots.
The playback span is the latest canonical motion end plus `hold`, rounded up
to whole frames; the receipt reports
that frame count and its duration divided by fps. Zero hold adds no final pause;
a static zero-hold composition still occupies one frame. Output has no audio or assets.
See [the runnable static example](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_static.py).

`canvas.validate_export("lottie")` lists unsupported source IDs and JSON paths.
Gradients, effects/presets, stagger, masks, viewport clipping,
paint/dash tracks, motion paths, images, plugins and Deck output are
not supported in this slice.
Export rejects them before opening the destination, including when a policy asks
for static or raster fallback. It never silently drops features or embeds rendered
frames. No Lottie import, ZIP or editor API is provided.

Quadratics convert exactly to cubic tangent handles. Elliptical arcs use the
same bounded cubic conversion as native PDF paths (at most 1/8 device pixel
approximation, with command and coordinate precision limits). No ReportLab or
other document-renderer dependency is needed for Lottie. Closed contours retain
their closing tangents and multiple contours share the even-odd fill rule.
Admission uses the conservative control hull: some curves that visually fit
are rejected when their controls exceed the fixed viewport. Rescale or reposition
the path data inside its view box instead of expecting implicit cropping.
See the [curved Path example](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_paths.py).

Canonical position, uniform/axis scale, rotation and opacity timelines retain
ordered composition, easing, delays and held keys. Authored rotation is retained;
track opacity multiplies authored layer opacity. Paths use their fixed viewport
pivot. Shapes use the same whole painted-source pivot as canonical sampling,
including authored static rotation, alignment and irregular geometry. Preparing
an animated Shape uses one bounded untimed source probe to determine that pivot;
it does not embed pixels. Animated Shape sources must fit inside the Canvas.
Nonpositive uniform Shape/Null scale is explicitly unsupported by this renderer;
axis scales and Path scales retain their canonical behavior.

Pose properties are held vector samples at `LottieOptions.fps`, augmented with
exact event and authored-key boundaries shared across the Canvas. Between those instants the previous
pose remains visible; output does not claim continuous native Lottie easing.
Static properties remain native constants. Capability diagnostics report this
sampling distinction. Export stops before writing if more than 100,000 total
pose/contour-vertex observations or native coordinate precision limits would be exceeded.
`ExportPolicy(reduced_motion=True)` intentionally removes the timelines and
exports the authored static pose for `hold` seconds, rather than the animation
endpoint. Other unsupported features still fail before writing.
See the [pose-motion example](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_motion.py).

Top-level Null and supported Shape layers can form transform hierarchies with
`parent`. Parenting composes existing canonical local frames, including authored
rotation, anchors and nonuniform axes; local poses do not bake ancestors again.
Percent coordinates still resolve against Canvas dimensions, even on children.
Opacity affects each painted source independently and does not propagate from
an invisible parent to its children. Axis-zero collapse and axis reflections
retain the canonical parent behavior. Source drawing order remains independent
of the graph order, including a child listed before its parent.

Linked Shape pivots retain the canonical opaque-reference footprint, even when
the parent's own paint is transparent. Their local sources may begin outside the
Canvas: ancestor transforms can bring them into view. Unlinked animated Shape
sources keep the earlier unclipped-source requirement. Cycles, missing parents,
unsupported groups/effects and Path parenting are rejected before writing.
See the [parenting example](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_parenting.py).

### Lottie path morph

`PathMorphTrack` uses the same bounded contour correspondence, eased local clock
and exact authored endpoints as canonical Path sampling. Export with the ordinary
`canvas.export("morph.lot", animation=LottieOptions(fps=24, hold=0.5))`;
see the runnable [logo morph](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_morph.py).

Geometry is held at the same fps/event/key instants as pose properties, including
fractional boundaries. Open and closed contours, nested even-odd fills, solid
RGBA fill/stroke and simultaneous pose/trim tracks retain their existing meaning.
Each sampled shape stays in the authored fixed view box; Lottie does not interpolate
between samples. Endpoint curves retain their native cubic handles, while intermediate
polylines follow the canonical morph. Repeated endpoint vertices keep each animated
contour at a fixed vertex count without changing its curves; padding counts toward
the observation budget.

The existing [morph topology limits](../api/path.md#path-morphing) apply. The authored
Path and morph keys must also have the same contour count and open/closed status. In addition,
every sampled control hull and stroke margin must fit the viewport. Sampled contour
vertices count toward the existing Canvas-wide 100,000-observation budget. Lower fps or simplify geometry
if that bound is exceeded. Authored/keyframe viewport violations are reported by
`validate_export("lottie")`; sample-dependent topology, precision or budget errors
are detected during compilation before the destination is opened. Gradients,
dashes and Path parenting remain unsupported; no raster fallback is substituted.
Reduced-motion export retains the authored static path, as for other timelines.

## Lottie stroke trim

Paths support authored `trim_start`, `trim_end`, `trim_offset` and their
`TrimStartTrack`, `TrimEndTrack`, `TrimOffsetTrack` timelines. Trim uses one
normalized local arc-length clock across all contours, including cyclic wrapped
windows and negative or multi-turn offsets. Full 0→1 ignores offset; equal
endpoints and 1→0 are empty. Fill remains complete underneath the trimmed stroke.
Closed seams retain their joins; open cuts use the authored cap.

Trim properties use the same held fps samples, authored boundaries, composition,
easing and reduced-motion policy as pose properties above. They remain native
vector trim modifiers, with no frame images. Native endpoint rounding must not
collapse a nonempty interval or exceed a conservative 1/8-pixel endpoint bound
under the sampled scale; otherwise export rejects it before writing. The existing
viewport, uniform stroke scaling and nondegenerate contour limits still apply.
Dashes and dash-offset tracks remain unsupported; there is no trim-then-dash
approximation. See the [stroke-trim example](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_trim.py).

## Lottie outlined text

Static plain single-line printable ASCII text exports as self-contained native
cubic glyph outlines. Install `quickthumb[lottie]` for the optional fonttools
dependency; shape and Path output do not require it. The actual resolved local
FreeType face, including Pillow's embedded default font, supplies the outlines.
The file embeds neither font assets nor editable Lottie text. Canonical baseline,
alignment and explicit letter spacing determine glyph positions; font contour
winding preserves holes within each independently painted glyph, so overlapping
glyphs cannot cancel each other. Opacity applies once to the whole text layer. Text paint itself
must be opaque: the canonical direct-draw alpha-paint behavior on a backdrop is
not equivalent to native Lottie compositing.

Text must not use animation, parenting, rotation, wrapping/fitting, rich content,
counters, effects, masks, gradients, variable/color fonts or remote font sources.
Missing glyphs fail explicitly instead of becoming replacement boxes. Unspaced
multi-character RAQM layout requires shaping and is rejected; use explicit
nonzero `letter_spacing`. Unspaced BASIC text is admitted only when its measured
advances are additive. This subset does not promise complex-script shaping.

Each layer is bounded to 1024 characters, 65536 outline vertices and a 64 MiB
font source, with native coordinate-precision checks. Unsupported text and missing
fonttools produce source-specific diagnostics before opening the destination.
See the [outlined-text example](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_text.py).
