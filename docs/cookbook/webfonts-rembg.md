---
description: Load fonts from Google Fonts or a URL, and cut subjects out of photos with remove_background, in quickthumb.
---

# Webfonts & Background Removal

## Fonts

A text layer's `font` can be a family name or a URL. There are three ways to
get a font that isn't installed on your machine.

### A Google Font by name

Set `font_source="google"`. quickthumb downloads the family the first time,
caches it, and picks the file that matches `weight` and `italic`:

```python
from quickthumb import Canvas

canvas = Canvas(1280, 720).background(color="#0A1730").text(
    content="Hello from Inter",
    font="Inter",
    font_source="google",
    weight=800,
    size=96,
    color="#FFFFFF",
    position=("50%", "50%"),
    align="center",
)
canvas.render("inter.png")
```

This is the easiest option and the one the [home page](../index.md) example
uses.

### A font file by URL

Pass the URL of a `.ttf`, `.otf`, `.woff`, or `.woff2` file. It is downloaded
once and cached:

```python
SHOW_FONT_URL = "https://fonts.gstatic.com/s/dmserifdisplay/v17/-nFnOHM81r4j6k0gjAW3mujVU2B2K_c.ttf"

canvas.text(content="Signal to Noise", font=SHOW_FONT_URL, size=50, color="#F5F5F7")
```

A URL points at one specific file, so `weight`, `bold`, and `italic` are
ignored. For a bold and a regular style, use two URLs, for example one per
`TextPart`. The [podcast promo](podcast-promo.md) recipe loads its show title
this way.

### A local font folder

Point `QUICKTHUMB_FONT_DIR` at a folder of font files and refer to families by
name. `QUICKTHUMB_DEFAULT_FONT` sets the font used when a layer has no `font`:

```python
import os

os.environ["QUICKTHUMB_FONT_DIR"] = "assets/fonts"
os.environ["QUICKTHUMB_DEFAULT_FONT"] = "Roboto"

canvas.text(content="Hello", font="NotoSerif", weight=700, size=64, color="#FFFFFF")
```

All of the cookbook examples work this way, with the fonts bundled in the
repository's `assets/fonts` folder.

## Background removal

`remove_background=True` on an image layer cuts the subject out of the photo
and drops the rest:

```python
from quickthumb import Canvas, Shadow

canvas = (
    Canvas(1280, 720)
    .background(color="#1C1C1E")
    .image(
        path="portrait.jpg",
        position=(1280, 720),
        width=620,
        height=710,
        fit="cover",
        align=("right", "bottom"),
        remove_background=True,
        effects=[Shadow(offset_x=-12, offset_y=12, color="#00000099", blur_radius=26)],
    )
)
```

`path` can also be an `http(s)` URL.

It needs the `rembg` extra, which requires Python 3.11 or later:

```bash
pip install "quickthumb[rembg]"
```

The first call downloads the segmentation model (about 170 MB) and caches it.

Things worth knowing:

- **The cut-out happens first.** quickthumb removes the background, then
  resizes the result, then applies `effects`. A `Shadow` therefore follows the
  person's outline, not the original rectangle, and a `Filter` changes the
  colors of the cut-out but has no effect on how it was cut.
- **People work best.** The model is trained mostly on portraits. A subject
  that stands out clearly from its background gives the cleanest edge.
- **Pin the subject to an edge.** `position=(1280, 720)` with
  `align=("right", "bottom")` keeps the portrait in the corner whatever its
  size, as in the [talking-head](youtube-thumbnail.md#talking-head) and
  [reaction](youtube-thumbnail.md#reaction) thumbnails.
