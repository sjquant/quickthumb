# quickthumb examples

Runnable scripts that use the current quickthumb API. Each one writes its
output next to itself in this folder. The [cookbook](https://quickthumb.solaqua.dev/cookbook/)
shows the thumbnail examples with their images.

Run them from the repository root:

```bash
uv run python examples/youtube_thumbnail_01.py
```

The scripts set `QUICKTHUMB_FONT_DIR` to `assets/fonts` and
`QUICKTHUMB_DEFAULT_FONT` to `Roboto`, and load photos from `assets/images`, so
they need nothing from the network unless noted below.

## Thumbnails and social images

| Script | Output | What it shows | Needs |
| --- | --- | --- | --- |
| `youtube_thumbnail_01.py` | 1280×720 PNG | Photo with a side gradient, a three-size `TextPart` headline, two rotated cards | |
| `youtube_thumbnail_02.py` | 1280×720 PNG | One large question over a desaturated photo; each line its own layer | |
| `youtube_talking_head.py` | 1280×720 PNG | Headline beside a cut-out portrait pinned to the bottom-right corner | `rembg` extra, network |
| `youtube_reaction.py` | 1280×720 PNG | Big word and number, a cut-out portrait, a radial glow, a faint `#1` | `rembg` extra |
| `youtube_tutorial_explainer.py` | 1280×720 PNG | No photos; a code snippet "highlighted" with `TextPart` colors | |
| `instagram_news_card.py` | 1080×1080 PNG | Label from a text `Background` effect, serif headline, percentage positions | |
| `podcast_interview_promo.py` | 1280×720 PNG | Full-bleed portrait, a gradient that makes room for text, a webfont URL | network (first run) |
| `shorts_cover_agent.py` | 1080×1920 PNG | The whole design in `shorts_cover_agent.json`, rendered with `Canvas.from_json()` | |
| `launch_announcement.py` | 1280×720 PNG | Auto-layout groups, theme tokens, and `diagnose()` before rendering, from `launch_announcement.json` | `svg` extra |
| `social_preview.py` | 1200×630 PNG | The docs site's link preview card, written to `docs/assets/brand/social-preview.png` | |

Extras install with `uv run --extra <name> python examples/<script>.py`. The
`rembg` extra requires Python 3.11 or later.

## Decks and video

### `investor_deck.py`

A 10-slide Series A pitch deck exported to `investor_deck.html` and
`investor_deck.pptx` from the same code. The HTML plays the slide transitions
and has a presenter view with speaker notes:

```bash
quickthumb serve examples/investor_deck.py   # open /?presenter for notes
```

All company figures in the deck are marked as illustrative. The PPTX export
needs the `pptx` extra.

### `product_hype_reel.py`

A 35-second vertical (1080×1920) product video in eight scenes, exported to
GIF, MP4, WebM, HTML, and PPTX. It shows:

- `AnimationSpec` motion: staggered headlines, growing bars, a playhead that
  moves along a timeline
- `Canvas.counter(...)` for animated numbers
- `Cut`, `Fade`, and `Wipe` transitions between scenes
- Eight bundled voiceovers mixed over a looping soundtrack with
  `VideoOptions(soundtrack=AudioTrack(...))`
- `deck.diagnose()` before exporting

MP4 and WebM need the `ffmpeg` binary on `PATH`; the other formats render
without it. Fonts, voiceovers, and music are bundled.

### `ordinary_moments.py`

A 60-second 16:9 product video in nine scenes, built from five bundled stock
clips (their sources are listed in a manifest in `assets/video`). It shows:

- One clip placed in 16:9, 1:1, and 9:16 frames at once, to show what `fit`
  does
- Timed captions
- A `BackdropBlur` panel
- A soundtrack that fades out at the end

Outputs `ordinary_moments.mp4`, `ordinary_moments.webm`, and a short
`ordinary_moments_preview.gif`. All three need `ffmpeg`.
