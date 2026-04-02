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

-
-
