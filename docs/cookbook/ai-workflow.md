---
description: Generate reliable quickthumb JSON specs with LLMs, validate them, render images, and iterate on AI-assisted thumbnail workflows.
---

# AI Workflow

quickthumb is designed to be a reliable target for LLM-generated image specs. This recipe walks through a full end-to-end workflow: writing a prompt, getting output, rendering it, and iterating.

## Why quickthumb works well with AI

- The schema is flat and typed — no nested ambiguity
- Every layer has a required `type` discriminator
- `ValidationError` gives specific field-level messages before any rendering
- The same spec can be round-tripped from JSON to Python and back
- Output is deterministic — the same spec always produces the same image

## Workflow overview

```
1. Write a prompt describing the layout
2. Model outputs quickthumb JSON or Python
3. Validate locally (ValidationError catches bad specs immediately)
4. Render to a PNG file
5. Review and iterate with targeted instructions
```

## Step 1 — Write a prompt

### For JSON output

```text
Generate a quickthumb JSON config for a 1280×720 YouTube thumbnail.

Schema rules:
- Top-level fields: "width", "height", "layers"
- Every layer must have a "type": "background" | "text" | "image" | "shape" | "outline"
- Every effect must have a "type": "stroke" | "shadow" | "glow" | "filter" | "background"
- Positions are [x, y] JSON arrays — values can be integers (px) or percentage strings ("50%")
- Colors are hex strings: "#RRGGBB" or "#RRGGBBAA"
- Layers render bottom-to-top in array order

Layout:
- Dark background photo with a semi-transparent black overlay
- Bold left-aligned white headline with stroke and shadow effects
- Subject photo on the right (use a placeholder path "portrait.png")
- Cyan (#22d3ee) outline border, width 12

Return only the JSON object. No explanation, no markdown fencing.
```

### For Python output

```text
Generate quickthumb Python code for a 1280×720 YouTube thumbnail.

Available imports:
  from quickthumb import (
      Canvas, Filter, LinearGradient, RadialGradient,
      Background, Shadow, Stroke, Glow, TextPart,
      Align, BlendMode, FitMode,
  )

Rules:
- Use Canvas.from_aspect_ratio("16:9", base_width=1280)
- Chain all layer calls on one canvas object
- Text on the left at position ("8%", "50%"), align=("left", "middle")
- Subject image on the right at position ("74%", "54%"), align=("center", "middle")
- Use high-contrast typography: Stroke + Shadow on all text
- End with canvas.render("thumbnail.png")

Return only the Python code block.
```

## Step 2 — Validate before rendering

For JSON specs, parse and validate before rendering to catch errors early:

```python
from quickthumb import Canvas, ValidationError

spec = """{ "width": 1280, ... }"""

try:
    canvas = Canvas.from_json(spec)
    print("Spec is valid")
except ValidationError as e:
    print(f"Invalid spec: {e}")
```

`ValidationError` messages are field-specific:

```
Field 'layers -> 2 -> effects -> 0 -> width': Input should be greater than 0
```

This makes it easy to feed the error back to the model with a targeted correction prompt.

## Step 3 — Render

```python
canvas.render("preview.png")
```

For quick iteration, render to a data URL and display in a Jupyter notebook:

```python
from IPython.display import Image
import base64

data_url = canvas.to_data_url(format="PNG")
b64 = data_url.split(",", 1)[1]
Image(data=base64.b64decode(b64))
```

## Step 4 — Iterate

Instead of regenerating the whole spec, give the model the current spec and a specific change:

```text
Here is my current quickthumb JSON spec:

<paste spec>

Change the outline color from "#22d3ee" to "#B8FF00" and increase the headline font
size from 88 to 104. Return only the updated JSON.
```

Or for layout changes:

```text
Move the subject image from position ["74%", "54%"] to ["78%", "52%"] and increase
its height from 520 to 580. Keep everything else identical. Return only the JSON.
```

## Full example: JSON round-trip

```python
import json
from quickthumb import Canvas, ValidationError

# Spec from an AI agent (or written by hand)
spec = {
    "width": 1280,
    "height": 720,
    "layers": [
        {"type": "background", "color": "#0F172A"},
        {"type": "background", "color": "#000000", "opacity": 0.4},
        {
            "type": "text",
            "content": [
                {"text": "AI-GENERATED\n", "color": "#22d3ee", "weight": 900, "effects": []},
                {"text": "THUMBNAILS", "color": "#FFFFFF", "weight": 900, "effects": []}
            ],
            "size": 96,
            "position": ["8%", "50%"],
            "align": "left",
            "effects": [
                {"type": "stroke", "width": 4, "color": "#000000"},
                {"type": "shadow", "offset_x": 4, "offset_y": 4, "color": "#000000", "blur_radius": 8}
            ]
        },
        {"type": "outline", "width": 12, "color": "#22d3ee"}
    ]
}

try:
    canvas = Canvas.from_json(json.dumps(spec))
    canvas.render("ai_thumbnail.png")
    print("Rendered successfully")
except ValidationError as e:
    print(f"Fix this and retry: {e}")
```

## Tips for reliable AI output

**Provide the layer schema explicitly.** Models hallucinate field names when working from memory. Including the layer types and effect types in the prompt reduces errors significantly.

**Use JSON over Python for agent workflows.** JSON is easier to validate, diff, and store. Python code requires a safe execution environment.

**One change at a time.** Rather than asking the model to redesign the whole layout, ask for one specific change. The spec stays mostly stable; only the target field changes.

**Validate before rendering.** Always call `Canvas.from_json()` before rendering. It's fast, catches all schema errors, and returns a specific error message you can forward back to the model.

**Use percentage positions.** Percentage strings like `"50%"` are more portable and easier for models to reason about than pixel coordinates that depend on knowing the canvas size.

**Keep specs in files.** Store each version of a spec as a `.json` file. This lets you roll back, diff between versions, and reuse specs across projects.
