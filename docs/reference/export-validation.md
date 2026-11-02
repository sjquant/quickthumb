---
description: Reference for format fidelity and validation in quickthumb.
---

# Format fidelity and validation

[Export reference](../exports.md) · [Choose an output format](../output-guide.md)

## Optional static SVG fidelity report

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

## Optional static PDF fidelity report

Canvas PDF exports accept the same three explicit limits under the `"pdf"` key:

```python
policy = ExportPolicy(fidelity={"pdf": {
    "pixel_tolerance": 0,
    "max_different_pixel_ratio": 0,
    "min_hash_similarity": 1,
}})
result = Canvas(160, 90).background(color="#123456").export("checked.pdf", policy=policy)
print(result.pixel_metrics.fidelity.verdict)
```

Install `quickthumb[pdf]` for ReportLab and the optional PDFium observer. Default
PDF exports do not import PDFium. Requested comparison renders the actual PDF
bytes on transparent RGBA at scale 1: this exporter uses one PDF point per
canonical pixel, not a 96-DPI print-size conversion. The report records PDFium
and binding versions, actual page size in points, page count, rendered dimensions
and the canonical environment. Native PDFium document/render/cleanup calls are
serialized across threads; canonical rendering and pixel comparison stay outside
that lock. It requires exactly one page of the expected
point dimensions; mismatches stay out of policy even under permissive pixel
limits. No resizing or white-background flattening hides alpha or geometry loss.

The same visible-RGBA/hash criteria and report-only behavior described above
apply. For an unexpected multi-page Canvas result, metrics observe its first
page and the reported page count makes the verdict out of policy. PDF generation
and requested comparison finish before opening the destination; missing/failed
observation preserves an existing file. Native text/vectors and explained raster
fragments are retained regardless of the fidelity verdict. Native PDF text is
searchable vector content; this does not promise PowerPoint-style editing.
Deck PDF comparison is rejected explicitly; export its Canvas slides individually.
This observation does not establish PPTX or animation fidelity.

## PPTX compatibility

PPTX keeps supported text and shapes editable. Glow can accompany that editable
content as a fixed image; re-export after edits to update the glow. Outlined
content may also require editing multiple objects together or re-exporting.

These effect combinations export the affected layer as a picture:

- Translucent text, shapes or outlines with stroke/glow effects.
- Gradient-filled shapes with stroke/glow effects.
- Rich text with glow, or content combining glow and shadow.
- Shape glow whose source extends beyond the slide.

Text with an opaque linear gradient can retain its editable fill and outline. Only the
paint actually used by each text part determines whether it is translucent;
unused or overridden colors do not remove editability.

Inspect `canvas.validate_export("pptx")` before export or the result's
`capability_report` afterward to see compatibility decisions. A mixed editable
foreground and fixed effect has `support="partial"`; a complete layer image has
`support="fallback"`. See [document layer routing](export-methods.md#document-layer-routing)
for receipt fields.

`ExportPolicy(pptx={"title": "native"})` rejects these effect image or mixed
representations for the layer with ID `title`. `ExportPolicy(unsupported_motion="error")` also
rejects these effect fallbacks. Canvas and Deck `to_pptx(policy=...)` enforce the
same policy checks as file exports. Defaults allow the explained fallbacks.

## HTML browser validation harness

The developer-only harness captures actual exported Canvas and two-slide Deck
stages with an explicitly selected Chrome and Node's built-in WebSocket. It does
not install a browser or change `ExportPolicy`:

```bash
PYTHONPATH=. python scripts/check_html_fidelity.py \
  --chrome "/path/to/chrome" --output /tmp/quickthumb-html-observations
```

The output directory must be new. Chrome runs headless with a temporary profile
and loopback CDP; the harness never attaches to an existing browser session.
It waits for fonts, images and slide transitions, captures only the original-size
stage at DPR 1, and seeks a real click-triggered CSS fade at 0, 5 and 10 seconds.
The report records browser/Node versions, canonical environment, input asset
hashes, executed route diagnostics, dimensions, seek points, explicit fixture
limits, pixel/hash metrics and verdicts. Canonical/browser PNGs remain beside it.

The mixed text/shape/image/mask fixtures allow a channel tolerance of 16, at most
8% differing pixels, and average-hash similarity of at least 0.94. Every component
must also satisfy its recorded region criteria: text allows 20% differing pixels
and requires hash similarity 0.95; the native ellipse allows 2% and requires 0.98.
The embedded image is exact; the masked fragment allows only one channel level
of rounding. Text/ellipse channel tolerance is 16. These local criteria prevent
small missing features from passing a whole-stage average. Negative controls
remove each text/image/mask/ellipse element in both the wide Canvas and tall Deck
and must fail that specific region, not merely another metric. All allowances
are fixture-specific and are not general document budgets. The simple
fade permits only one channel level of rounding; a deliberately wrong document
must fail comparison. Unexpected verdicts fail the command while retaining its
report. No automatic raster fallback or browser/CI installation is performed.

This observes one Chrome/font/platform environment and one bounded CSS animation,
not every browser, animation, cue, or Deck transition. CairoSVG cannot substitute
for this browser observation. Existing Node runtime tests check scheduling and
state behavior separately from browser pixels.

## Static cross-export checks

`tests/test_static_export_matrix.py` sends the same authored content through the
public Canvas and Deck file-export boundaries. The first 160×120 slide combines
repository-font text, a native rectangle, a generated image and an elliptical
mask; the second Deck slide has a translucent rectangle on a transparent canvas.
The checks distinguish measured appearance from structural evidence:

| Format | Canvas | Deck | Capability and fallback evidence |
| --- | --- | --- | --- |
| PNG | Decoded RGBA equals the canonical sample | Each numbered slide equals its canonical sample | Raster output; no native-object or document-viewer claim |
| SVG | Actual CairoSVG observation plus native text/vector and PNG checks | Single-file Deck SVG is rejected; each Canvas slide is measured separately | Executed source IDs, native routes and explained image/mask PNG routes |
| HTML | Stage markup, native text/CSS and exact mask PNG | Stage count and slide-local routes | Structural only; no browser pixel measurement in this matrix |
| PDF | Actual PDFium observation, searchable text, vector paths and image objects | Page count/geometry, native objects and rendered component regions | Canvas routes reported; Deck executed routes and receipt fidelity are not collected yet |
| PPTX | Editable OOXML text/shapes and exact positioned mask PNG | Slide count and per-slide native/raster objects | Executed routes reported; PowerPoint/Keynote appearance remains unmeasured |

The mixed SVG/PDF fixture uses explicit whole-image limits: zero channel
tolerance, at most 8% different pixels, and hash similarity of at least 0.94.
These are fixture-specific font/edge budgets, not export defaults. Native text
must also be present as text, and small rectangle, image and mask-interior regions
must match exactly so a missing component cannot hide in the whole-image budget.
The text region also requires hash similarity of at least 0.95 and permits at most
30% different pixels after a channel tolerance of 16 for font rasterization edges.
A real Deck PDF containing searchable white-on-white text must fail this regional
check, even though its text objects and other component regions are intact.
For the transparent rectangle only, alpha must match exactly while visible RGB
may differ by at most two levels per channel because of renderer
premultiplication/unpremultiplication rounding. Fully hidden RGB follows the
existing visible-RGBA comparison rule; PNG still preserves raw RGBA exactly.
No output is resized or flattened onto an invented matte.

Run `uv run --locked pytest tests/test_static_export_matrix.py --no-cov -q`.
The existing quality workflow already runs this file through `pytest tests/`
with the SVG/PDF/PPTX extras and native Cairo installed. Local environments
without an optional observer skip its cases with the dependency reason.
Pytest case IDs identify the format and document kind. Each case keeps its
source JSON, canonical PNGs, actual exports and JSON receipts in its temporary
directory; measured receipts include renderer versions, canonical environment,
limits and metrics. A failure is reproducible from the shared fixture and named
format check rather than a platform-specific screenshot baseline.

This is a bounded static matrix. It does not run a browser, certify PPTX viewer
pixels/fonts/timing, or add a Deck PDF fidelity policy. The separate HTML browser
harness and native presentation-viewer observations require their own execution
and environment evidence. Structural success must not be reported as a rendered
pixel-fidelity verdict.
