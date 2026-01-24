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
- **Typed methods without prefixes**: `.text()`, `.background()`, `.outline()` - call multiple times for layers
- **Method chaining**: All layer methods return `self` for fluent API (e.g., `canvas.background().text()`)
- **Blend modes for backgrounds only**: Images, gradients, solid colors support opacity and blend modes
- **Helper classes for complex types**: `LinearGradient`, `RadialGradient`, etc.
- **Unified layer structure**: JSON uses single "layers" array with "type" field for each layer
- **Bidirectional JSON**: Load from JSON with `from_json()`, export to JSON with `to_json()`

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
    content="Title",  # str or list of TextPart for rich text
    font="Roboto",
    size=72,
    color="#FFFFFF",
    position=None,  # None = use alignment
    align=("center", "middle"),  # (horizontal, vertical)
    stroke=None,  # (width, color) tuple
    bold=False,
    italic=False,
    max_width=None,  # For word wrapping
    shadow=None,  # (x_offset, y_offset, color, blur) tuple
    glow=None,  # (color, radius, opacity) tuple
    letter_spacing=None,  # pixels between characters
    line_height=None,  # multiplier for line spacing (e.g., 1.5)
)

# Rich text with partial styling using TextPart
canvas.text(
    content=[
        TextPart("Hello ", color="#FFFFFF"),
        TextPart("World", color="#FF0000", stroke=(2, "#000000")),
    ],
    size=72,
    shadow=(4, 4, "#00000080", 5),  # effects apply to all parts
)

# Decoration layers
canvas.outline(width=5, color="#000000", offset=10)

# Render
canvas.render(path="output.png", format="png", quality=95)

# JSON operations
canvas = Canvas.from_json(json_str)  # Load from JSON string
json_str = canvas.to_json()          # Export canvas to JSON string
```

### JSON Structure

```json
{
  "width": 1920,
  "height": 1280,
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
      "bold": true,
      "shadow": [4, 4, "#00000080", 5],
      "glow": ["#FF0000", 10, 0.8],
      "letter_spacing": 2,
      "line_height": 1.5
    },
    {
      "type": "text",
      "content": [
        {"text": "Hello ", "color": "#FFFFFF"},
        {"text": "World", "color": "#FF0000", "stroke": [2, "#000000"]}
      ],
      "size": 72,
      "shadow": [4, 4, "#00000080", 5]
    },
    {
      "type": "outline",
      "width": 10,
      "color": "#FFFFFF",
    }
  ]
}
```

### Method Chaining

All layer methods (`.background()`, `.text()`, `.outline()`) return `self`, enabling fluent method chaining:

```python
# Single-line chaining
canvas = Canvas(1920, 1080).background(color="#2c3e50").text("Title", size=84)

# Multi-line chaining for readability
canvas = (
    Canvas(1920, 1080)
    .background(color="#2c3e50")
    .text("Python Tutorial", font="Roboto", size=84, color="#FFFFFF", bold=True)
    .text("Learn the Basics", font="Roboto", size=48, color="#EEEEEE")
)

# Mixed with traditional syntax
canvas = Canvas(1920, 1080)
canvas.background(color="#FF5733").text("Hello")
canvas.text("Another layer")  # Can still call methods separately
```

### JSON Serialization

Canvas instances can be serialized to JSON and deserialized from JSON:

```python
# Create canvas programmatically
canvas = Canvas(1920, 1080) \
    .background(color="#2c3e50") \
    .text("Hello", size=72, color="#FFFFFF")

# Export to JSON string
json_str = canvas.to_json()
# Returns: '{"size": {"width": 1920, "height": 1080}, "layers": [...]}'

# Load from JSON string
canvas = Canvas.from_json(json_str)

# Round-trip example
original = Canvas(1920, 1080).background(color="#FF5733")
exported = original.to_json()
recreated = Canvas.from_json(exported)
assert recreated.to_json() == exported  # Perfect round-trip
```

### Helper Classes

```python
from quickthumb import LinearGradient, RadialGradient, BlendMode, TextPart

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

# Rich text parts (for partial text styling)
TextPart(
    text="Hello",
    color="#FF0000",  # optional, inherits from parent text layer
    stroke=None,  # optional (width, color) tuple
)
```

### Text Effects

Text layers support various effects for enhanced visual styling:

```python
# Drop shadow - (x_offset, y_offset, color, blur)
canvas.text("Shadow", size=72, shadow=(4, 4, "#00000080", 5))

# Glow/outer glow - (color, radius, opacity)
canvas.text("Glow", size=72, glow=("#FF0000", 10, 0.8))

# Letter spacing - pixels between characters
canvas.text("SPACED", size=72, letter_spacing=10)

# Line height - multiplier for multi-line text
canvas.text("Line 1\nLine 2", size=72, line_height=1.5)

# Combined effects
canvas.text(
    "Epic Title",
    size=96,
    color="#FFFFFF",
    stroke=(3, "#000000"),
    shadow=(4, 4, "#00000080", 8),
    glow=("#FF5733", 15, 0.6),
)
```

### Rich Text (Partial Styling)

Use `TextPart` to apply different styles to portions of text:

```python
from quickthumb import TextPart

# Different colors for different words
canvas.text(
    content=[
        TextPart("Hello ", color="#FFFFFF"),
        TextPart("World", color="#FF0000"),
    ],
    size=72,
)

# Mix styled and unstyled parts (unstyled inherits defaults)
canvas.text(
    content=[
        TextPart("Normal "),  # inherits color="#FFFFFF"
        TextPart("RED", color="#FF0000", stroke=(2, "#000000")),
        TextPart(" Normal"),  # inherits color="#FFFFFF"
    ],
    color="#FFFFFF",  # default for parts without explicit color
    size=72,
    shadow=(4, 4, "#000000", 5),  # effects apply to all parts
)
```

## Design Consistency Checks

### ✅ Consistency Validations

1. **Required vs Optional Parameters**
   - ✅ Canvas dimensions always required (either explicit size or aspect ratio)
   - ✅ Text content is required; font/size have sensible defaults
   - ✅ Background color/gradient/image are mutually exclusive (one required)

2. **Method Naming**
   - ✅ Consistent: `.background()`, `.text()`, `.outline()`
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

7. **Method Chaining**
   - ✅ All layer methods return `self` for fluent API
   - ✅ Enables both chained and traditional syntax
   - ✅ Consistent return type across all mutating methods

8. **JSON Serialization**
   - ✅ Bidirectional: `from_json()` for loading, `to_json()` for exporting
   - ✅ Perfect round-trip: `Canvas.from_json(canvas.to_json())` recreates identical canvas
   - ✅ Uses Pydantic's `model_dump()` and `model_validate()` for serialization
   - ✅ Accepts only JSON strings (not dictionaries) for type safety

## Implementation Priority

### Phase 1: Core (Minimum Viable)
- Canvas creation (size + aspect ratio)
- Solid background
- Basic text (no stroke, center alignment)
- PNG output
- Pydantic models for validation
- Method chaining (all layer methods return `self`)

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
- JSON operations (`from_json()`, `to_json()`)
- Comprehensive error messages

### Phase 5: Text Effects
- Drop shadow (`shadow` parameter)
- Glow/outer glow (`glow` parameter)
- Letter spacing (`letter_spacing` parameter)
- Line height (`line_height` parameter)
- Rich text with `TextPart` (partial text styling)