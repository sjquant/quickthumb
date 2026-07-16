---
description: Export quickthumb canvases to SVG, editable PowerPoint (PPTX), PDF documents, and animated GIF/MP4/WebM alongside PNG/JPEG/WEBP.
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
```

Each format also has a direct method when you want the content in memory:

```python
svg_markup = canvas.to_svg()
pptx_bytes = canvas.to_pptx()
pdf_bytes = canvas.to_pdf()
gif_bytes = canvas.to_gif()
mp4_bytes = canvas.to_mp4()      # and canvas.to_webm()
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

## Animated GIF & video (Canvas MP4/WebM, Deck GIF/WebM)

Animated export renders per-layer `animation` effects and deck slide `transition`s as real raster frames, sampled through the same pixel pipeline as PNG output. Canvas GIF/MP4/WebM and Deck GIF/WebM play this animated timeline. `deck.render("deck.mp4", soundtrack=...)` also uses it; Deck MP4 without a soundtrack is the separate static narration workflow below.

```python
from quickthumb import Canvas, Deck, Fade, GifOptions, VideoOptions
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

`Canvas.render()` and `Deck.render()` accept a format-specific options object for
animated file output. Use `GifOptions` for GIF (`fps`, `matte`, `loop`,
`max_size=(width, height)`, and `colors`) and `VideoOptions` for MP4/WebM
(`fps`, `matte`, `soundtrack`, and `loop_audio`). GIF sizing and palette controls
are rejected for video output, and video options are rejected for GIF output.
The generic `quality` option remains reserved for JPEG and WebP raster output.

Deck MP4 and WebM exports support per-slide narration. Pass `audio=` to `Deck.slide()`;
without `duration=`, Quickthumb uses the file's ffprobe duration. An explicit
duration trims audio or pads it with silence, while a slide without audio holds
silently for `default_duration` (3 seconds). `deck.render("deck.mp4")` and
`deck.render_mp4("deck.mp4")` produce H.264/yuv420p video with an AAC track on
every output. Without a soundtrack or animation options, this is the static
narrated path: layer animations and slide transitions are not played. Pass
`soundtrack=AudioTrack(path="music.mp3", volume=0.16, loop=True)` or
`animation=VideoOptions(...)` to `deck.render()` for animated MP4/WebM.
Quickthumb mixes that bed and the
scheduled `Deck.slide(audio=...)` narration during rendering; `deck.to_animated_mp4()`
and `deck.to_webm()` do the same for byte exports. Callers do not
need to pre-mix audio themselves.

The timing model mirrors the HTML slideshow, with one difference a non-interactive medium forces: there is nothing to click, so `on_click` animations play automatically in sequence, exactly like `after_previous` (the same choice PowerPoint's own video export makes). Each slide plays its transition (over the previous slide's final frame), runs its animation timeline (starting when the transition starts, like the HTML runtime), then holds its settled state — for the transition's `advance_after` when set, else for `slide_duration` (`hold` on `Canvas`). In narrated MP4/WebM output, the inferred or explicit narration duration (or the silent-slide default) extends the visual slide when it is longer than `advance_after`. A slide with no transition cross-fades in over 0.5s (slide 0 with none starts instantly); set a transition on slide 0 to animate in from the matte, which also makes looping GIFs wrap smoothly.

GIF is encoded by Pillow with per-frame durations, so no extra dependency is needed. MP4 (H.264) and WebM (VP9) require the `ffmpeg` binary on `PATH` (or pointed to by the `QUICKTHUMB_FFMPEG` environment variable).

Canvas MP4 and WebM output can carry a soundtrack — any audio file ffmpeg decodes (MP3, WAV, AAC, OGG, ...), encoded as AAC in MP4 and Opus in WebM:

```python
mp4 = canvas.to_mp4(soundtrack="music.mp3")                    # loops to fill the video
mp4 = canvas.to_mp4(soundtrack="jingle.wav", loop_audio=False) # plays once, then silence
```

The audio is always trimmed to the video length. For an `AudioTrack`, `loop=True` repeats a shorter track and `loop=False` plays it once before silence; `loop_audio` is an explicit override. Legacy string paths keep the previous looping default. GIF exports do not accept a soundtrack.

!!! note "Format limits"
    None of these formats carry transparency: frames are composited onto the opaque `matte` color (default black). Mixed-size slides are scaled to fit and centered on the first slide's size. H.264/VP9 4:2:0 output needs even dimensions, so odd-sized canvases lose their last pixel row/column in MP4/WebM output. GIF encoding keeps frames in memory and rejects timelines that exceed its frame budget; reduce FPS or duration, or use MP4/WebM for long, high-resolution animations. Animated Deck MP4/WebM accepts at most 64 slides with narration because each narration is decoded as a concurrent FFmpeg input; split larger narrated decks into multiple exports. Silent slides do not count toward this limit.

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
deck.render("deck.mp4", soundtrack={"path": "music.mp3", "loop": True})  # animated + mixed audio
deck.render("animated.mp4", animation=VideoOptions(fps=20))  # animated, silent
deck.render("slides.png")   # numbered sequence: slides_01.png, slides_02.png, …

pdf_bytes = deck.to_pdf()
pptx_bytes = deck.to_pptx()
gif_bytes = deck.to_gif()
webm_bytes = deck.to_webm()
mp4_bytes = deck.to_mp4()   # static slides with per-slide narration
```

`render()` dispatches on the output extension: `.pdf` and `.pptx` produce a single document; `.gif` and `.webm` produce an animation; `.mp4` produces static slides with per-slide narration unless `soundtrack` or `animation` selects the animated path; and raster extensions have no native multi-page container, so the deck writes one file per slide as a zero-padded numbered sequence and returns the written paths.

Slides may have different dimensions. `deck.diagnose()` aggregates each slide's [diagnostics](diagnostics.md) (each tagged with its `slide_index`) and adds a `mixed-slide-size` warning when they differ. The PDF path sizes each page to its slide, but PPTX has a single presentation size taken from the first slide, so slides larger than the first are clipped by PowerPoint — keep slides a uniform size when targeting `.pptx`. Decks round-trip through JSON with `deck.to_json()` / `Deck.from_json(...)`, reusing the per-canvas serialization.

## CLI

The CLI picks the format from the output extension too:

```bash
quickthumb render spec.json -o card.svg
quickthumb render spec.json -o card.pptx
quickthumb render spec.json -o card.pdf
```
