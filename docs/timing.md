---
description: How canonical sampling, GIF/video playback, Deck narration and interactive HTML use time.
---

# Animation timing

Use seconds for authored motion, slide durations, holds, video placement and
caption cues. `sample()` observes the canonical timeline; `export()` reports the
visual timeline actually encoded. Those measurements serve different purposes.

## Choose the clock

| Output or observation | Timing contract |
| --- | --- |
| `sample()` with no time or fps | One authored-static frame per Canvas/page, matching raster output without seeking an animation endpoint; `duration=0`, frame `time=None`. |
| `sample(time=...)` | Observe explicit document times. Slide windows are `[start, end)`; an exact boundary belongs to the incoming slide. Times beyond the end show the settled final scene. |
| `sample(fps=...)` | Observe a uniform grid `0, 1/fps, 2/fps, …` before the timeline end. A zero-length timeline is still observed once at zero. |
| GIF | Silent, variable frame durations in 10 ms steps; identical frames can coalesce. Default sampling rate 20 fps; supported rate is greater than zero and at most 100 fps. |
| MP4 / WebM / MOV | Constant-rate encoded frames, including repeated held frames. Default 30 fps; supported rate is greater than zero and at most 120 fps. |
| HTML | Browser-driven, interactive cues and slide navigation. No encoded fps or fixed total playback duration, and no Deck narration playback. |

`GifOptions.fps` and `VideoOptions.fps` request the sampling density. Moving spans
are sampled within their own timing boundaries; static spans become held shots.
Video allocates repeated frames on a cumulative frame clock, while GIF quantizes
cumulative durations to centiseconds. A canonical uniform sample grid is therefore
not an index into the encoded file: arbitrary fractional spans, palette/lossy
encoding and duplicate-frame coalescing can change frame positions or counts.

Read `ExportResult.timing_metrics` after an animated export:

| Field | Meaning |
| --- | --- |
| `fps` | The selected sampling rate; for GIF this is not stored frames divided by playback duration. |
| `frame_count` | Frames actually encoded, after GIF coalescing or video hold repetition. |
| `duration` | Encoded visual playback seconds: summed GIF delays or video frame count divided by fps. Audio container padding can differ. |

`FrameSequence.duration` instead describes the unquantized canonical timeline.
HTML returns no fixed playback timing in `timing_metrics`; its zero duration is
not a claim that its interactive animations take no time.

```python
from quickthumb import AnimationSpec, Canvas, GifOptions

canvas = Canvas(160, 90).background(color="#000000").shape(
    "rectangle", (40, 20), 80, 50, "#FF0000",
    animation=AnimationSpec.fade(duration=1),
)
samples = canvas.sample(fps=7, hold=0.37)
result = canvas.export("timed.gif", animation=GifOptions(fps=7, hold=0.37))
print(samples.duration, len(samples.frames))
print(result.timing_metrics.model_dump())
```

## Slide duration and transitions

Layer motion and the incoming transition start on the same slide clock. For
noninteractive media, `on_click` cues run in sequence like `after_previous`;
`with_previous` cues overlap. Delays are part of those clocks. Transitions play
over the previous slide's settled scene; a slide without an explicit transition
starts instantly on the first slide and uses a 0.5-second crossfade thereafter.
Use `Cut()` for an immediate boundary.

A slide's exit is determined by the latest applicable boundary:

- With neither a duration override nor `advance_after`, transition and layer
  motion finish, then the settled scene holds for `hold` seconds (default 3).
- For Deck video, `slide(duration=...)` sets a total slide window, including its
  transition and motion. Without an explicit duration, narration supplies that
  window. Neither trims a longer visual animation; the slide lasts long enough
  for both. Narration itself is trimmed or padded to its scheduled window.
- A transition's `advance_after` replaces `hold`: its boundary is counted after
  the incoming transition. The exit is the latest of that boundary, completed
  motion and any narration/explicit duration. For example, a one-second animation
  with `Cut(advance_after=0.1)` ends at one second even when `hold=3`; it does not
  add a three-second tail.

GIF ignores Deck narration and `slide(duration=...)`; it uses motion,
transitions, `advance_after` and `hold`. `Deck.sample()` uses the narration-aware
video schedule, so a narrated Deck's GIF need not match its sampled duration.

The encoder shows the settled state even with `hold=0`, replacing the final
motion shot when needed rather than always appending a full hold. A static or
sub-frame slide still needs a representable frame. GIF and video durations can
therefore differ slightly from the mathematical timeline. Deck video currently
requires a positive `hold` for slides with neither narration nor an explicit
positive duration; a zero hold remains valid for Canvas and Deck GIF.

## Audio, captions and reduced motion

MP4/WebM/MOV mix supported clip audio, Deck narration and an optional soundtrack.
Narration starts at its slide's absolute offset. The soundtrack is trimmed to the
visual timeline and can loop; audio padding from the codec does not extend the
reported visual duration. GIF and image sequences carry no audio. Use video when
the soundtrack or narration must accompany the motion. Ordinary MP4 exports play
animations; `to_narrated_mp4()` / `render_narrated_mp4()` are the separate
static-slide narration path.

A video layer's `start` is slide-local. Its `trim_start`, `trim_end` and `speed`
select source media time; caption `start`/`end` are relative to the placed clip,
not to the original source file. Captions are active over `[start, end)` and are
burned into the foreground of supported raster/video output. They remain timed
when reduced motion freezes the clip's picture.

`ExportPolicy(reduced_motion=True)` suppresses authored layer motion and authored
slide transitions. It retains holds, narration and caption timing; default Deck
crossfades can remain between slides. Use the actual export receipt for the
resulting duration, rather than the original motion duration.

HTML keeps `on_click` cues interactive and `after_previous` cues automatic.
`advance_after` enables conditional auto-advance after the incoming transition;
it does not turn the presentation into fixed-duration video. Video layers use a
static fallback in HTML, so their playback/caption timing is not reproduced.
Check `validate_export()` and the returned fallback diagnostics for the target.
GIF/video option families, unsupported transparency and codec rate limits fail
with actionable errors rather than silently selecting another format.

## Verify playback

The three-slide integration scene in `tests/test_video_layers.py` checks actual
GIF, MP4 and WebM output: selected pixels against canonical samples, incoming
transitions, caption start/end windows, encoded timing, and decoded soundtrack
and narration frequencies. Reduced-motion cases check frozen clip imagery and timed captions. Run it with FFmpeg and ffprobe installed:

```bash
uv run --locked pytest tests/test_video_layers.py -k motion_package --no-cov
```

Existing HTML timeline tests execute the JavaScript in Node stage fixtures;
target-specific browser fidelity remains a separate check.
