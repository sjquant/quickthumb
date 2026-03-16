## Tasks

### P0 — Critical / Quick Wins
- [DONE] Export `RenderingError` from `__init__.py` so users can `from quickthumb import RenderingError`
- [DONE] Raise `ValidationError` when `canvas.background()` is called with no `color`, `gradient`, or `image`
- [DONE] Remove dead `_get_style_string` method in `canvas.py` (defined but never called)

### P1 — High Impact Features
- [DONE] Rich text word-wrapping: auto-wrap `list[TextPart]` content when `max_width` is set (currently only plain string content wraps)
- [DONE] Long-word overflow: truncate or warn when a single word exceeds `max_width` in `_wrap_text`
- [TODO] Configurable font cache directory via `QUICKTHUMB_FONT_CACHE_DIR` env var (currently hardcoded to `/tmp`)

### P1 — Planned Features (see SPEC.md)

#### CLI (`quickthumb[cli]`)
- [TODO] Create `quickthumb/cli.py` with `click`; add `quickthumb[cli]` optional extra in `pyproject.toml`
- [TODO] Implement `quickthumb render <spec.json>` with `-o`, `--format`, `--quality` flags
- [TODO] Implement `--var KEY=VALUE` template variable substitution in the `render` subcommand
- [TODO] Add `quickthumb watch <spec.json>` subcommand using `watchdog` (`quickthumb[cli,watch]`)
- [TODO] Wire up exit codes: 0 success, 1 `ValidationError`, 2 `RenderingError`

#### Template System
- [TODO] Implement `Canvas.from_template(spec_or_path, variables={})` with `$var` / `${var}` string substitution
- [TODO] Raise `ValidationError` on unresolved placeholders before JSON parsing
- [TODO] Add `Canvas.register_template(name, path)` and `Canvas.unregister_template(name)` registry
- [TODO] Create `quickthumb/templates/` directory with starter templates: `youtube-16x9`, `instagram-square`, `twitter-card`, `og-image`

#### Gradient / Image-Filled Text (Knockout Text)
- [TODO] Add `TextFillImage` model with `path` and `fit` fields and `type: Literal["image"]` discriminator
- [TODO] Add `fill` parameter to `TextLayer` accepting `LinearGradient`, `RadialGradient`, or `TextFillImage`
- [TODO] Add `fill` parameter to `TextPart` for per-segment fill overrides
- [TODO] Implement knockout rendering: render glyphs as alpha mask, composite fill through mask
- [TODO] Ensure existing effects (Stroke, Shadow, Glow) apply to the filled text shape
- [TODO] Add JSON round-trip support using `type` discriminators (`linear_gradient`, `radial_gradient`, `image`)

#### Noise / Grain Effect
- [TODO] Add `Grain` effect model: `intensity`, `monochrome`, `blend_mode`, `opacity` fields with `type: "grain"` discriminator
- [TODO] Add `Grain` to `BackgroundEffect` and `ImageEffect` unions
- [TODO] Implement grain rendering using Pillow only (no NumPy)
- [TODO] Add `canvas.grain(intensity, monochrome, blend_mode, opacity)` builder that appends a `GrainLayer`
- [TODO] Add `GrainLayer` model and rendering for full-canvas grain compositing
- [TODO] Add JSON round-trip for both per-layer `Grain` effect and top-level `GrainLayer`

### P2 — Docs & Discoverability
- [TODO] Homepage headline: make the AI/JSON workflow angle front and center (currently buried)
- [TODO] Add "Common LLM Mistakes" section to the JSON schema page (invalid hex, wrong position format, unsupported effects, etc.)
- [TODO] Add "Why not X" section: brief comparison vs raw Pillow and html2image to help developers justify the dependency
- [TODO] Add community entry point: link to GitHub issues/discussions for bug reports and questions

### P3 — Lower Priority
- [TODO] Fix color tuple JSON round-trip: `BackgroundLayer.color` accepts RGB tuples but they break `to_json()` / `from_json()`
- [TODO] Font metadata reading: use `fonttools` to read font weight/style from file metadata instead of relying on filename parsing
- [TODO] Split `canvas.py` (currently 2466 lines) into smaller modules before it becomes a maintenance burden

## Handoff Notes
-
-
