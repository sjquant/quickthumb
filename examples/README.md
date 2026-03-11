# QuickThumb Examples

This directory contains runnable end-to-end compositions that match the current QuickThumb API.

## Run an Example

From the repository root:

```bash
uv run python examples/youtube_thumbnail_01.py
uv run python examples/youtube_thumbnail_02.py
uv run python examples/instagram_news_card.py
```

All examples write their rendered image back into this directory.

## Included Examples

### `youtube_thumbnail_01.py`

Output: `youtube_thumbnail_01.png`

Shows:

- 16:9 canvas via `Canvas.from_aspect_ratio("16:9", 1280)`
- Background image with brightness adjustment using `Filter`
- Dark overlay background for readability
- Rich text via `TextPart`
- Thick text strokes and outer border for classic YouTube-thumbnail styling

Use it when you want a bright, punchy thumbnail with large stacked headline text.

### `youtube_thumbnail_02.py`

Output: `youtube_thumbnail_02.png`

Shows:

- Full manual layout on a `1280x720` canvas
- Background image with `FitMode.COVER`
- Gradient overlay for contrast
- Heavy-weight typography using CSS-style numeric font weights
- `Shadow`, `Stroke`, and text `Background` effects together

Use it when you want a more editorial thumbnail with strong hierarchy and multiple text blocks.

### `instagram_news_card.py`

Output: `instagram_news_card.png`

Shows:

- Square `1080x1080` social card layout
- Cover-fit background image with darkening filter
- Vertical gradient overlay for headline legibility
- Badge-style label using text background effects
- Multiline headline, supporting copy, and rich-text metadata row

Use it when you want a reusable template for Instagram posts, X cards, or social news promos.

## Assets and Fonts

The example scripts set:

- `QUICKTHUMB_FONT_DIR` to `assets/fonts`
- `QUICKTHUMB_DEFAULT_FONT` to `Roboto`

They also use bundled example images from `assets/images`.

## Extending These Examples

Common edits that are safe to make:

- Replace the background image path or URL
- Swap headline copy and highlight colors
- Change the canvas size or aspect ratio
- Add `canvas.image(...)` for logos, cutouts, or subject overlays
- Export as JPEG or WebP instead of PNG
