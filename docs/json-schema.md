# JSON Schema & AI Workflow

QuickThumb canvases can be fully described as JSON. This makes them easy to generate with an LLM, store in a database, pass through an API, or version-control alongside your content.

## Round-trip serialization

Any canvas that uses only built-in layer types can be serialized and deserialized without loss:

```python
from quickthumb import Canvas

# Python → JSON
json_str = canvas.to_json()

# JSON → Python
canvas = Canvas.from_json(json_str)
```

!!! note
    `Canvas.from_json()` expects a **JSON string**. If you have a Python dict, call `json.dumps(data)` first.
    Canvases with `.custom(fn)` layers cannot be serialized — callbacks are not representable in JSON.

## JSON structure

A QuickThumb JSON document has three top-level fields:

```json
{
  "width": 1280,
  "height": 720,
  "layers": [ ... ]
}
```

Every layer object requires a `"type"` discriminator field. Layers render in array order — first item is backmost.

## Layer schemas

### Background layer

```json
{
  "type": "background",
  "color": "#0F172A",
  "gradient": null,
  "image": null,
  "opacity": 1.0,
  "blend_mode": null,
  "fit": null,
  "effects": []
}
```

Only include the fields you need — unspecified fields use their defaults.

**Gradient variants:**

```json
{
  "type": "background",
  "gradient": {
    "type": "linear",
    "angle": 120,
    "stops": [["#111827", 0.0], ["#11182700", 1.0]]
  }
}
```

```json
{
  "type": "background",
  "gradient": {
    "type": "radial",
    "stops": [["#00000000", 0.0], ["#000000CC", 1.0]],
    "center": [0.5, 0.5]
  }
}
```

**Image background:**

```json
{
  "type": "background",
  "image": "https://example.com/photo.jpg",
  "fit": "cover",
  "blend_mode": "multiply",
  "effects": [
    { "type": "filter", "blur": 4, "brightness": 0.75, "contrast": 1.1, "saturation": 0.9 }
  ]
}
```

---

### Text layer

```json
{
  "type": "text",
  "content": "Hello World",
  "size": 72,
  "color": "#FFFFFF",
  "position": ["50%", "50%"],
  "align": "center",
  "opacity": 1.0,
  "rotation": 0.0,
  "effects": []
}
```

**Rich text with `TextPart` list:**

```json
{
  "type": "text",
  "content": [
    { "text": "5 ", "color": "#FBBF24", "weight": 900, "effects": [] },
    { "text": "WARNING SIGNS", "color": "#FFFFFF", "weight": 900, "effects": [] }
  ],
  "size": 80,
  "position": ["8%", "55%"],
  "align": "left",
  "max_width": "65%",
  "auto_scale": false,
  "rotation": 0.0,
  "opacity": 1.0,
  "effects": [
    { "type": "stroke", "width": 3, "color": "#000000" },
    { "type": "shadow", "offset_x": 4, "offset_y": 4, "color": "#000000", "blur_radius": 8 }
  ]
}
```

**Gradient-filled text:**

```json
{
  "type": "text",
  "content": "GRADIENT",
  "size": 120,
  "fill": {
    "type": "linear_gradient",
    "angle": 90,
    "stops": [["#FF6B6B", 0.0], ["#4ECDC4", 1.0]]
  },
  "position": ["50%", "50%"],
  "align": "center",
  "effects": []
}
```

**Image-filled text:**

```json
{
  "type": "text",
  "content": "TEXTURE",
  "size": 140,
  "fill": {
    "type": "image",
    "path": "fire_texture.jpg",
    "fit": "cover"
  },
  "position": ["50%", "50%"],
  "align": "center",
  "effects": []
}
```

`fill` discriminator values: `"linear_gradient"`, `"radial_gradient"`, `"image"`. `fill` can also be set per `TextPart` entry using the same discriminated object.

**Align values:** `"center"`, `"left"`, `"right"`, `"top-left"`, `"top-center"`, `"top-right"`, `"bottom-left"`, `"bottom-center"`, `"bottom-right"`

---

### Image layer

```json
{
  "type": "image",
  "path": "portrait.png",
  "position": ["74%", "54%"],
  "width": 420,
  "height": 520,
  "fit": "cover",
  "align": "center",
  "opacity": 1.0,
  "rotation": 0.0,
  "remove_background": false,
  "border_radius": 24,
  "blend_mode": "normal",
  "effects": [
    { "type": "filter", "contrast": 1.1, "saturation": 1.05 },
    { "type": "shadow", "offset_x": 0, "offset_y": 12, "color": "#000000", "blur_radius": 24 }
  ]
}
```

---

### Shape layer

```json
{
  "type": "shape",
  "shape": "rectangle",
  "position": [48, 48],
  "width": 320,
  "height": 96,
  "color": "#CC0000",
  "border_radius": 14,
  "opacity": 1.0,
  "rotation": 0.0,
  "align": "top-left",
  "effects": [
    { "type": "stroke", "width": 2, "color": "#FFFFFF" }
  ]
}
```

`"shape"` values: `"rectangle"` or `"ellipse"`

---

### Outline layer

```json
{
  "type": "outline",
  "width": 12,
  "color": "#B8FF00",
  "offset": 0,
  "opacity": 1.0
}
```

---

## Effect schemas

Effects are embedded in each layer's `"effects"` array and use a `"type"` discriminator:

=== "Stroke"
    ```json
    { "type": "stroke", "width": 4, "color": "#000000" }
    ```

=== "Shadow"
    ```json
    { "type": "shadow", "offset_x": 4, "offset_y": 8, "color": "#000000", "blur_radius": 12 }
    ```

=== "Glow"
    ```json
    { "type": "glow", "color": "#B8FF00", "radius": 16, "opacity": 0.35 }
    ```

=== "Filter"
    ```json
    { "type": "filter", "blur": 4, "brightness": 0.75, "contrast": 1.1, "saturation": 0.9 }
    ```

=== "Background (text)"
    ```json
    { "type": "background", "color": "#111827CC", "padding": [16, 24], "border_radius": 14, "opacity": 1.0 }
    ```

=== "Grain"
    ```json
    { "type": "grain", "intensity": 0.12, "monochrome": true, "blend_mode": "overlay", "opacity": 1.0 }
    ```

    `blend_mode` values: `"overlay"`, `"screen"`, `"multiply"`, `"normal"`. Optional `"seed"` integer for deterministic output.

## Complete example

A full YouTube-style thumbnail spec:

```json
{
  "width": 1280,
  "height": 720,
  "layers": [
    {
      "type": "background",
      "image": "https://images.unsplash.com/photo-1516321318423-f06f85e504b3",
      "fit": "cover",
      "effects": [{ "type": "filter", "brightness": 0.6 }]
    },
    {
      "type": "background",
      "color": "#000000",
      "opacity": 0.35
    },
    {
      "type": "shape",
      "shape": "rectangle",
      "position": [52, 52],
      "width": 360,
      "height": 96,
      "color": "#CC0000",
      "border_radius": 14,
      "effects": []
    },
    {
      "type": "text",
      "content": [
        { "text": "AI ", "color": "#B8FF00", "weight": 900, "effects": [] },
        { "text": "THUMBNAILS", "color": "#FFFFFF", "weight": 900, "effects": [] }
      ],
      "size": 108,
      "position": ["8%", "52%"],
      "align": "left",
      "max_width": "58%",
      "rotation": 0.0,
      "opacity": 1.0,
      "effects": [
        { "type": "stroke", "width": 6, "color": "#000000" },
        { "type": "shadow", "offset_x": 4, "offset_y": 4, "color": "#000000", "blur_radius": 8 }
      ]
    },
    {
      "type": "image",
      "path": "portrait.png",
      "position": ["75%", "55%"],
      "width": 430,
      "height": 540,
      "fit": "cover",
      "align": "center",
      "border_radius": 24,
      "effects": [
        { "type": "shadow", "offset_x": 0, "offset_y": 14, "color": "#000000", "blur_radius": 24 }
      ]
    },
    {
      "type": "outline",
      "width": 12,
      "color": "#B8FF00",
      "offset": 0,
      "opacity": 1.0
    }
  ]
}
```

## AI workflow

QuickThumb JSON is well-suited for LLM generation because the schema is flat, every field is typed, and the output is directly renderable without transformation.

### Recommended prompt (JSON output)

```text
Generate a QuickThumb JSON config for a 1280×720 YouTube thumbnail.

Rules:
- Top-level fields: "width", "height", "layers"
- Every layer must have a "type" field: "background", "text", "image", "shape", or "outline"
- Every effect must have a "type" field: "stroke", "shadow", "glow", "filter", "background", or "grain"
- Positions are [x, y] arrays — values can be integers (px) or percentage strings like "50%"
- Colors are hex strings: "#RRGGBB" or "#RRGGBBAA"
- Layers render bottom-to-top in array order

Layout: dark background image, semi-transparent black overlay, bold left-aligned title text,
subject image on the right, cyan outline border.
Return only the JSON object, no explanation.
```

### Recommended prompt (Python output)

```text
Generate QuickThumb Python code for a 1280×720 YouTube thumbnail.

Available imports:
from quickthumb import Canvas, Filter, LinearGradient, RadialGradient, Background,
    Shadow, Stroke, Glow, TextPart, Align, BlendMode, FitMode

Rules:
- Use Canvas.from_aspect_ratio("16:9", base_width=1280) to create the canvas
- Chain all layer calls on a single canvas object
- Keep text on the left (position around "8%", "50%"), subject image on the right (around "74%", "54%")
- Use high-contrast typography with Stroke and Shadow effects
- End with canvas.render("thumbnail.png")
Return only the Python code block.
```

### Validation and iteration workflow

1. Have the model produce a QuickThumb JSON or Python spec.
2. Render it locally with `canvas.render("preview.png")`.
3. Identify what to change — colors, text, layout — without rewriting the full spec.
4. Feed the rendered result back to the model with targeted instructions if needed.

### Tips for reliable LLM output

- Provide the complete layer schema (or a link to this page) as context.
- Ask for one layer type at a time if the model struggles with complex compositions.
- Validate JSON before rendering: `Canvas.from_json(spec)` raises `ValidationError` immediately on bad input with a descriptive message.
- Use `"content": "plain string"` for simple text and `"content": [{"text": ...}]` for rich text — both are valid.

## Serialization notes

| Field | Serialized form |
| --- | --- |
| `align` | String: `"center"`, `"top-left"`, etc. |
| `blend_mode` | String: `"multiply"`, `"normal"`, etc. |
| `fit` | String: `"cover"`, `"contain"`, `"fill"` |
| `position` | JSON array: `[640, 360]` or `["50%", "50%"]` |
| Gradient stops | JSON array of `["#color", 0.0]` pairs |
| `null` fields | Omitted fields default to `null` / their default value |
