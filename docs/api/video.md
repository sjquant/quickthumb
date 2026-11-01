---
description: Reference for quickthumb video layers, including trimming, fit, speed, captions, color grading, masking, and animation.
---

# Video

`.video()` adds a video clip to a canvas. It behaves just like any other visual layer: you can trim, scale, loop, reposition, round corners, grade colors, mask, and animate it across your timeline.

Video layers render natively in animated outputs (GIF, MP4, WebM, MOV) and in `render_frame(...)`. In static document targets (PPTX, PDF, SVG, HTML), the clip renders as a static still frame.

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
| `source` | `str` | **required** | File path to the video. |
| `position` | `tuple` | **required** | `(x, y)` position in pixels or percentage strings (`"50%"`). |
| `width` | `int` | **required** | Layer width in pixels. |
| `height` | `int` | **required** | Layer height in pixels. |
| `fit` | `str \| FitMode` | `"contain"` | How the video fits inside its layer box: `"contain"`, `"cover"`, or `"fill"`. See [FitMode](enums.md#fitmode). |
| `trim_start` | `float` | `0.0` | Playback start time in the source file, in seconds. |
| `trim_end` | `float \| None` | `None` | Playback end time in the source file. Defaults to clip end. |
| `start` | `float` | `0.0` | When the clip starts playing on the timeline, in seconds. |
| `duration` | `float \| None` | `None` | How long the clip appears on the scene. |
| `speed` | `float` | `1.0` | Playback speed multiplier (e.g. `0.5` for half speed, `2.0` for double speed). |
| `volume` | `float` | `1.0` | Clip audio volume (for MP4/WebM/MOV). GIF exports are always silent. |
| `captions` | `list \| None` | `[]` | Timed caption text overlays burned into the frames. |
| `border_radius` | `int` | `0` | Corner radius in pixels. |
| `opacity` | `float` | `1.0` | Layer opacity from `0.0` to `1.0`. |
| `rotation` | `float` | `0.0` | Rotation angle in degrees. |
| `align` | `str \| Align \| tuple \| None` | `None` | Anchor point for `position`. See [Align](enums.md#align). |
| `blend_mode` | `str \| BlendMode \| None` | `None` | Compositing blend mode. |
| `effects` | `list \| None` | `[]` | Visual filters: `Filter`, `Duotone`, `Grain`, `Glow`, `Shadow`, `Stroke`, `InnerShadow`. |
| `clip` | `LayerClip \| None` | `None` | Clip the layer to a geometric bounding box. |
| `mask` | `LayerMask \| None` | `None` | Mask the layer with a shape or path. |
| `animation` | `Animation \| AnimationSpec \| list \| None` | `None` | Entrance/exit presets or custom keyframe motion. |

## Examples

### Trimming and color grading

Trim a clip to a 6-second window, convert it to black-and-white, and round the corners:

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
    border_radius=16,
    effects=[Filter(saturation=0.0, contrast=1.15)],
)
```

### Animating position

Slide a video horizontally across the scene while it plays:

```python
from quickthumb import AnimationSpec, Canvas, KeyframeSpec, PositionTrack, TimingSpec

canvas = Canvas(1280, 720).video(
    "clip.mp4",
    position=(0, 200),
    width=480,
    height=270,
    fit="cover",
    duration=4.0,
    animation=AnimationSpec.timeline(
        PositionTrack(
            keyframes=[
                KeyframeSpec(time=0.0, value=(0, 0)),
                KeyframeSpec(time=4.0, value=(800, 0)),
            ]
        ),
        timing=TimingSpec(start=0.0, duration=4.0),
        easing="ease_in_out",
    ),
)
```

### Spring easing

Add natural, physics-based bounce using `SpringEasing`:

```python
from quickthumb import AnimationSpec, KeyframeSpec, PositionTrack, SpringEasing

motion = AnimationSpec.timeline(
    PositionTrack(keyframes=[
        KeyframeSpec(time=0, value=(0, 0)),
        KeyframeSpec(time=1, value=(180, 0)),
    ]),
    easing=SpringEasing(stiffness=100, damping=10, mass=1),
)
```

### Wiggle track modifiers

Attach `Wiggle(frequency=2, amplitude=12, seed=42)` to any track to add organic, deterministic jitter:

```python
from quickthumb import AnimationSpec, KeyframeSpec, PositionTrack, TimingSpec, Wiggle

motion = AnimationSpec.timeline(
    PositionTrack(
        keyframes=[KeyframeSpec(time=0, value=(0, 0))],
        wiggle=Wiggle(frequency=2, amplitude=12, seed=42),
    ),
    timing=TimingSpec(duration=2),
)
```

## Transparent video overlays

Export videos with transparent backgrounds (ideal for lower-thirds, animated stickers, or game overlays):

- **WebM (VP9 with alpha)**: `VideoOptions(transparent=True)`
- **ProRes 4444 MOV**: `canvas.export("overlay.mov", animation=VideoOptions(transparent=True))`

```python
from quickthumb import Canvas, VideoOptions

canvas = Canvas(1280, 720).shape("pill", (100, 600), 400, 80, "#42CEB7")
canvas.export("lower_third.webm", animation=VideoOptions(transparent=True))
```

See [Transparent video](../reference/export-transparency.md) for details.

## Notes

- **Source length**: If the scene is longer than the source clip, set `speed` below `1.0` to stretch playback smoothly.
- **Captions**: Captions render above all layers in the composition to guarantee legibility.
- **Diagnostics**: `canvas.diagnose()` automatically checks caption placement, margins, and reading speed.

---

# Advanced Motion & Compositing

The sections below describe advanced animation and compositing capabilities shared across all visual layers (text, shapes, images, paths, and video).

## Curved motion paths

Use `PositionKeyframeSpec` with tangent handles to create smooth Bézier motion curves instead of straight lines:

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
            auto_orient=True,  # Rotate layer to follow the path tangent
        ),
        timing=TimingSpec(start=0, duration=4),
        easing="linear",
    ),
)
```

### Handles and speed

- `out_tangent=(dx, dy)` shapes the curve leaving a keyframe.
- `in_tangent=(dx, dy)` shapes the curve entering a keyframe.
- With `easing="linear"`, layers travel along the curve at a constant speed.

### Following the tangent

When `auto_orient=True`, the layer automatically rotates to match its direction of travel (facing right is `0°`, clockwise positive).

### Export support

Curved motion paths are supported in raster animations (GIF, MP4, WebM) and HTML. Document targets (PPTX, PDF) display the initial frame.

## Transform anchors and independent scale

By default, layers scale and rotate around their center (`anchor=(0.5, 0.5)`). Customize `anchor=(x, y)` to set a different pivot:

- `(0, 0)`: Top-left
- `(0.5, 0.5)`: Center (default)
- `(1, 1)`: Bottom-right

```python
from quickthumb import (
    AnimationSpec, Canvas, KeyframeSpec, RotationTrack, ScaleXTrack, ScaleYTrack, TimingSpec,
)

canvas = Canvas(320, 240).shape(
    "rectangle", (100, 100), 80, 40, "#42CEB7",
    anchor=(0, 1),  # Pivot around bottom-left corner
    animation=AnimationSpec.timeline(
        ScaleXTrack(keyframes=[KeyframeSpec(time=0, value=1), KeyframeSpec(time=2, value=1.5)]),
        ScaleYTrack(keyframes=[KeyframeSpec(time=0, value=1), KeyframeSpec(time=2, value=0.6)]),
        RotationTrack(keyframes=[KeyframeSpec(time=0, value=0), KeyframeSpec(time=2, value=30)]),
        timing=TimingSpec(duration=2),
    ),
)
```

### Export support

Custom anchors and independent axis scaling (`ScaleXTrack`, `ScaleYTrack`) work across raster frames, GIF, MP4, WebM, and modern HTML presentations.

## Animated text and shape colors

Animate fills and text colors smoothly over time using `ColorTrack`:

```python
from quickthumb import AnimationSpec, Canvas, ColorTrack, KeyframeSpec, TimingSpec

canvas = Canvas(640, 360).text(
    "Color in motion", position=(40, 40), size=48, color="#FF0000",
    animation=AnimationSpec.timeline(
        ColorTrack(keyframes=[
            KeyframeSpec(time=0, value="#FF0000"),
            KeyframeSpec(time=2, value="#0055FF"),
        ]),
        timing=TimingSpec(start=0, duration=2),
    ),
)
```

Colors interpolate smoothly in perceptually uniform Oklab color space, avoiding muddy transitions.

## Live timeline preview

Scrub through animations interactively in your browser without encoding a video file:

```bash
quickthumb serve scene.py --timeline
```

This launches a live scrubber at `http://localhost:3030/timeline` with frame seeking and instant reload on save.

## Parent links and null controllers

Link layers hierarchically using `parent="parent-layer-id"`. When the parent moves, rotates, or scales, its children follow:

```python
from quickthumb import Canvas

scene = (
    Canvas(320, 240)
    .null(position=(100, 50), id="controller")  # Invisible point controller
    .shape("rectangle", (10, 20), 40, 20, "#42CEB7", parent="controller")
)
```

### Geometry contract

- Child positions are relative to their parent's coordinate space.
- Parent motion transforms (position, rotation, scale) are inherited by children.
- Parent styling (opacity, effects, masks) is **not** inherited, keeping child styling independent.

### Current adapters and boundaries

Parent links are fully supported in raster, GIF, MP4, and WebM exports. In document formats (PPTX, PDF, SVG), parented groups export as static rendered fragments.

## Text range selectors

Animate text word-by-word, line-by-line, or character-by-character using `RangeSelector`:

```python
from quickthumb import AnimationSpec, Canvas, KeyframeSpec, PositionTrack, RangeSelector, TimingSpec

canvas = Canvas(800, 400).text(
    "Words appear one by one",
    size=48,
    color="#FFFFFF",
    position=(50, 150),
    animation=AnimationSpec.timeline(
        PositionTrack(keyframes=[
            KeyframeSpec(time=0, value=(0, 20)),
            KeyframeSpec(time=0.4, value=(0, 0)),
        ]),
        selector=RangeSelector(
            target="words",  # "words", "lines", or "characters"
            offset=[KeyframeSpec(time=0, value=-100), KeyframeSpec(time=2, value=100)],
        ),
        timing=TimingSpec(duration=2),
    ),
)
```

### Character ownership

When `target="characters"`, each glyph receives its own animation phase. Spaces and punctuation are preserved with accurate font metrics.

## Track mattes

Use another layer as an alpha or luma mask using `mask=TrackMatte(layer="source-id")`:

```python
from quickthumb import Canvas, TrackMatte

canvas = (
    Canvas(640, 360)
    .shape("ellipse", (120, 80), 200, 200, color="#FFFFFF", id="hole")
    .image("photo.jpg", position=(0, 0), width=640, height=360, mask=TrackMatte(layer="hole"))
)
```

- `mode="alpha"`: Masks using the source layer's transparency.
- `mode="luma"`: Masks using the source layer's brightness.
- `invert=True`: Inverts the cutout area.

### Animated shape-mask geometry

Animate a mask's position, size, or feather dynamically using `MaskPositionTrack`, `MaskSizeTrack`, or `MaskFeatherTrack`.

### Native HTML shape masks

Rectangle, pill, and ellipse masks export to clean CSS clipping in HTML slideshows.

### Owner-attached path masks

Attach custom SVG path masks directly to any layer using `LayerMask(shape="path", d="M0 0 H40 V40 H0 Z")`.

### Path-shaped mattes

Reference a `Canvas.path()` layer as a dynamic, moving track matte for custom animated cutouts.
