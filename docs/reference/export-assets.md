---
description: Reference for samples, assets, and reproducibility in quickthumb.
---

# Samples, assets, and reproducibility

[Export reference](../exports.md) · [Choose an output format](../output-guide.md)

## Canonical samples

`sample()` returns the renderer-independent reference that exports are compared against, as a JSON-serializable `FrameSequence`. Canvas and Deck share the same contract, and a canvas produces the same observations as a one-slide deck containing it.

```python
still = canvas.sample()                         # settled frame(s), as PNG/PDF/PPTX draw them
timed = deck.sample(fps=10)                     # uniform grid over the whole animated timeline
probe = deck.sample([0.0, 1.25, 4.0], hold=2.0) # explicit instants, ascending
```

- **Frames.** Each `CanonicalFrame` holds `width * height` pixels as raw 8-bit RGBA (row-major from the top-left, sRGB, straight alpha), base64-encoded in `data`, plus the `sha256` of those bytes. `index` is the frame's position in the sequence and `slide` the page it shows. A frame whose digest or dimensions do not match its data is rejected when it is loaded.
- **Still captures** (`capture="still"`) hold one frame per page in slide order, at each page's own size, with transparency preserved. `time` is `None`, `duration` is `0`, and `timeline` is empty.
- **Timeline captures** (`capture="timeline"`) observe the timeline that animated WebM/MP4 exports play: transitions, Morph, layer animations, narration-driven slide durations, and a settled hold of `hold` seconds (default 3) for pages without an explicit duration. Frames are ordered by ascending `time` in seconds, share the first slide's size, and are composited onto the opaque `matte` (default black), which is reported as `#RRGGBB`. Deck GIF export currently ignores explicit and narration slide durations, so it matches this timeline only for decks without them.
- **Sampling.** `fps=N` (at most 120) observes every instant `k / N` before `duration`; explicit times must be ascending, and times at or past `duration` show the final settled frame. One capture observes at most 100,000 instants; a larger explicit list or fps grid is rejected with a `ValidationError` before any frame renders. This grid is an observation schedule, not an exporter's frame schedule: exporters sample each span on their own frame grid, and stretch a slide shorter than one frame to a full frame.
- **Timing.** `duration` is the exact timeline length and never depends on `fps` or on the requested instants. Each `TimelineSegment` gives a slide's absolute `start`, `transition_end`, `animation_end`, and `end`, rounded to nanoseconds; a slide is on screen over `[start, end)`, so a boundary instant belongs to the incoming slide.
- **Memory.** A capture whose distinct frames would exceed 768 MiB of raw RGBA is rejected with a `ValidationError`, before any frame renders when every page of a still capture, or one frame of a timeline capture, already exceeds it; request fewer instants, a lower `fps`, a shorter `hold`, or a smaller document.
- **Environment.** `sample()` and `export()` report quickthumb, Pillow and FreeType versions, the text layout engine (`basic` or `raqm`), available RAQM/HarfBuzz/FriBidi versions, and the FFmpeg version for documents with video layers. Sampling video without a working FFmpeg raises `RenderingError` before any frame renders. `environment.fonts` reports the actual font face bytes selected by that operation; the asset manifest separately describes authored references.

## Render reproducibility

Font family names and `QUICKTHUMB_DEFAULT_FONT` depend on the machine's font
search path. Inspect the selected faces rather than treating those names as
portable identifiers:

```python
capture = canvas.sample()
for font in capture.environment.fonts:
    print(font.source, font.sha256, font.variations)
```

Each face has its resolved file path (or `pillow:default`), SHA-256 and applied
variable coordinates keyed by the font's axis names. The hash identifies the
font bytes. Pillow's embedded
face reports no hash if its bytes are unavailable. Paths are diagnostic: compare
hashes and coordinates across machines. Only faces loaded for the current
operation are reported; unused named fonts and faces from earlier operations
are excluded.

Remote and Google fonts load from content-addressed copies of their resolved
bytes, so another document refreshing the original URL does not change a
prefetched face. These copies live in the asset cache and follow its caller-owned
cleanup lifecycle. Keep local input files unchanged during an operation.

For repeatable canonical raster output, use identical document data, input asset
bytes, selected fonts and variable coordinates, rendering options and environment;
seed procedural effects where supported. Different font, shaping or rasterizer
versions can change layout and edge pixels. This report explains those inputs;
it does not promise exact pixels across platforms or native-output viewers.
Use format-specific fidelity tolerances when comparing such outputs.

## Remote assets and caching

`render()` and `export()` download remote images, SVGs, text fills, and fonts into a shared cache, and `export()` returns an `asset_manifest` describing every asset it used. `prefetch_assets()` is optional: it does the same downloads up front and returns the manifest without rendering, so you can catch network failures or stale entries before a long export, or warm the cache for offline renders. Each `AssetManifestEntry` has the `source` as written, its semantic `asset_type`, a `status`, and whatever identity it has: `source_key` (canonical URL), `cache_key` and `cache_path`, `content_hash` (SHA-256 of the bytes used), and `fetched_at` (UTC time of the download).

| `status` | Meaning |
| --- | --- |
| `local` | An existing local file. |
| `missing` | A local path that does not exist. |
| `network` | Downloaded now and written to the cache. |
| `fresh` | Read from a cache entry within `max_age` (always, when no `max_age` is set). |
| `stale` | Read from an expired cache entry, or while offline, because it could not be refreshed. `stale_reason` explains why. |
| `unresolved` | A remote reference that has not been resolved yet. |

The cache is controlled by environment variables:

- `QUICKTHUMB_ASSET_CACHE_DIR`: cache directory (default: the system temp directory).
- `QUICKTHUMB_ASSET_MAX_AGE`: seconds after which a cached entry is refreshed from the network. When the refresh fails, the old bytes are used and reported as `stale`. Unset means cached entries never expire.
- `QUICKTHUMB_ASSET_OFFLINE=1`: never make network requests. Cached entries are used, and expired ones are reported as `stale`.

## Ownership and reuse

Keep the same `Canvas` or `Deck` to reuse resolution across `prefetch_assets()`,
`sample()`, and exports. Each canvas retains its first remote resolution result
and status; a deck uses its slides' results. Remote images, text fills, and SVGs
render from these retained bytes. Remote fonts, including Google fonts, load
from content-addressed copies of the resolved bytes, so another document's URL
refresh does not change a prefetched face. Keep those cache files available
through sampling and export. Construct a new document to resolve the same
reference again under the current cache policy.

`PrefetchResult` and `asset_manifest` are JSON-safe reports, not resource handles.
Saving or loading their JSON does not transfer bytes or preload another document.
A new document can reuse the persisted cache and reports `fresh` when its entry
is usable. Local image, font, video, and audio paths remain caller-owned files:
keep them available and unchanged through sampling or export; prefetch does not
freeze or copy them. Video and audio sources are not downloaded by prefetch;
remote video is read by FFmpeg when needed and is outside this cache contract.
Generated content without a file/URL reference has no external asset entry.

The caller owns the cache directory and its cleanup. Quickthumb atomically writes
remote cache files and metadata but does not automatically evict them. Remove
unused entries only when documents and export workers are no longer using that
cache; existing manifests are observations, not guarantees that their
`cache_path` still exists. No explicit document close is required for the
in-memory remote results: they are released with the document.

When neither a usable cache entry nor a network response exists, resolution raises `RenderingError` naming the source, the cause, and the cache directory it searched. To refuse stale inputs, check the manifest before rendering:

```python
prefetched = canvas.prefetch_assets()
stale = [entry for entry in prefetched.asset_manifest if entry.status == "stale"]
if stale:
    raise SystemExit(f"stale assets: {[(e.source, e.stale_reason) for e in stale]}")
```

## Asset and plugin lifecycle fixtures

The shared font/texture scenarios in `tests/test_asset_cache.py` use a private
plugin registry, a repository TTF and generated image bytes served by a temporary
localhost HTTP server. They exercise public Canvas/Deck operations and cache
environment settings. A controlled standard clock advances expiry without
sleeping or editing cache files or metadata. No public network service or
platform-specific pixel snapshot is required.

| Scenario | Observable evidence | Regression check |
| --- | --- | --- |
| Network → fresh new document → expired refresh | Resolution status, fetched time, changed content hashes, actual font identity and decoded PNG pixels; original documents retain their resolved bytes | `test_combined_resources_refresh_only_for_new_expired_documents` (`canvas`, `deck`) |
| Expired cache while offline | Both resources report `stale` with source, hash, fetch time and offline/max-age reason before plugin execution or output; a caller proceeding gets the original RGBA/font bytes without requests | `test_combined_offline_stale_evidence_precedes_optional_rendering` (`canvas`, `deck`) |
| Cold offline font or plugin texture | Public prefetch identifies the later slide, source URL and cache directory; plugin texture errors also identify the layer/asset path. No callback or file write occurs | `test_combined_cold_offline_failure_identifies_later_slide_resource` (`font`, `texture`) |
| Prefetched resources across raster and native document output | Canvas/Deck raster agreement, actual font SHA, asset manifest, native SVG text and exact plugin PNG fallback | `test_prefetched_font_and_private_plugin_keep_shared_export_evidence` |
| Missing declared plugin dependency | Escaped JSON Pointer, layer identity and prewrite failure | `test_plugin_declared_missing_assets_fail_before_output_or_callback` |
| Plugin native match, tolerated difference, mismatch or unsupported target | Actual local SVG comparison and adopted native/PNG representation; explained fallback and strict rejection | `tests/test_plugin_svg.py`, `test_plugin_document_fallback_reports_and_preserves_output` in `tests/test_plugin_runtime.py` |
| Default, family, file and variable fonts | Actual selected face hashes and applied coordinates in sample/export environments | Font identity cases in `tests/test_canonical_sampling.py` |

Stale refusal is a caller decision using the returned manifest, as shown above;
there is no automatic refuse-stale export flag. The offline fixture verifies
that evidence is available before any plugin callback or destination change,
then separately verifies the caller's choice to render with those stale bytes.
Cold misses fail rather than substituting a font or empty plugin texture.

Run `uv run --locked pytest tests/test_asset_cache.py tests/test_plugin_runtime.py
tests/test_plugin_svg.py tests/test_canonical_sampling.py --no-cov -q`.
These files are included in the existing automated `pytest tests/` quality job.
Named scenarios and parameter IDs identify the resource/document failure;
expected hashes are computed from the controlled source bytes and rendered
samples are compared in the same recorded font/render environment. This does
not promise identical font pixels across machines or native viewers.
