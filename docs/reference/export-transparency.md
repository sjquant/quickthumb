---
description: Reference for transparent video in quickthumb.
---

# Transparent video

[Export reference](../exports.md) · [Choose an output format](../output-guide.md)

## Transparent WebM

VP9 WebM can preserve alpha through `VideoOptions(transparent=True)`, or the
keyword-only `transparent=True` argument to `Canvas.to_webm()` and
`Deck.to_webm()`. The default is `False`; existing opaque exports keep their
matte and encoder settings. This is an export option, not a layer or motion
property, so it is absent from Canvas/Deck JSON and `inspect_motion()`;
`VideoOptions.model_validate_json()` and its model JSON schema expose the strict
boolean option. `validate_export()` continues to describe document motion,
while `render()` rejects transparent options on unsupported output formats.

```python
canvas.render("overlay.webm", animation=VideoOptions(transparent=True))
deck.render("overlay.webm", animation=VideoOptions(transparent=True, render_quality="high", workers=2))
webm_bytes = canvas.to_webm(transparent=True)
options = VideoOptions.model_validate_json('{"transparent": true, "fps": 24}')
```

Only the export matte is skipped. Authored backgrounds remain visible, empty
areas and mixed-size slide letterboxing stay transparent, and a transition on
slide zero starts from transparency. Fade and mask transitions interpolate
premultiplied colors; covering and scaled slides composite with source-over
alpha. Keyed Morph normalizes mixed-size slides to the first slide's output
space before interpolating positions, dimensions and translucent pixels. The
existing parent/caption Morph fallback restrictions still apply.

Both compositing quality modes, spawn workers, soundtracks and Deck narration
work with transparent WebM. The encoder streams RGBA into VP9 `yuva420p` with
lossless VP9 coding to protect the alpha plane. The RGBA-to-YUV conversion can
change decoded alpha by one 8-bit level; RGB remains chroma-subsampled (4:2:0),
so source color pixels are not lossless. Files can be larger than opaque WebM.
The existing bounded frame batches and atomic destination replacement remain.
Transparent transitions use temporary floating-point planes for accurate
premultiplied blending; memory usage grows with frame size and worker count.
MP4, GIF, and document/raster output reject this video option before writing
the destination. PNG animation sequences use the separate
[`export_image_sequence()` API](export-frames.md#image-sequences).

Use a player or editor that supports VP9 WebM alpha. To inspect the actual
alpha plane with FFmpeg, select the libvpx decoder **before** the input:

```bash
ffmpeg -c:v libvpx-vp9 -i overlay.webm -frames:v 1 -pix_fmt rgba frame.png
```

The native VP9 decoder may report/decode only color; `alpha_mode` metadata
alone is not proof of preserved transparency. The regression tests decode RGBA
with libvpx and compare transparent, translucent and opaque pixels. See
`examples/transparent_lower_third.py` for an overlay with an authored translucent
panel and transparent surroundings.

## ProRes 4444 MOV

Canvas and Deck can export `.mov` with the fixed ProRes 4444 profile, using
FFmpeg's `prores_ks` encoder. MOV always plays the animated timeline, including
Deck transitions and narration. `transparent` is the same strict boolean option
as WebM and defaults to `False`: ordinary MOV composites onto the matte; opt-in
alpha skips only that matte. Authored backgrounds, letterboxing, transitions,
quality modes and workers follow the transparent WebM behavior above.

```python
canvas.render("overlay.mov", animation=VideoOptions(transparent=True, fps=24))
deck.export("overlay.mov", animation=VideoOptions(transparent=True, render_quality="high", workers=2))
mov_bytes = canvas.to_mov(hold=2.0, transparent=True)
mov_bytes = deck.to_mov(hold=2.0, transparent=True, soundtrack="music.wav")
```

MOV retains exact canvas dimensions without cropping odd-width or odd-height frames. It encodes 4:4:4 chroma with 16-bit alpha coding (`yuva444p10le`) for transparent output, delivering industry-standard alpha fidelity for professional video editing tools such as Final Cut Pro, DaVinci Resolve, and Adobe Premiere.


Soundtracks, per-slide narration and embedded video audio are encoded as AAC,
using the same scheduling, looping, padding and trimming rules as animated MP4.
A Canvas MOV with no audio inputs contains only video. Deck MOV retains the
existing narration workflow’s silent AAC bed even when no slides have narration.
The fixed codec/profile and audio choices have no selection API. ProRes files can be substantially larger than
WebM/MP4, and require a ProRes-capable player or editor. Encoded segments stay
bounded and destinations are replaced only after the full encode and mux succeed.
A missing `prores_ks` encoder raises a rendering error and preserves any existing
destination. Decode pixels, rather than relying on profile metadata, to check alpha:

```bash
ffmpeg -i overlay.mov -frames:v 1 -pix_fmt rgba frame.png
```

`examples/transparent_lower_third.py` writes both WebM and ProRes MOV overlays.
