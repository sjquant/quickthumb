---
description: Reference for image sequences and render quality in quickthumb.
---

# Image sequences and render quality

[Export reference](../exports.md) · [Choose an output format](../output-guide.md)

## Image sequences

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

All frames and `manifest.json` are rendered to an atomic staging directory before publication. The target directory must be non-existent; export fails safely if the destination directory already exists, preventing accidental overwrites.


Run `examples/image_sequence_overlay.py` for PNG, white-matted JPEG and
lossless WebP lower-third sequences with no FFmpeg dependency. All three
output directories must be fresh on every run.

## High-quality animated compositing

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

## Parallel animated rendering

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
