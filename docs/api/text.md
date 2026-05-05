---
description: Reference for quickthumb text layers, including rich text parts, fonts, alignment, wrapping, strokes, shadows, and sizing.
---

# Text

`.text()` adds a text layer. Content can be a plain string or a list of `TextPart` objects for per-segment styling.

## Signature

```python
canvas.text(
    content,
    font=None,
    size=None,
    color=None,
    fill=None,
    position=None,
    align=None,
    bold=False,
    italic=False,
    weight=None,
    max_width=None,
    effects=None,
    line_height=None,
    letter_spacing=None,
    auto_scale=False,
    rotation=0.0,
    opacity=1.0,
)
```

## Parameters

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `content` | `str \| list[TextPart]` | **required** | Text content. Plain string or a list of `TextPart` for rich text. |
| `font` | `str \| None` | `None` | Font family name, local file path, or remote webfont URL. |
| `size` | `int \| None` | `None` | Font size in pixels. Must be a positive integer. |
| `color` | `str \| None` | `None` | Default text color. Hex string (`"#RRGGBB"` or `"#RRGGBBAA"`). |
| `fill` | `LinearGradient \| RadialGradient \| TextFillImage \| None` | `None` | Gradient or image fill applied to the text glyphs. Takes visual precedence over `color` when set. See [Gradient and image fills](#gradient-and-image-fills). |
| `position` | `tuple \| None` | `None` | `(x, y)` position. Values can be integers (px) or percentage strings (`"50%"`). |
| `align` | `str \| Align \| tuple \| None` | `None` | Alignment of the text block. See [Align values](#align-values). |
| `bold` | `bool` | `False` | Bold flag. Mutually exclusive with `weight`. |
| `italic` | `bool` | `False` | Italic flag. |
| `weight` | `int \| str \| None` | `None` | CSS-style font weight (e.g. `700`, `900`, `"bold"`). Mutually exclusive with `bold`. |
| `max_width` | `int \| str \| None` | `None` | Wrap width in pixels or percentage string (e.g. `"60%"`). Required for `auto_scale`. |
| `effects` | `list \| None` | `[]` | List of effects: `Stroke`, `Shadow`, `Glow`, `Background`. |
| `line_height` | `float \| None` | `None` | Line height multiplier. Positive float. |
| `letter_spacing` | `int \| None` | `None` | Horizontal tracking adjustment in pixels. |
| `auto_scale` | `bool` | `False` | Shrink the font until the text fits within `max_width`. Requires `max_width`. |
| `rotation` | `float` | `0.0` | Rotation in degrees. |
| `opacity` | `float` | `1.0` | Layer opacity from `0.0` to `1.0`. |

## Align values

`align` accepts any of these forms:

```python
align="center"              # shorthand
align="top-left"            # compound string
align=("left", "middle")    # (horizontal, vertical) tuple
align=Align.BOTTOM_RIGHT    # enum
```

| String | Enum | Position |
| --- | --- | --- |
| `"center"` | `Align.CENTER` | Horizontally and vertically centered |
| `"left"` | `Align.LEFT` | Left-aligned, vertically centered |
| `"right"` | `Align.RIGHT` | Right-aligned, vertically centered |
| `"top-left"` | `Align.TOP_LEFT` | Top-left corner |
| `"top-center"` | `Align.TOP_CENTER` | Top edge, horizontally centered |
| `"top-right"` | `Align.TOP_RIGHT` | Top-right corner |
| `"bottom-left"` | `Align.BOTTOM_LEFT` | Bottom-left corner |
| `"bottom-center"` | `Align.BOTTOM_CENTER` | Bottom edge, horizontally centered |
| `"bottom-right"` | `Align.BOTTOM_RIGHT` | Bottom-right corner |

When using a tuple: horizontal values are `left`, `center`, `right`; vertical values are `top`, `middle`, `bottom`.

## Examples

### Plain text

```python
canvas.text(
    content="Hello World",
    size=64,
    color="#FFFFFF",
    align="center",
)
```

### Rich text with `TextPart`

```python
from quickthumb import Stroke, TextPart

canvas.text(
    content=[
        TextPart(text="5 ", color="#FBBF24", weight=900),
        TextPart(text="WARNING SIGNS", color="#FFFFFF", weight=900),
    ],
    size=72,
    position=("8%", "55%"),
    align=("left", "middle"),
)
```

### With effects

```python
from quickthumb import Background, Glow, Shadow, Stroke

canvas.text(
    content="BREAKING",
    size=96,
    color="#FFFFFF",
    position=("8%", "50%"),
    align=("left", "middle"),
    weight=900,
    max_width="65%",
    effects=[
        Stroke(width=4, color="#000000"),
        Shadow(offset_x=4, offset_y=4, color="#000000", blur_radius=8),
        Glow(color="#B8FF00", radius=16, opacity=0.25),
        Background(color="#111827CC", padding=(16, 24), border_radius=14),
    ],
)
```

### Auto-scale to fit

```python
canvas.text(
    content="This is a very long title that should fit",
    size=80,
    color="#FFFFFF",
    max_width="70%",
    auto_scale=True,
    position=("8%", "50%"),
    align=("left", "middle"),
)
```

### Using a webfont

```python
canvas.text(
    content="Custom Font",
    font="https://fonts.gstatic.com/s/inter/v13/UcCO3FwrK3iLTeHuS_fvQtMwCp50KnMw2boKoduKmMEVuLyfAZ9hiA.woff2",
    size=72,
    color="#FFFFFF",
    align="center",
)
```

!!! note "Webfont URLs"
    When `font` is a URL, `bold`, `italic`, and `weight` are ignored — the URL already points to a specific variant. Download separate URLs for bold/italic versions.

### Gradient and image fills

Fill text glyphs with a gradient or image instead of a flat color. Pass a `LinearGradient`, `RadialGradient`, or `TextFillImage` to `fill`.

```python
from quickthumb import Canvas, LinearGradient, RadialGradient, TextFillImage, TextPart

# Linear gradient headline
canvas.text(
    content="GRADIENT",
    size=120,
    fill=LinearGradient(angle=90, stops=[("#FF6B6B", 0.0), ("#4ECDC4", 1.0)]),
    position=("50%", "50%"),
    align="center",
)

# Image-filled text
canvas.text(
    content="TEXTURE",
    size=140,
    fill=TextFillImage(path="fire_texture.jpg", fit="cover"),
    position=("50%", "50%"),
    align="center",
)

# Per-segment fills using TextPart
canvas.text(
    content=[
        TextPart(
            text="HOT ",
            fill=LinearGradient(angle=45, stops=[("#FF4500", 0.0), ("#FFD700", 1.0)]),
            weight=900,
        ),
        TextPart(
            text="COLD",
            fill=LinearGradient(angle=45, stops=[("#00BFFF", 0.0), ("#8A2BE2", 1.0)]),
            weight=900,
        ),
    ],
    size=110,
    position=("50%", "50%"),
    align="center",
)
```

`fill` on a `TextPart` overrides the layer-level `fill` for that segment only. `fill` and `color` are independent; when `fill` is set it takes visual precedence. See [TextFillImage](enums.md#textfillimage) for image fill options.

## TextPart

`TextPart` enables per-segment styling within a text layer.

```python
from quickthumb import Stroke, TextPart

TextPart(
    text="HOT",
    color="#FF3B30",
    fill=None,
    size=56,
    font="Impact",
    weight=900,
    italic=False,
    line_height=None,
    letter_spacing=0,
    effects=[Stroke(width=3, color="#000000")],
)
```

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `text` | `str` | **required** | The text segment. Cannot be empty. |
| `color` | `str \| None` | `None` | Hex color override for this segment. |
| `fill` | `LinearGradient \| RadialGradient \| TextFillImage \| None` | `None` | Gradient or image fill for this segment. Overrides the layer-level `fill` for this segment only. |
| `size` | `int \| None` | `None` | Font size override for this segment. |
| `font` | `str \| None` | `None` | Font override for this segment. |
| `bold` | `bool \| None` | `None` | Bold override. Mutually exclusive with `weight`. |
| `italic` | `bool \| None` | `None` | Italic override. |
| `weight` | `int \| str \| None` | `None` | Font weight override. Mutually exclusive with `bold`. |
| `line_height` | `float \| None` | `None` | Line height multiplier override. |
| `letter_spacing` | `int \| None` | `None` | Letter spacing override. |
| `effects` | `list[TextEffect]` | `[]` | Per-segment effects: `Stroke`, `Shadow`, `Glow`, `Background`. |

## Validation rules

- `content` is required and cannot be an empty list.
- `TextPart.text` cannot be an empty string.
- `weight` and `bold=True` are mutually exclusive on both `TextLayer` and `TextPart`.
- `auto_scale=True` requires `max_width` to also be set.
- `max_width` must be a positive integer or a positive percentage string like `"60%"`.
- Percentage strings in `position` must match the pattern `-?N%` (negative percentages are valid).
- `fill` and `color` are independent fields; `fill` takes visual precedence when both are set.
- `TextFillImage.path` supports local file paths and remote URLs; missing local files raise `FileNotFoundError` at render time.
