# Recorded export measurements

The dated JSON reports retain raw successful runs, source commits, environment,
workload identity, options, output checks, and median/minimum/maximum values.
They describe the recorded host and workload, not universal speed guarantees.

## Reproduce

The `measurement_script` in `2026-10-19-178.json` is the exact standalone
uninstrumented export driver. Extract it to `/tmp/export_once.py`, check out each
recorded commit in a separate worktree, and use one matching locked Python
environment for every revision. For example, from a recorded checkout:

```bash
uv run --locked python /tmp/export_once.py \
  '{"pr":178,"format":"gif","fps":12,"repetition":1,"output":"/tmp/result.gif"}'
```

Match the recorded scene, worker count and quality when those options are present.
Rotate revisions/worker counts between repetitions; do not run tests or profiling
alongside timings. Retain every attempt. The reports include three observations
per condition, with six balanced pairs for the separate static-hold workload.
Decoded video/audio hashes use FFmpeg's SHA-256 hash muxer with RGB24 video and
PCM S16LE audio, after timing; frame counts and durations come from ffprobe.

## Read the evidence

- GIF hashes, decoded pixels, frame counts and duration establish equivalence for
  the measured exports; they do not certify every possible scene or instant
- Video speed comparisons use a matched 10 fps workload with identical decoded
  frames/audio. The legacy 12 fps path can drop counted frames and is not a fair
  equal-work reference
- Instrumented font/render/encoder and process-tree RSS diagnostics are separate
  single observations, not replicated speed estimates
- Timing-run RSS is Python-only. Tree RSS sums simultaneous resident pages and
  double-counts shared pages; scheduling gaps can miss peaks. Read the recorded
  maximum sampling gap rather than assuming the requested 50 ms interval held
- Preserve noisy/overlapping timing ranges and an inconclusive verdict. Quality
  steps intentionally change pixels; their cost is not a lossless speed contest
