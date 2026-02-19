# QuickThumb

A Python library for programmatic thumbnail generation with support for layers, gradients, and flexible styling.

## Features

- **Dual API**: Use Python method chaining or JSON configuration
- **Layer-based composition**: Stack backgrounds, text, and decorations
- **Flexible sizing**: Aspect ratios (16:9, 9:16, 4:3, 1:1, 1.91:1, 4:5) or explicit dimensions
- **Rich backgrounds**: Solid colors, linear/radial gradients, images with blend modes
- **Advanced text styling**: Custom fonts, CSS-style font weights, strokes, alignment, bold/italic
- **Smart font loading**: Automatic weight mapping with fallback support
- **Multiple output formats**: PNG, JPEG, WebP
- **Type-safe**: Full type hints with Pydantic validation

## Installation

```bash
# Using uv (recommended)
uv pip install quickthumb

# Using pip
pip install quickthumb
```

## Quick Start

### Python API

```python
from quickthumb import Canvas, LinearGradient, BlendMode, Stroke

# Create a 1920x1080 thumbnail
canvas = Canvas(1920, 1080)

# Add a gradient background
canvas.background(
    gradient=LinearGradient(45, [("#FF5733", 0.0), ("#3333FF", 1.0)]),
    opacity=0.8,
    blend_mode=BlendMode.MULTIPLY
)

# Add title text with stroke
canvas.text(
    "Python Tutorial",
    font="Roboto",
    size=72,
    color="#FFFFFF",
    align=("center", "middle"),
    effects=[Stroke(width=3, color="#000000")],
    bold=True
)

# Add an outline
canvas.outline(width=10, color="#FFFFFF")

# Render to file or export as base64/data URL
canvas.render("thumbnail.png")
# base64_str = canvas.to_base64(format="PNG")
# data_url = canvas.to_data_url(format="JPEG", quality=85)
```

### Using Aspect Ratios

```python
from quickthumb import Canvas

# Create 16:9 canvas with base width 1920
canvas = Canvas.from_aspect_ratio("16:9", base_width=1920)

# For YouTube thumbnails (16:9)
canvas = Canvas.from_aspect_ratio("16:9", base_width=1280)

# For Instagram posts (1:1)
canvas = Canvas.from_aspect_ratio("1:1", base_width=1080)
```

### JSON Configuration

```python
from quickthumb import Canvas

# Load from JSON string

config = """
{
    "size": {"width": 1920, "height": 1080},
    "layers": [
        {
            "type": "background",
            "color": "#2c3e50",
            "opacity": 1.0
        },
        {
            "type": "text",
            "content": "Hello World",
            "font": "Arial",
            "size": 72,
            "color": "#FFFFFF",
            "align": ["center", "middle"]
        },
        {
            "type": "outline",
            "width": 5,
            "color": "#ecf0f1",
        }
    ]
}
"""
canvas = Canvas.from_json(config)
canvas.render("output.png")
```

## Advanced Examples

### Multiple Background Layers with Blend Modes

```python
from quickthumb import Canvas, LinearGradient, RadialGradient, BlendMode

canvas = Canvas(1920, 1080)

# Base solid color
canvas.background(color="#2c3e50")

# Gradient overlay
canvas.background(
    gradient=LinearGradient(135, [("#e74c3c", 0.0), ("#3498db", 1.0)]),
    opacity=0.6,
    blend_mode=BlendMode.OVERLAY
)

# Image texture
canvas.background(
    image="texture.png",
    opacity=0.3,
    blend_mode=BlendMode.MULTIPLY,
    fit="cover"
)
```

### Text with Custom Positioning

```python
canvas = Canvas(1920, 1080)

# Absolute positioning (pixels)
canvas.text("Top Left", position=(50, 50), color="#FFFFFF")

# Percentage positioning
canvas.text("Centered", position=("50%", "50%"), color="#FFFFFF")

# Alignment-based positioning
canvas.text(
    "Bottom Right",
    align=("right", "bottom"),
    color="#FFFFFF"
)
```

### Radial Gradients

```python
from quickthumb import Canvas, RadialGradient

canvas = Canvas(1920, 1080)
canvas.background(
    gradient=RadialGradient(
        stops=[("#3498db", 0.0), ("#1a252f", 1.0)],
        center=(0.5, 0.5)  # Center position (0-1 range)
    )
)
```

## Color Formats

QuickThumb supports multiple color formats:

```python
# Hex strings
canvas.background(color="#FF5733")
canvas.background(color="#FF5733AA")  # With alpha

# RGB tuples
canvas.background(color=(255, 87, 51))

# RGBA tuples
canvas.background(color=(255, 87, 51, 200))
```

## Text Effects

Add visual effects to text using effect classes:

```python
from quickthumb import Canvas, Stroke

canvas = Canvas(1920, 1080)

# Text with stroke outline
canvas.text(
    "Bold Title",
    size=96,
    color="#FFFFFF",
    align=("center", "middle"),
    effects=[Stroke(width=3, color="#000000")]
)

# Multiple effects
canvas.text(
    "Epic Title",
    size=96,
    color="#FFFFFF",
    effects=[
        Stroke(width=5, color="#000000"),
        Stroke(width=2, color="#FF0000"),
    ]
)
```

**Available Effects:**
- `Stroke(width, color)` - Adds an outline around text

## Image Layers

Overlay images or logos onto your canvas:

```python
from quickthumb import Canvas

canvas = Canvas(1920, 1080)

# Add a logo
canvas.image(path="logo.png", position=(50, 50), width=200)
```

### Background Removal

Remove the background from an image before overlaying it using the `rembg` extra:

```bash
pip install quickthumb[rembg]
```

```python
canvas.image(
    path="portrait.png",
    width=400,
    align=("center", "middle"),
    remove_background=True,
)
```

## Font Weights

QuickThumb supports CSS-style font weights (100-900) or named weights like "thin", "bold", "black". See [DESIGN.md](DESIGN.md#font-weights) for full details.

```python
canvas.text("Light Text", font="Roboto", size=48, weight=300)
canvas.text("Bold Text", font="Roboto", size=48, weight=700)
canvas.text("Black Text", weight="black")  # Named weight
```

## Development

### Setup

```bash
# Clone the repository
git clone https://github.com/sjquant/quickthumb.git
cd quickthumb

# Install dependencies with uv
uv sync
```

### Running Tests

```bash
# Run all tests
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ --cov=quickthumb --cov-report=html

# Type checking with ty
uv run ty quickthumb/

# Linting
uv run ruff check quickthumb/
```

## API Reference

For complete API documentation including all methods, parameters, blend modes, and advanced features, see [DESIGN.md](DESIGN.md).

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
