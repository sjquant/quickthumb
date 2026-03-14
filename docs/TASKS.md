# Documentation Website Tasks

Tasks are ordered by dependency. Complete them roughly top-to-bottom.

---

## Phase 1 — Scaffold

- [ ] Add `mkdocs-material` to `[dependency-groups.docs]` in `pyproject.toml`
- [ ] Create `mkdocs.yml` at repo root with site metadata, nav, theme, and plugins
- [ ] Create stub `docs/index.md` (landing page — gallery, tagline, install snippet, quick start)
- [ ] Verify `uv run mkdocs serve` starts without errors

## Phase 2 — Core Content Pages

- [ ] `docs/installation.md` — pip/uv install commands, optional `rembg` extra, env vars (`QUICKTHUMB_FONT_DIR`, `QUICKTHUMB_DEFAULT_FONT`)
- [ ] `docs/getting-started.md` — step-by-step walkthrough: create canvas → add background → add text → render → view result
- [ ] `docs/concepts.md` — canvas model, layer order, composition, JSON round-trip explanation
- [ ] `docs/faq.md` — gotchas and common errors lifted from DESIGN.md "Validation Rules and Gotchas" plus any new ones

## Phase 3 — API Reference

- [ ] `docs/api/index.md` — overview table: layer types, effect types, enums, export methods
- [ ] `docs/api/canvas.md` — `Canvas(w, h)`, `from_aspect_ratio()`, `render()`, `to_base64()`, `to_data_url()`, `to_json()`, `from_json()`
- [ ] `docs/api/background.md` — all parameters, notes, full example
- [ ] `docs/api/text.md` — `TextLayer` parameters, `TextPart` fields, rich text rules
- [ ] `docs/api/image.md` — all parameters, fit/align/blend notes, full example
- [ ] `docs/api/shape.md` — rectangle and ellipse, all parameters, full example
- [ ] `docs/api/outline.md` — parameters and example
- [ ] `docs/api/effects.md` — `Stroke`, `Shadow`, `Glow`, `Filter`, `Background` effect; which layers each supports
- [ ] `docs/api/enums.md` — `BlendMode`, `FitMode`, `Align`, `LinearGradient`, `RadialGradient`

## Phase 4 — JSON Schema + AI Workflow

- [ ] `docs/json-schema.md` — complete JSON schema with annotated example, AI prompt patterns (Python and JSON), recommended workflow

## Phase 5 — Cookbook / Examples

- [ ] `docs/cookbook/index.md` — gallery grid with all example output images and one-line descriptions
- [ ] `docs/cookbook/youtube-thumbnail.md` — two YouTube thumbnail walkthroughs (thumbnail_01, thumbnail_02)
- [ ] `docs/cookbook/instagram-card.md` — Instagram news card walkthrough
- [ ] `docs/cookbook/podcast-promo.md` — podcast / interview promo card walkthrough
- [ ] `docs/cookbook/shorts-cover.md` — shorts / vertical cover walkthrough (Python + JSON agent versions)
- [ ] `docs/cookbook/ai-workflow.md` — JSON-first AI agent workflow end-to-end (prompt → JSON → render)
- [ ] `docs/cookbook/webfonts-rembg.md` — remote images, webfont URLs, background removal

## Phase 6 — Changelog + Deployment

- [ ] `docs/changelog.md` — create initial changelog with current version (0.3.0) and key features
- [ ] `.github/workflows/docs.yml` — GitHub Actions workflow to deploy on push to `main` via `mkdocs gh-deploy`
- [ ] Update `pyproject.toml` `[project.urls]` Documentation URL to point to the GitHub Pages URL
- [ ] Update `README.md` to link to the new docs site instead of the repo README anchor
- [ ] Smoke-test the deployed site
