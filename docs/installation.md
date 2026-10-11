---
description: Install quickthumb, add the optional extras for SVG, PDF, PPTX, video, background removal and the CLI, and check your environment.
---

# Installation

quickthumb needs Python 3.10 or later.

```bash
pip install quickthumb
```

or, with uv:

```bash
uv add quickthumb
```

That is enough to render PNG, JPEG, WebP, GIF, SVG, and HTML.

## Optional extras

Some features need extra packages. Install them by name, for example
`pip install "quickthumb[svg,pdf]"`.

| Extra | Adds | Needed for |
| --- | --- | --- |
| `svg` | cairosvg | `canvas.svg(...)` layers. Without it, rendering an SVG layer raises `RenderingError`. Exporting *to* SVG doesn't need it. |
| `pdf` | reportlab, fonttools | `.to_pdf()` and `render("out.pdf")` |
| `pptx` | python-pptx | `.to_pptx()` and `render("out.pptx")` |
| `rembg` | rembg, onnxruntime | `remove_background=True` on image layers. Requires Python 3.11+; downloads a model of about 170 MB on first use. |
| `cli` | typer, watchfiles, jinja2 | The `quickthumb` command: `render`, `lint`, `watch`, `serve`, `doctor`, and more |

MP4 and WebM export also need [ffmpeg](https://ffmpeg.org/), which is a system
program rather than a Python package:

```bash
brew install ffmpeg      # macOS
sudo apt install ffmpeg  # Debian / Ubuntu
```

## Check your environment

`quickthumb doctor` (from the `cli` extra) checks that everything a given export
needs is installed and working:

```bash
quickthumb doctor            # PNG, the default
quickthumb doctor mp4        # is ffmpeg on PATH and usable?
quickthumb doctor pdf --spec card.json -o out/card.pdf
```

It exits with status 1 if a required check fails, so it also works as a CI
step. See [Diagnostics & CLI](diagnostics.md#quickthumb-doctor) for details.

## Environment variables

All optional.

| Variable | What it does |
| --- | --- |
| `QUICKTHUMB_FONT_DIR` | Folder of font files to search when `font` is a family name |
| `QUICKTHUMB_DEFAULT_FONT` | Font to use when a text layer has no `font` |
| `QUICKTHUMB_FONT_CACHE_DIR` | Where downloaded fonts are cached (default: the system temp folder) |
| `QUICKTHUMB_ASSET_CACHE_DIR` | Where downloaded images are cached (default: the system temp folder) |
| `QUICKTHUMB_ASSET_MAX_AGE` | Seconds before a cached download is refreshed. Unset means never. |
| `QUICKTHUMB_ASSET_OFFLINE` | Set to `1` to never download; only cached files are used |
| `QUICKTHUMB_FFMPEG`, `QUICKTHUMB_FFPROBE` | Paths to `ffmpeg` and `ffprobe` if they aren't on `PATH` |

[Remote assets and caching](exports.md#remote-assets-and-caching) explains the
cache in more detail.
