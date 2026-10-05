---
description: A 1080×1080 breaking-news card for Instagram built with quickthumb, shown with the exact script that rendered it.
---

# Instagram Card

![Square breaking-news card reading "Wildfires Spread Across 18,000 Acres" over a photo of flames](../assets/examples/instagram_news_card.png)

A square news card: a photo, a red label, a serif headline, and a source line.

```bash
git clone https://github.com/sjquant/quickthumb
cd quickthumb
uv run python examples/instagram_news_card.py
```

## How it's built

- **The label is text with a `Background` effect.** `Background(color="#CC0000",
  padding=(11, 22))` draws the red box around "BREAKING NEWS", so it grows
  with the text instead of being a separate shape you have to resize.
- **The headline uses a different font from the rest.** `font="NotoSerif"`
  loads the serif from the bundled font folder; every other layer uses the
  default Roboto.
- **The red bar is a 9px-wide rectangle.** It is a separate shape, so its
  height (336px) is set by hand to match the two headline lines.
- **The source line is one text layer.** Two `TextPart`s give "WORLD NEWS" and
  the date different colors and weights.
- **Positions are percentages**, such as `("8%", "92%")`, so the same layout
  works if you change the canvas size.

## Code

```python
--8<-- "examples/instagram_news_card.py"
```
