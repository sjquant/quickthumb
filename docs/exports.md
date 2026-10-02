---
description: Export quickthumb canvases to SVG, editable PowerPoint (PPTX), PDF documents, and animated GIF/MP4/WebM/MOV alongside PNG/JPEG/WEBP.
---

# Exporting to SVG, PPTX, PDF & video

Beyond raster images, a canvas can render to vector, document, and animated formats. The output format is detected from the file extension:

```python
canvas.render("thumbnail.png")   # raster (PNG/JPEG/WEBP)
canvas.render("thumbnail.svg")   # vector SVG
canvas.render("thumbnail.pptx")  # editable PowerPoint slide
canvas.render("thumbnail.pdf")   # single-page PDF
canvas.render("thumbnail.gif")   # animated GIF playing the layer animations
canvas.render("thumbnail.mp4")   # H.264 video (requires ffmpeg); .webm for VP9
canvas.render("thumbnail.mov")   # ProRes 4444 video (requires ffmpeg with prores_ks)
```

Each format also has a direct method when you want the content in memory:

```python
svg_markup = canvas.to_svg()
pptx_bytes = canvas.to_pptx()
pdf_bytes = canvas.to_pdf()
gif_bytes = canvas.to_gif()
mp4_bytes = canvas.to_mp4()      # and canvas.to_webm() / canvas.to_mov()
```

## How export works

Exporters keep layers **native** wherever the target format can express them, and embed **pixel-exact PNG fragments** (rendered by the regular pipeline) everywhere else. Positions, wrapping, and alignment are computed with the same layout math as the raster renderer, so output matches the PNG render closely.

| Layer | SVG | PPTX | PDF |
| --- | --- | --- | --- |
| Background color / gradient | Native `rect` + gradient defs | Native shape fill (linear gradients native, radial embedded) | Native fill; opaque gradients native, translucent gradients embedded |
| Outline | Native `rect` stroke | Native bordered rectangle | Native rectangle stroke |
| Shapes (all primitives) | Native elements, incl. rotation and stroke/shadow/glow | Native autoshapes; polygons become freeforms | Native paths incl. rotation; shapes with effects embedded |
| Text (simple & rich) | Native `<text>` per line/run, incl. wrapping, letter spacing, gradient fills, effects | Editable text boxes with per-run styling | Native selectable text when its font can be embedded and the text does not need complex shaping; unsupported fonts and gradient/image fills or blur effects are embedded as pixels |
| Groups (auto-layout) | Children exported natively at their layout positions | Same | Same |
| Images & image-filled text | Embedded PNG fragment | Embedded picture | Embedded picture |
| SVG layers | Embedded as vector data URL (raster when effects are applied) | Embedded picture | Embedded picture |
| Blend modes & custom layers | Everything below the last blend/custom layer is flattened into one PNG | Same | Same |

## SVG

```python
svg = canvas.to_svg()
svg = canvas.to_svg(embed_fonts=True)
```

By default the SVG references fonts by family name (`font-family="Roboto"`), which keeps files small but requires the font on the viewing machine. With `embed_fonts=True` the used font files are inlined as `@font-face` data URLs so text renders identically everywhere.

!!! note "Viewer support"
    Shadow and glow effects use SVG filters (`feGaussianBlur`). Browsers render them faithfully; some minimal SVG rasterizers apply filters only partially.

## PPTX

PPTX export requires the optional dependency:

```bash
uv pip install "quickthumb[pptx]"
```

The canvas becomes a single slide sized to the canvas pixels (at 96 dpi). Text stays fully editable — font family, size, weight, color, alignment, and line wrapping are carried over run by run, and stroke/shadow/glow effects map to PowerPoint text outline and effect properties.

```python
canvas.render("promo.pptx")
# or
with open("promo.pptx", "wb") as f:
    f.write(canvas.to_pptx())
```

!!! note "Fidelity"
    PowerPoint lays text out with its own font metrics, so text placement is a close approximation rather than pixel-identical. Radial background gradients and multi-stop text gradients beyond what DrawingML supports are embedded as pictures or approximated.

## PDF

PDF export requires the optional dependency:

```bash
uv pip install "quickthumb[pdf]"
```

The canvas becomes a single PDF page sized to the canvas pixels (one point per pixel). Backgrounds, outlines, shapes, and eligible text are drawn as native PDF vector primitives using the same layout math as the raster renderer. Fonts that can be safely embedded are subset when their text does not need complex shaping; unsupported text is embedded as a pixel-exact PNG fragment so its visual result remains faithful.

```python
canvas.render("promo.pdf")
# or
with open("promo.pdf", "wb") as f:
    f.write(canvas.to_pdf())
```

!!! note "Fidelity"
    PDF shadings cannot express transparency, so translucent gradients (and gradients with translucent stops) are embedded as pictures. Blur effects (shadow, glow), strokes on shapes, and gradient/image glyph fills have no faithful PDF vector form and are likewise embedded as pixel-exact PNG fragments.

## Animated GIF & video (Canvas MP4/WebM/MOV, Deck GIF/WebM/MOV)

Animated export renders per-layer `animation` effects and deck slide `transition`s as real raster frames, sampled through the same pixel pipeline as PNG output. Canvas GIF/MP4/WebM/MOV and Deck GIF/WebM/MOV play this animated timeline. `deck.render("deck.mp4", animation=VideoOptions(...))` also uses it; Deck MP4 without `VideoOptions` is the separate static narration workflow below.

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
gif = deck.to_gif(fps=20, slide_duration=3.0, loop=0)
webm = deck.to_webm(fps=30, slide_duration=3.0)
```

Every effect takes `duration`, `delay`, and `trigger`, plus two timing controls:

- `easing` picks the curve the reveal follows, from the shared easing vocabulary
  (`"linear"`, `"ease"`, `"ease_out_cubic"`, `"ease_out_back"`, …). It defaults to
  `"ease"`; a bar that reports elapsed time wants `"linear"`, or it will
  misrepresent its own progress.
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
guarded. See the [parent transform boundaries](api/video.md#current-adapters-and-boundaries)
and runnable `examples/parent_stagger.py` example.

`Canvas.render()` and `Deck.render()` accept a format-specific options object for
animated file output. Use `GifOptions` for GIF (`fps`, `matte`, `loop`,
`max_size=(width, height)`, and `colors`) and `VideoOptions` for MP4/WebM/MOV
(`fps`, `matte`, `soundtrack=AudioTrack(...)`, `loop_audio`, and WebM/MOV
`transparent=True`). GIF sizing and palette controls
are rejected for video output, and video options are rejected for GIF output.
The generic `quality` option remains reserved for JPEG and WebP raster output.

File execution resolves the concrete format and animation mode before checking
export policy. In particular, `Deck.render("slides.mp4")` and
`Deck.export("slides.mp4")` both use narrated still slides; pass `VideoOptions()`
to play the animated timeline. Canvas MP4 always uses the animated path.
Unused authored Morph transitions do not produce fallback errors or receipt
diagnostics for narrated stills, static files, or reduced-motion execution.
Reduced animation retains the encoder's holds and default transitions between
slides. Built-in animated GIF and MP4/WebM/MOV exports report the encoded visual
frame count and duration. GIF counts include palette-equivalent frame merging,
and duration follows its centisecond delays; its reported FPS remains the
configured sampling rate. Video duration is the encoded frame count divided by
that rate, excluding container audio padding. Narrated still-slide MP4 and
custom render overrides retain their nominal timing estimates.

`ExportResult.pixel_metrics.width` and `height` remain the canonical first-canvas
raster dimensions. They do not describe GIF resizing or MP4/WebM cropping. PNG
sequence results separately report their full-size output dimensions.

`validate_export(target)` is a declared motion-capability query, independent of
file execution options. For example, `validate_export("mp4")` still queries
animated video, even with a reduced-motion policy. Concrete `svg` and `pdf`
queries describe their static document fallback with the existing `raster`
family label. Targets are case-insensitive; `jpg`, `jpeg`, `webp`, `png`, `gif`,
`mp4`, `webm`, `mov`, `htm`, and `png_sequence` are accepted as corresponding family
aliases. The GIF query uses `raster`, while a GIF `ExportResult.target` remains
`video` for compatibility.

### Transparent WebM

VP9 WebM can preserve alpha through `VideoOptions(transparent=True)`, or the
keyword-only `transparent=True` argument to `Canvas.to_webm()` and
`Deck.to_webm()`. The default is `False`; existing opaque exports keep their
matte and encoder settings. This is an export option, not a layer or motion
property, so it is absent from Canvas/Deck JSON and `inspect_motion()`;
`VideoOptions.model_validate_json()` and its model JSON schema expose the strict
boolean option. `validate_export()` continues to describe document motion,
while `render()` rejects transparent options on unsupported output formats.

```python
canvas.render("overlay.webm", animation=VideoOptions(transparent=True))
deck.render("overlay.webm", animation=VideoOptions(transparent=True, quality="high", workers=2))
webm_bytes = canvas.to_webm(transparent=True)
options = VideoOptions.model_validate_json('{"transparent": true, "fps": 24}')
```

Only the export matte is skipped. Authored backgrounds remain visible, empty
areas and mixed-size slide letterboxing stay transparent, and a transition on
slide zero starts from transparency. Fade and mask transitions interpolate
premultiplied colors; covering and scaled slides composite with source-over
alpha. Keyed Morph normalizes mixed-size slides to the first slide's output
space before interpolating positions, dimensions and translucent pixels. The
existing parent/caption Morph fallback restrictions still apply.

Both compositing quality modes, spawn workers, soundtracks and Deck narration
work with transparent WebM. The encoder streams RGBA into VP9 `yuva420p` with
lossless VP9 coding to protect the alpha plane. The RGBA-to-YUV conversion can
change decoded alpha by one 8-bit level; RGB remains chroma-subsampled (4:2:0),
so source color pixels are not lossless. Files can be larger than opaque WebM.
The existing bounded frame batches and atomic destination replacement remain.
Transparent transitions use temporary floating-point planes for accurate
premultiplied blending; memory usage grows with frame size and worker count.
MP4, GIF, and document/raster output reject this video option before writing
the destination. PNG animation sequences use the separate
[`export_png_sequence()` API](#png-image-sequences).

Use a player or editor that supports VP9 WebM alpha. To inspect the actual
alpha plane with FFmpeg, select the libvpx decoder **before** the input:

```bash
ffmpeg -c:v libvpx-vp9 -i overlay.webm -frames:v 1 -pix_fmt rgba frame.png
```

The native VP9 decoder may report/decode only color; `alpha_mode` metadata
alone is not proof of preserved transparency. The regression tests decode RGBA
with libvpx and compare transparent, translucent and opaque pixels. See
`examples/transparent_lower_third.py` for an overlay with an authored translucent
panel and transparent surroundings.

### ProRes 4444 MOV

Canvas and Deck can export `.mov` with the fixed ProRes 4444 profile, using
FFmpeg's `prores_ks` encoder. MOV always plays the animated timeline, including
Deck transitions and narration. `transparent` is the same strict boolean option
as WebM and defaults to `False`: ordinary MOV composites onto the matte; opt-in
alpha skips only that matte. Authored backgrounds, letterboxing, transitions,
quality modes and workers follow the transparent WebM behavior above.

```python
canvas.render("overlay.mov", animation=VideoOptions(transparent=True, fps=24))
deck.export("overlay.mov", animation=VideoOptions(transparent=True, quality="high", workers=2))
mov_bytes = canvas.to_mov(hold=2.0, transparent=True)
mov_bytes = deck.to_mov(slide_duration=2.0, transparent=True, soundtrack="music.wav")
```

MOV retains odd dimensions and even 1-pixel-wide or 1-pixel-high frames; it does
not crop the final row or column. It uses full-resolution 4:4:4 chroma with
`yuv444p10le` encoder input for opaque output and `yuva444p10le` with 16-bit
alpha coding for transparent output. The renderer still supplies **8-bit RGBA**;
16-bit alpha coding does not create additional source precision. Decoding all
256 source alpha levels with FFmpeg 7.1.5 measured a maximum error of one 8-bit
level with 16-bit alpha coding, compared with two levels for 8-bit coding.
Transparent and opaque endpoints are retained. This conversion is not guaranteed
to reproduce source alpha exactly, and ProRes color compression plus RGB/YUV
conversion is lossy despite 4:4:4 chroma. The codec's lossless alpha coding claim
does not imply lossless RGBA conversion. See the
[FFmpeg ProRes options](https://www.ffmpeg.org/ffmpeg-codecs.html#ProRes) and
[Apple ProRes white paper](https://www.apple.com/final-cut-pro/docs/Apple_ProRes.pdf).

Soundtracks, per-slide narration and embedded video audio are encoded as AAC,
using the same scheduling, looping, padding and trimming rules as animated MP4.
A Canvas MOV with no audio inputs contains only video. Deck MOV retains the
existing narration workflow’s silent AAC bed even when no slides have narration.
The fixed codec/profile and audio choices have no selection API. ProRes files can be substantially larger than
WebM/MP4, and require a ProRes-capable player or editor. Encoded segments stay
bounded and destinations are replaced only after the full encode and mux succeed.
A missing `prores_ks` encoder raises a rendering error and preserves any existing
destination. Decode pixels, rather than relying on profile metadata, to check alpha:

```bash
ffmpeg -i overlay.mov -frames:v 1 -pix_fmt rgba frame.png
```

`examples/transparent_lower_third.py` writes both WebM and ProRes MOV overlays.

### PNG image sequences

`Canvas.export_png_sequence(output_directory, *, options=None, policy=None)` and
the matching Deck method export the actual animated timeline as independent,
lossless PNG files. Every frame contains the renderer's exact **8-bit RGBA bytes
with straight alpha**, including hidden RGB where the rendered frame supplies
it. The export adds no matte; authored backgrounds remain visible. Odd sizes
and one-pixel dimensions retain every row and column. Imported images are not
ICC-normalized, so the PNGs and manifest make no sRGB/color-profile claim and
carry no inherited ICC or sRGB metadata.
Every frame uses the first canvas's full dimensions; differently sized slides
are scaled proportionally and centered with transparent padding.

```python
from quickthumb import PngSequenceOptions

# The parent must already exist; this destination must be new.
result = canvas.export_png_sequence(
    "overlay_frames",
    options=PngSequenceOptions(fps=24, hold=2, quality="high", workers=2),
)
print(result.frame_count, result.duration, result.manifest_path)
```

`PngSequenceOptions` has only four fields:

| Field | Default | Allowed values |
| --- | --- | --- |
| `fps` | `30` | Finite numeric rate greater than zero and at most 120 |
| `hold` | `3` | Finite nonnegative seconds held after animation |
| `workers` | `1` | Strict integer from 1 through 8 |
| `quality` | `"standard"` | `"standard"` or `"high"` |

The models and JSON schemas are public: `PngSequenceOptions`,
`PngSequenceManifest`, and `PngSequenceResult` support `model_dump_json()`,
`model_validate_json()`, and `model_json_schema()`. They describe this Python
export API; they add no Canvas/Deck document fields or raster format enum values.
Existing still `.png` rendering and animation bytes methods keep their behavior.

The directory contains `000000.png`, `000001.png`, and so on, plus one compact
`manifest.json`. Its fixed relative `filename_pattern` is `%06d.png` (at least
six digits), with `start_index: 0`. It records `version: "1"`, document `kind`,
`format: "png_sequence"`, actual `frame_count`, `fps`, `duration`, `width`,
`height`, `mode: "RGBA"`, `bit_depth: 8`, and `alpha: "straight"`. There is no
growing list of frames, asset paths, or timestamps. The result contains the same
fields plus absolute `output_directory`, `manifest_path`, and
`capability_report` diagnostics. Repeated frames are separate editable files,
not hardlinks. Frame memory stays bounded as the sequence grows; the existing
scene preparation and per-worker buffers still consume memory.

Timing follows animated exports, including explicit slide durations,
`advance_after`, narration-derived visual timing, transitions, and Morph.
Cumulative frame allocation avoids drift across fractional holds; short or
zero-hold still slides receive at least one frame. The reported duration is
exactly `frame_count / fps`, measured from the files actually written. This
can differ from the independent timeline sampler's duration or sample count.
`validate_export("png_sequence")` and `inspect_motion(target="png_sequence")`
use video motion capabilities. Existing strict/reduced-motion policies and
parent, Morph, caption, and worker restrictions apply.

Sequences are silent: no audio encoding, mux, soundtrack, or audio sidecars.
Narration retains its existing file validation and duration inference, without
the encoder's 64-audio-input limit. PNG-only scenes need no FFmpeg; inferred
narration lengths still require ffprobe, and video layers retain their normal
probe/decode requirements.

All frames and the manifest are prepared in a private sibling staging directory;
render resources close before publication. A single exclusive rename publishes
the complete directory, refusing files, directories, and live or dangling
symlinks, including destinations created by a competing exporter. This requires
Linux `renameat2(RENAME_NOREPLACE)`, macOS `renamex_np(RENAME_EXCL)`, or Windows
same-volume rename support. Unsupported systems/filesystems fail clearly with
no ordinary Unix rename or copying fallback. Failures clean only verified owned
staging and never delete the destination, even if a commit error has an ambiguous
outcome. This is atomic visibility and no-overwrite publication, not an fsync
crash-durability guarantee or protection from hostile same-user replacement of
the parent directory.

Run `examples/png_sequence_overlay.py` for a transparent lower third with no
FFmpeg dependency. Its output directory must be fresh on every run.

### High-quality animated compositing

`GifOptions(quality="high")` and `VideoOptions(quality="high")` opt into a 2×
layer-compositing surface followed by one LANCZOS downsample. The default is
`quality="standard"`, which preserves existing output. This namespaced option
is separate from `render(..., quality=...)` for JPEG/WebP.

```python
canvas.render("smooth.mp4", animation=VideoOptions(fps=30, quality="high"))
deck.render("smooth.gif", animation=GifOptions(fps=12, colors=64, quality="high"))
```

High mode filters prepared layers and staggered targets directly into the
larger surface without retaining enlarged copies of every source image. It
improves integration of rotated/downscaled edges; dimensions, timing, audio,
GIF palette/size controls and `workers` keep their existing meanings. Frames
and cached background plates contain four times as many pixels, so high mode
costs more rendering time and memory. Each worker adds its own buffers, so
aggregate memory can increase with worker count.

This is supersampled **layer compositing**, not higher-resolution source layout:
fonts/assets and backdrop-dependent source surfaces are still prepared at their
native size. Authored static rotation is already baked into those sources.
Captions retain native rendering after the downsample, while slide transitions
and keyed Morph keep their existing native-resolution paths. High mode cannot
restore details absent from a prepared source and may soften very small text.
See the [benchmark guide](https://github.com/sjquant/quickthumb/tree/main/benchmarks)
for matched cost measurements and before/after text crops.

### Parallel animated rendering

`GifOptions(workers=2)` and `VideoOptions(workers=2)` opt into process-based
frame rendering. `workers` is a strict integer from 1 to 8; the default remains
1, with no automatic CPU scaling. Small/static exports may be faster with one
worker because starting processes, preparing slides, and copying frames cost
time. Encoding and audio mixing still run in the parent export path.

Use an importable script and Python's main guard: workers always use `spawn`,
including on Linux, without changing the application's global start method.
Interactive environments that cannot import the main module should use
`workers=1`.

```python
from quickthumb import Canvas, Fade, VideoOptions

def main():
    canvas = Canvas(640, 360).background(color="#123456")
    canvas.shape("rectangle", (40, 40), 200, 160, "#FF3355",
                 animation=Fade(duration=2))
    canvas.render("parallel.mp4", animation=VideoOptions(fps=30, workers=2))

if __name__ == "__main__":
    main()
```

Workers rebuild built-in canvases with separate fonts and video decoders.
Only a bounded, ordered window of frame jobs is outstanding, preserving the
existing shot durations, collapsed holds, caption boundaries, and transition
order. Local video layers, captions, seeded grain and built-in motion work in
parallel. Custom/plugin layers, Canvas subclasses, remote video sources and
unseeded nonzero grain require `workers=1`. Remote images/fonts resolved by
slide preparation are pinned for workers; keep local assets and font-cache
files unchanged during export. A source or worker failure fails the export
and preserves a pre-existing destination.

More workers require more memory: each has a Python runtime, fonts, prepared
slide images and decoder caches, in addition to its in-flight RGB frame.
Normal completion and errors wait for running jobs to finish and close their
decoders. Pending jobs are canceled on failure; abruptly terminated workers
are reported as rendering errors. An OS-level kill cannot run normal cleanup.
Deck MP4 without `VideoOptions` remains the separate static narration workflow.

Deck MP4, WebM, and MOV exports support per-slide narration. Pass `audio=` to `Deck.slide()`;
without `duration=`, Quickthumb uses the file's ffprobe duration. An explicit
duration trims audio or pads it with silence, while a slide without audio holds
silently for `default_duration` (3 seconds). `deck.render("deck.mp4")` and
`deck.render_mp4("deck.mp4")` produce H.264/yuv420p video with an AAC track on
every output. Without `VideoOptions`, this is the static narrated path: layer
animations and slide transitions are not played. Pass
`animation=VideoOptions(soundtrack=AudioTrack(path="music.mp3", volume=0.16, loop=True))`
to `deck.render()` for animated MP4/WebM/MOV.
Quickthumb mixes that bed and the
scheduled `Deck.slide(audio=...)` narration during rendering; `deck.to_animated_mp4()`
and `deck.to_webm()` do the same for byte exports. Callers do not
need to pre-mix audio themselves.

The timing model mirrors the HTML slideshow, with one difference a non-interactive medium forces: there is nothing to click, so `on_click` animations play automatically in sequence, exactly like `after_previous` (the same choice PowerPoint's own video export makes). Each slide plays its transition (over the previous slide's final frame), runs its animation timeline (starting when the transition starts, like the HTML runtime), then holds its settled state — for the transition's `advance_after` when set, else for `slide_duration` (`hold` on `Canvas`). In narrated MP4/WebM/MOV output, the inferred or explicit narration duration (or the silent-slide default) extends the visual slide when it is longer than `advance_after`. A slide with no transition cross-fades in over 0.5s (slide 0 with none starts instantly); set a transition on slide 0 to animate in from the matte, which also makes looping GIFs wrap smoothly.

GIF is encoded by Pillow with per-frame durations, so no extra dependency is needed. MP4 (H.264), WebM (VP9), and MOV (ProRes 4444) require the `ffmpeg` binary on `PATH` (or pointed to by the `QUICKTHUMB_FFMPEG` environment variable).

Canvas MP4, WebM, and MOV output can carry a soundtrack — any audio file ffmpeg decodes (MP3, WAV, AAC, OGG, ...), encoded as AAC in MP4/MOV and Opus in WebM:

```python
mp4 = canvas.to_mp4(soundtrack="music.mp3")                    # loops to fill the video
mp4 = canvas.to_mp4(soundtrack="jingle.wav", loop_audio=False) # plays once, then silence
```

The audio is always trimmed to the video length. For an `AudioTrack`, `loop=True` repeats a shorter track and `loop=False` plays it once before silence; `loop_audio` is an explicit override. Legacy string paths keep the previous looping default. GIF exports do not accept a soundtrack.

!!! note "Format limits"
    Canonical layer translation, rotation and scaling use subpixel bicubic affine
    sampling while geometry is moving. Still images, held geometry and settled
    endpoints retain their existing pixels, including nonidentity final transforms.
    Image viewport zoom/pan keeps its separate image-renderer behavior.

    By default, frames are composited onto the opaque `matte` color (default black). VP9 WebM and ProRes MOV support opt-in alpha as described above; GIF and MP4 remain opaque. Mixed-size slides are scaled to fit and centered on the first slide's size. H.264/VP9 4:2:0 output needs even dimensions, so odd-sized canvases lose their last pixel row/column in MP4/WebM output. GIF encoding streams quantized frames through Pillow, keeping only a bounded number of uncompressed frames instead of imposing a timeline frame-memory budget. The final compressed GIF is still buffered in memory, including for file exports; large canvases, documents and encoded files can still exhaust available memory. `max_size` and `colors` remain useful for reducing output size. GIF dimensions and each coalesced frame duration must still fit the format’s 16-bit fields (65,535 pixels and 655.35 seconds). Animated Deck MP4/WebM/MOV accepts at most 64 slides with narration because each narration is decoded as a concurrent FFmpeg input; split larger narrated decks into multiple exports. Silent slides do not count toward this limit.

## Canonical samples

`sample()` returns the renderer-independent reference that exports are compared against, as a JSON-serializable `FrameSequence`. Canvas and Deck share the same contract, and a canvas produces the same observations as a one-slide deck containing it.

```python
still = canvas.sample()                         # settled frame(s), as PNG/PDF/PPTX draw them
timed = deck.sample(fps=10)                     # uniform grid over the whole animated timeline
probe = deck.sample([0.0, 1.25, 4.0], hold=2.0) # explicit instants, ascending
```

- **Frames.** Each `CanonicalFrame` holds `width * height` pixels as raw 8-bit RGBA (row-major from the top-left, sRGB, straight alpha), base64-encoded in `data`, plus the `sha256` of those bytes. `index` is the frame's position in the sequence and `slide` the page it shows. A frame whose digest or dimensions do not match its data is rejected when it is loaded.
- **Still captures** (`capture="still"`) hold one frame per page in slide order, at each page's own size, with transparency preserved. `time` is `None`, `duration` is `0`, and `timeline` is empty.
- **Timeline captures** (`capture="timeline"`) observe the timeline that animated WebM/MP4 exports play: transitions, Morph, layer animations, narration-driven slide durations, and a settled hold of `hold` seconds (default 3) for pages without an explicit duration. Frames are ordered by ascending `time` in seconds, share the first slide's size, and are composited onto the opaque `matte` (default black), which is reported as `#RRGGBB`. Deck GIF export currently ignores explicit and narration slide durations, so it matches this timeline only for decks without them.
- **Sampling.** `fps=N` (at most 120) observes every instant `k / N` before `duration`; explicit times must be ascending, and times at or past `duration` show the final settled frame. One capture observes at most 100,000 instants; a larger explicit list or fps grid is rejected with a `ValidationError` before any frame renders. This grid is an observation schedule, not an exporter's frame schedule: exporters sample each span on their own frame grid, and stretch a slide shorter than one frame to a full frame.
- **Timing.** `duration` is the exact timeline length and never depends on `fps` or on the requested instants. Each `TimelineSegment` gives a slide's absolute `start`, `transition_end`, `animation_end`, and `end`, rounded to nanoseconds; a slide is on screen over `[start, end)`, so a boundary instant belongs to the incoming slide.
- **Memory.** A capture whose distinct frames would exceed 768 MiB of raw RGBA is rejected with a `ValidationError`, before any frame renders when every page of a still capture, or one frame of a timeline capture, already exceeds it; request fewer instants, a lower `fps`, a shorter `hold`, or a smaller document.
- **Environment.** `environment` records the facts that can change pixels for an identical document: quickthumb, Pillow, and FreeType versions, the text layout engine (`basic` or `raqm`), and, for documents with video layers, the version of the FFmpeg that decodes them (`QUICKTHUMB_FFMPEG` or `ffmpeg` on `PATH`). Sampling a video document without a working FFmpeg raises `RenderingError` before any frame renders. Identical documents sampled in identical environments produce identical digests; fonts and images are described by the asset manifest (see below).

## Remote assets and caching

`render()` and `export()` download remote images, SVGs, text fills, and fonts into a shared cache, and `export()` returns an `asset_manifest` describing every asset it used. `prefetch_assets()` is optional: it does the same downloads up front and returns the manifest without rendering, so you can catch network failures or stale entries before a long export, or warm the cache for offline renders. Each `AssetManifestEntry` has the `source` as written, its semantic `asset_type`, a `status`, and whatever identity it has: `source_key` (canonical URL), `cache_key` and `cache_path`, `content_hash` (SHA-256 of the bytes used), and `fetched_at` (UTC time of the download).

| `status` | Meaning |
| --- | --- |
| `local` | An existing local file. |
| `missing` | A local path that does not exist. |
| `network` | Downloaded now and written to the cache. |
| `fresh` | Read from a cache entry within `max_age` (always, when no `max_age` is set). |
| `stale` | Read from an expired cache entry, or while offline, because it could not be refreshed. `stale_reason` explains why. |
| `unresolved` | A remote reference that has not been resolved yet. |

The cache is controlled by environment variables:

- `QUICKTHUMB_ASSET_CACHE_DIR`: cache directory (default: the system temp directory).
- `QUICKTHUMB_ASSET_MAX_AGE`: seconds after which a cached entry is refreshed from the network. When the refresh fails, the old bytes are used and reported as `stale`. Unset means cached entries never expire.
- `QUICKTHUMB_ASSET_OFFLINE=1`: never make network requests. Cached entries are used, and expired ones are reported as `stale`.

Each canvas (including each deck slide) tries to refresh an expired asset at most once; later renders and exports of it reuse the same `stale` result. When neither a usable cache entry nor a network response exists, resolution raises `RenderingError` naming the source, the cause, and the cache directory it searched. To refuse stale inputs, check the manifest before rendering:

```python
prefetched = canvas.prefetch_assets()
stale = [entry for entry in prefetched.asset_manifest if entry.status == "stale"]
if stale:
    raise SystemExit(f"stale assets: {[(e.source, e.stale_reason) for e in stale]}")
```

## Decks (multiple images and slides)

A `Deck` is an ordered collection of canvases. Each slide is a full `Canvas` and renders exactly as it would on its own, so a deck is just a multi-output container on top of the same pipeline. See the [Deck API reference](api/deck.md) for the full method list.

Give the deck a size once and each slide can be a bare `Canvas()` that inherits it:

```python
from quickthumb import Canvas, Deck

deck = (
    Deck(1280, 720)   # default slide size; Deck.from_aspect_ratio("16:9", 1280) also works
    .slide(Canvas().background(color="#101820").text(content="Cover", ...))
    .slide(Canvas().background(color="#1A1A2E").text(content="Body", ...))
)
# pre-built canvases work too: Deck(slides=[cover, body])

deck.render("deck.pdf")     # one multi-page PDF (a page per slide)
deck.render("deck.pptx")    # one multi-slide PPTX (a slide per slide)
deck.render("deck.gif")     # one animation playing transitions between slides
deck.render("deck.mp4")     # static slides with per-slide narration
deck.render(
    "deck.mp4",
    animation=VideoOptions(soundtrack=AudioTrack(path="music.mp3", loop=True)),
)  # animated + mixed audio
deck.render("animated.mp4", animation=VideoOptions(fps=20))  # animated, silent
deck.render("slides.png")   # numbered sequence: slides_01.png, slides_02.png, …

pdf_bytes = deck.to_pdf()
pptx_bytes = deck.to_pptx()
gif_bytes = deck.to_gif()
webm_bytes = deck.to_webm()
mp4_bytes = deck.to_mp4()   # static slides with per-slide narration
```

`render()` dispatches on the output extension: `.pdf` and `.pptx` produce a single document; `.gif`, `.webm`, and `.mov` produce an animation; `.mp4` produces static slides with per-slide narration unless `animation=VideoOptions(...)` selects the animated path; and raster extensions have no native multi-page container, so the deck writes one file per slide as a zero-padded numbered sequence and returns the written paths.

Slides may have different dimensions. `deck.diagnose()` aggregates each slide's [diagnostics](diagnostics.md) (each tagged with its `slide_index`) and adds a `mixed-slide-size` warning when they differ. The PDF path sizes each page to its slide, but PPTX has a single presentation size taken from the first slide, so slides larger than the first are clipped by PowerPoint — keep slides a uniform size when targeting `.pptx`. Decks round-trip through JSON with `deck.to_json()` / `Deck.from_json(...)`, reusing the per-canvas serialization.

## CLI

The CLI picks the format from the output extension too:

```bash
quickthumb render spec.json -o card.svg
quickthumb render spec.json -o card.pptx
quickthumb render spec.json -o card.pdf

# Live HTML slides; open /?presenter for the presenter dashboard
quickthumb serve slides.py
```
