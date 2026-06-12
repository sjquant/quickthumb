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

SVG and HTML export need no extra dependencies. See [Exporting to SVG, HTML & PPTX](exports.md) for details.

## Optional: CLI

To use the `quickthumb` command (`render`, `lint`, `watch`), install the `cli` extra:

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

quickthumb reads two optional environment variables at startup:

| Variable | Purpose |
| --- | --- |
| `QUICKTHUMB_FONT_DIR` | Directory that contains custom font files |
| `QUICKTHUMB_DEFAULT_FONT` | Font family/name to use when `font` is omitted |

```python
import os

os.environ["QUICKTHUMB_FONT_DIR"] = "assets/fonts"
os.environ["QUICKTHUMB_DEFAULT_FONT"] = "Roboto"
```
