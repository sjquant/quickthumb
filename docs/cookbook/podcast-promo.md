---
description: Build a podcast promo card with quickthumb using remote images, webfonts, background removal, rich text, and layered composition.
---

# Podcast Promo

A 1280×720 podcast episode promo card. This recipe demonstrates three advanced features together: **remote image URLs**, a **webfont loaded from a URL**, and **background removal** on a portrait.

!!! note "Requirements"
    This recipe requires network access and the `rembg` extra:
    ```bash
    pip install "quickthumb[rembg]"
    ```

## Layer stack

1. Remote background photo (darkened, desaturated, blurred)
2. Top-to-bottom gradient overlay for text legibility
3. "NEW EPISODE" badge (shape + text)
4. Show title in a webfont
5. Episode headline
6. Teaser copy (wrapped)
7. Guest info card (shape + three text layers)
8. Guest portrait — cutout with background removed

## Code

```python
from quickthumb import (
    Canvas, Filter, FitMode, LinearGradient, Shadow, Stroke,
)

BACKGROUND_URL = (
    "https://images.unsplash.com/photo-1478737270239-2f02b77fc618"
    "?auto=format&fit=crop&w=1600&q=80"
)
GUEST_URL = (
    "https://images.unsplash.com/photo-1494790108377-be9c29b29330"
    "?auto=format&fit=crop&w=900&q=80"
)
# Pacifico — a decorative webfont loaded directly from Google's CDN
SHOW_FONT_URL = (
    "https://fonts.gstatic.com/s/pacifico/v22/FwZY7-Qmy14u9lezJ-6H6MmBp0u-.woff2"
)

(
    Canvas(1280, 720)
    # Remote background — heavily processed for contrast
    .background(
        image=BACKGROUND_URL,
        fit=FitMode.COVER,
        effects=[Filter(brightness=0.42, saturation=0.75, blur=2)],
    )
    # Top-to-bottom gradient (dark top, fading out mid-way)
    .background(
        gradient=LinearGradient(
            angle=0,
            stops=[("#07111F", 0.0), ("#07111FE8", 0.45), ("#07111F70", 1.0)],
        )
    )
    # "NEW EPISODE" badge
    .shape(
        shape="rectangle",
        position=(56, 48),
        width=220,
        height=54,
        color="#F04D23",
        border_radius=18,
        effects=[Shadow(offset_x=0, offset_y=8, color="#00000066", blur_radius=14)],
    )
    .text(
        content="NEW EPISODE",
        size=24,
        color="#FFF7F2",
        weight=900,
        letter_spacing=2,
        position=(166, 75),
        align=("center", "middle"),
    )
    # Show title in webfont — font is downloaded and cached on first run
    .text(
        content="Signal to Noise",
        font=SHOW_FONT_URL,
        size=62,
        color="#8CE1FF",
        position=(60, 130),
        effects=[Shadow(offset_x=0, offset_y=6, color="#021018CC", blur_radius=12)],
    )
    # Episode headline
    .text(
        content="HOW GREAT TEAMS\nBUILD BETTER\nFEEDBACK LOOPS",
        size=70,
        color="#FFFFFF",
        weight=900,
        line_height=1.0,
        position=(60, 220),
        effects=[
            Stroke(width=3, color="#04111A"),
            Shadow(offset_x=0, offset_y=10, color="#00000099", blur_radius=18),
        ],
    )
    # Teaser copy
    .text(
        content="A practical interview on shipping faster without breaking trust.",
        size=34,
        color="#C7D5E0",
        position=(64, 415),
        max_width=600,
        line_height=1.2,
        effects=[Shadow(offset_x=0, offset_y=4, color="#00000080", blur_radius=8)],
    )
    # Guest info card background
    .shape(
        shape="rectangle",
        position=(62, 530),
        width=430,
        height=120,
        color="#0E2436",
        border_radius=28,
        opacity=0.92,
        effects=[
            Stroke(width=2, color="#8CE1FF66"),
            Shadow(offset_x=0, offset_y=12, color="#00000066", blur_radius=16),
        ],
    )
    # Guest label
    .text(
        content="Guest",
        size=22,
        color="#8CE1FF",
        weight=700,
        letter_spacing=2,
        position=(90, 556),
    )
    # Guest name
    .text(
        content="Mina Park",
        size=42,
        color="#FFFFFF",
        weight=900,
        position=(88, 582),
    )
    # Guest title
    .text(
        content="AI Product Lead",
        size=24,
        color="#C7D5E0",
        weight=500,
        position=(90, 622),
    )
    # Guest portrait — bottom-right, background removed
    .image(
        path=GUEST_URL,
        position=(1095, 698),
        width=500,
        height=660,
        fit=FitMode.COVER,
        align=("center", "bottom"),
        remove_background=True,
        effects=[Shadow(offset_x=16, offset_y=18, color="#000000AA", blur_radius=22)],
    )
    .outline(width=10, color="#8CE1FF")
    .render("podcast_promo.png")
)
```

## Key techniques

### Remote images

Both the background and the guest portrait are fetched from remote URLs. quickthumb downloads them at render time and caches them locally. Pass any `http://` or `https://` URL to `image=` or `path=`.

### Webfont from URL

```python
.text(
    content="Signal to Noise",
    font=SHOW_FONT_URL,   # .woff2 URL downloaded and cached on first use
    size=62,
    color="#8CE1FF",
    ...
)
```

!!! note "Webfont limitations"
    When `font` is a URL, `bold`, `italic`, and `weight` are ignored — the URL already points to a specific variant. For bold or italic versions, use a separate URL.

### Background removal

```python
.image(
    path=GUEST_URL,
    remove_background=True,   # requires quickthumb[rembg]
    ...
)
```

The ONNX model is downloaded (~170 MB) on the first call and cached. Subsequent calls are fast.

### Portrait shadow casting inward

The portrait shadow uses a negative `offset_x` to cast the shadow leftward — toward the text — which separates the subject from the content visually.

```python
effects=[Shadow(offset_x=16, offset_y=18, color="#000000AA", blur_radius=22)]
```

## Customization

| What to change | Where |
| --- | --- |
| Background photo | `BACKGROUND_URL` |
| Guest photo | `GUEST_URL` |
| Show name font | `SHOW_FONT_URL` |
| Show title | `content="Signal to Noise"` |
| Episode headline | Multi-line `.text()` content |
| Guest name and title | Two `.text()` calls in the guest card |
| Accent color | Replace `#8CE1FF` throughout |
