## Tasks

### P0 — Critical / Quick Wins

- [DONE] Export `RenderingError` from `__init__.py` so users can `from quickthumb import RenderingError`
- [DONE] Raise `ValidationError` when `canvas.background()` is called with no `color`, `gradient`, or `image`
- [DONE] Remove dead `_get_style_string` method in `canvas.py` (defined but never called)

### P1 — High Impact Features

- [DONE] Rich text word-wrapping: auto-wrap `list[TextPart]` content when `max_width` is set (currently only plain string content wraps)
- [DONE] Long-word overflow: truncate or warn when a single word exceeds `max_width` in `_wrap_text`
- [DONE] Configurable font cache directory via `QUICKTHUMB_FONT_CACHE_DIR` env var (currently hardcoded to `/tmp`)

### P1 — Planned Features (see SPEC.md)

#### CLI (`quickthumb[cli]`)

- [DONE] Create `quickthumb/cli.py` with `click`; add `quickthumb[cli]` optional extra in `pyproject.toml`
- [DONE] Implement `quickthumb render <spec.json>` with `-o`, `--format`, `--quality` flags
- [DONE] Implement `--var KEY=VALUE` template variable substitution in the `render` subcommand
- [DONE] Add `quickthumb watch <spec.json>` subcommand using `watchfiles` (`quickthumb[cli]`)
- [DONE] Wire up exit codes: 0 success, 1 `ValidationError`, 2 `RenderingError`

#### Template System

- [DONE] Implement `Canvas.from_template(spec_or_path, variables={})` with `$var` / `${var}` string substitution
- [DONE] Raise `ValidationError` on unresolved placeholders before JSON parsing
- [DONE] Add `Canvas.register_template(name, path)` and `Canvas.unregister_template(name)` registry
- [DONE] Create `quickthumb/templates/` directory with starter templates: `youtube-16x9`, `instagram-square`, `twitter-card`, `og-image`

#### Gradient / Image-Filled Text (Knockout Text)

- [DONE] Add `TextFillImage` model with `path` and `fit` fields and `type: Literal["image"]` discriminator
- [DONE] Add `fill` parameter to `TextLayer` accepting `LinearGradient`, `RadialGradient`, or `TextFillImage`
- [DONE] Add `fill` parameter to `TextPart` for per-segment fill overrides
- [DONE] Implement knockout rendering: render glyphs as alpha mask, composite fill through mask
- [DONE] Ensure existing effects (Stroke, Shadow, Glow) apply to the filled text shape
- [DONE] Add JSON round-trip support using `type` discriminators (`linear_gradient`, `radial_gradient`, `image`)

#### Noise / Grain Effect

- [DONE] Add `Grain` effect model: `intensity`, `monochrome`, `blend_mode`, `opacity` fields with `type: "grain"` discriminator
- [DONE] Add `Grain` to `BackgroundEffect` and `ImageEffect` unions
- [DONE] Implement grain rendering using Pillow only (no NumPy)
- [DONE] Add JSON round-trip for per-layer `Grain` effect

### P2 — Docs & Discoverability

- [TODO] Homepage headline: make the AI/JSON workflow angle front and center (currently buried)
- [TODO] Add "Common LLM Mistakes" section to the JSON schema page (invalid hex, wrong position format, unsupported effects, etc.)
- [TODO] Add "Why not X" section: brief comparison vs raw Pillow and html2image to help developers justify the dependency
- [DONE] Add community entry point: link to GitHub issues/discussions for bug reports and questions

### P1 — CLI Hardening (from code review)

- [DONE] CLI `render`: catch `FileNotFoundError` / `PermissionError` from `spec.read_text()` and exit with code 1
- [DONE] CLI `render`: catch `json.JSONDecodeError` from `Canvas.from_json()` and exit with code 1
- [DONE] `_substitute_vars`: raise `ValidationError` on unresolved `$VAR` / `${VAR}` placeholders (currently passes them through silently)
- [DONE] Guard CLI entrypoint import: print a helpful message and exit if `typer` is not installed instead of crashing with `ImportError`
- [DONE] CLI `render`: validate `--var` entries contain `=`; raise a clear error when `--var keyonly` is passed (currently silently maps to empty string)
- [DONE] CLI `render`: replace bare `except Exception` with `except (RenderingError, OSError)` to avoid masking real bugs
- [DONE] CLI `render`: validate `--quality` is in `1–95` range (`typer.Option(..., min=1, max=95)`)
- [DONE] CLI `render`: validate `--format` is one of `PNG`, `JPEG`, `WEBP`; reject unknown values early

### P2 — Font Cache Hardening (from code review)

- [DONE] Use `tempfile.gettempdir()` instead of hardcoded `"/tmp"` as the default font cache dir (fixes Windows compatibility)
- [DONE] Validate downloaded font content before writing to cache (currently writes arbitrary data from any URL)
- [DONE] Call `os.makedirs(cache_dir, exist_ok=True)` before writing cached font; `QUICKTHUMB_FONT_CACHE_DIR` pointing to a non-existent dir currently crashes with `FileNotFoundError`

### P2 — CLI Polish (from code review)

- [DONE] Rename `format` parameter to `fmt` or `output_format` internally — currently shadows Python's built-in `format()`
- [DONE] Widen typer version pin from `>=0.24.1,<0.25.0` to `>=0.24.1,<1.0` to avoid unnecessary resolver conflicts

### P3 — Lower Priority

- [DONE] Fix color tuple JSON round-trip: `BackgroundLayer.color` accepts RGB tuples but they break `to_json()` / `from_json()`
- [TODO] Font metadata reading: use `fonttools` to read font weight/style from file metadata instead of relying on filename parsing
- [TODO] Split `canvas.py` (currently 2466 lines) into smaller modules before it becomes a maintenance burden

## Handoff Notes

### canvas.py split — IN PROGRESS (branch: `claude/refactor-canvas-SvPD9`)

**Goal:** Split `canvas.py` (2968 lines) into focused modules for readability and to
prepare the rendering pipeline for future slide/video reuse.

**Target structure:**

| File | Purpose | Status |
|------|---------|--------|
| `quickthumb/_effects.py` | Pure functions: color, opacity, filters, grain, gradients, blending, image loading, image-layer effects (shadow/stroke/glow), coordinate/padding parsing | **DONE** |
| `quickthumb/_text_renderer.py` | `TextRenderer(width, height)` class — all ~80 text rendering methods | **NOT STARTED** |
| `quickthumb/_renderer.py` | `CanvasRenderer(width, height)` class — background/image/shape/outline rendering, delegates to `TextRenderer` | **NOT STARTED** |
| `quickthumb/canvas.py` | Canvas class — builder API + serialization only; `render()` / `to_base64()` / `to_data_url()` delegate to `CanvasRenderer` | **NOT STARTED** |

**Design decisions:**
- `_effects.py` exports **module-level pure functions** (no class, no state).
- `TextRenderer.__init__(width, height)` stores canvas dimensions needed for percentage coordinate parsing and text layout.
- `CanvasRenderer.__init__(width, height)` stores dimensions; composes a `TextRenderer` internally.
- `Canvas.render()` does: `CanvasRenderer(self.width, self.height).render(self._layers)`.
- Public API of `Canvas` is **100% unchanged** — no breaking changes.
- `_VALID_FONT_MAGIC`, `_download_and_cache_font`, `_load_font`, `_load_font_variant` live in `TextRenderer`.
- `_remove_background` lives in `CanvasRenderer` (image layer concern).

**What `_text_renderer.py` needs to contain** (extract from `canvas.py` as-is, just change `self._method()` → internal calls):
- `TextRenderer.render(image, layer)` — was `Canvas._render_text_layer`
- All `_render_simple_text`, `_render_rich_text`, `_render_multiline_text`, etc.
- All `_resolve_*` helpers (color, size, bold, italic, weight, font_name, line_height, letter_spacing, fill)
- All `_wrap_text`, `_measure_text_bounds`, `_calculate_*`, `_get_*` text helpers
- All `_draw_*` text drawing methods
- All `_render_glow`, `_render_shadow`, `_render_background`, `_render_background_box`
- All `_auto_scale_*` methods
- `_download_and_cache_font`, `_load_font`, `_load_font_variant`
- Import `parse_color`, `apply_opacity_to_color`, `parse_coordinate`, `parse_padding`, `create_linear_gradient`, `create_radial_gradient`, `load_and_fit_image`, `is_url` from `._effects`

**What `_renderer.py` needs to contain:**
- `CanvasRenderer.__init__(width, height)` — creates `self._text = TextRenderer(width, height)`
- `CanvasRenderer.render(layers) -> Image.Image` — main dispatch loop (was `_render_to_image`)
- `_render_background_layer`, `_create_layer_image`
- `_render_image_layer`, `_render_shape_layer`, `_render_outline_layer`, `_render_custom_layer`
- `_remove_background`
- Imports image-effect functions from `._effects` (apply_opacity, apply_filter, apply_grain, apply_blend_mode, apply_image_shadow, apply_image_stroke, apply_image_glow, apply_image_alignment, apply_border_radius, resize_image, load_and_fit_image, parse_color, apply_opacity_to_color, parse_coordinate, is_url, load_image_from_url, create_linear_gradient, create_radial_gradient)

**What stays in `canvas.py`:**
- `Canvas.__init__`, `Canvas.layers` property, `Canvas.from_aspect_ratio`
- All builder methods: `background()`, `text()`, `image()`, `shape()`, `outline()`, `custom()`, `grain()`
- Serialization: `to_json()`, `from_json()`, `from_template()`, `to_base64()`, `to_data_url()`, `render()`
- `_validate_image_paths()`, `_detect_format()`, `_convert_for_format()`, `_build_save_kwargs()`, `_save_to_file()`
- Registry class methods: `register_layer_fn`, `unregister_layer_fn`, `register_template`, `unregister_template`
- `render()` body becomes: `CanvasRenderer(self.width, self.height).render(self._layers)`
- `_is_url` can be replaced by importing `is_url` from `._effects`
- **Remove** all `_render_*`, `_apply_*`, `_create_*`, `_draw_*`, `_measure_*`, `_calculate_*`, `_get_*`, `_wrap_*`, `_load_*`, `_blend_*`, `_generate_*`, `_resolve_*`, `_parse_*` rendering internals

**Imports canvas.py will need after refactor:**
```python
from quickthumb._effects import is_url
from quickthumb._renderer import CanvasRenderer
```

**After completing the split**, mark the P3 task `[DONE]` and run:
```bash
uv run pytest
```
All tests should pass without modification (public API unchanged).
