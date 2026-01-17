# QuickThumb API Design

## Required Interface Code

This section defines the core interfaces and type signatures that must be implemented.

### Color Format Support

Colors can be specified in multiple formats:
- Hex string: `"#FF5733"` or `"#FF5733AA"` (with alpha)
- RGB tuple: `(255, 87, 51)`
- RGBA tuple: `(255, 87, 51, 255)`

### Position Format Support

Positions can be specified as:
- Pixels: `100`
- Percentage: `"50%"`


## Design Overview

### Core Principles
- **Required params upfront**: `Canvas(width, height)` or `Canvas.from_aspect_ratio(ratio)` or `Canvas.from_json()`
- **Typed methods without prefixes**: `.text()`, `.background()`, `.border()` - call multiple times for layers
- **Blend modes for backgrounds only**: Images, gradients, solid colors support opacity and blend modes
- **Helper classes for complex types**: `LinearGradient`, `RadialGradient`, etc.
- **Unified layer structure**: JSON uses single "layers" array with "type" field for each layer

### API Structure

```python
# Canvas creation
canvas = Canvas(width=1920, height=1080)
canvas = Canvas.from_aspect_ratio("16:9", base_width=1920)

# Background layers (can call multiple times, supports blend modes)
canvas.background(color="#FF5733", opacity=1.0, blend_mode=None)
canvas.background(image="path/to/img.jpg", brightness=0.8, fit="cover", opacity=0.5, blend_mode="multiply")
canvas.background(gradient=LinearGradient(45, [("#FF5733", 0.0), ("#3333FF", 1.0)]), opacity=0.7)

# Text layers (can call multiple times)
canvas.text(
    content="Title",
    font="Roboto",
    size=72,
    color="#FFFFFF",
    position=None,  # None = use alignment
    align=("center", "middle"),  # (horizontal, vertical)
    stroke=None,  # (width, color) tuple
    bold=False,
    italic=False,
    max_width=None  # For word wrapping
)

# Decoration layers
canvas.outline(width=5, color="#000000", offset=10)

# Render
canvas.render(path="output.png", format="png", quality=95)

# JSON loading
canvas = Canvas.from_json(json)      # Load from json string
```

### JSON Structure

```json
{
  "size": {"width": 1920, "height": 1080},
  "layers": [
    {
      "type": "background",
      "color": "#FF5733",
      "opacity": 1.0,
      "blend_mode": null
    },
    {
      "type": "background",
      "gradient": {
        "type": "linear",
        "angle": 45,
        "stops": [["#FF5733", 0.0], ["#3333FF", 1.0]]
      },
      "opacity": 0.7,
      "blend_mode": "multiply"
    },
    {
      "type": "text",
      "content": "Hello World",
      "font": "Roboto",
      "size": 72,
      "color": "#FFFFFF",
      "align": ["center", "middle"],
      "stroke": [3, "#000000"],
      "bold": true
    },
    {
      "type": "outline",
      "width": 10,
      "color": "#FFFFFF",
    }
  ]
}
```

### Helper Classes

```python
from quickthumb import LinearGradient, RadialGradient, BlendMode

# Gradients
LinearGradient(angle=45, stops=[("#FF5733", 0.0), ("#3333FF", 1.0)])
RadialGradient(stops=[("#FF5733", 0.0), ("#3333FF", 1.0)], center=(0.5, 0.5))

# Blend modes
BlendMode.NORMAL      # Default
BlendMode.MULTIPLY
BlendMode.OVERLAY
BlendMode.SCREEN
BlendMode.DARKEN
BlendMode.LIGHTEN
```

## Design Consistency Checks

### ✅ Consistency Validations

1. **Required vs Optional Parameters**
   - ✅ Canvas dimensions always required (either explicit size or aspect ratio)
   - ✅ Text content is required; font/size have sensible defaults
   - ✅ Background color/gradient/image are mutually exclusive (one required)

2. **Method Naming**
   - ✅ Consistent: `.background()`, `.text()`, `.border()`, `.outline()`
   - ✅ No `add_` prefix (as requested)
   - ✅ Plural for multi-instance methods is handled by calling multiple times

3. **Layer Ordering**
   - ✅ Implicit z-index by call order: first called = bottom layer
   - ✅ Backgrounds rendered first, then text, then decorations

4. **Blend Mode Scope**
   - ✅ Blend modes only for backgrounds (as clarified)
   - ✅ Text and decorations use standard alpha compositing
   - ✅ Opacity available for all layer types

5. **Color Format**
   - ✅ Consistent hex string format: "#RRGGBB" or "#RRGGBBAA"
   - ✅ Auto-conversion from hex to RGBA internally

6. **Position/Alignment**
   - ✅ Either `position=(x, y)` or `align=(h, v)` for text
   - ✅ Position in pixels or percentage: 100 or "50%"
   - ✅ Alignment uses enum/string: "center", "top", "left", etc.

## Implementation Priority

### Phase 1: Core (Minimum Viable)
- Canvas creation (size + aspect ratio)
- Solid background
- Basic text (no stroke, center alignment)
- PNG output
- Pydantic models for validation

### Phase 2: Enhanced Backgrounds
- Linear gradients
- Radial gradients
- Image backgrounds with fit modes
- Blend modes and opacity

### Phase 3: Text Features
- Text stroke/outline
- Custom positioning
- Font loading and caching
- Bold/italic variants

### Phase 4: Decorations & Polish
- Outline decoration
- JPEG/WebP output
- JSON loading
- Comprehensive error messages