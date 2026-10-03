# Animated export benchmarks

Run from the repository root after the locked setup in `CONTRIBUTING.md`:

```bash
uv run --locked python -m benchmarks.animated_export --json /tmp/baseline.json
```

The command prints one table, including CPU, Python, Pillow, FreeType, text
layout, FFmpeg, platform, and source commit. Every numeric cell is the median
of **three fresh subprocesses**. Linux and macOS are supported; the memory
measurement uses `resource.getrusage`. FFmpeg and ffprobe must be available for
MP4/WebM. A failed export fails the command rather than becoming a skipped row.
No extra Python dependencies are needed.

## Fixed workload and measurement boundaries

- The complete eight-scene `examples/product_hype_reel.py` composition is used
  at its original 1080×1920 size, with its checked-in fonts and narration
- Three 256×192 synthetic scenes slowly translate, rotate, and scale an
  asymmetric white marker on black over two seconds
- The default export rate is 12 fps. GIF uses the example's bounded 432×768
  maximum size and 64 colors; MP4/WebM retain the original canvas dimensions
  and narration. No extra soundtrack is added
- Each run measures the public `Deck.render(..., animation=...)` path, including
  document construction, preflight, rendering, and final output writes
- `Render ms/shot` amortizes all work outside the encoder over produced shots.
  A *shot* is one generated image plus its duration, not a duplicated playback
  frame. Static holds can span many playback frames. This is deliberately
  different from dividing by duration × fps
- `Encode s` is wall time inside the existing GIF/video encoder, **minus time
  spent pulling its lazy shot iterator**. It includes quantization, resizing,
  PNG intermediates, FFmpeg and audio encoding/muxing as applicable. These
  developer-only wrappers do not replace rendering or encoding algorithms
- `Python RSS MiB` is the isolated Python process's lifetime peak resident
  memory, including native Pillow allocations and imports. It excludes child
  FFmpeg processes. It is not total machine memory or a Python allocation-only
  trace, and the three-run median is not the worst observed peak
- `Font loads` counts successful native FreeType `getfont` calls; failed family
  probes are excluded. `Font s` includes time in successful and failed calls
- The JSON file retains every raw run as well as the medians. Medians for
  different columns may come from different runs; do not add medians to derive
  another median

Use `--scenes translation rotation scale` or `--formats gif` for development
smoke runs. `--fps` selects another rate explicitly. Compare only matching
scene/format/options and environments; partial or lower-rate runs are not the
full baseline. Run timings without concurrent tests or other heavy workloads.
Fresh processes reset process-local font caches, but filesystem caches are not
flushed. Results are local measurements, not universal performance guarantees.

## Jitter metric

A separate fixed **30 fps** public `Deck.sample()` capture tracks the
intensity-weighted centroid of the white marker. The metric is the population
standard deviation of consecutive Euclidean centroid displacements, in pixels
per frame. Translation at 0.2 pixels/frame exposes the current 0/1-pixel
staircase. The off-centre centroid also moves under rotation/scale, avoiding a
misleading zero from a symmetric marker. The product reel has no isolated
marker, so its jitter cell is `n/a`.

The probe is run three times in separate processes before export measurements,
so it cannot warm the export's caches or inflate its RSS. This is a diagnostic
metric, not a complete perceptual quality score or a fixed acceptance threshold.
Rotation/scale rasterization and centroid measurement can contribute variation.

## Lossless frame-identity gate

Capture before and after a change in the same environment:

```bash
uv run --locked python -m benchmarks.frame_identity capture /tmp/before.json
# Apply the candidate change, without changing benchmark scenes or dependencies.
uv run --locked python -m benchmarks.frame_identity capture /tmp/after.json
uv run --locked python -m benchmarks.frame_identity compare /tmp/before.json /tmp/after.json
```

The default capture checks **every 12 fps canonical timeline sample**, the exact
final instant, and each settled slide from the public `Deck.sample()` API.
Full-resolution reel frames are captured in bounded batches; manifests contain
only digests and metadata, never base64 pixels. This costs extra timeline setup
work and is not used for performance measurements.

Comparison exits nonzero for any changed digest, missing frame, changed sample
instant, dimensions, slide, timeline, document specification, selection, rate,
or rendering environment. Source commit and CPU may differ. Paths under the
checkout root are normalized so equivalent worktrees can be compared. Identical
SHA-256 digests mean identical canonical raw RGBA bytes at the sampled instants.
The script does not certify unsampled instants, encoder container bytes, audio,
or codec fidelity; those require their existing export tests. Use `--fps 30`
(or another matching rate) to strengthen a particular lossless change's gate.

Baseline results and subsequent speedups belong in the discussion for
[performance issue #144](https://github.com/sjquant/quickthumb/issues/144).

## Loaded-font reuse (#148)

The font optimization reuses up to 128 resolved faces across canvases in a
process. Size, normalized variation settings and weight are part of the cache
key; file identity and modification metadata distinguish replaced fonts. Remote
font resolution still checks the document's asset policy before consulting the
loaded-face cache. Existing canvases keep their existing per-canvas reuse
semantics; a file change is observed when a new font resolution is performed.

Shared faces serialize mask rendering and metrics, including color-font
foreground-palette changes. Variable axes are configured before sharing a face.
Fallback resolution, warnings, cloning and export compatibility are covered by
regressions. No public cache-control API or new dependency is introduced.

Fresh-process benchmark runs deliberately measure cold process caches. Repeated
exports in a long-lived process can reuse more faces, but those warm timings are
not interchangeable with the baseline. See the results discussion in #144 for
same-workload font-load counts, byte-identity checks and measured timing changes.

## Raw video streaming (#150)

MP4/WebM send RGB24 frames directly to FFmpeg, allocating repeats on the same
cumulative half-up clock. Each shot is converted to bytes once and written for
its allocated frame count. Batches still contain at most 64 distinct emitted
shots, and the encoded segments use the existing audio mux. There is no PNG
image spool, and shot generation remains lazy. Stderr is drained concurrently
into a bounded diagnostic tail; failed producers and encoders are reaped.

Decoded-byte comparisons against the former PNG/concat path pass at 10 and
25 fps. The former path was not an exact-count reference at all rates: PNG
input used a 25 Hz time base, and its half-frame end trim could remove a counted
frame. A 129-frame numbered sequence spanning three batches lost two frames
at 12, 24, 29.97, 30, 60 and 120 fps in the old encoder. Streaming preserves all
129 frames in order. Tests check decoded frame identity/order, ffprobe counts,
durations and even-dimension cropping. Container bytes are not an identity
gate, and this timing correction intentionally differs from the old output.
Audio scheduling, codecs, and the 504-observation canonical RGBA gate remain
unchanged.

Long static holds trade the old compressed-image reuse for repeated raw pipe
writes. Benchmark those separately from the animated reel before generalizing
the measured encode-stage speedup. The existing timer excludes lazy rendering;
FFmpeg may now perform some encoding concurrently with that rendering, so total
wall time is also important when comparing results.

## Static slide-prefix plate (#149)

Each slide pre-composites the leading static units once, in their original
order, onto a transparent RGBA plate. Frames start from a copy of that plate.
Static units above or between animated units remain in the per-frame stack;
regrouping translucent units there would change layer order or alpha rounding.
The internal frame compositor accepts an ordered unit sequence and an optional
prepared background, and returns a caller-owned full-canvas RGBA image.

Legacy effects, canonical and staggered timelines, animated components and
backdrop-dependent motion all stop the cached prefix. Video descendants stop
it even in reduced-motion mode, since foreground captions still sample time.
The optimization adds no public API or dependency.

`tests/test_static_slide_prefix.py` compares exact bytes against the uncached
ordered stack, including non-monotonic samples and returned-frame mutation.
It also counts `PIL.Image.alpha_composite` calls, including plate preparation:
for five samples of five units with a two-unit static prefix, calls fall from
25 to 17. An all-static three-unit stack falls from 15 to 3; a stack starting
with motion has the same call count. The complete workload's count and clean
median-of-three export timings belong in the #144 results discussion. Timing
and RSS must include slide preparation and the retained full-size plates.

## Incremental GIF encoding (#153)

GIF quantization and drift-free centisecond allocation are unchanged. A bounded
Pillow adapter retains the previous normalized image and one pending encoded
frame; identical images extend the pending duration. It uses Pillow's existing
palette, delta-bound and frame encoders, and preserves the different
single-frame/interlaced fallback. The supported Pillow range remains
`>=12.2,<13`; byte comparisons against ordinary `save_all` guard the adapter's
private Pillow calls when dependencies change.

`tests/test_gif_streaming.py` checks exact encoded bytes, including palette
changes, a fully occupied 256-color palette, reduced palettes, cropped deltas,
repeated frames, resize options, loops and fractional timing. It also checks
that output begins before input is exhausted and that live uncompressed image
count stays bounded across a long generated stream. The final compressed GIF
is still held by the bytes-returning path and file exporter. Rendering state
and output bytes are not constant-memory, so peak RSS is still measured.

The old `768 MiB` estimated frame-list ceiling is removed. To check the complete
example at its original 1080×1920 size, without the benchmark's usual resize:

```python
from examples.product_hype_reel import build_deck
from quickthumb import GifOptions

build_deck().render("full-size.gif", animation=GifOptions(fps=12, colors=64))
```

Compare encoded GIF hashes on the same Pillow version and environment. The
canonical RGBA gate alone does not establish encoded-byte identity. The usual
benchmark command deliberately retains its original 432×768 / 64-color GIF
workload so before/after timing and RSS remain comparable. A full-size export
is a separate capability/memory check, not a like-for-like speedup claim.
