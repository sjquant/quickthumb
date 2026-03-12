# QuickThumb TODO

## ✅ Completed

### Core API & Models

- ✅ Canvas creation (explicit dimensions, aspect ratios)
- ✅ Background layers (solid colors, linear/radial gradients, images, blend modes, opacity, brightness adjustment)
- ✅ Text layers (fonts, positioning, alignment, bold/italic, letter spacing, line height, word wrapping, auto-scale)
- ✅ Outline decoration layer
- ✅ JSON serialization/deserialization
- ✅ Method chaining API

### Rendering Engine

- ✅ Output formats: PNG, JPEG, WebP (with quality parameter)
- ✅ Gradients: Linear (angle-based, multi-stop) and Radial (configurable center)
- ✅ Image backgrounds (URL support, fit modes: cover/contain/fill)
- ✅ Blend modes: MULTIPLY, OVERLAY, SCREEN, DARKEN, LIGHTEN, NORMAL
- ✅ Text positioning with percentages (e.g., `position=("50%", "50%")`)
- ✅ Base64 encoding and data URL generation

### Text Effects

- ✅ Stroke, Shadow (with blur), Glow (outer glow), Background (with padding and border radius)
- ✅ Rich text with `TextPart` (per-segment styling)
- ✅ Rotation support for text layers (simple and rich text)

### Font System

- ✅ CSS-style `font-weight` support (100-900 numeric, "thin"/"bold"/"black" named)
- ✅ Automatic font file mapping with fallback to closest weight
- ✅ WebFont support (load from URLs, cached to /tmp)

### Image Layers

- ✅ Image overlay with position (pixels/percentages), sizing (aspect ratio preserved), opacity, rotation, and alignment
- ✅ URL and local path support, JSON serialization, method chaining
- ✅ Background removal for image layers via `remove_background=True` (requires `quickthumb[rembg]`)
- ✅ `effects` list on image layers (mirrors TextLayer), currently supports `Shadow`, `Stroke`, `Glow`, and `Filter`

---

## 🚧 TODO

### High Priority

- ✅ Shape layers — Rectangle and ellipse primitives with fill color, stroke, border radius, opacity, rotation, and alignment. API: `canvas.shape(shape="rectangle", position=(x, y), width=300, height=200, color="#FF5733", stroke_color="#000000", stroke_width=2, border_radius=10)`
- ✅ Blur/filter effects on background layers — `blur` (Gaussian blur radius), `contrast`, and `saturation` adjustments. API: `canvas.background(image="...", blur=10, contrast=1.2, saturation=0.8)`

### Medium Priority

- ✅ Rounded corners on image layers — Clip image to rounded rectangle mask. API: `canvas.image(..., border_radius=20)`
- ✅ Drop shadow on image layers — Cast shadow from image alpha shape. API: `canvas.image(..., effects=[Shadow(offset_x=5, offset_y=5, color="#000000", blur_radius=10)])`

### Medium Priority (Image Effects)

- ✅ Image content filters — `blur`, `brightness`, `contrast`, `saturation` on image overlay layers via `effects=[Filter(...)]`, matching background-layer filter capabilities. API: `canvas.image(..., effects=[Filter(blur=5, brightness=0.8, contrast=1.2, saturation=0.5)])`

### Medium Priority (Image Layer Composition)

- ✅ Image layer fit modes — Add `fit` for overlays (`fill`/`contain`/`cover`) when both `width` and `height` define a target box. API: `canvas.image(..., width=300, height=200, fit="cover")`
- ✅ Image layer blend modes — Add `blend_mode` on image overlays (`multiply`, `overlay`, `screen`, `darken`, `lighten`, `normal`) for non-alpha compositing. API: `canvas.image(..., blend_mode="multiply", opacity=0.8)`

### Low Priority

- ✅ Custom layer hook — Users can inject arbitrary Pillow drawing logic as a layer via `canvas.custom(fn)` where `fn` receives the `PIL.Image.Image` and draws onto it directly, e.g. `canvas.custom(lambda img: ImageDraw.Draw(img).polygon([...], fill="#FF0000"))`

### Documentation, Examples, and Adoption

#### README Overhaul

- [x] Rewrite `README.md` so all code snippets match the current API exactly
- [x] Fix outdated/invalid examples in `README.md` (JSON schema, gradients, `canvas.image(...)`, `render(...)`, etc.)
- [x] Add a gallery-first introduction with rendered example images near the top
- [x] Reposition QuickThumb for AI-assisted thumbnail generation, not just generic image composition
- [x] Add an "AI-friendly workflows" section with prompt patterns for generating QuickThumb Python/JSON
- [x] Document environment variables such as `QUICKTHUMB_FONT_DIR` and `QUICKTHUMB_DEFAULT_FONT`
- [x] Add a clearer feature matrix covering text effects, image effects, shapes, rich text, filters, webfonts, and export helpers

#### API Reference Cleanup

- [x] Update `DESIGN.md` to reflect the actual implemented API surface
- [x] Remove stale examples from `DESIGN.md` that no longer run against the codebase
- [x] Expand `DESIGN.md` into a reliable reference for layer types, effects, enums, JSON schema, and validation rules
- [x] Add an explicit "gotchas" section (e.g. `weight` vs `bold`, `auto_scale` requires `max_width`, custom layers are not JSON-serializable, webfont styling flags are ignored)

#### Example Expansion

- [x] Expand `examples/README.md` so it documents every example currently shipped
- [ ] Add more end-to-end examples for real thumbnail use cases:
- [ ] YouTube talking-head thumbnail
- [ ] YouTube reaction / commentary thumbnail
- [ ] YouTube tutorial / explainer thumbnail
- [x] Instagram / X / social news card
- [ ] Podcast / interview promo card
- [x] Shorts / vertical cover design
- [x] Add example outputs/screenshots for every example script
- [x] Add examples showing JSON-first workflows for AI agents that emit specs instead of Python
- [ ] Add examples showing remote image URLs, webfont URLs, and background removal workflows

#### Package Discoverability

- [x] Improve PyPI metadata in `pyproject.toml`
- [x] Add project URLs (homepage, repository, issues, documentation)
- [x] Add keywords related to thumbnails, social media, AI content creation, Pillow, image generation
- [x] Add trove classifiers so the package is easier to discover and trust
- [x] Align package description/tagline with the actual product direction

#### Documentation Website

- [ ] Create a dedicated documentation website instead of relying only on repo markdown files
- [ ] Set up a docs framework suitable for Python library docs (for example, MkDocs Material or similar)
- [ ] Publish documentation sections for:
- [ ] Getting started
- [ ] Installation and optional extras
- [ ] Core concepts (canvas, layers, effects, composition order)
- [ ] API reference
- [ ] JSON schema / AI agent usage
- [ ] Cookbook / examples gallery
- [ ] FAQ / troubleshooting
- [ ] Add visual comparison pages inspired by high-quality Python documentation sites
- [ ] Make the docs site fast to scan, example-heavy, and easy for both humans and AI agents to follow
