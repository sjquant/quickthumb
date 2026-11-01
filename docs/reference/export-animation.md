---
description: Reference for gif, video, and narration in quickthumb.
---

# GIF, video, and narration

[Export reference](../exports.md) · [Choose an output format](../output-guide.md)

## Animated GIF & video { #animated-gif-video }

See [animation timing](../timing.md) for canonical sampling versus encoded frame
counts, slide/narration clocks, captions and interactive HTML behavior.

Animated export renders per-layer `animation` effects and deck slide `transition`s as real raster frames, sampled through the same pixel pipeline as PNG output. Canvas and Deck GIF/MP4/WebM/MOV all play this animated timeline, including file exports with no explicit options.

```python
from quickthumb import AudioTrack, Canvas, Deck, Fade, GifOptions, VideoOptions
from quickthumb.transitions import Push

canvas = Canvas(1280, 720).background(color="#101820").text(
    content="Hello", position=("50%", "50%"), size=96, color="#FFFFFF",
    animation=Fade(duration=0.6),
)
canvas.render("hello.gif")                     # defaults: 20 fps, 3s hold
canvas.render(
    "preview.gif",
    animation=GifOptions(fps=8, max_size=(540, 960), colors=128),
)
mp4 = canvas.to_mp4(fps=30, hold=2.0)          # tunable variants return bytes

other = Canvas(1280, 720).background(color="#204060")
deck = Deck(1280, 720).slide(canvas).slide(other, transition=Push(direction="left"))
gif = deck.to_gif(fps=20, hold=3.0, loop=0)
webm = deck.to_webm(fps=30, hold=3.0)
```

Every effect takes `duration`, `delay`, and `trigger`, plus two timing controls:

- `easing` picks the curve the reveal follows, from the shared easing vocabulary
  (`"linear"`, `"ease"`, `"ease_out_cubic"`, `"ease_out_back"`, …). Legacy effects
  default to `"ease"`; canonical presets resolve their easing/feel and otherwise
  use `"linear"`. A bar that reports elapsed time needs `"linear"` to represent
  its progress. HTML sends named easing and custom cubic-bezier
  timing functions to CSS. Named polynomial curves use the existing CSS
  cubic-bezier approximations: their shape is similar, but intermediate pixel
  states need not match canonical sampling exactly.
- `start` pins the effect to an absolute time on the slide instead of chaining it
  to whatever ran before. Anchored effects do not move the cursor the relative
  effects around them are chained from, so the two styles can be mixed.

```python
from quickthumb import Wipe

canvas.shape(
    shape="rectangle", position=(0, 700), width=1280, height=6, color="#E8A552",
    animation=Wipe(direction="right", duration=6.0, easing="linear"),
)
canvas.shape(
    shape="rectangle", position=(80, 180), width=180, height=14, color="#E8A552",
    animation=Wipe(direction="right", duration=2.4, start=0.9, easing="linear"),
)
```

A canonical `AnimationSpec` with a `stagger` moves each target on its own beat.
Line targets are sliced out of the layer's finished render, so every line keeps
the layout it was drawn with and waits off screen until its turn:

```python
from quickthumb import AnimationSpec

canvas.text(
    content="가로로 한 번.\n세로로 한 번.\n미리보기로 또 한 번.",
    position=(80, 150), size=38, color="#F2EFE9", line_height=1.5,
    animation=AnimationSpec.rise(
        from_="bottom", distance=26, duration=0.45, stagger=0.32, target="lines"
    ),
)
```

Lines set tight enough to touch cannot be told apart in the render, and word and
character targets have no separable band; those fall back to moving the layer as
a whole.

Static text and top-level groups may also stagger as leaves of an explicit
parent chain. Separated bands inherit the ancestor's full affine transform and
keep their own anchors and appearance tracks. This uses the same partial band
adapter and whole-block fallback described above; a staggered layer cannot itself
be another layer's parent. Counter-plus-stagger and dynamic sources remain
guarded. See the [parent transform boundaries](../api/video.md#current-adapters-and-boundaries)
and runnable `examples/parent_stagger.py` example.

`Canvas.render()` and `Deck.render()` accept a format-specific options object for
animated file output. Use `GifOptions` for GIF (`fps`, `hold`, `matte`, `loop`,
`max_size=(width, height)`, and `colors`) and `VideoOptions` for MP4/WebM/MOV
(`fps`, `hold`, `matte`, `soundtrack=AudioTrack(...)`, `loop_audio`, and WebM/MOV
`transparent=True`). Both accept `workers=1` and `render_quality="standard"`.
GIF sizing and palette controls are rejected for video output, and video
options are rejected for GIF output. The generic `render(..., quality=...)`
option remains reserved for JPEG and WebP raster output.

Both option models use `hold=3.0` for the settled-state hold, matching `hold`
on Canvas and Deck byte methods. It must be
a finite nonnegative number; booleans and strings are rejected. A default hold
is omitted from serialized options and restored when loaded; an explicit zero
is retained. Narration and explicit Deck slide durations still determine the
video schedule, while Deck GIF continues to ignore those per-slide durations.
Deck animated video retains its existing restriction: `hold=0` fails when any slide has neither narration nor an explicit
positive duration, because its audio schedule requires a positive silent bed.
Use a positive hold for those slides. Canvas, Deck GIF, and silent image sequences
continue to permit a zero hold.

The byte methods accept the same rendering controls as keyword-only scalars:
`workers=1` and `render_quality="standard"` on Canvas GIF/MP4/WebM/MOV and Deck
GIF/animated MP4/WebM/MOV, plus `max_size=None` and `colors=None` on GIF.
These methods use `hold` and do not accept options objects. Narration uses the
same Deck MP4 timeline as other video output.

File execution resolves the format before checking export policy. Canvas and
Deck MP4 always play the animated timeline, with default `VideoOptions()` when
no options are supplied.
Unused authored Morph transitions do not produce fallback errors or receipt
diagnostics for static files or reduced-motion execution.
Reduced animation retains the encoder's holds and default transitions between
slides. See [animation timing](../timing.md) for sampling rates and encoded visual
frame counts and durations.

`ExportResult.pixel_metrics.width` and `height` remain the canonical first-canvas
raster dimensions. They do not describe GIF resizing or MP4/WebM cropping. Image
sequence results separately report their full-size output dimensions.

`validate_export(target)` is a declared motion-capability query, independent of
file execution options. For example, `validate_export("mp4")` still queries
animated video, even with a reduced-motion policy. Concrete `svg` and `pdf`
queries describe their static document fallback with the existing `raster`
family label. Targets are case-insensitive; `jpg`, `jpeg`, `webp`, `png`, `gif`,
`mp4`, `webm`, `mov`, `htm`, and `image_sequence` are accepted as corresponding family
aliases. The GIF query uses `raster`, while a GIF `ExportResult.target` remains
`video` for compatibility.

## Narrated deck video

A deck can be exported as a video with a voice-over per slide:

- Pass `audio=` to `Deck.slide()`. Without `duration=`, the narration duration
  is measured with `ffprobe`. An explicit `duration=` trims the audio or pads
  it with silence. A slide with no audio holds silently for `hold` (3 seconds).
- `deck.export("deck.mp4")` and `deck.render("deck.mp4")` play layer animations
  and transitions with narration by default. `deck.to_mp4()`, `deck.to_webm()`,
  and `deck.to_mov()` return animated video bytes.
- To show still slides with narration, author static canvases and set an
  explicit `Cut()` transition. The output is H.264/yuv420p with AAC when audio
  is present. Omitting a transition uses the default fade, not a cut.
  `reduced_motion=True` also selects default transitions; it is not a still-slide
  export mode. Existing animated layers still play in the ordinary MP4 path.
- Add background music with
  `animation=VideoOptions(soundtrack=AudioTrack(path="music.mp3", volume=0.16, loop=True))`
  on `deck.export()` or `deck.render()`. Quickthumb mixes it with the slide
  narration; callers do not need to pre-mix audio themselves.

```python
from quickthumb import Canvas, Deck, VideoOptions
from quickthumb.transitions import Cut

deck = Deck(640, 360).transition(Cut())
deck.slide(Canvas(640, 360).background(color="#123456"),
           audio="voice.wav", duration=2.5)
deck.slide(Canvas(640, 360).background(color="#456789"), duration=1.0)
result = deck.export("narrated.mp4", animation=VideoOptions(fps=30))
mp4_bytes = deck.to_mp4(fps=30)
```

## Timing

Video and GIF follow the HTML slideshow's timing, except that nobody can
click: `on_click` animations play automatically, one after another, like
`after_previous` (PowerPoint's own video export does the same). Each slide
plays its transition over the previous slide's last frame, runs its
animations (starting with the transition, as in HTML), then holds its settled
state for the transition's `advance_after` if set, otherwise for `hold`.
In narrated MP4/WebM/MOV output, the inferred or explicit narration duration
(or the silent-slide default) extends the visual slide when it is longer
than `advance_after`. A slide with no transition cross-fades in over 0.5s
(slide 0 with none starts instantly); set a transition on slide 0 to animate
in from the matte, which also makes looping GIFs wrap smoothly.

GIF is encoded by Pillow with per-frame durations, so no extra dependency is needed. MP4 (H.264), WebM (VP9), and MOV (ProRes 4444) require the `ffmpeg` binary on `PATH` (or pointed to by the `QUICKTHUMB_FFMPEG` environment variable).

Canvas MP4, WebM, and MOV output can carry a soundtrack: any audio file ffmpeg decodes (MP3, WAV, AAC, OGG, ...), encoded as AAC in MP4/MOV and Opus in WebM:

```python
mp4 = canvas.to_mp4(soundtrack="music.mp3")                    # loops to fill the video
mp4 = canvas.to_mp4(soundtrack="jingle.wav", loop_audio=False) # plays once, then silence
```

The audio is always trimmed to the video length. For an `AudioTrack`, `loop=True` repeats a shorter track and `loop=False` plays it once before silence; `loop_audio` is an explicit override. Legacy string paths keep the previous looping default. GIF exports do not accept a soundtrack.

!!! tip "Format tips"
    - **Backgrounds**: Frames are composited on an opaque matte (default black). Use `transparent=True` with WebM or MOV for alpha overlays.
    - **Resolution**: H.264/VP9 4:2:0 video encoding requires even pixel dimensions (e.g. 1280×720).
    - **GIF Optimization**: Use `max_size=(w, h)` and `colors=128` (or 64) in `GifOptions` to keep GIF file sizes compact.
    - **Narrated Decks**: A single Deck video export supports up to 64 narrated slides. Split longer narrated presentations into separate videos.

