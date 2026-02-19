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
    bold=False,
    italic=False,
    weight=None,  # CSS-style font weight: 100-900 or "thin"/"bold"/"black" etc. (mutually exclusive with bold)
    max_width=None,  # For word wrapping
    effects=None,  # list of effect objects (Stroke, Shadow, Glow, etc.)
    background_color=None,  # Hex string for text background
    padding=None,  # int or (horizontal, vertical) tuple
    border_radius=None,  # int for rounded background corners
)

# Text with background (Badge style)
canvas.text(
    content="20:19",
    size=30,
    color="#FFFFFF",
    background_color="#000000",
    padding=(15, 8),
    border_radius=10,
)

# Image layers (Overlay images/logos)
canvas.image(
    path="assets/logo.png",  # Local path or URL
    position=(50, 50),
    width=200,  # width or height (preserves aspect ratio if one is None)
    opacity=1.0,
    rotation=0,  # Degrees
    align=("top", "left"),
    remove_background=True,  # Remove background using rembg (requires quickthumb[rembg])
)

# Text with effects using effect classes
from quickthumb import Stroke

canvas.text(
    content="Epic Title",
    size=72,
    effects=[
        Stroke(width=3, color="#000000"),
    ],
)

# Rich text with partial styling using TextPart
canvas.text(
    content=[
        TextPart("Hello ", color="#FFFFFF"),
        TextPart("World", color="#FF0000", effects=[Stroke(width=2, color="#000000")]),
    ],
    size=72,
    effects=[Stroke(width=1, color="#000000")],  # effects apply to all parts
)

# Decoration layers
canvas.image(path="logo.png", position=(20, 20), width=100)
canvas.outline(width=5, color="#000000", offset=10)

# Render
canvas.render(path="output.png", format="png", quality=95)

# Export methods
base64_str = canvas.to_base64(format="PNG", quality=None)  # Returns base64-encoded image string
data_url = canvas.to_data_url(format="PNG", quality=None)  # Returns data URL (e.g., "data:image/png;base64,...")

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
        "stops": [
          ["#FF5733", 0.0],
          ["#3333FF", 1.0]
        ]
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
      "bold": true,
      "effects": [{ "type": "stroke", "width": 3, "color": "#000000" }],
      "background_color": "#000000",
      "padding": [10, 5],
      "border_radius": 5
    },
    {
      "type": "image",
      "path": "assets/logo.png",
      "position": [50, 50],
      "width": 200,
      "opacity": 1.0,
      "rotation": 0,
      "remove_background": true
    },
    {
      "type": "text",
      "content": [
        { "text": "Hello ", "color": "#FFFFFF" },
        {
          "text": "World",
          "color": "#FF0000",
          "effects": [{ "type": "stroke", "width": 2, "color": "#000000" }]
        }
      ],
      "size": 72,
      "effects": [{ "type": "stroke", "width": 1, "color": "#000000" }]
    },
    {
      "type": "outline",
      "width": 10,
      "color": "#FFFFFF"
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

### Export Methods

Canvas can be exported in multiple formats:

```python
# Render to file
canvas.render("output.png", format="PNG", quality=None)

# Export as base64 string (without data URL prefix)
base64_str = canvas.to_base64(format="PNG", quality=None)
# Returns: "iVBORw0KGgoAAAANSUhEUgAA..."

# Export as data URL (with MIME type prefix)
data_url = canvas.to_data_url(format="PNG", quality=None)
# Returns: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA..."

# Supported formats: PNG, JPEG, WEBP
canvas.to_base64(format="JPEG", quality=85)
canvas.to_data_url(format="WEBP", quality=90)
```

**Quality Parameter**:

- Only applicable for JPEG and WEBP formats (1-100)
- Raises `RenderingError` if used with PNG
- Defaults to None (uses PIL defaults: JPEG=75, WEBP=80)

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

````python
from quickthumb import LinearGradient, RadialGradient, BlendMode, TextPart, Stroke

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

# Text effects
Stroke(width=3, color="#000000")

# Rich text parts (for partial text styling)
    TextPart(
        text="Hello",
        color="#FF0000",  # optional, inherits from parent text layer
        effects=None,  # optional list of effect objects
        background_color="#FFFF00",  # Highlight specific words
        padding=5,
    )
    ```

    ### Text Effects

Text layers support effects for enhanced visual styling using effect classes:

```python
from quickthumb import Stroke

# Single effect
canvas.text("Title", size=72, effects=[
    Stroke(width=3, color="#000000")
])

# Multiple stroke effects
canvas.text("Epic Title", size=96, color="#FFFFFF", effects=[
    Stroke(width=5, color="#000000"),
    Stroke(width=2, color="#FF0000"),
])

# Effects are composable and reusable
stroke_style = [Stroke(width=3, color="#000000")]
canvas.text("Title 1", size=72, effects=stroke_style)
canvas.text("Title 2", size=60, effects=stroke_style)
````

**Available Effects:**

- `Stroke(width, color)`: Adds an outline around text

### Rich Text (Partial Styling)

Use `TextPart` to apply different styles to portions of text:

```python
from quickthumb import TextPart, Stroke

# Different colors for different words
canvas.text(
    content=[
        TextPart("Hello ", color="#FFFFFF"),
        TextPart("World", color="#FF0000"),
    ],
    size=72,
)

# Mix styled and unstyled parts with effects
canvas.text(
    content=[
        TextPart("Normal "),  # inherits color="#FFFFFF"
        TextPart("RED", color="#FF0000", effects=[Stroke(width=2, color="#000000")]),
        TextPart(" Normal"),  # inherits color="#FFFFFF"
    ],
    color="#FFFFFF",  # default for parts without explicit color
    size=72,
    effects=[Stroke(width=1, color="#000000")],  # effects apply to all parts
)
```

### Font Weights

QuickThumb supports CSS-style font weights for precise typography control:

```python
# Numeric weights (100-900)
canvas.text("Thin Text", font="Roboto", size=48, weight=100)
canvas.text("Light Text", font="Roboto", size=48, weight=300)
canvas.text("Regular Text", font="Roboto", size=48, weight=400)
canvas.text("Bold Text", font="Roboto", size=48, weight=700)
canvas.text("Black Text", font="Roboto", size=48, weight=900)

# Named weights (case-insensitive, supports hyphens/underscores/spaces)
canvas.text("Thin", weight="thin")           # 100
canvas.text("Extra Light", weight="extra-light")  # 200
canvas.text("Light", weight="light")         # 300
canvas.text("Normal", weight="normal")       # 400
canvas.text("Medium", weight="medium")       # 500
canvas.text("Semi Bold", weight="semi-bold") # 600
canvas.text("Bold", weight="bold")           # 700
canvas.text("Extra Bold", weight="extra-bold")    # 800
canvas.text("Black", weight="black")         # 900

# Rich text with different weights per part
canvas.text(
    content=[
        TextPart("Light ", weight=300),
        TextPart("Heavy", weight=900),
    ],
    font="NotoSerif",
    size=48,
)
```

**Weight Fallback**: If the exact weight isn't available, QuickThumb automatically finds the closest available weight variant.

**Important**: The `weight` and `bold` parameters are mutually exclusive. Using both will raise a `ValidationError`:

```python
# ❌ This raises ValidationError
canvas.text("Error", weight=700, bold=True)

# ✅ Use weight instead of bold
canvas.text("Bold Text", weight=700)  # or weight="bold"

# ✅ Or use the traditional bold parameter
canvas.text("Bold Text", bold=True)
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

- Image overlays (positioned images)
- Text backgrounds (labels/badges)
- Outline decoration
- JPEG/WebP output
- JSON operations (`from_json()`, `to_json()`)
- Comprehensive error messages

### Phase 5: Text Effects

- Effect classes (currently: `Stroke`)
- Effects list (`effects` parameter)
- Rich text with `TextPart` (partial text styling with effects support)
- Future: Additional effects like `Shadow`, `Glow`, etc.
