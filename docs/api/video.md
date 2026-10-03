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
