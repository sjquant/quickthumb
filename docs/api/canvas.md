---
description: Reference for quickthumb Canvas creation, aspect ratios, layer composition, rendering, JSON loading, and image output.
---

# Canvas

The `Canvas` is the root object. It holds dimensions and an ordered list of layers.

## Creation

### `Canvas(width=None, height=None)`

```python
from quickthumb import Canvas

canvas = Canvas(1280, 720)
```

| Parameter | Type | Description |
| --- | --- | --- |
| `width` | `int \| None` | Canvas width in pixels. Must be a positive integer. |
| `height` | `int \| None` | Canvas height in pixels. Must be a positive integer. |

Width and height must be given together or both omitted. A canvas built **without** a size (`Canvas()`) is *unsized*: it accepts layer builders but cannot be rendered, diagnosed, or serialized until it gets a size — either directly or by being added to a sized [`Deck`](deck.md), which injects its default size. Check `canvas.has_size` to tell the difference.

### `Canvas.from_aspect_ratio(ratio, base_width)`

Creates a canvas from an aspect ratio string and a base width. Height is calculated automatically.

```python
wide     = Canvas.from_aspect_ratio("16:9", base_width=1280)   # 1280×720
square   = Canvas.from_aspect_ratio("1:1",  base_width=1080)   # 1080×1080
vertical = Canvas.from_aspect_ratio("9:16", base_width=1080)   # 1080×1920
```

| Parameter | Type | Description |
| --- | --- | --- |
| `ratio` | `str` | Aspect ratio string in `"W:H"` format, e.g. `"16:9"` |
| `base_width` | `int` | Canvas width in pixels |

## Layer builders

All builder methods mutate the canvas and return `self`, enabling method chaining.

| Method | Description |
| --- | --- |
| `.background(...)` | Add a full-canvas background layer |
| `.text(...)` | Add a text layer |
| `.image(...)` | Add an overlay image layer |
| `.shape(...)` | Add a shape layer |
| `.svg(...)` | Add an SVG layer, rasterized at render time |
| `.group(...)` | Add an auto-layout group of child layers |
| `.outline(...)` | Add a canvas border |
| `.chart(...)` | Add a deterministic bar or line chart layer from a typed chart spec |
| `.qr_code(...)` | Add a square QR code layer |
| `.custom(fn)` | Add a Pillow callback layer |

See the [data visualization reference](data-visualizations.md) and the other
individual reference pages for full parameter details.

## `.diagnose()`

Checks the composition for layout and legibility issues without writing a file. Returns a `DiagnosticReport` whose `findings` list contains `Diagnostic` entries (empty when clean):

```python
for finding in canvas.diagnose().findings:
    print(finding.severity, finding.code, finding.message)
```

Finding codes: `off-canvas`, `tiny-text`, `text-overflow`, `text-clipped`, `missing-glyph`,
`low-contrast`, `layer-overlap`, `layer-hidden`, and `edge-crowding`. See
[Diagnostics & CLI](../diagnostics.md) for details and the `quickthumb lint` (or
`quickthumb diagnose`) equivalent.

## `.prefetch_assets()` (optional)

You never need to call this: `render()` and `export()` download remote images,
SVGs, text fills, and fonts themselves, and `export()` returns the resulting
`asset_manifest`. Call it only to do those downloads up front — to catch a
network failure or a stale cache entry before a long export, or to warm the
cache for later offline renders. It returns the manifest without rendering:

```python
manifest = canvas.prefetch_assets().asset_manifest
if any(entry.status == "stale" for entry in manifest):
    ...  # decide whether to proceed with cached bytes
```

See [Remote assets and caching](../exports.md#remote-assets-and-caching) for
statuses, `QUICKTHUMB_ASSET_MAX_AGE`, and offline mode.

## Export methods

### `.render(path, format=None, quality=None, debug=False, animation=None)`

Renders the canvas and writes the result to a file. The format is detected from the file extension; `.svg`, `.pptx`, and `.pdf` produce vector/document output, and `.gif`/`.mp4`/`.webm`/`.mov` produce an animation playing the canvas's layer `animation` effects (see [Exporting to SVG, PPTX, PDF & video](../exports.md)).

```python
from quickthumb import GifOptions, VideoOptions

canvas.render("output.png")
canvas.render("output.jpg", format="JPEG", quality=85)
canvas.render("output.webp", format="WEBP", quality=90)
canvas.render("debug.png", debug=True)  # raster output with public layer-id bboxes
canvas.render("output.svg")
canvas.render("output.pptx")  # requires quickthumb[pptx]
canvas.render("output.pdf")   # requires quickthumb[pdf]
canvas.render("output.gif")   # animated; .mp4/.webm/.mov require the ffmpeg binary
canvas.render(
    "preview.gif",
    animation=GifOptions(fps=8, max_size=(540, 960), colors=128),
)
canvas.render("preview.mp4", animation=VideoOptions(fps=30))
```

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `path` | `str` | — | Output file path |
| `format` | `str \| None` | `None` | Optional raster output format override: `"PNG"`, `"JPEG"`, or `"WEBP"` |
| `quality` | `int \| None` | `None` | Compression quality (1–95). Only valid for `JPEG` and `WEBP`. |
| `debug` | `bool` | `False` | Draw public layer-id bounding boxes on raster output for visual review. |
| `animation` | `GifOptions \| VideoOptions \| None` | `None` | Format-specific options: `GifOptions` for GIF, `VideoOptions` for MP4/WebM/MOV. |

!!! warning
    Passing `quality` with `format="PNG"` raises `RenderingError`. Passing `debug=True` for document or animated output (`.svg`, `.pptx`, `.pdf`, `.html`, `.gif`, `.mp4`, `.webm`, or `.mov`) raises `RenderingError`.

`GifOptions` and `VideoOptions` are available from `quickthumb`. `GifOptions`
accepts `fps`, `matte`, `loop`, `max_size=(width, height)`, and `colors`.
`VideoOptions` accepts `fps`, `matte`, `soundtrack=AudioTrack(...)`, and `loop_audio`.
`VideoOptions(transparent=True)` preserves alpha in VP9 WebM or ProRes 4444 MOV (strict
boolean, default `False`); all other output targets reject this option.
Both accept `workers` (an integer from 1 to 8, default 1) for opt-in parallel
frame rendering. See [parallel animated rendering](../exports.md#parallel-animated-rendering)
for spawn setup and supported inputs. GIF sizing and palette controls are rejected for MP4/WebM/MOV output.

### `.to_svg(embed_fonts=False)`

Returns the canvas as an SVG document string. Set `embed_fonts=True` to inline the used font files as `@font-face` data URLs.

```python
svg = canvas.to_svg(embed_fonts=True)
```

### `.to_pptx()`

Returns the canvas as PowerPoint file bytes — a single slide with editable text boxes and autoshapes. Requires the `pptx` extra.

```python
with open("deck.pptx", "wb") as f:
    f.write(canvas.to_pptx())
```

### `.to_pdf()`

Returns the canvas as PDF file bytes — a single page with native vector backgrounds, shapes, and selectable text when its font can be safely embedded and the text does not require complex shaping. Unsupported text is embedded as a pixel-exact image fragment. Requires the `pdf` extra.

```python
with open("card.pdf", "wb") as f:
    f.write(canvas.to_pdf())
```

### `.to_gif(...)` / `.to_mp4(...)` / `.to_webm(...)` / `.to_mov(...)`

Return the canvas as an animation that plays its layer `animation` effects in sequence, then holds the settled composition for `hold` seconds (see [Animated GIF & video](../exports.md#animated-gif-video-canvas-mp4webmmov-deck-gifwebmmov)). A canvas with no animations yields a single-frame GIF. `.to_mp4()`/`.to_webm()`/`.to_mov()` require the `ffmpeg` binary on `PATH` (or named by `QUICKTHUMB_FFMPEG`).

```python
gif_bytes = canvas.to_gif(fps=20, hold=3.0, loop=0, matte="#000000")
mp4_bytes = canvas.to_mp4(fps=30, hold=2.0, soundtrack="music.mp3")
webm_bytes = canvas.to_webm(fps=30, hold=2.0)
overlay_bytes = canvas.to_webm(fps=30, hold=2.0, transparent=True)
```

`.to_mp4()`/`.to_webm()`/`.to_mov()` also accept `soundtrack` (an audio file muxed into the video, trimmed to the video length) and `loop_audio` (an explicit override). `AudioTrack(..., loop=True)` repeats a shorter configured track; legacy string paths keep the previous default of looping. GIF cannot carry audio. See the [Deck API](deck.md) for the full parameter table.

The keyword-only `transparent` flag on `.to_webm()` and `.to_mov()` skips only the export matte;
authored backgrounds stay visible. See [transparent WebM](../exports.md#transparent-webm)
for codec, alpha decoding and transition details.

`.to_mov()` uses the same parameters and timing as `.to_webm()`, with fixed
ProRes 4444 video and AAC audio. It retains odd and one-pixel dimensions.
The RGBA source remains 8-bit; 16-bit alpha coding can decode with one-level
8-bit alpha differences, and color is lossy 4:4:4 YUV. See
[ProRes MOV](../exports.md#prores-4444-mov) for the measured conversion limits
and encoder requirements. `render()` and `export()` accept `.mov` with
`VideoOptions` for both opaque and transparent output.

### `.export_png_sequence(output_directory, *, options=None, policy=None)`

Write silent animation frames and `manifest.json` to a new directory whose
parent already exists. `PngSequenceOptions(fps=30, hold=3, workers=1,
quality="standard")` controls timing and rendering. Every independent PNG holds
the renderer's exact RGBA8 straight-alpha bytes, with no export matte or color
profile claim. `PngSequenceResult` reports actual `frame_count`,
`duration=frame_count/fps`, dimensions, the numeric filename pattern, published
paths, and motion diagnostics. Files, directories and symlinks at the destination
are never replaced. See [PNG sequences](../exports.md#png-image-sequences) for
the full schema, timing, resource, and atomic-publication contract.

### `.to_base64(format="PNG", quality=None)`

Returns the rendered image as a base64-encoded string.

```python
b64 = canvas.to_base64(format="PNG")
b64 = canvas.to_base64(format="WEBP", quality=90)
```

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `format` | `str` | `"PNG"` | Output format: `"PNG"`, `"JPEG"`, or `"WEBP"` |
| `quality` | `int \| None` | `None` | Compression quality. Only valid for `JPEG` and `WEBP`. |

### `.to_data_url(format="PNG", quality=None)`

Returns the rendered image as a data URL (`data:<mime>;base64,...`).

```python
url = canvas.to_data_url(format="JPEG", quality=90)
# → "data:image/jpeg;base64,..."
```

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `format` | `str` | `"PNG"` | Output format: `"PNG"`, `"JPEG"`, or `"WEBP"` |
| `quality` | `int \| None` | `None` | Compression quality. Only valid for `JPEG` and `WEBP`. |

### `.inspect()`

Returns a deterministic `CanvasInspection` containing layer identities, order,
visibility, bounding boxes and authored text-layout metadata. No output file is
written. Existing font/image assets may be read for sizing, but parent-layer
drawing is not invoked.

```python
report = canvas.inspect()
for layer in report.layers:
    print(layer.id, layer.bbox)
```

For supported parent-linked scenes, bounds describe the **authored-static** world
layout, not the state at animation time zero. They conservatively enclose each
existing measured local body after its ancestor transforms and can extend outside
the canvas. Transparent corners can make these boxes looser than painted pixels.
Text sizes/wrapping remain authored-local; intrinsic counters use their settled
formatted text for these measurements, without sampling the timeline. Nulls have
no visible body or bbox.
`canvas.render("debug.png", debug=True)` overlays the same authored-static boxes.
`diagnose()` uses the same authored-static world layout, with transformed painted
alpha for overlap/occlusion and transformed glyph/background pixels for contrast.
Parent opacity is not inherited. Geometry animation on an ancestor prevents a
static footprint from being reported as permanently hiding another layer.
Repair suggestions describe parent-local positions or containing group layout;
world coordinates must not be copied directly into those local fields.
A top-level group's own clip/mask restricts its complete painted source,
including sampled counters in settled group slots.
Inspection reports the boundary-intersected group box and keeps conservative
laid-out child boxes. Each layer or group box intersects only its own finite
boundary before applying world transforms; enclosing group boundaries do not
cut descendant inspection boxes. Static leaves and nested
structural groups can have their own clips and masks at several depths, using
the top-level group's shared parent-local plane and original canvas dimensions
for percentages. Inverted masks retain conservative boxes around their cutouts.
Child transforms still use the full authored group body;
the boundary does not clip independently linked children. Counter observations
use settled text, including glyph backgrounds and preceding group content.
Groups with descendant boundaries support `plain`, `odometer` and `flip` text
counters in settled layout slots. Each counter's fragments are combined before
its own boundary, and each nested group's children before that group's boundary;
changing counter paint does not move siblings, pivots or independently linked
children. Other intrinsic dynamic sources and authored stagger on any structural
descendant remain guarded. The participating top-level group's own
animation may override other authored descendant animations; an external
ancestor's animation or only an inner group's animation does not qualify.
Static inspection and diagnostics retain the authored layout and composition;
HTML, SVG, PDF and PPTX retain whole-scene authored-static fallback for overridden
descendant motion. Intrinsic counter clocks continue through that override;
counter-group stagger remains guarded. Static graph-leaf groups with their own
or descendant clip/mask boundaries can use root stagger through the existing
partial horizontal-band adapter; it does not establish which child owns a band. See
[parent adapter boundaries](video.md#current-adapters-and-boundaries).

### `.to_json()`

Serializes the canvas to a JSON string.

```python
json_str = canvas.to_json()
```

Raises `ValidationError` if the canvas contains `.custom(fn)` layers (callbacks cannot be serialized).

### `Canvas.from_json(json_str)`

Deserializes a canvas from a JSON string.

```python
canvas = Canvas.from_json(json_str)
```

!!! note
    `from_json()` expects a **JSON string**, not a Python dict. Use `json.dumps(data)` first if you have a dict.

## `.custom(fn)`

Adds a callback that receives and returns a Pillow `Image`.

```python
from PIL import ImageDraw
from quickthumb import Canvas

def draw_badge(image):
    d = ImageDraw.Draw(image)
    d.polygon([(70, 70), (240, 70), (155, 180)], fill="#FF3B30")
    return image

canvas = Canvas(512, 512).custom(draw_badge)
```

| Rule | Detail |
| --- | --- |
| `fn` must be callable | Receives a `PIL.Image.Image` |
| Return value | May return the same image (mutated), a new image of the same size, or `None` |
| Errors | Exceptions from the callback are wrapped as `RenderingError` |
| Serialization | Custom layers are **not** JSON-serializable |
