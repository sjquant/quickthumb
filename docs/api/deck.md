---
description: Reference for quickthumb Deck — collecting canvases into multi-page PDFs, multi-slide PPTX, numbered image sequences, and contact-sheet grids.
---

# Deck

A `Deck` is an ordered collection of `Canvas` slides. Each slide renders exactly as it would on its own; the deck adds multi-output export on top of the same pipeline.

## Creation

### `Deck(slides=None)`

```python
from quickthumb import Canvas, Deck

deck = Deck()                     # empty
deck = Deck([cover, body])        # from a list of canvases
```

| Parameter | Type | Description |
| --- | --- | --- |
| `slides` | `list[Canvas] \| None` | Initial slides, in order. Each must be a `Canvas`. |

## Adding slides

Both builders mutate the deck and return `self` for chaining.

| Method | Description |
| --- | --- |
| `.slide(canvas)` | Append one `Canvas` as the next slide |
| `.add(*canvases)` | Append several canvases at once |

```python
deck = Deck().slide(cover).add(body, outro)
```

A deck is also a sequence: `len(deck)`, `deck[i]`, and iteration over slides all work, and `deck.slides` returns the underlying list.

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

### `.contact_sheet(columns=3, thumb_width=480, gap=24, padding=24, background="#FFFFFF")`

Renders every slide and letterboxes it into a uniform grid cell sized from the first slide's aspect ratio, returning a normal `Canvas` you can render to any raster format.

```python
deck.contact_sheet(columns=2).render("grid.png")
```

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `columns` | `int` | `3` | Grid columns (clamped to the slide count) |
| `thumb_width` | `int` | `480` | Cell width in pixels |
| `gap` | `int` | `24` | Pixels between cells |
| `padding` | `int` | `24` | Outer padding around the grid |
| `background` | `str` | `"#FFFFFF"` | Sheet background color |

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

A `mixed-slide-size` warning is added when slides do not all share the same dimensions, because PPTX export uses the first slide's size for the whole deck.

## JSON

### `.to_json()` / `Deck.from_json(json_str)`

Round-trips the deck through JSON, reusing each canvas's serialization. The shape is `{"slides": [<canvas spec>, ...]}`.

```python
spec = deck.to_json()
restored = Deck.from_json(spec)
```

!!! note
    As with `Canvas.to_json()`, decks containing `.custom(fn)` slides cannot be serialized unless those callbacks are registered. `from_json()` expects a **JSON string**, not a dict.
