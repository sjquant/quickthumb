---
description: Choose an output format and export your first image, presentation, or animation with quickthumb.
---

# Choose an output format

Use the same Canvas or Deck to create images, presentations, and animation.
Choose a format for where you want to use the result:

| I want to… | Choose | What you need |
| --- | --- | --- |
| Publish an image | PNG, JPEG, or WebP | The base package |
| Share a presentation in a browser | HTML | The base package |
| Edit slides in PowerPoint or Keynote | [PPTX](reference/export-documents.md#pptx) | The `pptx` extra |
| Share a document | PDF | The `pdf` extra |
| Share a short animation | GIF | The base package |
| Publish a video | MP4, WebM, or MOV | FFmpeg; MOV also needs the `prores_ks` encoder |
| Use vector artwork | SVG or Lottie | SVG uses the base package. Lottie supports a limited Canvas-only subset. |

## Export an image

The file extension selects the format. This example needs Python 3.11+ and
`pip install quickthumb`:

```python
from quickthumb import Canvas

canvas = Canvas(1280, 720).background(color="#155BD7").text(
    "Make an idea visible.", size=72, color="#FFFFFF", position=(80, 300)
)
result = canvas.export("image.png")
print(result.written_paths)
```

Open `image.png` in the working directory. Exporting again replaces the file.
Use `.jpg` or `.webp` for those formats. A Deck exported to an image format
writes numbered slide files; `written_paths` tells you their names.

## Make slides or animation

Follow the [presentation and video examples](cookbook/decks-and-video.md) for
a runnable image, two-slide HTML presentation, and GIF. For PowerPoint or PDF,
install the relevant [optional extra](installation.md#optional-extras) first.
MP4 and WebM require FFmpeg installed separately.

Formats do not preserve every effect or animation in the same way. PowerPoint
and PDF may use image fallbacks, and an HTML presentation does not play Deck
narration. Check the result in the app where you plan to use it.

For format support, export receipts, advanced options, and fallbacks, see the
[export reference](exports.md).
