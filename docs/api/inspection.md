---
description: Inspect Canvas and Deck documents through one JSON-safe envelope and join canonical samples to page layout without document-kind branching.
---

# Document inspection and sampling

Use `inspect_document()` when a tool or agent handles both Canvas and Deck
documents. It combines the existing layout, motion, and diagnostic reports
with the observed asset manifest in a `DocumentInspection` envelope:

```python
from quickthumb import Canvas, Deck, inspect_document

document = Deck(slides=[Canvas(320, 180).background(color="#FFFFFF")])
report = inspect_document(document, target="video", fps=24, max_samples=100)
print(report.model_dump_json(indent=2))

for page_index, page in enumerate(report.pages):
    print(page_index, page.width, page.height, len(page.layers))
```

## Common fields

| Field | Meaning for either document kind |
| --- | --- |
| `version` | Result schema version, currently `"1"` |
| `kind` | Source document discriminator: `"canvas"` or `"deck"` |
| `width`, `height` | First page dimensions in pixels, matching the animated output stage |
| `pages` | One `CanvasInspection` for a Canvas, or every Deck slide in document order |
| `motion` | The existing `MotionInspection`, including timing, sampled property states, per-slide details, capability rows, and export diagnostics |
| `diagnostics` | The existing `DiagnosticReport`; Deck findings retain `slide_index`, including `null` for document-wide findings |
| `asset_manifest` | Observed asset references, resolution status, and available identity/hash/cache information |

Every page retains layer identities, order, nested children, bounding boxes,
and text measurements. Mixed-size Deck pages keep their own dimensions.
The outer size is the first page's size, even when an authored Deck default
differs; the existing `deck.inspect()` still reports that authored default.

`target` accepts one exporter family (`raster`, `html`, `pptx`, or `video`),
an iterable of families, or `None` for all four. `policy`, `fps`, and
`max_samples` are passed to `inspect_motion()` unchanged. Motion observations
are bounded by `max_samples`; they are property states, not raster frames.
Empty Decks and invalid options raise the existing structured Quickthumb errors.

The call writes no export. Like the individual inspection/diagnostic methods,
it can load fonts, resolve assets, or decode media for measurement. The manifest
describes the state after those operations; it does not initiate another
prefetch or certify unresolved resources as available. Use `prefetch_assets()`
when explicit resolution is wanted, and `doctor` for environment readiness.

`canvas.inspect()` and `deck.inspect()` keep their existing result types and
JSON fields. Use those narrower methods when only layout is needed.

`DocumentInspection.model_json_schema()` describes this result envelope.
The document-authoring schemas still describe input specs, not this result.
As with `DiagnosticReport`, diagnostic findings deserialize as ordinary JSON
objects; read their `code`, `severity`, `message`, and location fields rather
than relying on a Python finding class after a JSON round trip.

## Join canonical samples to layout

Both document kinds already return the same `FrameSequence` from `sample()`.
Page indexes are zero-based and match `frames[].slide` and `timeline[].slide`:

```python
from quickthumb import DocumentInspection, FrameSequence

layout = DocumentInspection.model_validate_json(report.model_dump_json())
samples = FrameSequence.model_validate_json(document.sample().model_dump_json())
for frame in samples.frames:
    page = layout.pages[frame.slide]
    print(frame.index, frame.time, frame.width, frame.height, len(page.layers))
```

No document-kind branch is needed for this loop. `kind` still identifies the
source, and all per-page and per-frame details remain available.

- `sample()` captures one settled RGBA frame per page with its own dimensions
  and transparency; `time` is `None`, `duration` is zero, and `timeline` is empty
- `sample(time=[0, 0.5])` or `sample(fps=24)` captures the animated timeline,
  with frames in time order, first-page stage dimensions, and an opaque matte
- `frames[].index` orders the observations, while `frames[].slide` identifies
  the active page; the timeline segments describe page timing and transitions
- `environment` records renderer versions; each frame carries its raw RGBA
  data and SHA-256 digest for deterministic comparisons in that environment

Timing has separate meanings: `report.motion.duration` retains the existing
authored-motion inspection semantics. `samples.duration` is the canonical
capture duration, including its `hold` argument and resolved narration timing.
For example, a static Canvas has motion duration zero but a timed sample with
`hold=2` lasts two seconds. Use the sample's `duration`, `fps`, `timeline`, and
frame `time` fields for playback comparisons; do not infer those from the
layout report or motion property samples.
