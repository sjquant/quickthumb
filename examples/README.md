# quickthumb Examples

This directory contains runnable end-to-end compositions that match the current quickthumb API.

## Run an Example

From the repository root:

```bash
uv run python examples/youtube_thumbnail_01.py
uv run python examples/youtube_thumbnail_02.py
uv run python examples/youtube_talking_head.py
uv run python examples/youtube_reaction.py
uv run python examples/youtube_tutorial_explainer.py
uv run python examples/instagram_news_card.py
uv run python examples/podcast_interview_promo.py
uv run python examples/shorts_cover_agent.py
uv run python examples/launch_announcement.py
uv run python examples/investor_deck.py
uv run python examples/product_hype_reel.py
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

### `youtube_talking_head.py`

Output: `youtube_talking_head.png`

Shows:

- Split left/right layout: headline text on the left, subject portrait on the right
- Left-to-right `LinearGradient` overlay that fades to transparent, keeping the portrait visible
- Remote image URL for the subject portrait (swap for a local path)
- Topic badge built from a `shape` + `text` layer pair
- Rich text with a two-tone headline using `TextPart`

Use it when you want the classic YouTube talking-head format with a presenter or guest alongside the topic.

### `youtube_reaction.py`

Output: `youtube_reaction.png`

Shows:

- Programmatic layout with no background photo — uses solid color + blended texture overlay
- Oversized decorative text element (`?!`) as a right-side graphic at low opacity
- `Glow` effect on both a shape badge and the main headline word
- `blend_mode` overlay on a background image layer at very low opacity for subtle texture

Use it when you want a high-energy reaction or commentary thumbnail driven entirely by typography and shape layers.

### `youtube_tutorial_explainer.py`

Output: `youtube_tutorial_explainer.png`

Shows:

- Pure gradient background (no photo dependency) using a diagonal `LinearGradient`
- Reusable `add_step()` helper that composes an ellipse badge + two text layers per step
- Two-tone headline via `TextPart` segments
- Thin rectangle used as a visual divider between the headline area and the steps column

Use it when you want a clean numbered-steps or how-to layout for tutorial and explainer videos.

### `instagram_news_card.py`

Output: `instagram_news_card.png`

Shows:

- Square `1080x1080` social card layout
- Cover-fit background image with darkening filter
- Vertical gradient overlay for headline legibility
- Badge-style label using text background effects
- Multiline headline, supporting copy, and rich-text metadata row

Use it when you want a reusable template for Instagram posts, X cards, or social news promos.

### `podcast_interview_promo.py`

Output: `podcast_interview_promo.png`

Shows:

- Remote image URLs for both the background photo and the speaker portrait
- A webfont loaded from a URL for the show-title treatment
- `remove_background=True` on the portrait layer for a cutout-style guest visual
- Layered promo-card styling with shapes, shadows, and heavy headline typography

Use it when you want an end-to-end podcast or interview promo example that exercises quickthumb's network-backed asset loading and portrait cutout workflow.

### `shorts_cover_agent.py`

Output: `shorts_cover_agent.png`

Spec: `shorts_cover_agent.json`

Shows:

- JSON-first rendering with `Canvas.from_json(...)` instead of hand-authored layer calls
- Vertical `1080x1920` Shorts / Reels / cover layout
- Repo-checked JSON spec that an AI agent could emit directly
- Shape, rich text, `auto_scale`, gradient overlays, and outline layers in one spec

Use it when you want to generate a vertical promo cover from an LLM-produced JSON layout and keep the rendering step deterministic.

### `launch_announcement.py`

Output: `launch_announcement.png`

Spec: `launch_announcement.json`

Shows the quickthumb 0.5 feature set in a single themed JSON spec:

- Top-level `theme` block with `$theme.*` token references for every color and font size
- Auto-layout `group` layers — a column with a nested chip row, zero hand-placed text coordinates
- `star` shape primitives with glow and stroke effects
- Decorative `svg` layers (requires `quickthumb[svg]`)
- Gradient-filled headline text via per-`TextPart` `fill`
- `Grain` effect with a fixed seed for deterministic texture
- `canvas.diagnose()` before rendering, mirroring `quickthumb lint`

Use it when you want a brandable announcement-card template whose layout survives copy changes, or as a reference spec for LLM-generated layouts.

### `investor_deck.py`

Output: `investor_deck.html` and `investor_deck.pptx`

Builds a dark investor-style deck with staged text, metric cards, and chart-like visuals:

- HTML export for browser playback of slide transitions and layer animations
- PPTX export for editable presentation handoff
- Shared composition code that keeps the browser and PowerPoint outputs aligned

Use it when you want a realistic animated deck example that exercises both HTML and PPTX output from the same source.

### `product_hype_reel.py`

Output: `product_hype_reel.gif`, `product_hype_reel.mp4`, and `product_hype_reel.webm`

Builds a Korean-style vertical (1080x1920) three-slide app-launch teaser and exports it as a self-playing animation with a soundtrack:

- Native-register Korean (Hangul) copy set in Pretendard — the typeface behind most current Korean tech/startup product design (Toss, Naver, Danggeun, ...) — bundled locally per weight under `assets/fonts`, so rendering needs no network access
- A K-style promo palette (hot pink → violet) with sparkle-star and "신규 출시" pill-badge accents, and tight negative letter-spacing on display headlines for the native "premium Pretendard" look
- Per-layer entrance animations (`Box`, `Wipe`, `Fade`, `Dissolve`, `Wheel`) staggered with `with_previous`/`after_previous`
- Slide transitions (`Push`, `Zoom`) rendered as real frames through the raster pipeline, with cuts locked to the soundtrack's 128 BPM tempo via `advance_after` so every slide change lands on a downbeat instead of drifting against the music
- The bytes-returning tunable export API — `deck.to_gif(...)`, `.to_mp4(...)`, `.to_webm(...)`
- A looping soundtrack (`assets/audio/hype_beat.wav`, a procedurally generated synth-pop loop) muxed into the MP4/WebM output via `soundtrack=`
- Graceful fallback when `ffmpeg` isn't installed (GIF still renders; MP4/WebM are skipped with a message) and when the soundtrack asset is missing (both raise `QuickthumbError` subclasses)

Use it when you want a shareable, self-playing GIF or video clip (Reels/TikTok/Stories) instead of a static thumbnail, or as a reference for the animated export API, beat-synced editing via `advance_after`, and MP4/WebM audio.

## Assets and Fonts

The example scripts set:

- `QUICKTHUMB_FONT_DIR` to `assets/fonts`
- `QUICKTHUMB_DEFAULT_FONT` to `Roboto`

They also use bundled example images from `assets/images`.

The JSON-first examples use repo-relative asset paths inside their checked-in JSON specs. The companion Python scripts change into the repo root before rendering so the examples stay runnable from any working directory.

The launch announcement example renders SVG layers, so install `quickthumb[svg]` (cairosvg) to run it locally.

The podcast promo example additionally requires network access because it fetches remote images and a remote webfont at render time. It also uses `remove_background=True`, so install `quickthumb[rembg]` if you want to run it locally.

The product hype reel example needs the `ffmpeg` binary on `PATH` for the MP4/WebM outputs (the GIF still renders without it). Its Pretendard fonts (`assets/fonts/Pretendard-*.woff2`) and soundtrack (`assets/audio/hype_beat.wav`, a procedurally generated synth-pop loop) are both bundled with the repo, so rendering it needs no network access.

## Extending These Examples

Common edits that are safe to make:

- Replace the background image path or URL
- Swap headline copy and highlight colors
- Change the canvas size or aspect ratio
- Add `canvas.image(...)` for logos, cutouts, or subject overlays
- Export as JPEG or WebP instead of PNG
