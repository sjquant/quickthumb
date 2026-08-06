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
