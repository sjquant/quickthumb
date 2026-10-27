# Audio-reactive authoring

`quickthumb.audio.analyze_audio(path, cache_dir=None)` analyzes a local audio
source ahead of authoring. It returns a validated `AudioAnalysis` record with
transient onset times and source-relative RMS amplitudes. Onsets identify sharp
increases in loudness; they are **not** a musical beat grid or a tempo estimate.

Use an onset as an ordinary numeric `TimingSpec.start`. This avoids a dependency
on soundtrack options when sampling, restoring JSON, or rendering in workers:

```python
from quickthumb import AnimationSpec, ColorTrack, KeyframeSpec, TimingSpec
from quickthumb.audio import analyze_audio

analysis = analyze_audio("music.wav")
if analysis.onsets:
    motion = AnimationSpec.timeline(
        ColorTrack(keyframes=[
            KeyframeSpec(time=0, value="#102030"),
            KeyframeSpec(time=0.2, value="#42CEB7"),
        ]),
        timing=TimingSpec(start=analysis.onsets[0], duration=0.2),
        easing="linear",
    )
```

Attach `motion` to a layer's `animation=`. See the runnable
[`examples/audio_onsets.py`](https://github.com/sjquant/quickthumb/blob/main/examples/audio_onsets.py)
for a scene, analysis sidecar, canonical JSON and MP4 with the same source as its
soundtrack. The numeric motion is also inspectable with `inspect_motion()` and
uses each target's existing color-track support or declared fallback. HTML
presentation does not play the soundtrack; GIF remains silent. Baked timing is
not a claim of live audio synchronization in either format.

## Source clock and RMS

All times are seconds from the beginning of the first decoded audio stream.
Analysis uses mono audio resampled to 8 kHz and contiguous 160-sample (20 ms)
windows. `rms[i]` is the linear RMS amplitude of the window starting at `i * 0.02`;
the final window may be shorter. Values are source amplitudes, not normalized
per track. Silence has zero RMS and no onsets.

The versioned detector requires an RMS attack above 0.01 and twice both the
previous window and the mean of the previous ten windows, with at least 100 ms
between anchors. Reference transients are tested within one 20 ms window;
gradual attacks and musical offbeats need not produce anchors. An onset index
can be absent: check `onsets` before indexing.

Export gain, soundtrack looping/fade-out, narration and other mixed audio do not
change this source analysis. Deck timing is slide-local: authors must translate
a soundtrack onset into the intended slide's clock. Nothing automatically
repeats or relocates anchors when export options change.

## Loudness-driven scale

`AudioAnalysis.scale_track(min_scale=1.0, max_scale=1.15)` returns an ordinary
`ScaleTrack`. Attach it to `AnimationSpec.timeline()`; no soundtrack or analyzer
is consulted while converting stored RMS into motion:

```python
pulse = AnimationSpec.timeline(
    analysis.scale_track(min_scale=1.0, max_scale=1.4)
)
```

The helper divides each RMS amplitude by the loudest window in this analysis,
then maps that ratio into the requested scale range. Silence maps to
`min_scale`, the peak maps to `max_scale`, and an entirely silent analysis stays
at `min_scale`. This is source-relative normalization: a quiet recording can
produce the same response as a louder copy, and export volume does not affect it.
Both bounds must be finite positive numbers with `max_scale >= min_scale`.

Each keyframe holds its value over its 20 ms window, including a shorter final
window; there is no interpolation before an attack. At the exact source end an
additional keyframe returns to `min_scale`, so settled holds and subsequent
slides do not retain a loud final pulse. The inferred animation duration equals
`analysis.duration`. An explicit `TimingSpec` must allow that full duration;
setting `start` shifts the entire source clock rather than trimming it.

The generated track is regular canonical JSON: `sample()`, `inspect_motion()`,
workers and exporters consume it through the existing scale-track path.
Reduced motion suppresses this track and keeps the authored static geometry.
HTML/PPTX follow their declared scale support, but do not acquire live soundtrack playback or synchronization. The
runnable example combines an onset-triggered color change and a loudness-driven
scale pulse with source audio in MP4.

## Store and reuse

```python
from pathlib import Path
from quickthumb.audio import AudioAnalysis

Path("analysis.json").write_text(analysis.model_dump_json(), encoding="utf-8")
stored = AudioAnalysis.model_validate_json(Path("analysis.json").read_text())
```

The record includes its schema/algorithm version, source SHA-256, FFmpeg version,
sampling parameters, duration, ordered onsets and RMS windows. Its JSON schema
is available through `AudioAnalysis.model_json_schema()`. A sidecar and motion
baked into document JSON can be loaded and sampled without the source audio or
FFmpeg. Exporting audio still requires its source and the usual media tools.

`analyze_audio` itself requires FFmpeg (`QUICKTHUMB_FFMPEG` overrides the binary).
It caches records under the system temporary directory's `quickthumb-audio`
folder, or the supplied `cache_dir`, using source bytes, algorithm, fixed
parameters and FFmpeg version as the identity. Cache writes are atomic. Changing
source bytes or decoder/algorithm versions creates a new entry; a corrupt entry
raises an error identifying the file to remove. Keep a sidecar to pin authoring
results across decoder upgrades rather than relying on an evictable cache.

Inputs are bounded to 64 MiB and ten minutes of decoded audio. Analysis has a
60-second timeout. Missing/non-audio files, unsupported FFmpeg filters and
exceeded limits fail with actionable errors; analysis is never silently
truncated. These limits bound authoring work, not rendering duration.
