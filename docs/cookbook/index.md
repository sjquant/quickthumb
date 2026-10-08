---
description: Browse ready-to-run quickthumb recipes for YouTube thumbnails, Instagram cards, podcast promos, shorts covers, and AI workflows.
---

# Cookbook

Each image below was rendered by a script in the repository's `examples/` folder, and each recipe page shows that exact script.

## Gallery

<div class="qt-gallery qt-gallery--cookbook" markdown>
<figure markdown="span">
[![YouTube thumbnail](../assets/examples/youtube_thumbnail_01.png)](youtube-thumbnail.md#before-after)
<figcaption>YouTube thumbnail</figcaption>
</figure>
<figure markdown="span">
[![Burnout theme](../assets/examples/youtube_thumbnail_02.png)](youtube-thumbnail.md#burnout)
<figcaption>Burnout theme</figcaption>
</figure>
<figure markdown="span">
[![Instagram news card](../assets/examples/instagram_news_card.png)](instagram-card.md)
<figcaption>Instagram news card</figcaption>
</figure>
<figure markdown="span">
[![Talking head](../assets/examples/youtube_talking_head.png)](youtube-thumbnail.md#talking-head)
<figcaption>Talking head</figcaption>
</figure>
<figure markdown="span">
[![Reaction / commentary](../assets/examples/youtube_reaction.png)](youtube-thumbnail.md#reaction)
<figcaption>Reaction / commentary</figcaption>
</figure>
<figure markdown="span">
[![Tutorial / explainer](../assets/examples/youtube_tutorial_explainer.png)](youtube-thumbnail.md#tutorial)
<figcaption>Tutorial / explainer</figcaption>
</figure>
<figure markdown="span">
[![Podcast promo](../assets/examples/podcast_interview_promo.png)](podcast-promo.md)
<figcaption>Podcast promo</figcaption>
</figure>
<figure markdown="span">
[![Shorts / vertical cover](../assets/examples/shorts_cover_agent.png)](shorts-cover.md)
<figcaption>Shorts / vertical cover</figcaption>
</figure>
<figure markdown="span">
[![Launch announcement](../assets/examples/launch_announcement.png)](launch-announcement.md)
<figcaption>Launch announcement</figcaption>
</figure>
</div>

## Recipes

| Recipe | Size | What it shows |
| --- | --- | --- |
| [YouTube Thumbnails](youtube-thumbnail.md) | 1280×720 | Five layouts: before/after cards, a big question, talking head, reaction, tutorial |
| [Instagram Card](instagram-card.md) | 1080×1080 | A label built from a text `Background` effect, a serif headline, percentage positions |
| [Podcast Promo](podcast-promo.md) | 1280×720 | A full-bleed portrait, a gradient that makes room for text, a webfont from a URL |
| [Shorts / Vertical Cover](shorts-cover.md) | 1080×1920 | The whole design as a JSON spec, rendered with `Canvas.from_json()` |
| [Launch Announcement](launch-announcement.md) | 1280×720 | Auto-layout groups, theme tokens, and `diagnose()` before rendering |
| [AI Workflow](ai-workflow.md) | Any | Prompting an LLM for a spec, validating it, rendering, and iterating |
| [Webfonts & Background Removal](webfonts-rembg.md) | Any | Fonts from Google Fonts or a URL, and `remove_background` |

## Running the recipes

The scripts use fonts and photos bundled in the repository, so run them from a
clone:

```bash
git clone https://github.com/sjquant/quickthumb
cd quickthumb
uv run python examples/instagram_news_card.py
```

Two of the YouTube layouts cut out a portrait with `remove_background=True`.
They need the `rembg` extra, which requires Python 3.11 or later:

```bash
uv run --extra rembg python examples/youtube_reaction.py
```
