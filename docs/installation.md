---
description: Install quickthumb with pip or uv, enable optional background removal support, and configure font-related environment variables.
---

# Installation

## Requirements

- Python **3.10** or later
- [Pillow](https://pillow.readthedocs.io/) and [Pydantic](https://docs.pydantic.dev/) are installed automatically

## Install with pip

```bash
pip install quickthumb
```

## Install with uv (recommended)

```bash
uv pip install quickthumb
```

## Optional: Background Removal

To use `remove_background=True` on image layers, install the `rembg` extra:

```bash
# pip
pip install "quickthumb[rembg]"

# uv
uv pip install "quickthumb[rembg]"
```

!!! note
    The `rembg` extra pulls in `onnxruntime` and will download a model (~170 MB) on first use. It is not required for any other quickthumb feature.

## Optional: SVG Layers

To use `canvas.svg(...)` layers, install the `svg` extra ([cairosvg](https://cairosvg.org/)):

```bash
# pip
pip install "quickthumb[svg]"

# uv
uv pip install "quickthumb[svg]"
```

Rendering a canvas that contains an SVG layer without this extra raises `RenderingError`.

## Optional: PPTX Export

To export canvases to PowerPoint with `canvas.to_pptx()` or `canvas.render("deck.pptx")`, install the `pptx` extra ([python-pptx](https://python-pptx.readthedocs.io/)):

```bash
# pip
pip install "quickthumb[pptx]"

# uv
uv pip install "quickthumb[pptx]"
```

SVG export needs no extra dependencies. See [Exporting to SVG, PPTX, PDF & video](exports.md) for details.

## Optional: PDF Export

To export canvases to PDF with `canvas.to_pdf()` or `canvas.render("card.pdf")`, install the `pdf` extra ([reportlab](https://www.reportlab.com/)):

```bash
# pip
pip install "quickthumb[pdf]"

# uv
uv pip install "quickthumb[pdf]"
```

## Optional: MP4/WebM Export

Animated GIF export (`canvas.to_gif()` / `deck.render("deck.gif")`) needs no extra dependencies. MP4 and WebM export additionally require the [ffmpeg](https://ffmpeg.org/) binary on `PATH` (or pointed to by the `QUICKTHUMB_FFMPEG` environment variable) — it is a system program, not a Python package:

```bash
# macOS
brew install ffmpeg

# Debian/Ubuntu
apt install ffmpeg
```

## Optional: CLI

To use the `quickthumb` command (`render`, `lint`, `watch`, `serve`), install the `cli` extra:

```bash
pip install "quickthumb[cli]"
```

See [Diagnostics & CLI](diagnostics.md) for the command reference.

## Verify the installation

```python
from importlib.metadata import version

print(version("quickthumb"))
```

## Environment Variables

quickthumb reads a few optional environment variables:

| Variable | Purpose |
| --- | --- |
| `QUICKTHUMB_FONT_DIR` | Directory that contains custom font files |
| `QUICKTHUMB_DEFAULT_FONT` | Font family/name to use when `font` is omitted |
| `QUICKTHUMB_FFMPEG` | Path to the ffmpeg binary for MP4/WebM export (when not on `PATH`) |

```python
import os

os.environ["QUICKTHUMB_FONT_DIR"] = "assets/fonts"
os.environ["QUICKTHUMB_DEFAULT_FONT"] = "Roboto"
```
