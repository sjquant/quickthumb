---
description: Install quickthumb, add the optional extras for SVG, PDF, PPTX, video, background removal and the CLI, and check your environment.
---

# Installation

quickthumb needs Python 3.11 or later.

## Isolated environment

Install quickthumb 0.8.0 in a virtual environment outside any quickthumb checkout:

```bash
mkdir -p quickthumb-first-export
cd quickthumb-first-export
python3 -m venv .venv
source .venv/bin/activate
python -m pip install "quickthumb==0.8.0"
```

On Windows, activate with `.venv\Scripts\activate` instead.
The shell commands above use Bash/Zsh. Installing dependencies
needs the package index or a populated local cache. Running outside the checkout
ensures Python imports the installed wheel rather than the source directory.

### Existing uv project

```bash
uv add "quickthumb[cli]>=0.8.0"
```

### Development checkout

To try unreleased changes, run `uv build` in the repository, then install the
resulting wheel into the isolated environment using its absolute path, for
example `python -m pip install "/path/to/dist/quickthumb-0.8.0-py3-none-any.whl[cli]"`.
This installs the checkout's code rather than downloading the published release.
See the [0.8.0 migration notes](releases/0.8.0.md#migration-from-v070) when upgrading
from 0.7.0.

The base package is enough for PNG, JPEG, WebP, GIF, SVG output, and HTML.
Try [rendering your first episode cards](getting-started.md) before adding
optional renderers. The example needs no font or image downloads after installation.

## Optional extras

Some features need extra packages. Install them by name, for example
`pip install "quickthumb[svg,pdf]"`.

| Extra | Adds | Needed for |
| --- | --- | --- |
| `svg` | cairosvg | `canvas.svg(...)` layers. Without it, rendering an SVG layer raises `RenderingError`. Exporting *to* SVG doesn't need it. |
| `pdf` | reportlab, fonttools, pypdfium2 | PDF export and opt-in PDF fidelity observation |
| `pptx` | python-pptx | `.to_pptx()` and `render("out.pptx")` |
| `lottie` | fonttools | Self-contained supported text outlines in Canvas `.lot` exports; shape-only Lottie does not need this extra |
| `rembg` | rembg, onnxruntime | `remove_background=True` on image layers. Requires Python 3.11+; downloads a model of about 170 MB on first use. |
| `cli` | typer, watchfiles, jinja2 | The `quickthumb` command: `render`, `lint`, `watch`, `serve`, `doctor`, and more |

MP4, WebM, and MOV export also need [ffmpeg](https://ffmpeg.org/), which is a system
program rather than a Python package:

```bash
brew install ffmpeg      # macOS
sudo apt install ffmpeg  # Debian / Ubuntu
```

MOV requires an FFmpeg build with the `prores_ks` encoder.

Rendering SVG layers uses CairoSVG and its native Cairo library; installing the
Python extra does not install system libraries. The optional SVG fidelity
observer also uses CairoSVG. See [CairoSVG installation](https://cairosvg.org/documentation/)
for platform requirements. The `pdf` extra includes PDFium bindings for PDF
observation; plain PNG output needs neither renderer.

## Check your environment

`quickthumb doctor` (from the `cli` extra) discovers requirements for an export:

```bash
quickthumb doctor            # PNG, the default
quickthumb doctor mp4        # discover ffmpeg/ffprobe
quickthumb doctor pdf --spec card.json -o out/card.pdf
```

It exits with status 1 if a required check fails, so it also works as a CI
step. It does not render a test file or certify native libraries, codec support,
or visual fidelity. Run the intended export as well. See
[Diagnostics & CLI](diagnostics.md#quickthumb-doctor) for details.

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
