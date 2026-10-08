---
description: Answers to common quickthumb questions about installation, text, fonts, images, output formats, JSON specs, and errors.
---

# FAQ

## Installation

### Which Python versions are supported?

Python 3.10 or later. The package is classified for 3.10, 3.11, and 3.12, and
CI runs on 3.10. Background removal (the `rembg` extra) needs 3.11 or later.

### The `quickthumb` command isn't found

The command line tool is an optional extra: `pip install "quickthumb[cli]"`.
[Installation](installation.md) lists every extra.

### Why does my SVG layer raise `RenderingError`?

Drawing SVG files needs the `svg` extra: `pip install "quickthumb[svg]"`.
Exporting a canvas *to* SVG doesn't.

## Canvas and layers

### What happens if I render a canvas with no layers?

You get a fully transparent image of the canvas size. It isn't an error.

### Why does a group child raise "group children must not set position"?

A group positions its children itself. Remove `position` from the child and
place the group instead:

```python
canvas.group(
    children=[{"type": "text", "content": "TITLE", "size": 96, "color": "#FFFFFF"}],
    position=("8%", "50%"),
    align=("left", "middle"),
)
```

A child's `align` is ignored too. Use the group's `item_align` to line
children up across the group.

### How do I check a design for problems before rendering?

Call `canvas.diagnose()`, or run `quickthumb lint spec.json` on a JSON spec.
It reports text that is too small or off the canvas, low contrast, hidden
layers, and more. See [Diagnostics & CLI](diagnostics.md).

## Text and fonts

### My text runs off the canvas

Set `max_width` so it wraps:

```python
canvas.text(content="A longer title that needs two lines", size=72, color="#FFFFFF", max_width="60%")
```

Add `auto_scale=True` (with `max_width`, `max_height`, or both) to shrink the
text until it fits instead.

### I set `bold=True` and `weight=900` and got an error

They set the same thing, so use one. `weight` is more precise:
`TextPart(text="STRONG", weight=900)`.

### How do I use a Google Font?

Name it and set `font_source="google"`. It is downloaded once and cached, and
`weight` picks the matching file:

```python
canvas.text(content="Hello", font="Inter", font_source="google", weight=800, size=72, color="#FFFFFF")
```

You can also pass the URL of a font file, or point `QUICKTHUMB_FONT_DIR` at a
folder of fonts. See [Webfonts & Background Removal](cookbook/webfonts-rembg.md).

## Images

### Can I use images from a URL?

Yes. `background(image=...)` and `image(path=...)` accept `http(s)` URLs. They
are downloaded and cached while rendering. To control the cache, see
[Remote assets and caching](exports.md#remote-assets-and-caching).

### How do I remove the background behind a person?

Set `remove_background=True` on the image layer. It needs the `rembg` extra:

```python
canvas.image(path="portrait.jpg", position=("75%", "55%"), width=420, height=520, remove_background=True)
```

### What's the difference between `cover`, `contain`, and `fill`?

`cover` fills the box and crops what doesn't fit. `contain` fits the whole
image inside the box and leaves empty space. `fill` stretches the image to the
box, ignoring its proportions.

## Output

### Which formats can I export?

The format comes from the file extension you pass to `render()`:

| Kind | Formats | Needs |
| --- | --- | --- |
| Images | PNG, JPEG, WebP | |
| Vector and documents | SVG, PDF, PPTX | `pdf` / `pptx` extras for PDF and PPTX |
| Web | HTML | |
| Animation | GIF, MP4, WebM | `ffmpeg` for MP4 and WebM |

See [Exporting](exports.md) for what each format keeps and loses.

### Can I set `quality` for a PNG?

No. `quality` only applies to JPEG and WebP; passing it for PNG raises
`RenderingError`.

### How do I get the image without writing a file?

```python
png_base64 = canvas.to_base64(format="PNG")
jpeg_data_url = canvas.to_data_url(format="JPEG", quality=90)
```

## JSON

### Can I pass a dict to `Canvas.from_json()`?

No, it takes a JSON string. Convert first with `json.dumps(data)`.

### Why does `to_json()` raise `ValidationError`?

The canvas has a `.custom(fn)` layer. A Python function can't be written to
JSON, so remove that layer first.

### My `theme` block disappeared after `to_json()`

Theme tokens are replaced with their values when the spec is loaded, so
`to_json()` writes the values and no `theme` block. Keep your original spec
file if you want to keep editing the tokens.

## Errors

### What do the different errors mean?

- `ValidationError`: an argument or spec field is invalid. Raised as soon as
  you add the layer or load the spec.
- `RenderingError`: something failed while drawing, such as a download.
- `MissingAssetError`: a local file the spec refers to doesn't exist.

Every error has `details` with a stable code, the JSON Pointer of the field,
and the layer id. See [Structured Errors](errors.md).
