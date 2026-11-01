---
description: Browse ready-to-run quickthumb recipes for YouTube thumbnails, Instagram cards, podcast promos, shorts covers, and AI workflows.
---

# Cookbook

Choose an image, presentation, or video to make. Each preview comes from the
example linked with it; adapt its text, images, and colors for your own work.

## Presentations and video

<div class="qt-gallery" markdown>
<figure markdown="span">
[![Orbit Atlas presentation cover](../assets/home/orbit-slide-1.webp)](decks-and-video.md#orbit-atlas)
<figcaption>Presentation and slides</figcaption>
</figure>
<figure markdown="span">
[![Orbit Atlas video preview](../assets/home/orbit-film-poster.webp)](decks-and-video.md#orbit-atlas)
<figcaption>Animated video</figcaption>
</figure>
</div>

[Explore presentation and video examples →](decks-and-video.md)

## Images and graphics

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

## More ways to create

- [Render your first cards](../getting-started.md): reuse one layout without cloning the repository.
- [AI workflow](ai-workflow.md): generate, validate, and render a JSON layout.
- [Webfonts and background removal](webfonts-rembg.md): add a typeface or cut out a portrait.

## Running the recipes

Most recipes use fonts and photos bundled in the repository. Install
[uv](https://docs.astral.sh/uv/), then run them from a clone:

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
