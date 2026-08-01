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
uv run python examples/ordinary_moments.py
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

- A local, full-bleed editorial portrait composed directly into the dark stage
- A webfont loaded from a URL for the show-title treatment
- A tonal gradient that protects copy contrast without boxing in the subject
- Restrained editorial typography and a single semantic accent

Use it when you want a podcast or interview promo that integrates photography without visible cutout edges or a disconnected image panel.

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
- Auto-layout `group` layers for the headline column and feature row, with zero hand-placed coordinates inside either text group
- An abstract alignment field that communicates reflow without imitating a dashboard UI
- A `star` primitive and decorative `svg` accent (requires `quickthumb[svg]`)
- Rich-text headline coloring through themed `TextPart` values
- `Grain` effect with a fixed seed for deterministic texture
- `canvas.diagnose()` before rendering, mirroring `quickthumb lint`

Use it when you want a brandable announcement-card template whose layout survives copy changes, or as a reference spec for LLM-generated layouts.

### `investor_deck.py`

Output: `investor_deck.html` and `investor_deck.pptx`

Builds a restrained, evidence-led 10-slide Series A narrative:

- HTML export for browser playback of slide transitions and layer animations
- `quickthumb serve examples/investor_deck.py` for live reload and `?presenter` mode
- Per-slide speaker notes visible only in the presenter dashboard
- A complete investment arc: thesis, problem, why now, workflow, product proof, traction, business model, market and GTM, defensibility, and team plus ask
- Explicit periods, definitions, and `Illustrative` provenance notes for every sample company claim
- One dark product-proof surface inside an otherwise neutral editorial system with a single semantic blue accent
- PPTX export for editable presentation handoff
- Shared composition code that keeps the browser and PowerPoint outputs aligned

Use it when you want a realistic investor narrative that exercises HTML, presenter notes, and editable PPTX output from the same source.

### `product_hype_reel.py`

Output: `product_hype_reel.gif`, `product_hype_reel.mp4`, `product_hype_reel.webm`,
`product_hype_reel.html`, and `product_hype_reel.pptx`

Builds a restrained vertical (1080x1920) 8-scene product film — hook → pain point → solution → three features → proof → CTA — and exports it as a 34.69-second narration-led animation:

- Eight distinct visual ideas instead of one repeated card template: rhythm trace, broken timeline, readiness field, live pulse, adaptive plan, streak grid, measured outcome, and one clear action
- English copy set in locally bundled Pretendard, with every supporting label at least 48px for phone-scale legibility
- One semantic blue accent on neutral stages, without glow, elevated cards, progress chrome, or per-scene rainbow colors
- Per-scene durations of 8–10 beats derived from the actual 3.41–4.29-second voiceovers, preserving every narration ending while reducing the original timeline
- Semantic `Cut`, `Fade`, and `Wipe` transitions that support the story instead of adding arbitrary motion variety
- `deck.diagnose()` before export, validating contrast, overflow, overlap, canvas bounds, and UI-safe placement before encoding
- The file-rendering animation API with GIF-specific `GifOptions`, plus the video-specific `VideoOptions` and bytes-returning `.to_mp4(...)` / `.to_webm(...)` variants
- Eight bundled voiceovers mixed above a quieter looping soundtrack via `VideoOptions(soundtrack=AudioTrack(...))`
- Graceful per-format fallback when an optional renderer is unavailable; one failed export does not suppress the remaining formats

Use it when you want a shareable, self-playing GIF or video clip (Reels/TikTok/Stories) instead of a static thumbnail, or as a reference for the animated export API, beat-synced editing via `advance_after`, and MP4/WebM audio.

### `ordinary_moments.py`

Output: `ordinary_moments.mp4`, `ordinary_moments.webm`, and `ordinary_moments_preview.gif`

Builds a 60-second horizontal Korean-language product film that argues one case — remaking the same video for every screen is the expensive part — across nine scenes: hook, cost, turn, three proofs, delivery payoff, resolution, and close.

- Five locally bundled Pexels clips with a checked-in provenance manifest, each reused only as a deliberate callback in a different frame
- One proof scene places the same second of one source in 16:9, 1:1, and 9:16 frames simultaneously, so `fit` and placement are demonstrated rather than described
- Timed caption cues that prove their own timing: a cue strip and a playhead cross each block at the moment its caption appears
- `AnimationSpec` motion tied to meaning — line-staggered entrances for repeated work, position-track playheads for timeline scenes, `Canvas.counter(...)` for cost and render progress
- A frosted `BackdropBlur` readout panel printing the film's real `speed`, `volume`, and `fade_out` values
- Pretendard for the Korean voice and Roboto for every functional readout, on a shared margin and type scale
- An accent colour introduced at the narrative turn and held back from the opening act
- Purposeful `Cut`, `Fade`, and `Wipe` transitions over a restrained Mixkit soundtrack loop that fades out on the close
- MP4/WebM exports of the full 60-second composition plus a silent GIF preview of the delivery scene

Use it when you want a production-style reference for combining footage, captions, audio, and editorial motion in a reproducible 16:9 composition.

## Assets and Fonts

The example scripts set:

- `QUICKTHUMB_FONT_DIR` to `assets/fonts`
- `QUICKTHUMB_DEFAULT_FONT` to `Roboto`

They also use bundled example images from `assets/images`.

The JSON-first examples use repo-relative asset paths inside their checked-in JSON specs. The companion Python scripts change into the repo root before rendering so the examples stay runnable from any working directory.

The launch announcement example renders SVG layers, so install `quickthumb[svg]` (cairosvg) to run it locally.

The podcast promo example uses a bundled editorial portrait and requires network access only for its display webfont.

The product hype reel example needs the `ffmpeg` binary on `PATH` for the MP4/WebM outputs (the GIF still renders without it). Its Pretendard fonts, voiceovers, and soundtrack are bundled with the repo, so rendering it needs no network access.

## Extending These Examples

Common edits that are safe to make:

- Replace the background image path or URL
- Swap headline copy and highlight colors
- Change the canvas size or aspect ratio
- Add `canvas.image(...)` for logos, cutouts, or subject overlays
- Export as JPEG or WebP instead of PNG
