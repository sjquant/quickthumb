---
description: Control animation duration, slide transitions, sound, and playback in quickthumb.
---

# Animation timing

Set animation and slide durations in seconds. Export a GIF for a silent loop,
video for motion with sound, or HTML for an interactive presentation.

## Animate and hold a scene

This example fades in a shape over one second, then holds the final image for
two seconds. It writes `timed.gif` in the working directory, replacing any
existing file with that name:

```python
from quickthumb import AnimationSpec, Canvas, GifOptions

canvas = Canvas(320, 180).background(color="#102030").shape(
    "rectangle", (80, 40), 160, 100, "#42CEB7",
    animation=AnimationSpec.fade(duration=1),
)
canvas.export("timed.gif", animation=GifOptions(hold=2))
```

Use `VideoOptions(hold=2)` for MP4, WebM, or MOV. Video export requires FFmpeg.
`GifOptions` and `VideoOptions` also accept `fps`; their defaults are 20 and 30
respectively. GIF has no audio. See [output formats](output-guide.md) for setup.

## Slide duration and transitions

A Deck plays each slide's motion and incoming transition, then holds the settled
slide for `hold` seconds (three by default). Later slides use a 0.5-second
crossfade unless you choose another transition; `Cut()` switches immediately.

For Deck video, `slide(duration=...)` sets the slide's total window, including
its incoming transition and animation. Narration can set the window when no
explicit duration is supplied. A longer visual animation is allowed to finish;
narration is trimmed or padded to its scheduled window. GIF ignores slide
narration and `slide(duration=...)`.

`advance_after` on a transition replaces the usual hold; the slide still waits
for its animation and any video narration or explicit duration to finish. For
precise boundary rules, see the [timing reference](reference/timing-details.md#slide-duration-and-transitions).

## Audio, captions and reduced motion

MP4, WebM, and MOV can include supported clip audio, slide narration, and a
soundtrack. GIF is silent. Video clip captions use times relative to the placed
clip and are burned into supported video frames.

With `ExportPolicy(reduced_motion=True)`, authored layer motion and transitions
are suppressed while holds, narration, and caption timing remain. Default Deck
crossfades can remain. HTML presentations keep interactive click cues, but do
not play Deck narration and show video layers as static frames. Check your
export in the destination app.

## Temporal exposure

To add motion blur to GIF, video, or an image sequence, pass `MotionBlur` to the
corresponding export options:

```python
from quickthumb import MotionBlur, VideoOptions

canvas.export(
    "exposure.mp4",
    animation=VideoOptions(fps=30, motion_blur=MotionBlur(samples=8, shutter_angle=180)),
)
```

Motion blur is an export setting; HTML and PowerPoint do not reproduce it.
`MotionBlur` accepts 2–64 samples and a shutter angle greater than 0 and at
most 360 degrees. See the [motion blur reference](reference/timing-details.md#temporal-exposure)
for timing, support, and export receipts.

### Support and receipts

Use `result.capability_report` after export to inspect applied motion blur and
`result.timing_metrics` for encoded playback. See the [support table](reference/timing-details.md#support-and-receipts).

## Choose the clock

`sample()` observes the authored timeline; an encoded GIF or video can have a
slightly different duration or frame count because of its format. HTML is
interactive rather than a fixed-duration video. See the
[sampling and timing reference](reference/timing-details.md#choose-the-clock)
when exact frame times or export metrics matter.

## Verify playback

Play the exported file and check slide changes, captions, sound, and the final
hold in the app where it will be shared. For exact timing, inspect
`result.timing_metrics`; the [timing reference](reference/timing-details.md#verify-playback)
also describes the project's playback tests.
