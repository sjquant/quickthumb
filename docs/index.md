---
title: quickthumb · visuals from code
description: Create images, presentations, and animated videos from Python or JSON.
template: home.html
hide:
  - navigation
  - toc
---

<section class="qt-hero" aria-labelledby="qt-heading" markdown>
<div class="qt-container qt-hero-layout" markdown>
<div class="qt-hero-copy" markdown>

<p class="qt-eyebrow">A Python creative toolkit</p>

<h1 id="qt-heading">Make visuals<br>with code.</h1>

<p class="qt-hero-description">Create images, presentations, and animated videos from reusable layouts.</p>

<div class="qt-actions" markdown>
[Install quickthumb <span aria-hidden="true">→</span>](#install){ .qt-button .qt-button-white }
[Explore examples](cookbook/index.md){ .qt-button .qt-button-outline }
</div>

</div>
<div class="qt-artwork" aria-label="Examples made with quickthumb" markdown>

[![Creator thumbnail: I mapped the planet with Python](assets/home/orbit-thumbnail-planet.webp)](cookbook/decks-and-video.md#orbit-atlas){ .qt-art .qt-art-front }
[![Podcast guest promotion](assets/examples/podcast_interview_promo.png)](cookbook/podcast-promo.md){ .qt-art .qt-art-back }
[![Cover of the Orbit Atlas presentation](assets/home/orbit-slide-1.webp)](cookbook/decks-and-video.md#orbit-atlas){ .qt-art .qt-art-bottom }

</div>
</div>
</section>

<section class="qt-story" aria-labelledby="images-heading" markdown>
<div class="qt-container qt-story-grid" markdown>
<div class="qt-story-copy" markdown>

<p class="qt-kicker">Images &amp; graphics</p>

## Compose images. { #images-heading }

Combine text, photos, and shapes into thumbnails, social graphics, and more. Your layout stays in code, ready to adapt.

[See the complete example →](cookbook/decks-and-video.md#orbit-atlas){ .qt-story-link }

</div>
<div class="qt-visual qt-image-pair" markdown>

![Creator thumbnail: I mapped the planet with Python](assets/home/orbit-thumbnail-planet.webp)

<div class="qt-code-window" markdown>
<div class="qt-code-title" markdown="span"><span class="qt-code-dots" aria-hidden="true"><i></i><i></i><i></i></span> orbit_atlas.py · excerpt</div>

```python
canvas = Canvas(WIDTH, HEIGHT).image(
    CREATOR, (0, 0), WIDTH, HEIGHT, fit="cover"
)
canvas.text(
    "I MAPPED\nTHE PLANET", position=(716, 58),
    font=HEAVY, size=86, color=WHITE,
)
canvas.shape("rectangle", (722, 252), 486, 104,
             YELLOW, rotation=-3)
canvas.text("WITH PYTHON", position=(756, 270),
            font=HEAVY, size=62, color="#111923", rotation=-3)
```

</div>

</div>
</div>
</section>

<section class="qt-story qt-story-tinted" aria-labelledby="slides-heading" markdown>
<div class="qt-container qt-story-grid" markdown>
<div class="qt-story-copy" markdown>

<p class="qt-kicker">Presentations</p>

## Build presentations. { #slides-heading }

Bring canvases together in a deck with transitions and speaker notes. Export a presentation for the browser or PowerPoint.

[Explore the presentation →](cookbook/decks-and-video.md#orbit-atlas){ .qt-story-link }

</div>
<div class="qt-visual qt-deck-preview" markdown>

![Orbit Atlas presentation cover with mountains and a lake](assets/home/orbit-slide-1.webp)

<div class="qt-slide-strip" markdown>
![Orbit Atlas coverage chart](assets/home/orbit-slide-2.webp)
![Orbit Atlas metrics slide](assets/home/orbit-slide-3.webp)
![Orbit Atlas closing slide](assets/home/orbit-slide-4.webp)
</div>

</div>
</div>
</section>

<section class="qt-story" aria-labelledby="motion-heading" markdown>
<div class="qt-container qt-story-grid" markdown>
<div class="qt-story-copy" markdown>

<p class="qt-kicker">Video &amp; animation</p>

## Bring ideas to motion. { #motion-heading }

Animate layers and render a video or GIF. Add transitions, narration, and music as your story grows.

[Explore the video example →](cookbook/decks-and-video.md#orbit-atlas){ .qt-story-link }

</div>
<div class="qt-visual qt-video-preview">
<video controls playsinline preload="none" poster="assets/home/orbit-film-poster.webp" aria-label="Orbit Atlas animation generated with quickthumb">
<source src="assets/home/orbit-film.mp4" type="video/mp4">
Your browser does not support video. <a href="assets/home/orbit-film.mp4">Download the animation</a>.
</video>
</div>
</div>
</section>

<section class="qt-story qt-story-tinted" aria-labelledby="reuse-heading" markdown>
<div class="qt-container qt-story-grid" markdown>
<div class="qt-story-copy" markdown>

<p class="qt-kicker">Reusable by design</p>

## Create once. Reuse everywhere. { #reuse-heading }

Keep your design in Python or JSON. Change the content and generate a new series without rebuilding each visual by hand.

[See the complete example →](getting-started.md){ .qt-story-link }

</div>
<div class="qt-visual qt-reuse" markdown>
<div class="qt-code-window" markdown>
<div class="qt-code-title" markdown="span"><span class="qt-code-dots" aria-hidden="true"><i></i><i></i><i></i></span> episode_cards.py</div>

```python
episodes = [
    (12, "Ship your first release", "#FF4B1F"),
    (13, "Make room for better work", "#FFD400"),
    (14, "Build less. Finish more.", "#4D8DFF"),
]
for episode, title, accent in episodes:
    episode_card(episode, title, accent).render(
        f"episode-{episode}.png"
    )
```

</div>
<div class="qt-reuse-results" markdown>
![Episode 12 card](assets/home/episode-12.png)
![Episode 13 card](assets/home/episode-13.png)
![Episode 14 card](assets/home/episode-14.png)
</div>
</div>
</div>
</section>

<section class="qt-story" id="install" aria-labelledby="install-heading" markdown>
<div class="qt-container qt-story-grid" markdown>
<div class="qt-story-copy" markdown>

<p class="qt-kicker">Get started</p>

## Install quickthumb. { #install-heading }

Requires Python 3.11 or later.

[Installation options →](installation.md){ .qt-story-link }

</div>
<div class="qt-visual" markdown>

```bash
python -m pip install quickthumb
```

</div>
</div>
</section>
