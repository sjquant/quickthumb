---
title: quickthumb · thumbnails from code
description: Turn changing content into consistent images. Define a reusable thumbnail or social card layout in Python or JSON, then render it with new content.
template: home.html
hide:
  - navigation
  - toc
---

<section class="qt-hero" markdown>

# Thumbnails, from code

Create thumbnails and social images in Python or JSON. Build a layout once,
then update the text, images, and colors for your next post.

[Get started](getting-started.md){ .md-button .md-button--primary }
[Browse recipes](cookbook/index.md){ .md-button }

<figure class="qt-output" markdown="span">
[![YouTube thumbnail with a textured photographic background, bold headline, and overlapping before-and-after cards](assets/examples/youtube_thumbnail_01.png)](cookbook/youtube-thumbnail.md#before-after)
<figcaption markdown="span">Made with quickthumb · [See the source](cookbook/youtube-thumbnail.md#before-after)</figcaption>
</figure>

</section>

<section class="qt-block" markdown>

## Start with a layout that fits your content

Each image links to a runnable recipe and its source.

<div class="qt-gallery" markdown>
[![Release announcement with a large two-tone headline and blue artwork](assets/examples/launch_announcement.png)](cookbook/launch-announcement.md)
[![Commentary thumbnail with a large headline and cut-out portrait](assets/examples/youtube_reaction.png)](cookbook/youtube-thumbnail.md#reaction)
[![Podcast episode card with a guest portrait](assets/examples/podcast_interview_promo.png)](cookbook/podcast-promo.md)
[![Social news card with a serif headline over a photograph](assets/examples/instagram_news_card.png)](cookbook/instagram-card.md)
</div>

[Browse all recipes →](cookbook/index.md){ .qt-more }

</section>

<section class="qt-block" markdown>

## Try a reusable layout

Start with a small example: one function, three episode cards.
For the designs above, open a recipe to use its fonts, images, and full layout.

<div class="qt-gallery qt-variants" markdown>
![Episode 12: "Ship your first release" with a giant 12 on an orange band](assets/home/episode-12.png)
![Episode 13: "Make room for better work" with a giant 13 on a yellow band](assets/home/episode-13.png)
![Episode 14: "Build less. Finish more." with a giant 14 on a blue band](assets/home/episode-14.png)
</div>

Python 3.11+ · Base package only · No font or image downloads after installation

```bash
python -m pip install quickthumb
```

Save as `episode_cards.py`, then run `python episode_cards.py`:

```python
--8<-- "examples/episode_cards.py"
```

Open `episode-12.png`, `episode-13.png`, and `episode-14.png` in the same directory.
Edit the `episodes` list and run it again to replace the cards with your own content.

Prefer JSON? [Load a spec from your pipeline or an AI workflow](json-schema.md).

</section>

<section class="qt-block" markdown>

## Keep the layout. Change the content

- **Fit changing titles.** Set text wrapping and fitting bounds, or use
  [auto-layout groups](api/group.md) to arrange rows and columns.
- **Catch common problems.** [Diagnostics](diagnostics.md) flag issues such as
  off-canvas layers, small text, and low contrast before export.
- **Use the output where you need it.** Export PNG, JPEG, WebP, SVG, HTML, or GIF
  with the base package. [Other formats](exports.md), including PDF, PPTX, and
  video, have additional dependencies and format-specific behavior.

For repeatable pixels, keep assets, fonts, and the rendering environment fixed.
[Read the reproducibility requirements](exports.md#render-reproducibility).

Need several slides or narrated video? Explore [Deck](api/deck.md).

</section>

<section class="qt-block qt-end" markdown>

## Make the next image your own

[Get started](getting-started.md){ .md-button .md-button--primary }
[API reference](api/index.md){ .md-button }

</section>
