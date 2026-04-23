---
description: Build a square Instagram news card with QuickThumb using a full-bleed image, gradient overlay, badge, headline, and metadata.
---

# Instagram Card

A 1080×1080 square breaking news card. The layout uses a full-bleed background photo, a vertical gradient overlay for text legibility, a pill badge, a large headline, a body copy line, and a source/timestamp row.

## Layer stack

1. Background photo (cover fit, slightly darkened)
2. Dark gradient overlay fading from transparent (top) to near-black (bottom)
3. "BREAKING NEWS" badge with red fill
4. Large bold headline
5. Sub-headline / context line
6. Source and timestamp row in rich text

## Code

```python
from quickthumb import (
    Background, Canvas, Filter, FitMode, LinearGradient, Shadow, Stroke, TextPart,
)

(
    Canvas(1080, 1080)
    # Full-bleed background photo
    .background(
        image="fire.jpg",
        fit=FitMode.COVER,
        effects=[Filter(brightness=0.75)],
    )
    # Dark gradient overlay — transparent at top, near-black at bottom
    .background(
        gradient=LinearGradient(
            angle=90,
            stops=[("#00000000", 0.0), ("#000000CC", 0.45), ("#000000F0", 1.0)],
        ),
    )
    # "BREAKING NEWS" badge — centered near the top
    .text(
        content="BREAKING NEWS",
        size=38,
        color="#FFFFFF",
        weight=900,
        letter_spacing=4,
        position=("50%", "8%"),
        align=("center", "top"),
        effects=[
            Background(color="#CC0000", padding=(14, 28), border_radius=4),
        ],
    )
    # Main headline
    .text(
        content="Wildfires Spread\nAcross Thousands\nof Acres",
        size=96,
        color="#FFFFFF",
        weight=900,
        position=("8%", "48%"),
        align=("left", "middle"),
        line_height=1.15,
        effects=[
            Stroke(width=2, color="#000000"),
            Shadow(offset_x=4, offset_y=4, color="#000000", blur_radius=6),
        ],
    )
    # Context / sub-headline (wrapped)
    .text(
        content="Emergency evacuations ordered in three regions as firefighters battle the blaze",
        size=36,
        color="#E0E0E0",
        weight=400,
        position=("8%", "79%"),
        align=("left", "top"),
        max_width="84%",
        effects=[Shadow(offset_x=2, offset_y=2, color="#000000", blur_radius=4)],
    )
    # Source and timestamp row — two styles in one text layer
    .text(
        content=[
            TextPart(text="WORLD NEWS  ", color="#FF4444", weight=700),
            TextPart(text="·  Feb 20, 2026", color="#AAAAAA", weight=400),
        ],
        size=30,
        position=("8%", "92%"),
        align=("left", "top"),
    )
    .render("instagram_news_card.png")
)
```

## Key techniques

### Gradient from transparent to opaque

The overlay uses `angle=90` (top → bottom) with stops that start fully transparent and end near-black. This keeps the photo visible at the top while guaranteeing readable text below.

```python
LinearGradient(
    angle=90,
    stops=[("#00000000", 0.0), ("#000000CC", 0.45), ("#000000F0", 1.0)],
)
```

### Badge using the `Background` effect

The "BREAKING NEWS" badge is a text layer with a `Background` effect — no separate shape layer needed. `padding=(14, 28)` means 14px vertical, 28px horizontal.

```python
effects=[Background(color="#CC0000", padding=(14, 28), border_radius=4)]
```

### Rich text for inline styling

The source row mixes two styles in one `.text()` call using `TextPart`. One layer, one position, two colors and weights.

```python
content=[
    TextPart(text="WORLD NEWS  ", color="#FF4444", weight=700),
    TextPart(text="·  Feb 20, 2026", color="#AAAAAA", weight=400),
]
```

## Customization

| What to change | Parameter |
| --- | --- |
| Background photo | `image="fire.jpg"` |
| Badge color | `Background(color="#CC0000", ...)` |
| Headline text | `content="Wildfires Spread\n..."` |
| Sub-headline | Second `.text()` content |
| Brand name color | First `TextPart` |
| Date string | Second `TextPart` |
