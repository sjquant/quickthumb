---
description: Render three episode cards from one reusable Python layout, then change the content to make it your own.
---

# Render your first cards

Build one episode-card layout and render it with three sets of content.
Then change a title to make your own version.

![Episode 12: a giant black 12 standing on the edge of an orange band, above the white headline Ship your first release](assets/home/episode-12.png)

## 1. Install quickthumb

You need **Python 3.11 or later**. In your Python environment:

```bash
python -m pip install quickthumb
```

If you need an environment first, follow
[Installation](installation.md#isolated-environment), then return here.
The example uses only the base package and its built-in font: no font downloads,
photos, or optional renderers are needed after installation.

## 2. Save and run the layout

Save this as `episode_cards.py` in your working directory, outside any quickthumb
checkout:

```python
--8<-- "examples/episode_cards.py"
```

Run it from that directory:

```bash
python episode_cards.py
```

Open `episode-12.png`, `episode-13.png`, and `episode-14.png` in the same directory.
Each is a 1280 × 720 image. The script writes to those filenames each time it runs,
replacing any existing files with those names.

<div class="qt-gallery qt-variants" markdown>
![Episode 12: "Ship your first release" with a giant 12 on an orange band](assets/home/episode-12.png)
![Episode 13: "Make room for better work" with a giant 13 on a yellow band](assets/home/episode-13.png)
![Episode 14: "Build less. Finish more." with a giant 14 on a blue band](assets/home/episode-14.png)
</div>

## 3. Make the next card

Add another row to `episodes`, keeping the function unchanged:

```python
(15, "Your next big idea", "#FF4B1F"),
```

Run the script again and open `episode-15.png`. You have reused the same layout
with a new episode number, title, and color.

The title wraps within `max_width`. `auto_scale=True` lets it shrink to fit the
specified width and height. Check your longest real titles before using the
layout for a batch.

## Adapt the design

Inside `episode_card()`, change the colors, the numeral or title size, or the
positions once to update every card. Layers are drawn in the order you add them.
For your own typeface, add a local font path to each `.text()` call, such as
`font="/path/to/your-font.ttf"`, and remove the `Stroke` effects if the font is
already heavy enough.

When expanding the layout, use `canvas.diagnose()` to check for common problems
such as off-canvas layers and low contrast. This layout reports one `off-canvas`
finding because the numeral is cropped on purpose. See
[Diagnostics](diagnostics.md) for checks and their limits; a clean report does
not establish that a design looks good.

## Choose your next step

- [Cookbook](cookbook/index.md): adapt a thumbnail, social card, or podcast layout.
- [Core Concepts](concepts.md): understand layers, effects, and positioning.
- [Auto Layout](api/group.md): arrange changing content in rows and columns.
- [JSON & AI Workflow](json-schema.md): load and validate layouts as JSON.
- [Exporting](exports.md): save other formats and inspect export results.
- [API Reference](api/index.md): look up a class or parameter.
