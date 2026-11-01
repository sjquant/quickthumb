---
description: Reference for export methods and receipts in quickthumb.
---

# Export methods and receipts

[Export reference](../exports.md) · [Choose an output format](../output-guide.md)

## Recommended output API

Use `export()` to write a Canvas or Deck and receive an `ExportResult` with
`written_paths`, capability/fallback diagnostics, pixel/timing metadata, assets
and the observed rendering environment.
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
| Export narrated Deck slides | `export(path, animation=VideoOptions(hold=3))` / `to_mp4(hold=3)` |
| Write silent animation frames plus a manifest | `export_image_sequence(directory, options=...)` |
| Write bounded Canvas-only Lottie vectors | `canvas.export("scene.lot", animation=LottieOptions(fps=30, hold=3))`; see [Lottie vectors](export-lottie.md#lottie-vectors) |

All animated byte methods and options use `hold` for settled-state seconds.
`render_quality="standard"` or `"high"` controls animation compositing;
`quality` on `export()`/`render()` controls compression: JPEG accepts integer
values 1–95 and WebP accepts 1–100.
Keep `workers=1` unless advanced spawn-based rendering is needed.
Optional [temporal exposure](../timing.md#temporal-exposure) adds motion blur to Canvas exports.
Both `export()` and `render()` enforce file capability policies such as
`unsupported_motion="error"` before writing; `export()` also returns the receipt.
Byte methods expose target-specific controls without the shared file receipt.
Use the returned `written_paths` for Deck raster sequences: they are numbered files.
Image sequences keep a separate API because their destination is a new directory.

## Format and option selection

Canvas and Deck use the same selection rules except that `.lot` is Canvas-only;
Deck rejects Lottie output.

| Input | Result |
| --- | --- |
| File extension, with no `format` | Selects the output; `.jpg`/`.jpeg` report `output_format="jpeg"`, `.htm`/`.html` report `"html"`. |
| `format="PNG"`, `"JPEG"` or `"WEBP"` (case-insensitive) | Selects raster encoding for a raster, unknown or extensionless filename. The requested filename is kept; it is not renamed to match the encoding. |
| Raster `format` with a document or animated extension | Rejected rather than writing image bytes into an SVG, PDF, HTML, PPTX, video or `.lot` filename. |
| `quality` | JPEG integer 1–95 or WebP integer 1–100; rejected for other targets. |
| `animation` | `GifOptions` for GIF; `VideoOptions` for MP4/WebM/MOV; `LottieOptions` for Canvas `.lot`. Rejected for other static/document targets. |

Format selection, compression quality and animation option-family conflicts are
rejected before asset reads or file writes. Codec-specific limits are validated
during export preparation. Rendering or encoding failures can still occur later;
ordinary file exports are not an atomic multi-file transaction. Inspect `written_paths` rather than guessing Canvas or
numbered Deck filenames. A Deck cannot be written as a single SVG; export its
Canvas slides individually. See [image sequences](export-frames.md#image-sequences) for their
separate new-directory and encoding-option contract.

## Document layer routing

Canvas and Deck HTML/PPTX exports, and Canvas SVG/PDF exports, report
executed layer routes in `result.capability_report` with
`feature="layer_representation"`. Native HTML/CSS, SVG/PDF primitives, editable
PowerPoint objects and original
embedded SVG have `support="native"`; emitted PNG fragments have
`support="fallback"` and `fallback="rasterize"`. These are representation
observations, not pixel-fidelity measurements.

`result.fallback_diagnostics` identifies the affected inspection `layer_id` and
reason. A retained group includes its descendant IDs in `layer_ids`; a shared
backdrop-dependent prefix has no single `layer_id` and lists all contributing
sources in `layer_ids`. Such composites are reported together because their
appearance depends on the combined pixels. Flattened auto-layout children keep
their original inspection IDs. Empty raster fragments and empty text produce no
element and no representation observation.

For these executed routes, `native_attempt=True` includes native content emission
or execution/verification of a native candidate that falls back to raster.
Read `support` and `fallback` to identify the representation actually adopted.
`False` means raster capture was selected before native generation or verification.
Capability-only diagnostics can leave this fact unknown (`None`).
Parent scenes report their static composite in SVG/PDF/PPTX; HTML can also report PNG
sources with baked affine CSS motion. Existing motion capability diagnostics
remain separate. SVG/PDF observations describe authored-static output. PDF text
retains embedded fonts when supported; shaping, glyph coverage and font-embedding
constraints can instead select an explained raster fragment.

Executed Deck observations also carry a zero-based `slide_index`. Layer IDs stay
local to each slide, matching `deck.inspect().slides[index]`; use both fields to
distinguish repeated IDs between slides. Canvas observations omit `slide_index`.
Deck HTML keeps its interactive cues, transitions and notes; these representation
records do not turn a click-driven slideshow into fixed-duration playback.

For example, `ExportPolicy(unsupported_motion="error")` does not reject a static
masked shape: this HTML route preserves its mask using a PNG fragment and
reports that decision. No layer-selection policy is added. This executed routing
report covers Canvas SVG/PDF and Canvas/Deck HTML/PPTX; Deck PDF does not yet
collect these observations. Fidelity metrics describe the complete document and are
not attributed to individual fallback layers. Rendering all slides precedes
opening the HTML destination, so an
unsupported later slide or strict motion rejection preserves an existing file.

PPTX routes describe the actual OOXML representation: native text boxes and
autoshapes remain editable objects; PNG fragments preserve their raster payload
and placement but lose per-glyph/vector editing. Raster reasons include masks,
backdrop compositing, image/radial text fills and unsupported font semantics.
Canvas observations omit a slide index; Deck observations identify their slide.
PPTX file exports build the complete presentation before opening the destination,
so a later source-rendering failure preserves an existing file.

These structural observations do not certify a PowerPoint or Keynote pixel
match, font availability, animation timing or transparency in a particular viewer.
There is no PPTX fidelity policy or automatic application renderer. PPTX geometry
uses 9,525 EMU per source pixel (96 pixels per inch), or 0.75 PDF points per source
pixel. A later PDF-based viewer comparison must derive scale from its actual page
dimensions rather than assuming the PDF exporter's one-point-per-pixel mapping.

## Migrating output calls

- `Deck.to_mp4()` now plays animation, matching Canvas and file exports.
  Replace old `to_animated_mp4()` and `to_narrated_mp4()` calls with `to_mp4()`.
- Replace `render_mp4()` and `render_narrated_mp4()` with `export("deck.mp4")`.
  The separate still-slide encoder is removed, with no aliases. To retain still
  scenes, author static canvases and use `Cut()`; this does not freeze an
  already animated Deck or promise identical encoded output.
- `export_image_sequence()` replaces `export_png_sequence()`; the public
  options/manifest/result models are now `ImageSequence*`, with no obsolete aliases.
- Replace animated Deck `slide_duration=` and narrated `default_duration=` with
  `hold=`. Replace animation `quality=` with `render_quality=`, including saved
  GifOptions, VideoOptions and ImageSequenceOptions JSON. There are no aliases.

## How export works

SVG, PDF and PPTX exporters keep eligible layers **native** and use canonical
PNG fragments where a native representation is unavailable. Positions, wrapping
and alignment share the raster renderer's layout math. HTML uses the same
native-or-raster approach; see [HTML](export-documents.md#html) below.

[Lottie](export-lottie.md#lottie-vectors) instead accepts a bounded native-vector subset and
rejects unsupported content before writing. It never substitutes PNG frames.

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

## Decks (multiple images and slides)

A `Deck` is an ordered list of canvases. Each slide is a full `Canvas` and renders exactly as it would on its own. See the [Deck API reference](../api/deck.md) for the full method list.

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
mp4_bytes = deck.to_mp4()   # timeline with per-slide narration
```

`render()` dispatches on the output extension: `.pdf` and `.pptx` produce a single document; `.gif`, `.mp4`, `.webm`, and `.mov` produce an animation; and raster extensions have no native multi-page container, so the deck writes one file per slide as a zero-padded numbered sequence and returns the written paths.

Slides may have different dimensions. `deck.diagnose()` aggregates each slide's [diagnostics](../diagnostics.md) (each tagged with its `slide_index`) and adds a `mixed-slide-size` warning when they differ. The PDF path sizes each page to its slide, but PPTX has a single presentation size taken from the first slide, so slides larger than the first are clipped by PowerPoint. Keep slides the same size when targeting `.pptx`. Decks round-trip through JSON with `deck.to_json()` / `Deck.from_json(...)`, reusing the per-canvas serialization.

## CLI

The CLI picks the format from the output extension too:

```bash
quickthumb render spec.json -o card.svg
quickthumb render spec.json -o card.pptx
quickthumb render spec.json -o card.pdf

# Live HTML slides; open /?presenter for the presenter dashboard
quickthumb serve slides.py
```
