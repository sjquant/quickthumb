---
description: Use QuickThumb webfonts and background removal to load remote typefaces, isolate subjects, and compose polished thumbnail images.
---

# Webfonts & Background Removal

Two features that require a bit of setup but unlock a lot of creative flexibility: loading fonts directly from URLs and removing image backgrounds with AI.

---

## Webfonts

QuickThumb can load fonts from remote URLs at render time. The font file is downloaded once and cached locally.

### Basic usage

Pass any `.ttf`, `.otf`, or `.woff2` URL as the `font` parameter:

```python
from quickthumb import Canvas

INTER_BOLD_URL = (
    "https://fonts.gstatic.com/s/inter/v13/"
    "UcCO3FwrK3iLTeHuS_fvQtMwCp50KnMw2boKoduKmMEVuLyfAZ9hiA.woff2"
)

canvas = Canvas(1280, 720).text(
    content="Hello from Inter",
    font=INTER_BOLD_URL,
    size=72,
    color="#FFFFFF",
    align="center",
)
```

### Finding Google Font URLs

1. Open [fonts.google.com](https://fonts.google.com) and pick a font.
2. Click **Get font** → **Get embed code** → **@import**.
3. The `@import` URL points to a CSS file. Open it in your browser.
4. Inside the CSS, find the `src: url(...)` lines — copy the `.woff2` URL for the weight and style you need.

Common weights (check the CSS file for the exact URLs for your font):

| Weight | Name |
| --- | --- |
| 400 | Regular |
| 500 | Medium |
| 700 | Bold |
| 900 | Black |

### Using bold and italic variants

When `font` is a URL, `bold`, `italic`, and `weight` are **ignored** — the URL already points to a specific variant. Download separate URLs for each style you need:

```python
from quickthumb import Canvas, TextPart

REGULAR_URL = "https://fonts.gstatic.com/.../inter-regular.woff2"
BOLD_URL    = "https://fonts.gstatic.com/.../inter-bold.woff2"

canvas = Canvas(1280, 720).text(
    content=[
        TextPart(text="Regular text  ", font=REGULAR_URL, color="#AAAAAA"),
        TextPart(text="BOLD TEXT",      font=BOLD_URL,    color="#FFFFFF"),
    ],
    size=64,
    position=("50%", "50%"),
    align=("center", "middle"),
)
```

### Local font directory

For fonts you already have on disk, set the environment variable instead of URLs:

```python
import os
os.environ["QUICKTHUMB_FONT_DIR"] = "assets/fonts"
os.environ["QUICKTHUMB_DEFAULT_FONT"] = "Roboto"

# Now use the family name directly
canvas.text(content="Hello", font="Roboto", size=64, color="#FFFFFF", align="center")
```

QuickThumb searches `QUICKTHUMB_FONT_DIR` for files matching the family name, and falls back to `QUICKTHUMB_DEFAULT_FONT` when `font` is omitted.

---

## Background removal

`remove_background=True` on an `.image()` layer uses AI (via `rembg` + ONNX) to cut out the subject and remove the background, leaving a clean cutout composited on top of your canvas.

### Installation

```bash
pip install "quickthumb[rembg]"
```

The ONNX model (~170 MB) is downloaded on first use and cached. Subsequent renders are fast.

### Basic usage

```python
from quickthumb import Canvas, Shadow

canvas = Canvas(1280, 720).image(
    path="portrait.jpg",
    position=("75%", "55%"),
    width=430,
    height=540,
    align=("center", "middle"),
    remove_background=True,
    effects=[Shadow(offset_x=0, offset_y=14, color="#000000", blur_radius=24)],
)
```

The shadow is applied after the background is removed, so it follows the subject silhouette rather than the original rectangle.

### Works with remote images too

```python
GUEST_URL = "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=900"

canvas.image(
    path=GUEST_URL,
    position=(1280, 720),
    width=500,
    height=660,
    fit="cover",
    align=("right", "bottom"),
    remove_background=True,
)
```

### Combining both features

A podcast promo with a webfont show title and an AI-cutout guest portrait:

```python
from quickthumb import Canvas, Filter, FitMode, LinearGradient, Shadow, Stroke

SHOW_FONT = "https://fonts.gstatic.com/s/pacifico/v22/FwZY7-Qmy14u9lezJ-6H6MmBp0u-.woff2"
GUEST_URL = "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=900"
BG_URL    = "https://images.unsplash.com/photo-1478737270239-2f02b77fc618?w=1600"

canvas = (
    Canvas(1280, 720)
    .background(
        image=BG_URL,
        fit=FitMode.COVER,
        effects=[Filter(brightness=0.42, saturation=0.75, blur=2)],
    )
    .background(
        gradient=LinearGradient(
            angle=0,
            stops=[("#07111F", 0.0), ("#07111FE8", 0.45), ("#07111F70", 1.0)],
        )
    )
    # Webfont show title
    .text(
        content="Signal to Noise",
        font=SHOW_FONT,
        size=62,
        color="#8CE1FF",
        position=(60, 80),
        effects=[Shadow(offset_x=0, offset_y=6, color="#021018CC", blur_radius=12)],
    )
    # Episode headline
    .text(
        content="HOW GREAT TEAMS\nBUILD BETTER\nFEEDBACK LOOPS",
        size=70,
        color="#FFFFFF",
        weight=900,
        line_height=1.0,
        position=(60, 170),
        effects=[
            Stroke(width=3, color="#04111A"),
            Shadow(offset_x=0, offset_y=10, color="#00000099", blur_radius=18),
        ],
    )
    # AI-cutout guest portrait — bottom right, shadow follows silhouette
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
    .render("podcast_webfont_rembg.png")
)
```

### Tips

- **Portrait orientation works best.** `rembg` is trained on people — headshots and three-quarter shots give the cleanest cutouts.
- **High contrast helps.** Images where the subject is clearly separated from the background produce better results.
- **Apply `Filter` before `remove_background`.** Adjusting brightness or contrast on the image first can improve segmentation quality.
- **Cache is automatic.** Once the model is downloaded, there's nothing to configure.
