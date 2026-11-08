<p align="center">
  <img src="docs/assets/brand/quickthumb-icon-192.png" alt="quickthumb" width="88" />
</p>

<h1 align="center">quickthumb</h1>

<p align="center">
  <a href="README.md">English</a> · <a href="README.ko.md">한국어</a> · <a href="README.ja.md">日本語</a> · <a href="README.zh-CN.md">简体中文</a>
</p>

<p align="center">
  <strong>Your next thumbnail, from the same layout.</strong>
</p>

quickthumb is a **Python library for developers who publish recurring thumbnails and social images**.
Keep your layout in code, then pass in a new headline, episode number, or color
to make the next image. Use Python functions or JSON specs in your content pipeline.

<p align="center">
  <a href="https://quickthumb.solaqua.dev/getting-started/">Get started</a> · <a href="https://quickthumb.solaqua.dev/cookbook/">Browse recipes</a> · <a href="https://quickthumb.solaqua.dev/api/">API reference</a>
</p>

## Make your first three cards

This example turns one layout into three **1280 × 720 episode cards**.
It uses the base package and built-in font, with no asset downloads after installation.

| 12 | 13 | 14 |
| --- | --- | --- |
| ![Episode 12](docs/assets/home/episode-12.png) | ![Episode 13](docs/assets/home/episode-13.png) | ![Episode 14](docs/assets/home/episode-14.png) |

Requires **Python 3.11+**. Run in a working directory outside the quickthumb
checkout. Need a virtual environment? See [Installation](https://quickthumb.solaqua.dev/installation/)
for Bash/Zsh and Windows setup. Then install:

```bash
python -m pip install quickthumb
```

Save the complete example below as `episode_cards.py`, then run:

```bash
python episode_cards.py
```

Open `episode-12.png`, `episode-13.png`, and `episode-14.png` in the same directory.
**Each run overwrites these three files.**

The sample titles stay in English so you can try it with the built-in font.

```python
from quickthumb import Canvas, Stroke

INK = "#111111"
WHITE = "#FFFFFF"


def episode_card(episode, title, accent):
    return (
        Canvas(1280, 720)
        .background(color=INK)
        .shape("rectangle", position=(0, 0), width=1280, height=360, color=accent)
        # The numeral stands on the band and crops at the top edge.
        .text(
            str(episode),
            size=540,
            color=INK,
            # A stroke in the text color thickens the regular-weight built-in font.
            effects=[Stroke(width=8, color=INK)],
            position=(1240, 360),
            align=("right", "bottom"),
            letter_spacing=-10,
        )
        .text(
            "THE BUILDER'S\nNOTEBOOK",
            size=26,
            color=INK,
            effects=[Stroke(width=1, color=INK)],
            position=(48, 44),
            letter_spacing=1,
        )
        .text(
            "EPISODE",
            size=26,
            color=INK,
            effects=[Stroke(width=1, color=INK)],
            position=(48, 330),
            align=("left", "bottom"),
            letter_spacing=1,
        )
        .text(
            title,
            size=136,
            color=WHITE,
            effects=[Stroke(width=2, color=WHITE)],
            position=(48, 688),
            align=("left", "bottom"),
            max_width=1184,
            max_height=290,
            auto_scale=True,
            balance_lines=True,
            line_height=1.04,
        )
    )


episodes = [
    (12, "Ship your first release", "#FF4B1F"),
    (13, "Make room for better work", "#FFD400"),
    (14, "Build less. Finish more.", "#4D8DFF"),
]

for episode, title, accent in episodes:
    episode_card(episode, title, accent).render(f"episode-{episode}.png")
```

Change a title or accent color
in `episodes` and run again to see the same layout with new content.
Test your longest titles before running a batch.

For other languages, choose a local font with the glyphs you need; see
[Text](https://quickthumb.solaqua.dev/api/text/). The [first-use guide](https://quickthumb.solaqua.dev/getting-started/)
explains how to adapt this layout.

## Keep the layout. Let the content change

- **Separate content from layout.** Reuse a Python function, or load a
  [JSON spec](https://quickthumb.solaqua.dev/json-schema/) from your pipeline.
- **Fit changing titles.** Set wrapping and fitting bounds, or use
  [auto-layout groups](https://quickthumb.solaqua.dev/api/group/) for rows and columns.
- **Check before export.** `diagnose()` flags common issues such as off-canvas
  layers, small text, and low contrast. It does not judge design quality;
  see [diagnostic limits](https://quickthumb.solaqua.dev/diagnostics/).

To reproduce a render, retain the assets, fonts, and rendering environment.
See [reproducibility requirements](https://quickthumb.solaqua.dev/reference/export-assets/#render-reproducibility)
before expecting matching pixels across runs or machines.

## Start from a working design

![Launch announcement created with quickthumb](examples/launch_announcement.png)

| YouTube thumbnail | Commentary thumbnail | Podcast episode |
| --- | --- | --- |
| [![YouTube thumbnail](examples/youtube_thumbnail_01.png)](https://quickthumb.solaqua.dev/cookbook/youtube-thumbnail/) | [![Commentary thumbnail](examples/youtube_reaction.png)](https://quickthumb.solaqua.dev/cookbook/youtube-thumbnail/#reaction) | [![Podcast episode](examples/podcast_interview_promo.png)](https://quickthumb.solaqua.dev/cookbook/podcast-promo/) |

[Explore the layouts and their source →](https://quickthumb.solaqua.dev/cookbook/)

## Need another output?

The base package exports PNG, JPEG, WebP, SVG, HTML, and GIF. PDF and PPTX need
optional packages; MP4 and WebM need FFmpeg. Format support and visual behavior
vary: see [Installation](https://quickthumb.solaqua.dev/installation/) and [Exporting](https://quickthumb.solaqua.dev/exports/).

For multi-slide presentations and narrated video, see the
[Deck guide](https://quickthumb.solaqua.dev/api/deck/). For generated JSON specs, see the
[JSON & AI workflow](https://quickthumb.solaqua.dev/json-schema/).

## License

[MIT](LICENSE)
