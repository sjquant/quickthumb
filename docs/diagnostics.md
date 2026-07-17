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
| `code` | `str` | One of `"off-canvas"`, `"tiny-text"`, `"text-overflow"`, `"low-contrast"`, `"layer-overlap"` |
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
| `low-contrast` | Text color has a contrast ratio under 2.0 against the composited layers below it |
| `layer-overlap` | Two visible layers overlap substantially enough to obscure one another |

!!! tip "Agent loop"
    `diagnose()` is designed for render → diagnose → fix iteration: have an LLM emit a spec, run `diagnose()`, and feed the findings back as targeted edit instructions instead of re-prompting from scratch.

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

Exit codes make it easy to gate CI or agent pipelines:

| Exit code | Meaning |
| --- | --- |
| `0` | No issues found |
| `1` | Invalid spec (bad JSON, validation error, missing file) |
| `2` | Rendering failure |
| `3` | Findings reported |

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
`slides`, or `canvas`. A JSON source may be a canvas spec or a deck object with a
top-level `slides` list. Use `--host` and `--port` to change the listening
address, `--no-open` to suppress the initial browser window, and repeat
`--var KEY=VALUE` for JSON template substitutions.

The audience view is `/`. Presenter mode is selected by the `?presenter` query:

```text
http://localhost:3030/?presenter
```

Presenter mode shows the current slide, next-slide preview, speaker notes,
elapsed timer, and controls. Its navigation and per-slide animation progress
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
