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
    The `rembg` extra pulls in `onnxruntime` and will download a model (~170 MB) on first use. It is not required for any other QuickThumb feature.

## Verify the installation

```python
import quickthumb
print(quickthumb.__version__)
```

## Environment Variables

QuickThumb reads two optional environment variables at startup:

| Variable | Purpose |
| --- | --- |
| `QUICKTHUMB_FONT_DIR` | Directory that contains custom font files |
| `QUICKTHUMB_DEFAULT_FONT` | Font family/name to use when `font` is omitted |

```python
import os

os.environ["QUICKTHUMB_FONT_DIR"] = "assets/fonts"
os.environ["QUICKTHUMB_DEFAULT_FONT"] = "Roboto"
```
