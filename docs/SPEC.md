# Documentation Website Spec

## Goal

Build a dedicated documentation website for QuickThumb using MkDocs Material.
The site replaces reliance on repo markdown files as the primary reference and targets two audiences:
human developers and AI agents generating QuickThumb specs.

## Framework

- **MkDocs Material** — best-in-class Python library docs, zero-config search, responsive layout.
- Source lives in `docs/` directory (already exists).
- Config at repo root: `mkdocs.yml`.
- Deployed via GitHub Pages (`gh-pages` branch), triggered by a GitHub Actions workflow.

## Site Structure

```
docs/
├── index.md                    # Landing page — gallery, tagline, install, quick start
├── getting-started.md          # Step-by-step first thumbnail walkthrough
├── installation.md             # pip/uv install, optional extras (rembg), env vars
├── concepts.md                 # Canvas model, layer order, composition, JSON round-trip
├── api/
│   ├── index.md                # API overview / quick reference table
│   ├── canvas.md               # Canvas creation and export methods
│   ├── background.md           # Background layer
│   ├── text.md                 # Text layer, TextPart, rich text
│   ├── image.md                # Image layer
│   ├── shape.md                # Shape layer
│   ├── outline.md              # Outline layer
│   ├── effects.md              # Stroke, Shadow, Glow, Filter, Background effect
│   └── enums.md                # BlendMode, FitMode, Align, gradients
├── json-schema.md              # Full JSON schema + AI agent usage patterns
├── cookbook/
│   ├── index.md                # Gallery of all examples with output images
│   ├── youtube-thumbnail.md    # YouTube thumbnail walkthrough
│   ├── instagram-card.md       # Instagram / social news card
│   ├── podcast-promo.md        # Podcast promo card
│   ├── shorts-cover.md         # Shorts / vertical cover
│   ├── ai-workflow.md          # JSON-first AI agent workflow
│   └── webfonts-rembg.md       # Remote images, webfonts, background removal
├── faq.md                      # Gotchas, troubleshooting, common errors
└── changelog.md                # Release history (manual, not auto-generated)
```

## Design Principles

- **Example-first**: every page opens with a rendered output image or code sample before any prose.
- **Scannable**: short paragraphs, parameter tables, and code blocks over long explanations.
- **AI-readable**: JSON examples are complete and valid so LLMs can use them as few-shot references.
- **No duplication**: API reference is the single source of truth; README links here rather than duplicating.

## MkDocs Material Features to Enable

- `navigation.tabs` — top-level tabs for Docs / API / Cookbook
- `navigation.sections` — collapsible sidebar sections
- `navigation.top` — back-to-top button
- `search.suggest` + `search.highlight`
- `content.code.copy` — copy button on every code block
- `content.tabs` — tabbed content (Python vs JSON examples side by side)
- Syntax highlighting via Pygments (included)
- Admonitions (`note`, `tip`, `warning`) for gotchas

## Deployment

- GitHub Actions workflow: `.github/workflows/docs.yml`
- Trigger: push to `main` branch
- Command: `mkdocs gh-deploy --force`
- Requires no extra secrets; uses `GITHUB_TOKEN` with `contents: write` permission.

## Dependencies (dev only)

```
mkdocs-material>=9.0
```

Added to `[dependency-groups]` in `pyproject.toml` under a `docs` group.
