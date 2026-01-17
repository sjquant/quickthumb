# QuickThumb

A Python library for programmatic thumbnail generation with support for layers, gradients, and flexible styling.

## Features

- **Dual API**: Use Python method chaining or JSON configuration
- **Layer-based composition**: Stack backgrounds, text, and decorations
- **Flexible sizing**: Aspect ratios (16:9, 9:16, 4:3, 1:1, 1.91:1, 4:5) or explicit dimensions
- **Rich backgrounds**: Solid colors, linear/radial gradients, images with blend modes
- **Advanced text styling**: Custom fonts, strokes, alignment, bold/italic
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
from quickthumb import Canvas, LinearGradient, BlendMode

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
    stroke=(3, "#000000"),
    bold=True
)

# Add a border
canvas.border(width=10, color="#FFFFFF", radius=20)

# Render to file
canvas.render("thumbnail.png")
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
            "type": "border",
            "width": 5,
            "color": "#ecf0f1",
            "radius": 10
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

## API Design

For detailed API design, see [DESIGN.md](DESIGN.md).

### Canvas Methods

- `Canvas(width, height)` - Create canvas with explicit dimensions
- `Canvas.from_aspect_ratio(ratio, base_width)` - Create from aspect ratio
- `Canvas.from_json(source)` - Load from JSON file or dict
- `.background(color=..., gradient=..., image=..., opacity=..., blend_mode=...)` - Add background layer
- `.text(content, font=..., size=..., color=..., align=..., stroke=..., bold=..., italic=...)` - Add text layer
- `.border(width, color, radius=...)` - Add border decoration
- `.outline(width, color, offset=...)` - Add outline decoration
- `.render(output_path, format=..., quality=...)` - Render to file

### Blend Modes

- `BlendMode.NORMAL` - Default blending
- `BlendMode.MULTIPLY` - Multiply colors
- `BlendMode.OVERLAY` - Overlay effect
- `BlendMode.SCREEN` - Screen effect
- `BlendMode.DARKEN` - Darken
- `BlendMode.LIGHTEN` - Lighten

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
