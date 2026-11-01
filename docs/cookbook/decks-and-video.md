---
description: Run complete quickthumb examples for a presentation and an animated product video.
---

# Presentations and video

These examples are made with the same Canvas and Deck APIs. Their scripts,
fonts, images, and audio are in the repository. Clone it to run them:

```bash
git clone https://github.com/sjquant/quickthumb
cd quickthumb
```

## Investor deck

The Vela example builds ten slides with transitions and speaker notes. All
company data is illustrative. It exports an interactive HTML presentation and a
PowerPoint file from the same deck.

![The cover of the Vela investor deck](../assets/home/investor-slide-1.png)

```bash
uv run --extra pptx python examples/investor_deck.py
```

Open `examples/investor_deck.html` in a browser or
`examples/investor_deck.pptx` in PowerPoint. The script overwrites these files
when run again. See the [complete source](https://github.com/sjquant/quickthumb/blob/main/examples/investor_deck.py)
and the [Deck API](../api/deck.md).

PowerPoint output requires the `pptx` extra. Some effects or transitions may use
fallbacks in a given format; consult the [export guide](../exports.md) for details.

## Product reel

This 35-second vertical product video combines eight scenes with animated text,
charts, transitions, voiceovers, and a soundtrack. Play the actual output:

<video controls playsinline preload="none" width="360" poster="../../assets/home/product-hype-reel-poster.png">
<source src="../../assets/home/product-hype-reel.mp4" type="video/mp4">
Your browser does not support video. <a href="../../assets/home/product-hype-reel.mp4">Download the product reel</a>.
</video>

```bash
uv run --extra pptx python examples/product_hype_reel.py
```

The script writes GIF, HTML, PowerPoint, MP4, and WebM files in `examples/`,
replacing outputs of the same name. MP4 and WebM need FFmpeg on `PATH`;
PowerPoint needs the `pptx` extra. The [complete source](https://github.com/sjquant/quickthumb/blob/main/examples/product_hype_reel.py)
uses bundled fonts and audio. Read about [video exports](../exports.md) and
[animation timing](../timing.md) to adapt it.
