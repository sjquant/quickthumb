---
description: Catch layout and legibility problems with canvas.diagnose() and the quickthumb CLI — lint, render, and watch JSON specs from the terminal.
---

# Diagnostics & CLI

quickthumb can check a composition for common layout and legibility problems **without writing a file** — from Python with `canvas.diagnose()`, or from the terminal with `quickthumb lint`. This closes the loop for agent workflows: generate a spec, lint it, fix the findings, render.

## `canvas.diagnose()`

Returns a list of `Diagnostic` findings. An empty list means no issues.

```python
from quickthumb import Canvas

canvas = Canvas.from_json(spec)

for finding in canvas.diagnose():
    print(finding.severity, finding.code, finding.message)
```

Each `Diagnostic` has stable human-readable fields and optional structured fields for automation:

| Field | Type | Description |
| --- | --- | --- |
| `code` | `str` | One of `"off-canvas"`, `"tiny-text"`, `"text-overflow"`, `"text-clipped"`, `"missing-glyph"`, `"low-contrast"`, `"layer-overlap"`, `"layer-hidden"`, `"edge-crowding"`, or `"near-alignment"` |
| `severity` | `str` | `"warning"` or `"error"` |
| `layer_index` | `int` | Index of the offending layer in `canvas.layers` |
| `message` | `str` | Human-readable explanation with the measured values |
| `layer_id` | `str \| None` | Stable measured layer id, such as `"layer:3"` or `"layer:3:0"` for group children |
| `layer_name` | `str \| None` | Layer name when the layer model exposes one |
| `bbox` | `dict \| None` | Measured canvas-space bounding box with `x`, `y`, `width`, and `height` |
| `related_layers` | `list[str]` | Layer ids involved in the finding |
| `measured` | `dict` | Raw rule-specific values, such as contrast ratio, font size, or canvas dimensions |
| `suggestion` | `str \| None` | Repair hint when the rule can provide one |

### What gets checked

| Code | Trigger |
| --- | --- |
| `off-canvas` | A layer's bounding box falls partly or fully outside the canvas |
| `tiny-text` | Text smaller than 2.5% of the canvas height — likely illegible at thumbnail display sizes |
| `text-overflow` | A single word is wider than the layer's `max_width` and cannot be wrapped |
| `text-clipped` | Wrapped text extends past the canvas or its declared text box |
| `missing-glyph` | The selected font renders one or more characters as a missing-glyph placeholder |
| `low-contrast` | Text color has a contrast ratio under 2.0 against the composited layers below it |
| `layer-overlap` | Two visible layers overlap substantially enough to obscure one another |
| `layer-hidden` | A visible layer is fully covered by later opaque layers |
| `edge-crowding` | A visible layer is too close to a canvas safe margin or platform overlay |
| `near-alignment` | Related, unrotated layers have measured x/y starts within three pixels but are not exactly aligned |

!!! tip "Agent loop"
    `diagnose()` is designed for render → diagnose → fix iteration: have an LLM emit a spec, run `diagnose()`, and feed the findings back as targeted edit instructions instead of re-prompting from scratch.

Near-alignment findings compare final measured starts, rather than raw declared positions. The rule only compares layers that share a perpendicular span, ignores exact matches, intentional text-on-backdrop overlap, and layers with rotation or clip/mask composition, and reports the measured delta plus a coordinate repair suggestion.

!!! note
    The contrast check compares text color against the layers *below* the text layer. Text that gets its contrast from its own `Background` effect (e.g. dark text on its own bright pill) can report a false positive.

## The `quickthumb` CLI

The CLI requires the `cli` extra:

```bash
pip install "quickthumb[cli]"
```

### `quickthumb lint`

Checks a JSON spec for the same findings as `diagnose()`:

```bash
quickthumb lint spec.json
quickthumb lint spec.json --format json
quickthumb diagnose spec.json --format json
```

```text
[warning] layer 3: tiny-text — text size 14px is below 18px (2.5% of canvas height) ...
[warning] layer 4: low-contrast — text contrast ratio 1.47 against the layers below it ...
```

With `--format json`, lint prints a machine-readable payload:

```json
{
  "summary": {
    "diagnostic_count": 1,
    "error_count": 0,
    "warning_count": 1
  },
  "diagnostics": [
    {
      "code": "tiny-text",
      "severity": "warning",
      "layer_index": 3,
      "message": "text size 14px is below 18px ...",
      "layer_id": "layer:3",
      "bbox": {"x": 80, "y": 64, "width": 120, "height": 17},
      "related_layers": ["layer:3"],
      "measured": {"font_size": 14, "threshold": 18.0},
      "suggestion": "increase text size to at least 18px"
    }
  ]
}
```

### `quickthumb diff`

Compare a rendered image with a golden image before accepting a visual change:

```bash
quickthumb diff tests/snapshots/solid_background.png output.png
quickthumb diff golden.png output.png --format json --output diff.png
```

The comparison combines an average perceptual hash with pixel-level metrics.
By default, per-channel differences of up to 2 are ignored, but any pixel that
exceeds that tolerance fails the comparison. The default perceptual-hash
similarity threshold is `0.95`. Tighten or relax those values for a particular
renderer:

```bash
quickthumb diff golden.png output.png \
  --threshold 0.98 \
  --pixel-tolerance 1 \
  --max-diff-ratio 0.005
```

Use `--format json` for CI or agent pipelines. `--max-diff-ratio` can allow a
small fraction of pixels to differ, and `--output` writes a pixel-difference
image for visual inspection. Exit codes are:

| Exit code | Meaning |
| --- | --- |
| `0` | Images match within the configured tolerances |
| `1` | Images differ, inputs are invalid, or output cannot be written |

The same comparison is available as a Python assertion:

```python
from quickthumb import assert_image_similar

assert_image_similar(
    "tests/snapshots/solid_background.png",
    "output.png",
    threshold=0.95,
)
```

The assertion returns an `ImageDiff` with image sizes, changed-pixel counts,
normalized mean error, perceptual hashes, and similarity metrics when callers
need to report more detail.

Exit codes make it easy to gate CI or agent pipelines:

| Exit code | Meaning |
| --- | --- |
| `0` | No issues found |
| `1` | Invalid spec (bad JSON, validation error, missing file) |
| `2` | Rendering failure |
| `3` | Findings reported |

`diagnose` is an alias for `lint`. Both commands accept the same automation options:

```bash
quickthumb lint spec.json --fail-on error
quickthumb lint spec.json --ignore edge-crowding --ignore missing-glyph
```

`--fail-on warning` (the default) exits 3 for any remaining finding. `--fail-on error`
allows warnings while still failing on errors, and `--fail-on never` always exits 0 after
printing the findings. `--ignore` removes matching diagnostic codes from both the output and
the exit-status calculation. Invalid specs with `--format json` emit an `error` object rather
than a traceback.

JSON inputs must declare a top-level `kind` discriminator (`canvas` or `deck`). Deck findings
include `slide_index` and retain
the originating layer id, bounding box, measurements, related layers, and suggestion.

### `quickthumb render`

Renders a JSON spec to an image file:

```bash
quickthumb render spec.json -o thumbnail.png
quickthumb render spec.json -o thumbnail.webp --format WEBP --quality 90
quickthumb render spec.json -o debug.png --debug
```

| Option | Description |
| --- | --- |
| `-o, --output` | Output file path (default `output.png`) |
| `--format` | `PNG`, `JPEG`, or `WEBP` |
| `--quality` | Quality 1–95, JPEG/WEBP only |
| `--debug` | Overlay public layer-id bounding boxes on raster output |
| `--var KEY=VALUE` | Substitute `$KEY` placeholders in the spec (repeatable) |

### `quickthumb watch`

Re-renders the spec every time the file changes — useful while hand-tuning a layout:

```bash
quickthumb watch spec.json -o preview.png
```

`watch` takes the same options as `render`.

### `quickthumb serve`

Runs a local HTML slideshow server with live reload. With no source argument it
looks for `slides.py`, `slides.json`, `slides.html`, or `slides.htm` in that
order:

```bash
quickthumb serve
quickthumb serve examples/investor_deck.py
quickthumb serve deck.json --port 4040 --no-open
```

A Python source should define one module-level `Deck` or `Canvas` as `deck`,
`slides`, or `canvas`. A JSON source must declare `kind: "canvas"` or `kind: "deck"`;
Canvas documents contain `layers`, while Deck documents contain a top-level `slides` list.
Use `--host` and `--port` to change the listening
address, `--no-open` to suppress the initial browser window, and repeat
`--var KEY=VALUE` for JSON template substitutions.

The audience view is `/`. Presenter mode is selected by the `?presenter` query:

```text
http://localhost:3030/?presenter
```

Presenter mode shows the current slide, next-slide preview, speaker notes,
and a pause/resume/reset presentation timer. Its navigation and per-slide animation progress
are broadcast to audience tabs opened from the same server and restored on
reload. Audience-only navigation remains local. Add notes in Python with
`.slide(canvas, notes="...")` or as a `notes` string on a JSON slide.

### Variable substitution

The JSON-based commands accept `--var` to fill `$KEY` (or `${KEY}`) placeholders before parsing:

```bash
quickthumb render template.json -o ep42.png \
  --var TITLE="EPISODE 42" \
  --var ACCENT="#B8FF00"
```

Unresolved placeholders cause exit code `1`. `$theme.*` references are not variables — they are resolved by the [theme block](json-schema.md#theme-tokens) inside the spec itself.
