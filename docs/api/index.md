---
description: Explore the quickthumb API reference for Canvas, layers, backgrounds, text, images, shapes, outlines, effects, enums, and gradients.
---

# API Reference

Use `Canvas` to author a scene and `Deck` to sequence scenes. Both implement the
same document operations; individual layer pages describe their authoring fields.

## Supported public surface

Import documented authoring types and result models from `quickthumb`, and audio
analysis from the documented `quickthumb.audio` module. A name
being importable from another module does not make it a supported entry point.

| Surface | Supported use |
| --- | --- |
| Authoring | `Canvas`, `Deck`, documented layer/effect models, motion tracks, transitions and option models |
| Document operations | `validate()`, `inspect()`, `diagnose()`, `prefetch_assets()`, `sample()` and `export()` on either document kind; `inspect_document()` for generic consumers |
| Results | Typed reports, `ExportResult`, `CanonicalFrame` / `FrameSequence`, and `ImageSequence*` results; serialize them with `model_dump_json()` |
| JSON | `to_json()`, `Canvas.from_json()`, `Deck.from_json()`, `canvas_json_schema()` and `document_json_schema()` |
| Audio authoring | [`quickthumb.audio.analyze_audio()` and `AudioAnalysis`](audio.md); bake source-clock onset times and RMS-driven scale into numeric motion |
| Specialist output | Documented `render()`, `render_frame()`, `to_*()` and `export_image_sequence()` methods when their return type or controls fit the task |

`export()` is the recommended file boundary: it preflights capability policy and
returns written paths and diagnostics. Specialist methods have their own return
values and do not all enforce that policy; see [output API](../exports.md#recommended-output-api).
Keep format-specific options at that boundary rather than calling exporters directly.

Modules beginning with `_`, renderer/context objects, and timeline compilation
helpers are implementation details. They can change or disappear without a
supported lifecycle. Use `sample()` to consume frames instead of coordinating a
compiler and renderer. The reference pages and generated schema describe the
installed version's supported fields; public does not mean frozen across versions.

### One document workflow

This uses the same layer data in Python, canonical JSON and a Deck, with no
renderer objects or optional dependencies:

```python
from quickthumb import Canvas, Deck, Document, ExportResult

canvas = Canvas(320, 180).background(color="#102030").shape(
    "rectangle", position=(24, 24), width=80, height=40, color="#42CEB7",
    id="badge", motion_key="brand", anchor=(0, 0),
)
restored = Canvas.from_json(canvas.to_json())
document: Document = Deck(slides=[restored])
result: ExportResult = document.export("slides.png")
print(result.written_paths)  # Numbered paths are reported by the result.
print(document.sample().frames[0].sha256)
```

## Shared layer vocabulary

Canvas layers use the same fields when carried by a Deck slide or canonical
JSON. A Deck adds slide order, transitions, narration and notes; it does not
rename layer fields. Python tuples become JSON arrays, enum values become
strings, and each layer has a `type` discriminator.

| Field or concept | Meaning |
| --- | --- |
| `id` | Optional identifier unique within a Canvas scene, including group descendants. Each Deck slide has its own identity scope. |
| `motion_key` | Optional matching key across scenes for Morph transitions; distinct from a scene-local `id`. |
| `position`, `width`, `height` | Authored placement and size, in pixels or percentage strings where the layer accepts them. Percentages resolve against the canvas; consult the layer reference for required fields and sizing rules. |
| `align` | The point of a layer's layout box placed at `position`; also controls text alignment. See [Align](enums.md#align). |
| `rotation`, `anchor` | Rotation is in degrees. `anchor=(x, y)` is a normalized 0–1 pivot for canonical motion, distinct from layout alignment. Static rotation has its own framing; see [transform anchors](video.md#transform-anchors-and-independent-scale). |
| `opacity` | Layer opacity from 0 to 1 where supported. |
| `animation` | A preset or `AnimationSpec` containing typed tracks and timing. Position tracks are offsets from authored placement; scale tracks transform the outer object, while `ImageZoomTrack` changes image content inside its frame. |
| Group | Auto-layout owns child placement. Use `.group()` for rows/columns rather than positioning each child. |
| `parent` / null | Advanced, scene-local transform hierarchy for top-level animatable layers. Child placement is parent-local; percentage coordinates still resolve against the canvas. This is separate from group layout. See [parent transforms](video.md#parent-links-and-null-controllers). |

Not every layer accepts every field: backgrounds, outlines, nulls and drawable
layers have different roles. Their reference pages and the [JSON schema](../json-schema.md#published-schema)
are the field-level contract. [Plugin registrations](../json-schema.md#plugin-layers)
declare parameters and can supply rendering callbacks through an explicit
`PluginRegistry`; parsing JSON does not package or install those callbacks.

## Pages

| Page | What it covers |
| --- | --- |
| [Canvas](canvas.md) | Creating a canvas, every layer method, checks, and export methods |
| [Deck](deck.md) | Several canvases as one PDF, PPTX, HTML slideshow, video, or image sequence |
| [Document inspection](inspection.md) | `inspect_document()` and generic Canvas/Deck sampling consumers |
| [Background](background.md) | `.background()`: colors, gradients, and images |
| [Text](text.md) | `.text()` and `TextPart`: text and rich text |
| [Image](image.md) | `.image()`: placed images and cut-outs |
| [Shape](shape.md) | `.shape()`: rectangles, ellipses, pills, triangles, stars, polygons |
| [Path](path.md) | `.path()`: filled/stroked SVG path data and bounded motion |
| [SVG](svg.md) | `.svg()`: icons and logos from SVG files |
| [Video](video.md) | `.video()`: video clips, captions, and audio |
| [Group](group.md) | `.group()`: auto-layout rows and columns |
| [Outline](outline.md) | `.outline()`: a border around the canvas |
| [Data visualizations](data-visualizations.md) | `.chart()` and `.qr_code()` |
| [Effects](effects.md) | `Stroke`, `Shadow`, `Glow`, `Filter`, `Background`, `Grain`, `Duotone`, `InnerShadow`, `BackdropBlur` |
| [Enums & Gradients](enums.md) | `Align`, `BlendMode`, `FitMode`, `LinearGradient`, `RadialGradient`, `TextFillImage` |

## Error types

| Exception | When raised |
| --- | --- |
| `ValidationError` | Invalid arguments passed to a layer builder (raised immediately) |
| `RenderingError` | Failure during `.render()`, `.to_base64()`, or `.to_data_url()` |
