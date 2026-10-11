---
description: Have an LLM write quickthumb JSON specs, validate and lint them, feed errors back, and render the result.
---

# AI Workflow

An LLM is good at writing a layout as JSON and bad at guessing field names.
quickthumb fits this well: the spec has a published JSON Schema, a bad spec
fails with errors that point at the exact field, and a valid spec can be
checked for layout problems before you render it.

The loop looks like this:

1. Give the model the schema and describe the image you want.
2. Load its answer with `Canvas.from_json()`. If it fails, send the errors back.
3. Run `diagnose()`. If it finds problems, send those back too.
4. Render.

## 1. Give the model the schema

Export the schema once:

```bash
quickthumb schema --output quickthumb.schema.json
```

or from Python with `canvas_json_schema()`. It is large (about 100 KB), so the
best use is as the response schema in your provider's structured-output or
tool-calling feature, which stops the model from inventing fields at all. If
you put it in the prompt instead, the `layers` and `effects` definitions are
the parts that matter.

A prompt along these lines works:

```text
Write a quickthumb canvas spec as JSON, following the attached schema.

Canvas: 1280×720 YouTube thumbnail.
- Dark navy background (#0F172A).
- Left-aligned two-line headline: "AI-GENERATED" in cyan (#22D3EE),
  "THUMBNAILS" in white, 96px, weight 900.
- Cyan outline around the canvas, 12px.

Use percentage strings like "8%" for positions. Return only the JSON.
```

## 2. Load it, and send back errors

```python
import json
from quickthumb import Canvas, ValidationError

spec = """
{
  "kind": "canvas",
  "width": 1280,
  "height": 720,
  "layers": [
    {"type": "background", "color": "#0F172A"},
    {
      "type": "text",
      "id": "headline",
      "content": [
        {"text": "AI-GENERATED\\n", "color": "#22D3EE"},
        {"text": "THUMBNAILS", "color": "#FFFFFF"}
      ],
      "font": "Inter",
      "font_source": "google",
      "size": 96,
      "weight": 900,
      "position": ["8%", "50%"],
      "align": ["left", "middle"]
    },
    {"type": "outline", "width": 12, "color": "#22D3EE"}
  ]
}
"""

try:
    canvas = Canvas.from_json(spec)
except ValidationError as error:
    feedback = [
        f"{detail.path}: {detail.message}" + (f" ({detail.suggestion})" if detail.suggestion else "")
        for detail in error.details
    ]
    # Send `feedback` back to the model and ask for a corrected spec.
    raise
```

Each entry in `error.details` has the JSON Pointer of the field (`path`), the
layer's `id` if it has one, a stable `code`, and sometimes a `suggestion`.
Giving each layer an `id` makes the messages easier for the model to act on:

```text
/layers/1/size (layer 'headline'): Input should be greater than 0
```

See [Structured Errors](../errors.md) for the full list of codes.

## 3. Check the layout

A spec can be valid and still look wrong: text too small to read, a word that
runs off the edge, white text on a light photo. `diagnose()` catches these:

```python
findings = canvas.diagnose().findings
for finding in findings:
    print(finding.severity, finding.code, finding.message)
```

```text
warning low-contrast text worst-tile contrast ratio 1.04 against the layers below it is under 2.0; the text may be hard to read
```

Send the findings back the same way as validation errors. See
[Diagnostics & CLI](../diagnostics.md) for every check.

## 4. Render

```python
canvas.render("thumbnail.png")
```

## Asking for changes

Once you have a spec you like, ask for edits instead of a new design. Send the
current spec and one specific change:

```text
Here is the current spec:

<spec>

Change the outline color to #B8FF00 and the headline size to 104.
Keep everything else the same. Return only the JSON.
```

Small edits keep the rest of the layout stable, and a diff of the two JSON
files shows exactly what the model changed.

## Why JSON rather than Python

Models can write quickthumb Python too, but you then have to run generated
code. A JSON spec is data: you can validate it, store it, diff it, and render
it without executing anything the model wrote.
