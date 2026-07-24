---
description: Use quickthumb JSON specs with AI workflows to generate, validate, store, and render thumbnail designs from structured data.
---

# JSON Schema & AI Workflow

quickthumb canvases can be fully described as JSON. This makes them easy to generate with an LLM, store in a database, pass through an API, or version-control alongside your content.

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

A Canvas JSON document has four required top-level fields, plus an optional `theme` block:

```json
{
  "kind": "canvas",
  "width": 1280,
  "height": 720,
  "theme": { ... },
  "layers": [ ... ]
}
```

The top-level `"kind"` discriminator is required by the CLI and must be `"canvas"` or `"deck"`.
Canvas documents carry `layers`; Deck documents carry `slides` and may also define a shared
default size, theme, and transitions. Every layer object requires its own `"type"`
discriminator field. Layers render in array order — first item is backmost.

## Published schema

Emit the current JSON Schema from the same Pydantic models used by `Canvas.from_json()`:

```bash
quickthumb schema > quickthumb.schema.json
quickthumb schema --output quickthumb.schema.json
quickthumb schema --document --output quickthumb.document-schema.json
```

The same schemas are available from Python as `canvas_json_schema()` and
`document_json_schema()`.

!!! note "Schema scope"
    `quickthumb schema` describes concrete Canvas specs for external tooling and
    constrained generation. Use `quickthumb schema --document` for the combined
    Canvas/Deck discriminator schema. `Canvas.from_json()` remains the source of truth
    for what quickthumb can load.

    The CLI and `serve` command require the top-level `kind` discriminator. The
    direct `Canvas.from_json()` and `Deck.from_json()` APIs continue to accept
    legacy strings without it; newly serialized documents always include `kind`.

    Authoring conveniences such as `$theme.*` are resolved by quickthumb before
    model validation, so generic JSON Schema validators may reject unresolved
    authoring specs that quickthumb itself can load.

The command writes deterministic JSON only, so it can be checked into a repo, piped into an editor, or passed directly to a constrained-generation API. The Canvas schema includes the current canvas fields, built-in layer discriminators, effects, animations, supported platform presets, and the optional top-level `theme` block. The `--document` schema adds the Deck root and maps both document kinds through `kind`.

For constrained generation, prefer concrete resolved values in typed fields:

```text
Use quickthumb.schema.json as the JSON response schema.
Generate one valid quickthumb canvas spec for a 1280x720 YouTube thumbnail.
Return only the JSON object.
Use concrete hex colors and numeric sizes in layer fields.
Use only these layer type discriminators: background, text, image, shape, svg, group, outline.
```

## Theme tokens

Define brand tokens once in a top-level `theme` block and reference them anywhere in the spec with `$theme.path`:

```json
{
  "kind": "canvas",
  "width": 1280,
  "height": 720,
  "theme": {
    "colors": { "primary": "#B8FF00", "ink": "#111111" },
    "sizes": { "title": 96 }
  },
  "layers": [
    { "type": "background", "color": "$theme.colors.ink" },
    { "type": "text", "content": "Hello", "size": "$theme.sizes.title", "color": "$theme.colors.primary" }
  ]
}
```

Rules:

- The `theme` block can nest groups arbitrarily; reference paths with dots: `$theme.colors.primary`.
- A whole-string reference keeps its native JSON type — `"size": "$theme.sizes.title"` resolves to the number `96`, and tokens can hold lists too.
- Scalar tokens (strings, numbers) can also be embedded inside longer strings.
- Theme values may reference other theme tokens (aliases). Circular references raise `ValidationError`.
- Referencing an undefined token raises `ValidationError`.
- Tokens are resolved at parse time: `to_json()` emits resolved values without the `theme` block.
- Theme tokens work alongside `$var` template substitution (`quickthumb render --var KEY=VALUE`); `$theme.*` references are never treated as variables.

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
  "font_source": "auto",
  "font_variations": {},
  "emoji_style": "monochrome",
  "size": 72,
  "color": "#FFFFFF",
  "position": ["50%", "50%"],
  "align": "center",
  "max_height": null,
  "min_size": 1,
  "balance_lines": false,
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
    {
      "text": "5 ",
      "color": "#FBBF24",
      "font_source": null,
      "font_variations": null,
      "emoji_style": null,
      "weight": 900,
      "effects": []
    },
    {
      "text": "WARNING SIGNS",
      "color": "#FFFFFF",
      "font_source": "auto",
      "font_variations": {},
      "emoji_style": "monochrome",
      "weight": 900,
      "effects": []
    }
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
    "type": "linear",
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

`fill` discriminator values: `"linear"`, `"radial"`, `"image"` — the same tags as background gradients. `fill` can also be set per `TextPart` entry using the same discriminated object.

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

`"shape"` values: `"rectangle"`, `"ellipse"`, `"pill"`, `"triangle"`, `"star"`, `"polygon"`

**Star and polygon variants:**

```json
{
  "type": "shape",
  "shape": "star",
  "position": ["80%", "50%"],
  "width": 280,
  "height": 280,
  "color": "#7C5CFF",
  "align": "center",
  "rotation": 12,
  "star_points": 5,
  "inner_radius": 0.45
}
```

```json
{
  "type": "shape",
  "shape": "polygon",
  "position": [600, 60],
  "width": 160,
  "height": 100,
  "color": "#53BF9D",
  "points": [[0.0, 0.25], [0.6, 0.25], [0.6, 0.0], [1.0, 0.5], [0.6, 1.0], [0.6, 0.75], [0.0, 0.75]]
}
```

`points` is required for `"polygon"` (and only valid there): at least 3 vertices, normalized `0.0`–`1.0` inside the shape box. `star_points` (≥ 3) and `inner_radius` (between 0 and 1, exclusive) only apply to `"star"`.

---

### SVG layer

Rasterized at render time — requires the `quickthumb[svg]` extra. See the [SVG reference](api/svg.md).

```json
{
  "type": "svg",
  "path": "logo.svg",
  "position": ["92%", "10%"],
  "width": 120,
  "align": "center",
  "opacity": 1.0,
  "rotation": 0.0,
  "blend_mode": null,
  "effects": []
}
```

`width`/`height` set the raster size; aspect ratio is preserved when only one is given. SVG layers accept the same `effects` as image layers.

---

### Group layer

Auto-layout container — children are measured and stacked along a row or column, so they must not set `position`. See the [Group reference](api/group.md).

```json
{
  "type": "group",
  "direction": "column",
  "gap": 24,
  "padding": 0,
  "position": ["8%", "50%"],
  "align": ["left", "middle"],
  "item_align": "start",
  "children": [
    { "type": "shape", "shape": "pill", "width": 120, "height": 36, "color": "#E94560" },
    { "type": "text", "content": "AUTO LAYOUT", "size": 96, "color": "#FFFFFF", "weight": 900 },
    { "type": "text", "content": "No coordinates were harmed", "size": 40, "color": "#A2A8D3" }
  ]
}
```

- `direction`: `"column"` (default) or `"row"`
- `gap`: pixels between children; `padding`: int, `[vertical, horizontal]`, or `[top, right, bottom, left]`
- `item_align`: cross-axis placement — `"start"`, `"center"`, or `"end"`
- `children` types: `"text"`, `"image"`, `"shape"`, `"svg"`, or nested `"group"`

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

quickthumb JSON is well-suited for LLM generation because the schema is flat, every field is typed, and the output is directly renderable without transformation.

### Recommended prompt (JSON output)

```text
Generate a quickthumb JSON config for a 1280×720 YouTube thumbnail.

Rules:
- Top-level fields: "kind": "canvas", "width", "height", "layers" (optional "theme" for shared tokens)
- Every layer must have a "type" field: "background", "text", "image", "shape", "svg", "group", or "outline"
- Every effect must have a "type" field: "stroke", "shadow", "glow", "filter", "background", or "grain"
- Positions are [x, y] arrays — values can be integers (px) or percentage strings like "50%"
- Colors are hex strings: "#RRGGBB" or "#RRGGBBAA"
- Layers render bottom-to-top in array order
- Prefer a "group" layer for stacked text blocks: children must not set "position";
  the group is anchored once with "position" + "align"

Layout: dark background image, semi-transparent black overlay, a left-anchored column group
with badge text and a bold title, subject image on the right, cyan outline border.
Return only the JSON object, no explanation.
```

### Recommended prompt (Python output)

```text
Generate quickthumb Python code for a 1280×720 YouTube thumbnail.

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

1. Have the model produce a quickthumb JSON or Python spec.
2. Lint it: `quickthumb lint spec.json` or `canvas.diagnose()` flags off-canvas layers, tiny text, overflow, and low contrast before you ever look at pixels. See [Diagnostics & CLI](diagnostics.md).
3. Render it locally with `canvas.render("preview.png")` or `quickthumb render spec.json`.
4. Identify what to change — colors, text, layout — without rewriting the full spec.
5. Feed the findings (or the rendered result) back to the model with targeted instructions if needed.

### Tips for reliable LLM output

- Provide the complete layer schema (or a link to this page) as context.
- Ask for one layer type at a time if the model struggles with complex compositions.
- Validate JSON before rendering: `Canvas.from_json(spec)` raises `ValidationError` immediately on bad input with a descriptive message.
- Use `"content": "plain string"` for simple text and `"content": [{"text": ...}]` for rich text — both are valid.
- Prefer `group` layers over hand-placed coordinates — auto-layout specs survive content-length changes, which is where LLM-positioned layouts usually break.
- Put brand values in a `theme` block so iteration prompts only touch content, not styling.

## Serialization notes

| Field | Serialized form |
| --- | --- |
| `align` | String: `"center"`, `"top-left"`, etc. |
| `blend_mode` | String: `"multiply"`, `"normal"`, etc. |
| `fit` | String: `"cover"`, `"contain"`, `"fill"` |
| `position` | JSON array: `[640, 360]` or `["50%", "50%"]` |
| Gradient stops | JSON array of `["#color", 0.0]` pairs |
| `null` fields | Omitted fields default to `null` / their default value |
| `theme` block | Resolved at parse time — `to_json()` emits resolved values without the `theme` block |
