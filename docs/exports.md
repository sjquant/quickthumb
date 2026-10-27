---
description: Export quickthumb canvases and decks to PNG, JPEG, WebP, SVG, HTML, PDF, editable PowerPoint, GIF, MP4, WebM, and MOV.
---

# Exporting to SVG, PPTX, PDF & video

A canvas renders to raster, vector, document, web, and animated formats. The
format comes from the file extension:

```python
canvas.export("thumbnail.png")   # raster (PNG/JPEG/WEBP)
canvas.export("thumbnail.svg")   # vector SVG
canvas.export("thumbnail.html")  # self-contained web page that plays animations
canvas.export("thumbnail.pptx")  # editable PowerPoint slide
canvas.export("thumbnail.pdf")   # single-page PDF
canvas.export("thumbnail.gif")   # animated GIF playing the layer animations
canvas.export("thumbnail.mp4")   # H.264 video (requires ffmpeg); .webm for VP9
canvas.export("thumbnail.mov")   # ProRes 4444 video (requires ffmpeg with prores_ks)
```

Each format also has a direct method when you want the content in memory:

```python
svg_markup = canvas.to_svg()
html = canvas.to_html()
pptx_bytes = canvas.to_pptx()
pdf_bytes = canvas.to_pdf()
gif_bytes = canvas.to_gif()
mp4_bytes = canvas.to_mp4()      # and canvas.to_webm() / canvas.to_mov()
```

## Recommended output API

Use `export()` when building a workflow that accepts either a `Canvas` or a
`Deck`. Both accept a string or `Path` and return an `ExportResult`, including
the document `kind`, effective `output_format`, `written_paths`, capability and
fallback diagnostics, pixel/timing metadata, the asset manifest, and rendering
environment.

The extension selects the format. MP4, WebM, MOV and GIF play the animated timeline.
Deck video also mixes per-slide narration.

```python
from quickthumb import VideoOptions

result = deck.export("slides.mp4", animation=VideoOptions(hold=2, render_quality="high"))
print(result.written_paths, result.fallback_diagnostics)
deck.export("slides.html")  # interactive slideshow with click-triggered motion
canvas.export("card.webp", quality=85)  # JPEG/WebP compression quality
```

| Need | Entry point |
| --- | --- |
| Write a file with capability policy and a result receipt | `export(path, ...)` |
| Draw debug boxes or use the lower-level file renderer | `render(path, ...)` |
| Get bytes or an in-memory document | `to_mp4()`, `to_gif()`, `to_html()`, etc. |
| Export static narrated Deck slides | `render_narrated_mp4(path, hold=3)` / `to_narrated_mp4(hold=3)` |
| Write silent animation frames plus a manifest | `export_image_sequence(directory, options=...)` |

All animated byte methods and options use `hold` for settled-state seconds.
`render_quality="standard"` or `"high"` controls animation compositing;
`quality` on `export()`/`render()` controls compression: JPEG accepts integer
values 1–95 and WebP accepts 1–100.
Keep `workers=1` unless advanced spawn-based rendering is needed.
Both `export()` and `render()` enforce file capability policies such as
`unsupported_motion="error"` before writing; `export()` also returns the receipt.
Byte methods expose target-specific controls without the shared file receipt.
Use the returned `written_paths` for Deck raster sequences: they are numbered files.
Image sequences keep a separate API because their destination is a new directory.

### Format and option selection

Canvas and Deck use the same selection rules:

| Input | Result |
| --- | --- |
| File extension, with no `format` | Selects the output; `.jpg`/`.jpeg` report `output_format="jpeg"`, `.htm`/`.html` report `"html"`. |
| `format="PNG"`, `"JPEG"` or `"WEBP"` (case-insensitive) | Selects raster encoding for a raster, unknown or extensionless filename. The requested filename is kept; it is not renamed to match the encoding. |
| Raster `format` with a document or animated extension | Rejected rather than writing image bytes into an SVG, PDF, HTML, PPTX or video filename. |
| `quality` | JPEG integer 1–95 or WebP integer 1–100; rejected for other targets. |
| `animation` | `GifOptions` for GIF; `VideoOptions` for MP4/WebM/MOV; rejected for static/document targets. |

Format selection, compression quality and animation option-family conflicts are
rejected before asset reads or file writes. Codec-specific limits are validated
during export preparation. Rendering or encoding failures can still occur later;
ordinary file exports are not an atomic multi-file transaction. Inspect `written_paths` rather than guessing Canvas or
numbered Deck filenames. A Deck cannot be written as a single SVG; export its
Canvas slides individually. See [image sequences](#image-sequences) for their
separate new-directory and encoding-option contract.

### Optional static SVG fidelity report

Request a CairoSVG comparison through `ExportPolicy` when the current job has
explicit acceptance limits. All three limits are required; there are no built-in
format budgets. This example requests exact visible RGBA rather than an
application-specific allowance for edge or font differences:

```python
from quickthumb import Canvas, ExportPolicy

policy = ExportPolicy(fidelity={"svg": {
    "pixel_tolerance": 0,
    "max_different_pixel_ratio": 0,
    "min_hash_similarity": 1,
}})
canvas = Canvas(160, 90).background(color="#123456")
result = canvas.export("checked.svg", policy=policy)
comparison = result.pixel_metrics.fidelity
print(comparison.verdict, comparison.pixel_diff_ratio, comparison.hash_similarity)
```

The optional `quickthumb[svg]` extra and system Cairo are needed only when the
selected SVG export requests this check. The report records CairoSVG/Cairo
versions, the canonical render environment, applied limits and actual rasterized
dimensions. It compares the authored-static `sample()` still, with no resize.
`exact` means all visible RGBA channels match; `tolerated` satisfies the supplied
pixel-ratio and average-hash limits; `out_of_policy` fails a limit or dimensions.
Mean absolute error is normalized over four channels, and the maximum channel
delta is also reported. Fully transparent pixels ignore hidden RGB, so this
definition of exact is distinct from canonical raw-pixel SHA-256 equality.
The 8×8 average hash composites onto white; RGBA measurements independently catch
alpha loss even when that hash is identical.

This is report-only: the original SVG representation is written even when the
verdict is `out_of_policy`. A fidelity diagnostic describes the observation;
no new raster fallback is selected. Missing/failed reference rendering raises
before the destination is opened, preserving an existing file. Default exports
and non-SVG targets do not perform this comparison.

The observation applies to static Cairo rendering in the recorded environment.
Cairo uses installed fonts and does not honor embedded CSS `@font-face`, so the
same font environment must be available separately; see the
[CairoSVG documentation](https://cairosvg.org/documentation/). It is not a browser,
HTML, or animation fidelity guarantee. SVG keeps its existing authored-static
motion behavior.

### Migrating output calls

- `Deck.to_mp4()` now plays animation, matching Canvas and file exports.
  Replace old `to_animated_mp4()` calls with `to_mp4()`; use
  `to_narrated_mp4()` for still-slide narration.
- Replace `render_mp4()` with `render_narrated_mp4()` for still-slide files.
- `export_image_sequence()` replaces `export_png_sequence()`; the public
  options/manifest/result models are now `ImageSequence*`, with no obsolete aliases.
- Replace animated Deck `slide_duration=` and narrated `default_duration=` with
  `hold=`. Replace animation `quality=` with `render_quality=`, including saved
  GifOptions, VideoOptions and ImageSequenceOptions JSON. There are no aliases.

## How export works

Exporters keep layers **native** wherever the target format can express them, and embed **pixel-exact PNG fragments** (rendered by the regular pipeline) everywhere else. Positions, wrapping, and alignment are computed with the same layout math as the raster renderer, so output matches the PNG render closely.

HTML export works the same way; see [HTML](#html) below.

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

## HTML

```python
html = canvas.to_html()
canvas.render("card.html")
```

The result is one self-contained HTML file. Backgrounds, shapes, outlines, and
text become HTML and CSS; images and anything else without a CSS equivalent
are embedded as PNG fragments. Unlike SVG, PDF, and PPTX, the page plays layer
`animation` effects, advancing on click.

The design is a fixed-size stage that never reflows. By default
(`responsive=True`) the whole stage scales to fit the browser window; pass
`responsive=False` to get it at its exact pixel size. Fonts are embedded by
default (`embed_fonts=True`), so the page looks the same on any machine.

A deck exports to an HTML slideshow the same way, with a presenter view; see
[Deck](api/deck.md).

## PPTX

PPTX export needs the `pptx` extra:

```bash
pip install "quickthumb[pptx]"
```

The canvas becomes a single slide sized to the canvas pixels (at 96 dpi). Text stays editable: font family, size, weight, color, alignment, and line wrapping carry over run by run, and stroke, shadow, and glow map to PowerPoint's text outline and effect settings.

```python
canvas.render("promo.pptx")
# or
with open("promo.pptx", "wb") as f:
    f.write(canvas.to_pptx())
```

!!! note "Fidelity"
    PowerPoint lays text out with its own font metrics, so text placement is a close approximation rather than pixel-identical. Radial background gradients and multi-stop text gradients beyond what DrawingML supports are embedded as pictures or approximated.

## PDF

PDF export needs the `pdf` extra:

```bash
pip install "quickthumb[pdf]"
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

## Animated GIF & video { #animated-gif-video }

See [animation timing](timing.md) for canonical sampling versus encoded frame
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
These methods use `hold` and do not accept options objects. Static narration
uses `Deck.to_narrated_mp4()` / `Deck.render_narrated_mp4()`.

File execution resolves the format before checking export policy. Canvas and
Deck MP4 always play the animated timeline, with default `VideoOptions()` when
no options are supplied.
Unused authored Morph transitions do not produce fallback errors or receipt
diagnostics for static files or reduced-motion execution.
Reduced animation retains the encoder's holds and default transitions between
slides. See [animation timing](timing.md) for sampling rates and encoded visual
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
deck.render("overlay.webm", animation=VideoOptions(transparent=True, render_quality="high", workers=2))
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
[`export_image_sequence()` API](#image-sequences).

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
deck.export("overlay.mov", animation=VideoOptions(transparent=True, render_quality="high", workers=2))
mov_bytes = canvas.to_mov(hold=2.0, transparent=True)
mov_bytes = deck.to_mov(hold=2.0, transparent=True, soundtrack="music.wav")
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

### Image sequences

`Canvas.export_image_sequence()` and the matching Deck method write the actual
animated timeline as independent PNG, JPEG, or WebP files plus one manifest.
The destination must be new and its parent must exist. PNG is the default.

```python
from quickthumb import ImageSequenceOptions

options = ImageSequenceOptions(fps=24, hold=2, render_quality="high", workers=2)
result = canvas.export_image_sequence("overlay_frames", options=options)
canvas.export_image_sequence("review_frames", format="jpeg", quality=85, matte="white", options=options)
canvas.export_image_sequence("web_frames", format="webp", lossless=True, options=options)
print(result.frame_count, result.duration, result.manifest_path)
```

Encoding controls are keyword arguments to the method, separate from timing
and compositing in `ImageSequenceOptions(fps=30, hold=3, workers=1,
render_quality="standard")`:

| Control | PNG | JPEG | WebP |
| --- | --- | --- | --- |
| `format` (case-insensitive) | `"png"` (default) | `"jpeg"` | `"webp"` |
| `quality` | Rejected | Integer 1–95; default 90 | Integer 1–95 for lossy output; default 80 |
| `matte` | Rejected | Opaque color string; default white | Rejected |
| `lossless` | Rejected | Rejected | Boolean; default `False` |

`lossless=True` and `quality` cannot be combined: quality names lossy
compression, not lossless WebP encoder effort. Invalid types or incompatible
options fail before creating output or staging. Options models contain only
`fps` (finite, >0 and ≤120), `hold` (finite, nonnegative seconds), `workers`
(strict integer 1–8), and `render_quality` (`"standard"` or `"high"`).

PNG retains the renderer's exact **8-bit straight-alpha RGBA bytes**, including
hidden RGB. Lossless WebP also preserves those pixels, including hidden RGB.
JPEG flattens alpha onto the resolved matte and encodes RGB; JPEG and lossy
WebP can change colors and do not promise exact canonical pixels. WebP retains
alpha, but fully opaque files may omit the redundant alpha plane and open as
RGB in image readers. Convert those files to RGBA when consuming the manifest's
logical `mode: "RGBA"`. Authored backgrounds stay visible in every format.
Odd and one-pixel dimensions retain every row and column. Differently sized
slides fit the first canvas's full dimensions, with transparent padding before
encoding (matte-colored padding for JPEG). Imported images are not
ICC-normalized; output strips inherited profiles/metadata and makes no
sRGB/color-profile claim.

The directory contains `000000.png`, `.jpg`, or `.webp`, and so on, plus one
compact `manifest.json`. It records `version: "1"`, `format: "image_sequence"`,
document `kind`, `encoding: "png"|"jpeg"|"webp"`, relative `filename_pattern`
(`%06d.png`, `%06d.jpg`, or `%06d.webp`), and `start_index: 0`. Actual
`frame_count`, `fps`, `duration`, `width`, and `height` describe the written
files. Pixel fields describe logical decoding: PNG/WebP use `mode: "RGBA"`
and `alpha: "straight"`; JPEG uses `"RGB"` and `"none"`. `bit_depth` is 8.
`lossless` reports the selected encoding; resolved `quality` and `matte` are
recorded where applicable and otherwise `null`.

`ImageSequenceResult` adds absolute `output_directory`, `manifest_path`, and
`capability_report` diagnostics to `ImageSequenceManifest`. Both models and
`ImageSequenceOptions` support JSON round trips and `model_json_schema()`.
They add no Canvas/Deck document fields or raster format enum values. There
is no growing list of frame paths or timestamps. Repeated frames are encoded
once per canonical shot and written as independent editable files, not hardlinks.
Frame memory stays bounded; existing scene preparation and worker buffers
still consume memory.

Timing follows animated exports, including explicit slide durations,
`advance_after`, narration-derived visual timing, transitions, and Morph.
Cumulative frame allocation avoids drift across fractional holds; short or
zero-hold still slides receive at least one frame. The reported duration is
exactly `frame_count / fps`, measured from the files actually written. This
can differ from the independent timeline sampler's duration or sample count.
`validate_export("image_sequence")` and `inspect_motion(target="image_sequence")`
use video motion capabilities. Existing strict/reduced-motion policies and
parent, Morph, caption, and worker restrictions apply.

Sequences are silent: no audio encoding, mux, soundtrack, or audio sidecars.
Narration retains its existing file validation and duration inference, without
the encoder's 64-audio-input limit. Image-only scenes need no FFmpeg; inferred
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

Run `examples/image_sequence_overlay.py` for PNG, white-matted JPEG and
lossless WebP lower-third sequences with no FFmpeg dependency. All three
output directories must be fresh on every run.

### High-quality animated compositing

`GifOptions(render_quality="high")` and `VideoOptions(render_quality="high")` opt into a 2×
layer-compositing surface followed by one LANCZOS downsample. The default is
`render_quality="standard"`, which preserves existing output. This namespaced option
is separate from `render(..., quality=...)` for JPEG/WebP. Animated byte
methods also accept the keyword-only `render_quality="high"` argument.

```python
canvas.render("smooth.mp4", animation=VideoOptions(fps=30, render_quality="high"))
deck.render("smooth.gif", animation=GifOptions(fps=12, colors=64, render_quality="high"))
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
frame rendering. The same keyword-only `workers` argument is available on
animated byte methods. `workers` is a strict integer from 1 to 8; the default remains
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

Static narrated MP4 uses `render_narrated_mp4()` or `to_narrated_mp4()`.

### Narrated deck video

A deck can be exported as a video with a voice-over per slide:

- Pass `audio=` to `Deck.slide()`. Without `duration=`, the narration duration
  is measured with `ffprobe`. An explicit `duration=` trims the audio or pads
  it with silence. A slide with no audio holds silently for `hold` (3 seconds).
- `deck.export("deck.mp4")` and `deck.render("deck.mp4")` play layer animations
  and transitions with narration by default. `deck.to_mp4()`, `deck.to_webm()`,
  and `deck.to_mov()` return animated video bytes.
- To show static slides with narration, use
  `deck.render_narrated_mp4("deck.mp4")` or `deck.to_narrated_mp4()`.
  The output is H.264/yuv420p video with an AAC track.
- Add background music with
  `animation=VideoOptions(soundtrack=AudioTrack(path="music.mp3", volume=0.16, loop=True))`
  on `deck.export()` or `deck.render()`. Quickthumb mixes it with the slide
  narration; callers do not need to pre-mix audio themselves.

### Timing

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
- **Environment.** `sample()` and `export()` report quickthumb, Pillow and FreeType versions, the text layout engine (`basic` or `raqm`), available RAQM/HarfBuzz/FriBidi versions, and the FFmpeg version for documents with video layers. Sampling video without a working FFmpeg raises `RenderingError` before any frame renders. `environment.fonts` reports the actual font face bytes selected by that operation; the asset manifest separately describes authored references.

### Render reproducibility

Font family names and `QUICKTHUMB_DEFAULT_FONT` depend on the machine's font
search path. Inspect the selected faces rather than treating those names as
portable identifiers:

```python
capture = canvas.sample()
for font in capture.environment.fonts:
    print(font.source, font.sha256, font.variations)
```

Each face has its resolved file path (or `pillow:default`), SHA-256 and applied
variable coordinates keyed by the font's axis names. The hash identifies the
font bytes. Pillow's embedded
face reports no hash if its bytes are unavailable. Paths are diagnostic: compare
hashes and coordinates across machines. Only faces loaded for the current
operation are reported; unused named fonts and faces from earlier operations
are excluded.

Remote and Google fonts load from content-addressed copies of their resolved
bytes, so another document refreshing the original URL does not change a
prefetched face. These copies live in the asset cache and follow its caller-owned
cleanup lifecycle. Keep local input files unchanged during an operation.

For repeatable canonical raster output, use identical document data, input asset
bytes, selected fonts and variable coordinates, rendering options and environment;
seed procedural effects where supported. Different font, shaping or rasterizer
versions can change layout and edge pixels. This report explains those inputs;
it does not promise exact pixels across platforms or native-output viewers.
Use format-specific fidelity tolerances when comparing such outputs.

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

### Ownership and reuse

Keep the same `Canvas` or `Deck` to reuse resolution across `prefetch_assets()`,
`sample()`, and exports. Each canvas retains its first remote resolution result
and status; a deck uses its slides' results. Remote images, text fills, and SVGs
render from these retained bytes. Remote fonts, including Google fonts, load
from shared cache files instead: another document's refresh can replace that
file before a font face is loaded, while the earlier manifest still describes
the original resolution. Keep the font cache unchanged through export when
reproducible font bytes matter. Construct a new document to resolve the same
reference again under the current cache policy.

`PrefetchResult` and `asset_manifest` are JSON-safe reports, not resource handles.
Saving or loading their JSON does not transfer bytes or preload another document.
A new document can reuse the persisted cache and reports `fresh` when its entry
is usable. Local image, font, video, and audio paths remain caller-owned files:
keep them available and unchanged through sampling or export; prefetch does not
freeze or copy them. Video and audio sources are not downloaded by prefetch;
remote video is read by FFmpeg when needed and is outside this cache contract.
Generated content without a file/URL reference has no external asset entry.

The caller owns the cache directory and its cleanup. Quickthumb atomically writes
remote cache files and metadata but does not automatically evict them. Remove
unused entries only when documents and export workers are no longer using that
cache; existing manifests are observations, not guarantees that their
`cache_path` still exists. No explicit document close is required for the
in-memory remote results: they are released with the document.

When neither a usable cache entry nor a network response exists, resolution raises `RenderingError` naming the source, the cause, and the cache directory it searched. To refuse stale inputs, check the manifest before rendering:

```python
prefetched = canvas.prefetch_assets()
stale = [entry for entry in prefetched.asset_manifest if entry.status == "stale"]
if stale:
    raise SystemExit(f"stale assets: {[(e.source, e.stale_reason) for e in stale]}")
```

## Decks (multiple images and slides)

A `Deck` is an ordered list of canvases. Each slide is a full `Canvas` and renders exactly as it would on its own. See the [Deck API reference](api/deck.md) for the full method list.

Give the deck a size once and each slide can be a bare `Canvas()` that inherits it:

```python
from quickthumb import AudioTrack, Canvas, Deck, VideoOptions

deck = (
    Deck(1280, 720)   # default slide size; Deck.from_aspect_ratio("16:9", 1280) also works
    .slide(Canvas().background(color="#101820").text(content="Cover", size=96, color="#FFFFFF"))
    .slide(Canvas().background(color="#1A1A2E").text(content="Body", size=64, color="#FFFFFF"))
)
# pre-built canvases work too: Deck(slides=[cover, body])

deck.render("deck.pdf")     # one multi-page PDF (a page per slide)
deck.render("deck.pptx")    # one multi-slide PPTX (a slide per slide)
deck.render("deck.gif")     # one animation playing transitions between slides
deck.export("deck.mp4")     # animated slides with per-slide narration
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
mp4_bytes = deck.to_narrated_mp4()   # static slides with per-slide narration
```

`render()` dispatches on the output extension: `.pdf` and `.pptx` produce a single document; `.gif`, `.mp4`, `.webm`, and `.mov` produce an animation; and raster extensions have no native multi-page container, so the deck writes one file per slide as a zero-padded numbered sequence and returns the written paths.

Slides may have different dimensions. `deck.diagnose()` aggregates each slide's [diagnostics](diagnostics.md) (each tagged with its `slide_index`) and adds a `mixed-slide-size` warning when they differ. The PDF path sizes each page to its slide, but PPTX has a single presentation size taken from the first slide, so slides larger than the first are clipped by PowerPoint. Keep slides the same size when targeting `.pptx`. Decks round-trip through JSON with `deck.to_json()` / `Deck.from_json(...)`, reusing the per-canvas serialization.

## CLI

The CLI picks the format from the output extension too:

```bash
quickthumb render spec.json -o card.svg
quickthumb render spec.json -o card.pptx
quickthumb render spec.json -o card.pdf

# Live HTML slides; open /?presenter for the presenter dashboard
quickthumb serve slides.py
```
