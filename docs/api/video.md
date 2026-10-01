---
description: Reference for quickthumb video layers, including trimming, fit, speed, timed captions, grading, masking, and animation.
---

# Video

`.video()` places one clip in a composition. It is a layer like any other: it
trims, fits, and plays, and it also grades, rounds, masks, fades, and animates
with the same vocabulary as an image layer.

Video layers render in animated GIF/MP4/WebM output and in `render_frame(...)`.
Document targets (PPTX, PDF, SVG, HTML) rasterize the clip as a static frame;
`validate_export(...)` reports that fallback explicitly.

## Signature

```python
canvas.video(
    source,
    position,
    width,
    height,
    fit="contain",
    trim_start=0.0,
    trim_end=None,
    start=0.0,
    duration=None,
    speed=1.0,
    volume=1.0,
    captions=None,
    border_radius=0,
    opacity=1.0,
    rotation=0.0,
    align=None,
    blend_mode=None,
    effects=None,
    clip=None,
    mask=None,
    animation=None,
)
```

## Parameters

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `source` | `str` | **required** | Path to the video file. |
| `position` | `tuple` | **required** | `(x, y)` position. Values can be integers (px) or percentage strings (`"50%"`). |
| `width` | `int` | **required** | Layer width in pixels. Positive integer. |
| `height` | `int` | **required** | Layer height in pixels. Positive integer. |
| `fit` | `str \| FitMode` | `"contain"` | How the frame fills the layer box. See [FitMode](enums.md#fitmode). |
| `trim_start` | `float` | `0.0` | Where playback starts in the source, in seconds. |
| `trim_end` | `float \| None` | `None` | Where playback ends in the source. Defaults to the source duration. |
| `start` | `float` | `0.0` | When the clip starts on the slide's timeline, in seconds. |
| `duration` | `float \| None` | `None` | How long the clip occupies the slide. Cannot exceed the trimmed source divided by `speed`. |
| `speed` | `float` | `1.0` | Playback rate. Below `1.0` slows a short clip to fill a longer scene. |
| `volume` | `float` | `1.0` | Clip volume in MP4/WebM output. GIF carries no audio. |
| `captions` | `list \| None` | `[]` | Timed caption cues burned into the frames. Rendered in the foreground pass, above every other layer. |
| `border_radius` | `int` | `0` | Corner rounding in pixels. |
| `opacity` | `float` | `1.0` | Layer opacity from `0.0` to `1.0`. |
| `rotation` | `float` | `0.0` | Rotation in degrees. |
| `align` | `str \| Align \| tuple \| None` | `None` | Which point of the layer the `position` refers to. See [Align](enums.md#align). |
| `blend_mode` | `str \| BlendMode \| None` | `None` | How the clip blends with the layers beneath it. |
| `effects` | `list \| None` | `[]` | Image effects applied to each sampled frame: `Filter`, `Duotone`, `Grain`, `Glow`, `Shadow`, `Stroke`, `InnerShadow`, `BackdropBlur`. |
| `clip` | `LayerClip \| None` | `None` | Clip the layer to a region. |
| `mask` | `LayerMask \| None` | `None` | Mask the layer into a shape. |
| `animation` | `Animation \| AnimationSpec \| list \| None` | `None` | Entrance/exit effect or canonical motion. A clip can fade, wipe, move, scale, or rotate while it plays. |

## Examples

Grade a clip and round its corners:

```python
from quickthumb import Canvas
from quickthumb.models import Filter

canvas = Canvas(1280, 720).video(
    "clip.mp4",
    position=(64, 64),
    width=1152,
    height=592,
    fit="cover",
    trim_start=1.0,
    trim_end=7.0,
    duration=6.0,
    border_radius=12,
    effects=[Filter(saturation=0.0, contrast=1.1)],
)
```

Show one moment in three frame shapes by placing the same window three times:

```python
for x, (label, frame_width) in zip((80, 664, 1068), (("16:9", 412), ("1:1", 232), ("9:16", 131))):
    canvas.video(
        "clip.mp4",
        position=(x, 348),
        width=frame_width,
        height=232,
        fit="cover",
        trim_start=1.0,
        trim_end=7.0,
        duration=6.0,
    )
```

Move a clip across the frame while it plays:

```python
from quickthumb import AnimationSpec, KeyframeSpec, PositionTrack, TimingSpec

canvas.video(
    "clip.mp4",
    position=(0, 120),
    width=480,
    height=270,
    fit="cover",
    duration=4.0,
    animation=AnimationSpec.timeline(
        PositionTrack(
            keyframes=[
                KeyframeSpec(time=0.0, value=(0.0, 0.0)),
                KeyframeSpec(time=4.0, value=(800.0, 0.0)),
            ]
        ),
        timing=TimingSpec(start=0.0, duration=4.0),
        easing="linear",
    ),
)
```

## Notes

- A scene longer than its clip needs `speed` below `1.0`; asking for more
  frames than the trimmed source holds raises a validation error rather than
  freezing on the last frame.
- Captions are owned by their clip for timing and serialization but render
  after the whole layer stack, so a later panel cannot cover them.
- `diagnose()` reports captions that leave the canvas, enter the safe-area
  edge, outlast their layer, or overlap each other.

## Curved motion paths

`PositionTrack` accepts `PositionKeyframeSpec` with optional `in_tangent` and
`out_tangent` handles. Like ordinary position keyframes, `value=(x, y)` is a
pixel translation from the layer's authored, rendered position, not an absolute
canvas coordinate. Handles are finite `(dx, dy)` pixel vectors relative to
their own keyframe value, not absolute control points or velocity values.
The same track works on any layer that accepts canonical `AnimationSpec`
motion, including shapes, text, images, video and groups.

```python
from quickthumb import AnimationSpec, Canvas, PositionKeyframeSpec, PositionTrack, TimingSpec

canvas = Canvas(640, 360).shape(
    "pill", (60, 230), 48, 24, "#42CEB7",
    animation=AnimationSpec.timeline(
        PositionTrack(
            keyframes=[
                PositionKeyframeSpec(time=0, value=(0, 0), out_tangent=(120, -200)),
                PositionKeyframeSpec(time=4, value=(480, 0), in_tangent=(-120, -200)),
            ],
            auto_orient=True,
        ),
        timing=TimingSpec(start=0, duration=4),
        easing="linear",
    ),
)
canvas.render_frame(2).save("curved_path.png")
```

### Handles and speed

Each pair of keyframes defines a cubic Bézier segment with these four control
points, in order:

1. The left keyframe's `value`
2. The left `value + out_tangent`
3. The right `value + in_tangent`
4. The right keyframe's `value`

A missing handle is a zero vector. A segment with neither handle is straight.
Give an interior keyframe both handles to join two curves; smoothness depends
on the directions you author. Equal endpoint values can still describe a loop
when the handles are nonzero.

With `easing="linear"`, curved paths travel at approximately constant distance
per second **within each keyframe interval**. A cached, bounded adaptive
arc-length lookup maps distance back to the curve parameter. Different segment
lengths or durations can produce different speeds across a knot; there is no
whole-path retiming. Named timeline easing acts on each segment's distance
progress, clamped to `[0, 1]`, so even back easing cannot travel beyond the
segment endpoints. Authored keyframe times and positions are preserved.

Existing `KeyframeSpec` values remain accepted. With no handles anywhere and
`auto_orient=False` (the default), the track retains its previous linear
interpolation and easing behavior. Providing handles or enabling `auto_orient`
opts the track into path sampling. This does not add per-keyframe easing.

### Following the tangent

`auto_orient=True` rotates the rendered layer to the path tangent: right is
`0°`, down is `90°`, and positive rotation is clockwise. Author directional
artwork facing right. Rotation uses the layer's existing transform anchor.

Track order decides precedence. An auto-oriented position track replaces the
animated rotation accumulated before it; a `RotationTrack` after it replaces
the tangent heading. A layer's authored static `rotation` is already baked
into its source pixels and remains part of that artwork. Auto-orientation does
not add the heading to an earlier animated rotation.

An exact interior knot uses the incoming segment's heading. Stationary holds
reuse the nearest earlier available direction, or the next direction if the
path has not moved yet. A wholly stationary path preserves the incoming
rotation. These choices are deterministic when seeking or rendering frames
out of order.

The JSON form uses `"type": "position"`, optional `"auto_orient": true`, and
keyframes with `"in_tangent": [dx, dy]` / `"out_tangent": [dx, dy]`. The public
models, generated schema and `inspect_motion()` preserve this metadata.
Omitted handles and the default `auto_orient=False` are not serialized.

### Export support

- Raster frames, GIF, MP4 and WebM share the same path sampler, including
  `quality="high"` and spawn workers. Paths can be combined with `ColorTrack`
  on eligible text, shapes and groups
- HTML animates one geometry-only canonical timeline on a static rendered
  source, without stagger or composed animations. It bakes sampled transform
  stops at up to 120 Hz, bounded to 4097 stops, retaining every authored knot
  within that bound. The interpolation is approximate. Tangent headings are
  unwrapped across angle boundaries; authored multi-turn rotation is retained
- HTML reports `motion_path` as `partial` with no fallback for that supported
  sampled mapping. Strict `unsupported_motion="error"` validation rejects it.
  Unsupported combinations, including color tracks, dynamic sources or more
  authored knots than the bound permits, use authored-static fallback.
  Existing backdrop-dependent motion restrictions still apply
- PPTX uses a static fallback and does not emit animated path timing
- `validate_export()` reports the actual support or fallback for the
  composition. Use it before export to check the selected target

See [the runnable motion-path infographic](https://github.com/sjquant/quickthumb/blob/main/examples/motion_paths.py)
for a two-segment curve, tangent-following arrow and raster color changes. It
also exports a separate geometry-only HTML version so the path can animate
without requesting unsupported HTML color animation.

`diagnose()` warns with `motion-path-unused-handle` when a first incoming or
last outgoing handle has no adjacent segment. The generated schema includes a
complete curved-position example.

## Transform anchors and independent scale

Animatable text, image, SVG, video, shape, chart, QR-code, and group layers
accept `anchor=(x, y)`. Each coordinate is a finite number from `0` to `1`:
`(0, 0)` is the top-left of the rendered bounds, `(1, 1)` the bottom-right,
and the default `(0.5, 0.5)` preserves the existing centre pivot. It does not
change layout `position` or `align`.

```python
from quickthumb import (
    AnimationSpec, Canvas, KeyframeSpec, RotationTrack, ScaleXTrack,
    ScaleYTrack, TimingSpec,
)

canvas = Canvas(320, 240).shape(
    "rectangle", (100, 100), 80, 40, "#42CEB7",
    anchor=(0, 1),
    animation=AnimationSpec.timeline(
        ScaleXTrack(keyframes=[
            KeyframeSpec(time=0, value=1), KeyframeSpec(time=2, value=1.5),
        ]),
        ScaleYTrack(keyframes=[
            KeyframeSpec(time=0, value=1), KeyframeSpec(time=2, value=0.6),
        ]),
        RotationTrack(keyframes=[
            KeyframeSpec(time=0, value=0), KeyframeSpec(time=2, value=30),
        ]),
        timing=TimingSpec(duration=2),
        easing="linear",
    ),
)
canvas.render_frame(1).save("anchored.png")
```

`ScaleXTrack` and `ScaleYTrack` default to `1`. Their sampled values multiply
the existing uniform `ScaleTrack`: effective scales are `scale * scale_x` and
`scale * scale_y`. Axis values may be negative to reflect the layer; zero on
either axis collapses it to no visible pixels. The existing uniform scale's
non-positive raster behaviour remains unchanged. Image layers keep their
existing uniform-scale viewport zoom; the new axis tracks scale the outer image
frame instead.

The single affine transform subtracts the pivot, scales independently, rotates,
restores the pivot, then applies the motion translation. The pivot is measured
on the rendered visible bounds, after authored static rotation/effects, before
canonical opacity/reveal and motion blur. It applies to canonical
`AnimationSpec` motion; untimed still rendering and authored static `rotation`
retain their established behaviour. A group is one rendered unit; supported
stagger targets use their own bounds. Parent/child transform inheritance is
not introduced by this option.

The JSON equivalents are a layer's `"anchor": [0, 1]` and track types
`"scale_x"` / `"scale_y"`. The models, generated schema and `inspect_motion()`
include the new values. Default values are omitted from serialization so old
documents keep the same JSON and pixels. `transform_matrix(state, size=(w, h))`
and `apply_transform(point, state, size=(w, h))` resolve the normalized pivot
against explicit rendered bounds; omitting `size` preserves the origin-based
point API.

### Export support

- Raster, GIF, MP4 and WebM apply the same pivot and independent scales,
  including `quality="high"` and spawn workers
- HTML maps the new transform to `transform-origin` and `scale(x, y)` using
  registered CSS custom properties. One geometry-only canonical timeline is
  supported, with independent authored keyframe times and named easing.
  It embeds the authored layer pixels to keep the pivot bounds consistent
- HTML falls back to authored static pixels for composed animation lists,
  presets, stagger, unsupported property tracks, dynamic source content,
  image viewport scale, or non-positive uniform scale. Browsers must support
  CSS `@property` for interpolation. Existing backdrop-prefix restrictions
  still apply: HTML rejects motion on or underneath backdrop-dependent layers
- PPTX declares a static fallback for anchors and independent axis tracks;
  it does not silently claim native pivot animation
- `validate_export()` reports the actual mapping or fallback. Strict export
  policies reject unsupported combinations

See [the runnable pivot comparison](https://github.com/sjquant/quickthumb/blob/main/examples/transform_anchors.py) for
three identical cards rotating and stretching around different fixed pivots.

## Animated text and shape colors

`ColorTrack` replaces text color and shape fill in sampled raster frames, GIF,
MP4 and WebM. It also applies to eligible descendants of an animated group.
Layers without a color track keep their prepared source images; color animation
re-renders only the affected source unit before the usual geometry, opacity,
clip, effects and compositing steps. Both quality modes and spawn workers use
this path.

```python
from quickthumb import AnimationSpec, ColorTrack, KeyframeSpec, TimingSpec

canvas.text(
    "Color in motion", position=(40, 40), size=48, color="#FF0000",
    animation=AnimationSpec.timeline(
        ColorTrack(keyframes=[
            KeyframeSpec(time=0, value="#FF0000"),
            KeyframeSpec(time=2, value="#0000FF80"),
        ]),
        timing=TimingSpec(start=0, duration=2),
        easing="linear",
    ),
)
```

Colors accept `#RRGGBB` and `#RRGGBBAA`. RGB is interpolated in
[Oklab](https://bottosson.github.io/posts/oklab/), with premultiplied color
coordinates and linear alpha. This avoids invisible endpoint colors darkening
an appearance or disappearance. Out-of-gamut RGB channels are clipped to sRGB.
Authored endpoints remain exact; intermediate colors differ from the previous
encoded-RGB sampling contract. For example, opaque red to blue passes through
`#8C53A2`, and black to white passes through `#636363` at halfway. Existing
non-color motion and Morph color interpolation are unchanged.

An active color track overrides gradient/image fills and all rich-text part
colors; it leaves stroke, shadow, glow and other effect colors unchanged.
Before its start, and in untimed or reduced-motion stills, the authored fill
is preserved. A group's animation continues to override descendant animations;
intrinsic counter values still update. Separately rendered stagger lines sample
their own colors. Targets that cannot be split keep the existing approximate
whole-layer stagger fallback; full glyph/range animation is separate work.

Groups containing backdrop-dependent descendants support pure parent color
tracks. Combining those tracks with other parent motion or stagger is reported
as unsupported and raises a rendering error: animate the shape directly, or
separate its backdrop effects from the moving group. No static fallback is
claimed for this combination.

The existing `ColorTrack` model, generated JSON schema and `inspect_motion()`
include the track and its final color. `validate_export()` declares full
raster/video color support for text, shapes and eligible groups. Image, SVG,
chart and QR layer color tracks have a static fallback. Embedded multicolor
emoji retain their font-provided colors.

HTML declares an authored-static fallback for animation compositions containing
color tracks; it does not substitute an unrelated fade. PPTX declares a static
color fallback. `validate_export()` surfaces these limitations, and strict
policies reject them. Existing restrictions on animated backdrop prefixes and
clipped/masked group descendants still apply to their respective exporters.

See [the runnable color example](https://github.com/sjquant/quickthumb/blob/main/examples/color_tracks.py)
for text, a moving pill, and an initially transparent caption.

## Live timeline preview

Use `quickthumb serve scene.py --timeline` to scrub the canonical raster timeline
without encoding a video. The `/timeline` view offers a reduced 640-pixel proxy,
full-resolution standard-quality frames, segment boundaries, and live reload.
See [Timeline scrubber](../diagnostics.md#timeline-scrubber) for timing defaults,
proxy approximations, and the difference between canonical samples and encoded
playback. The [portrait storyboard example](https://github.com/sjquant/quickthumb/blob/main/examples/timeline_preview.py)
includes a curved color-changing path and a slide transition.

## Parent links and null controllers

Animatable layers accept `parent="layer-id"`. `Canvas.null(...)` and
`NullLayer(type="null", ...)` create invisible point controllers. IDs are
scene-local explicit `id` values, not generated inspection IDs. Complete JSON
and `Canvas(layers=...)` allow forward references. Fluent calls require a parent
to exist before adding a child; invalid calls leave the canvas unchanged.

```python
from quickthumb import Canvas

scene = (
    Canvas(320, 240)
    .null(position=(100, 50), id="controller")
    .shape("rectangle", (10, 20), 40, 20, "#42CEB7", parent="controller")
)
scene.render_frame(0).save("parented.png")  # Child starts at (110, 70).
```

### Geometry contract

- Authored child placement is parent-local. Position tracks remain offsets
  from that local placement. Percentage values still resolve against the
  original canvas dimensions before entering the parent coordinate space
- World transforms multiply full affine matrices along the chain. Rotated
  non-uniform scales retain their shear; signed axis scales reflect, and a zero
  axis collapses the child and its descendants
- Assigning `parent` does not perform an implicit keep-world adjustment
- Only geometry is inherited. Parent opacity, color, reveal, blur, clips, masks
  and blend modes do not alter an explicitly linked child's appearance
- A null has zero extent, so its normalized anchor has no effect. Position,
  rotation and scale tracks still drive descendants
- Static authored rotation keeps the source engine's existing framing. Its
  rotation is inherited by children without rotating the parent's already-baked
  source pixels twice
- Canonical anchors use a stable authored-source reference, before sampled
  opacity and reveal. Shape/text fill colors and layer opacity are neutralized
  for this reference, so invisible drawable parents remain useful controllers.
  Asset transparency can define the source silhouette; an empty source uses its
  measured body as a geometric fallback
- Image uniform `scale` remains viewport zoom. It changes the image contents,
  not the outer transform inherited by children; axis tracks scale that frame
- Paint order remains document order. Topological order only evaluates matrices

Linked nodes and their ancestors are independent rendering units. Unrelated
layers retain the existing grouping and static-plate path. Full local sources
are prepared before final canvas clipping, so an initially off-canvas child can
move onscreen. Standard/high-quality export, spawn workers and timeline sampling
share this geometry. Video captions retain their existing screen-space overlay
positions and do not inherit their video's transform.

Top-level groups participate as whole visual units, preserving their layout and
existing animation-override rules. Explicit links from or to their auto-layout
descendants are rejected; nulls are not group-layout children. Missing parents,
non-animatable targets and cycles are validation errors with a `/parent` pointer.
Later model mutations are revalidated when a new render is prepared.

### Current adapters and boundaries

Raster, GIF, MP4 and WebM render supported parent chains. This bounded adapter
rejects linked imagery on or below backdrop-dependent layers; linked clips,
masks and stagger; independently animated group descendants; and animated text
values that still need a stable local-source layout adapter. These combinations
are reported as unsupported and raise rather than dropping part of the motion.
Keyed Morph involving a parent-linked slide uses a declared fade fallback.

PPTX, SVG and PDF emit a parent-linked scene as one authored-static PNG
fragment. This preserves the composed geometry and paint order, including shear,
but freezes **all** motion on that scene (also unrelated animated layers). Text and
shapes in that scene are not editable document objects. HTML/PPTX Morph involving
parent geometry uses fade. Unlinked scenes retain their native/vector export paths. Strict export policies reject these fallbacks
before opening files; `export()` also reports the static fallback for SVG/PDF even
though their shared export target is `raster`.

HTML animates eligible hierarchies with six registered numeric affine coefficients
per drawable source and one shared clock. Sibling images retain scene paint order;
opacity belongs to each source, never its parent. This is a **sampled approximation**,
not native transform decomposition: authored stops and interior detail are retained,
with a nominal 120 Hz grid and rotation-aware refinement to prevent full-turn aliasing.
There are at most 4097 common stops, 32768 source/sample rows, and 1048576
graph-node evaluations (including invisible nulls). Between samples,
curves and composed motion can differ from the canonical raster evaluator.

The bounded HTML adapter requires one automatic, zero-start canonical track spec
per node, one track per property, geometry/opacity tracks, and static local sources.
Explicit triggers, delays, composed specs, presets, auto-orientation, unrelated animated layers,
animated chart/QR sources, videos, nonpositive uniform scale, uniform scale with
back easing, image viewport zoom and oversized sampling plans use a declared
whole-scene authored-static fallback. Static top-level groups are atomic sources.
Stable negative axis scale preserves reflections; ordinary positive uniform
scale is supported. Zero/sign-crossing axes and back-eased axis tracks use the
static fallback: floating-point singular matrices cannot guarantee the raster
adapter's exact collapse flag in every browser.
`ExportPolicy(unsupported_motion="error")` rejects sampled approximation;
`static`, `rasterize` and reduced-motion policies emit the authored-static scene.
The exported animation requires browser support for registered CSS numeric
properties (`@property`).
World-layout `inspect()` and `diagnose()` remain guarded; `validate()` checks
the graph and assets and warns that world-layout checks are unavailable.
`inspect_motion()` reports parent links and local track samples; those local
samples are not decomposed approximations of the world affine matrix.
`validate_export()` reports support or the actual unsupported combination, and
strict validation rejects unsupported adapters and Morph fallback.

See [the runnable hierarchy example](https://github.com/sjquant/quickthumb/blob/main/examples/parent_transforms.py).
Documents that omit `parent` keep their previous JSON and render path. These
bounded adapters do not yet complete every part of #161.
