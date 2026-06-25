---
description: Reference for quickthumb Deck — collecting canvases into multi-page PDFs, multi-slide PPTX, and numbered image sequences.
---

# Deck

A `Deck` is an ordered collection of `Canvas` slides. Each slide renders exactly as it would on its own; the deck adds multi-output export on top of the same pipeline.

## Creation

### `Deck(width=None, height=None, slides=None, theme=None)`

```python
from quickthumb import Canvas, Deck

deck = Deck()                          # empty, no default size
deck = Deck(1280, 720)                 # default slide size for unsized slides
deck = Deck(slides=[cover, body])      # from pre-built canvases
```

| Parameter | Type | Description |
| --- | --- | --- |
| `width` | `int \| None` | Default slide width. Provide with `height` or omit both. |
| `height` | `int \| None` | Default slide height. |
| `slides` | `list[Canvas] \| None` | Initial slides, in order. Each must be a `Canvas`. |
| `theme` | `dict \| None` | Token groups shared with every slide's `$theme.*` references (slide-level themes win). Preserved across `to_json()`/`from_json()`. |

### `Deck.from_aspect_ratio(ratio, base_width)`

Creates a deck whose default slide size comes from an aspect ratio string, mirroring `Canvas.from_aspect_ratio`.

```python
deck = Deck.from_aspect_ratio("16:9", 1280)   # default 1280×720
```

## Adding slides

Both builders mutate the deck and return `self` for chaining. When the deck has a default size, an **unsized** `Canvas()` inherits it; a canvas built with an explicit size keeps its own (and triggers a `mixed-slide-size` warning when it differs).

| Method | Description |
| --- | --- |
| `.slide(canvas)` | Append one `Canvas` as the next slide |
| `.add(*canvases)` | Append several canvases at once |

```python
deck = (
    Deck(1280, 720)
    .slide(Canvas().background(color="#101820").text(content="Cover", ...))
    .slide(Canvas().background(color="#1A1A2E").text(content="Body", ...))
)
```

Adding an unsized canvas to a deck with no default size raises `ValidationError`: give the deck a size or size the canvas.

A deck is also a sequence: `len(deck)`, `deck[i]`, and iteration over slides all work, and `deck.slides` returns a copy of the slide list (mutating it does not change the deck).

## Export methods

### `.render(path, format=None, quality=None)`

Renders the deck, dispatching on the output extension. Returns the list of written file paths.

```python
deck.render("deck.pdf")      # one multi-page PDF (a page per slide)
deck.render("deck.pptx")     # one multi-slide PPTX (a slide per slide)
deck.render("slides.png")    # slides_01.png, slides_02.png, …
deck.render("slides.jpg", quality=85)
```

| Extension | Behavior |
| --- | --- |
| `.pdf` | Single multi-page PDF. Requires the `pdf` extra. |
| `.pptx` | Single multi-slide PPTX. Requires the `pptx` extra. |
| `.png` / `.jpg` / `.jpeg` / `.webp` | One file per slide as a zero-padded numbered sequence. |

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `path` | `str` | — | Output path; raster names become `<stem>_NN<ext>` |
| `format` | `str \| None` | `None` | Raster format override (`"PNG"`, `"JPEG"`, `"WEBP"`) |
| `quality` | `int \| None` | `None` | Compression quality. Only valid for raster sequences. |

!!! warning
    Passing `quality` with `.pdf` or `.pptx` output raises `RenderingError`, as does rendering an empty deck.

### `.to_pdf()` / `.to_pptx()`

Return the deck as document bytes, one page/slide per canvas.

```python
with open("deck.pdf", "wb") as f:
    f.write(deck.to_pdf())   # requires quickthumb[pdf]
pptx_bytes = deck.to_pptx()  # requires quickthumb[pptx]
```

## `.diagnose()`

Aggregates each slide's [`Canvas.diagnose()`](canvas.md#diagnose) findings and adds deck-wide checks. Returns a list of `DeckDiagnostic` entries:

```python
for finding in deck.diagnose():
    print(finding.slide_index, finding.code, finding.message)
```

| Field | Type | Description |
| --- | --- | --- |
| `code` | `str` | Slide codes (`off-canvas`, `tiny-text`, …) or `mixed-slide-size` |
| `severity` | `str` | `"warning"` or `"error"` |
| `message` | `str` | Human-readable description |
| `slide_index` | `int \| None` | Originating slide, or `None` for deck-wide findings |
| `layer_index` | `int \| None` | Originating layer within the slide, when applicable |

A `mixed-slide-size` warning is added when slides do not all share the same dimensions. The PDF path sizes each page to its slide, but PPTX export uses the first slide's size for the whole deck, so larger later slides are clipped by PowerPoint — keep slides a uniform size when targeting `.pptx`.

## JSON

### `.to_json()` / `Deck.from_json(json_str)`

Round-trips the deck through JSON, reusing each canvas's serialization. The shape is `{"width": ..., "height": ..., "theme": {...}, "slides": [<canvas spec>, ...]}`, where `width`/`height` (the default slide size) and `theme` are emitted only when set. A top-level `theme` is shared with every slide so slides can use `$theme.*` tokens, exactly like `Canvas.from_json`.

```python
spec = deck.to_json()
restored = Deck.from_json(spec)
```

!!! note
    As with `Canvas.to_json()`, decks containing `.custom(fn)` slides cannot be serialized unless those callbacks are registered. `from_json()` expects a **JSON string**, not a dict.
