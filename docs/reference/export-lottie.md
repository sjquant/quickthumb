---
description: Create vector logo animations, self-drawing outlines, and moving shapes as Lottie files.
---

<a id="lottie-vectors"></a>

# Lottie animations

[Export reference](../exports.md) · [Choose an output format](../output-guide.md)

Export logos that change shape, outlines that draw themselves, and moving shapes
as vector animations for a Lottie player. The `.lot` file contains standard
Lottie JSON, with no embedded frame images or audio.

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

This creates a one-second square-to-diamond animation followed by a half-second
pause. Preview the file in your target Lottie player before publishing.
For a curved, filled and stroked logo, run the
[logo morph example](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_morph.py).

For a complete intro with a title, a self-drawing logo that becomes a circle,
and a rotating badge, run:

```bash
python -m examples.lottie_intro /tmp/intro.lot
```

The two-second animation ends with a half-second pause. The title is outlined,
so playback needs no font files. Change the title, colors, and geometry in the
[intro example](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_intro.py)
to reuse it.

## Choose artwork and timing

A single Canvas can include a solid background, solid shapes, SVG Paths,
position/scale/rotation/opacity animation, stroke trim, and supported static text.
Shapes include rectangles, rounded rectangles, ellipses, pills, triangles, stars,
and polygons. Paths accept `M/L/H/V/C/S/Q/T/A/Z`, solid fill/stroke, and holes
using even-odd fill.

`LottieOptions.fps` defaults to 30 and supports up to 120. Higher fps gives finer
motion steps and larger files. Motion is sampled at that rate and at authored
key/event boundaries; each pose stays visible until the next sample. Players do
not interpolate smoothly between those samples. Static artwork stays vector too.

`hold` adds a final pause in seconds and must be nonnegative. The result lasts
through the latest animation end plus that pause, rounded up to whole frames.
Even a static Canvas with zero hold occupies one frame. The export receipt gives
the frame count and duration.

Examples: [static shapes](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_static.py),
[curved Paths](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_paths.py),
[moving shapes](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_motion.py).

## Lottie path morph

`PathMorphTrack` changes Path geometry while keeping its authored view box.
Fill, solid stroke, opacity, transforms, and stroke trim can accompany the morph.
Open contours, closed contours, and nested holes are supported within the
[Path morph limits](../api/path.md#path-morphing).

The authored Path and all keys must have matching contour count and open/closed
status. All sampled curves, their control points, and stroke margins must fit
inside the view box. Some curves that look as though they fit can still exceed
this bound; rescale or reposition their geometry. Stroked Paths require uniform
view-box scaling, and degenerate stroked contours are rejected.

Large or complex animations can exceed the Canvas-wide limit of 100,000 pose
and contour-vertex observations. Lower fps or simplify paths if export reports
this limit. Intermediate morphs follow the same approximated outlines as rendered
Quickthumb frames; exact authored endpoints retain their curves.

## Lottie stroke trim

Use `TrimEndTrack` to draw an outline progressively, or `TrimStartTrack` and
`TrimOffsetTrack` to move a visible segment along it. Static `trim_start`,
`trim_end`, and `trim_offset` are supported too. See the
[stroke-trim example](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_trim.py).

Trim positions run from 0 to 1 across the total path length, in contour order.
Offsets wrap and may be negative or greater than one. Full 0→1 keeps the entire
stroke regardless of offset; equal endpoints and 1→0 hide it. Fill stays complete
underneath. Closed seams keep their joins; cut endpoints use the chosen cap.
Dashes and dash-offset animation are unsupported. Very small trim intervals may
be rejected if player rounding would hide them or noticeably move their endpoints.

## Move shapes together

Use `parent` to link supported Shape and Null layers, as in the
[parenting example](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_parenting.py).
Children follow parent transforms while keeping their independent drawing order
and opacity. Parent opacity does not fade children. Percentage positions resolve
against the Canvas, including for children. Path parenting is unsupported.

Unlinked animated shapes must fit inside the Canvas before animation. Linked
shapes may start outside it when parent transforms bring them into view.
Nonpositive uniform Shape/Null scale is unsupported; axis scaling retains its
usual behavior, including reflection and collapse.

## Lottie outlined text

Install `quickthumb[lottie]` to include static, single-line printable ASCII text.
Text becomes vector outlines: viewers need no font, but cannot edit it as text.
Shape and Path exports do not need this extra dependency. See the
[outlined-text example](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_text.py).

Use opaque text paint and a local, nonvariable, noncolor font with every required
glyph. Unsupported glyphs produce an error. Text animation, parenting, rotation,
wrapping/fitting, rich text, counters, effects, masks, gradients, remote fonts,
and complex-script shaping are unsupported. With RAQM layout, set explicit nonzero
`letter_spacing` for multiple characters; unspaced BASIC text requires additive
character advances. Each layer permits at most 1024 characters, 65,536 outline
vertices, and a 64 MiB font source.

## Check compatibility before exporting

`canvas.validate_export("lottie")` identifies unsupported layers and fields.
Export rejects unsupported content before opening the destination, preserving an
existing file. Some intermediate morph, precision, and resource-limit errors can
only be found when export compiles the animation.

Gradients, effects/presets, stagger, masks, viewport clipping, paint/dash tracks,
motion paths, images, plugins, and Deck output are unsupported. Lottie export
cannot substitute static or raster fallbacks, even when an export policy requests
them. Lottie import, ZIP packaging, and editing existing Lottie files are not
provided.

`ExportPolicy(reduced_motion=True)` exports the authored static artwork for
`hold` seconds. It does not choose the animation's final pose, and other
unsupported features still need to be removed.

## Playback verification

The reference players are **lottie-web 5.13.0 (SVG)** and **Lottie Android 6.7.1**
with Robolectric 4.17 native graphics on Android 15/API 35 at mdpi. The Android
check runs the official library's software Drawable renderer on Linux/JVM with
native Skia; it is not a physical device, emulator, ARM or GPU test.

The original 31 frames and 13 blank/frozen controls remain in the check. Six more
frames and two controls cover unequal contours, empty/full and wrapped windows,
negative offsets, changing morph lengths, and overlapping translucent strokes.
All nine files validate against Lottie schema 1.0.1. Each player is checked against
37 canonical frames and must detect 15 blank/frozen controls, without relaxing
the image limits. CI retains the web images and measurements; Android reports
its comparison results in the same job.

The comparison allows up to 32 channel levels, 8% differing pixels, and an
average-hash similarity of at least 0.93, both across each frame and in its artwork
regions. These fixture limits allow rasterizer edge differences; they are not
a guarantee for arbitrary artwork. See
[how to repeat the player check](export-validation.md#lottie-reference-player).

**Use the SVG renderer for this verified subset.** With lottie-web 5.12.2 and
5.13.0, the optional Canvas comparison shows incorrect combined paint/layer
opacity in some translucent scenes. Those Canvas observations do not pass the
reference limits. iOS native, Android physical devices, ARM/GPU rendering and real-app performance
remain unverified. Arbitrary combinations of artwork are not covered: an
exploratory translucent multi-contour morph still exceeded the Android region
hash limit, although the isolated contour-length and shared-stroke regressions
pass. Preview your actual file in its destination player before publishing.
