import json

import pytest
from quickthumb import (
    AnimationSpec,
    ColorTrack,
    KeyframeSpec,
    LayerState,
    OpacityTrack,
    PositionTrack,
    ScaleTrack,
    Timeline,
    TimingSpec,
    compile_timeline,
    compile_transition_timeline,
    sample_frames,
)
from quickthumb.errors import ValidationError
from quickthumb.transitions import Fade as SlideFade


class TestMotionTimeline:
    """Black-box coverage for normalized timeline compilation and sampling."""

    def test_should_compile_typed_tracks_into_one_normalized_event(self):
        """Typed tracks compile into a renderer-independent event with resolved duration."""
        # given: position and opacity tracks with different local durations
        spec = AnimationSpec.timeline(
            PositionTrack(
                keyframes=[
                    KeyframeSpec(time=0, value=(10, 20)),
                    KeyframeSpec(time=1, value=(30, 40)),
                ]
            ),
            OpacityTrack(
                keyframes=[KeyframeSpec(time=0, value=0), KeyframeSpec(time=0.5, value=1)]
            ),
        )

        # when: the canonical animation is compiled
        timeline = compile_timeline(spec)

        # then: both tracks share one event and the longest track defines duration
        assert len(timeline.events) == 1
        assert timeline.duration == 1
        assert [track.property for track in timeline.events[0].tracks] == ["position", "opacity"]

    def test_should_sample_all_supported_track_value_shapes(self):
        """Sampling interpolates vectors, scalars, and hexadecimal colors deterministically."""
        # given: tracks for every directly interpolated value shape
        spec = AnimationSpec.timeline(
            PositionTrack(
                keyframes=[
                    KeyframeSpec(time=0, value=(0, 10)),
                    KeyframeSpec(time=1, value=(20, 30)),
                ]
            ),
            ScaleTrack(keyframes=[KeyframeSpec(time=0, value=1), KeyframeSpec(time=1, value=2)]),
            ColorTrack(
                keyframes=[
                    KeyframeSpec(time=0, value="#000000"),
                    KeyframeSpec(time=1, value="#FFFFFF"),
                ]
            ),
        )

        # when: the timeline is sampled halfway through
        state = compile_timeline(spec).sample(0.5)

        # then: each property is resolved at the same deterministic progress
        assert state.position == (10.0, 20.0)
        assert state.scale == 1.5
        assert state.color == "#808080"

    def test_should_resolve_relative_and_absolute_timing(self):
        """Relative triggers and absolute starts produce stable event windows."""
        # given: sequential, overlapping, and absolute events
        first = AnimationSpec.timeline(
            OpacityTrack(keyframes=[KeyframeSpec(time=0, value=0), KeyframeSpec(time=1, value=1)]),
            timing=TimingSpec(duration=1),
        )
        parallel = AnimationSpec.timeline(
            ScaleTrack(keyframes=[KeyframeSpec(time=0, value=1), KeyframeSpec(time=1, value=2)]),
            timing=TimingSpec(duration=1, trigger="with_previous", delay=0.2),
        )
        absolute = AnimationSpec.timeline(
            PositionTrack(keyframes=[KeyframeSpec(time=0, value=(0, 0))]),
            timing=TimingSpec(start=3, duration=0.5),
        )

        # when: the specs are compiled in order
        timeline = compile_timeline([first, parallel, absolute])

        # then: anchors, delays, and settled ends are explicit
        assert [(event.start, event.active_start, event.end) for event in timeline.events] == [
            (0.0, 0.0, 1.0),
            (0.0, 0.2, 1.2),
            (3.0, 3.0, 3.5),
        ]
        assert timeline.duration == 3.5

    def test_should_preserve_base_state_before_and_after_events(self):
        """Sampling before an event preserves the base and after it keeps the final state."""
        # given: a delayed opacity event and a non-default base state
        spec = AnimationSpec.timeline(
            OpacityTrack(keyframes=[KeyframeSpec(time=0, value=0), KeyframeSpec(time=1, value=1)]),
            timing=TimingSpec(duration=1, delay=0.5),
        )
        timeline = compile_timeline(spec)
        base = LayerState(opacity=0.25, scale=2)

        # when: the timeline is sampled before, during, and after its window
        before = timeline.sample(0.25, base)
        during = timeline.sample(1.0, base)
        after = timeline.sample(4.0, base)

        # then: delay, interpolation, and settled values are deterministic
        assert before == base
        assert during.opacity == 0.5
        assert after.opacity == 1.0
        assert after.scale == 2

    def test_should_round_trip_timeline_and_sample_frames(self):
        """Canonical timeline JSON round-trips without changing sampled frames."""
        # given: a timeline with an effect and a typed track
        timeline = compile_timeline(
            [
                AnimationSpec.fade(duration=0.25),
                AnimationSpec.timeline(
                    ScaleTrack(
                        keyframes=[
                            KeyframeSpec(time=0, value=1),
                            KeyframeSpec(time=0.5, value=2),
                        ]
                    )
                ),
            ]
        )

        # when: it is serialized, restored, and sampled at a fixed rate
        restored = Timeline.from_json(json.dumps(timeline.to_dict()))
        frames = sample_frames(restored, 4)

        # then: serialization and deterministic frame sampling are stable
        assert restored == timeline
        assert [time for time, _ in frames] == [0.0, 0.25, 0.5, 0.75]
        assert frames[-1][1].scale == 2.0

    def test_should_normalize_effects_and_slide_transition_timing(self):
        """Effect presets and slide transitions share the normalized event shape."""
        # given: a canonical fade effect and a slide-level fade transition
        effect_timeline = compile_timeline(AnimationSpec.fade(duration=0.5, delay=0.25))
        transition_timeline = compile_transition_timeline(SlideFade(duration=0.75))

        # when: both timelines are sampled through the common LayerState API
        effect_state = effect_timeline.sample(0.5)
        transition_state = transition_timeline.sample(0.5)

        # then: effect metadata and transition timing are normalized without exporter logic
        assert effect_timeline.events[0].source == "effect"
        assert effect_timeline.events[0].effect == "fade"
        assert effect_state.opacity == 0.5
        assert transition_timeline.events[0].source == "transition"
        assert transition_timeline.duration == 0.75
        assert transition_state == LayerState()

    def test_should_handle_empty_and_zero_span_timelines(self):
        """Empty timelines and one-keyframe timelines settle immediately."""
        # given: no events and a track with one keyframe
        empty = compile_timeline([])
        instant = compile_timeline(
            AnimationSpec.timeline(OpacityTrack(keyframes=[KeyframeSpec(time=0, value=0.4)]))
        )

        # when: both timelines are sampled and frame times are requested
        # then: both have a clear zero-duration behavior
        assert empty.duration == 0
        assert empty.sample(10) == LayerState()
        assert instant.duration == 0
        assert instant.sample(0).opacity == 0.4
        assert instant.frame_times(30) == (0.0,)

    def test_should_reject_invalid_sampling_and_timing_inputs(self):
        """Invalid timeline inputs fail with actionable errors at the public boundary."""
        # given: a track whose timing window is shorter than its keyframes
        spec = AnimationSpec.timeline(
            OpacityTrack(keyframes=[KeyframeSpec(time=0, value=0), KeyframeSpec(time=1, value=1)]),
            timing=TimingSpec(duration=0.5),
        )

        # when: compilation or sampling receives invalid values
        with pytest.raises(ValidationError, match="shorter than"):
            compile_timeline(spec)
        with pytest.raises(ValidationError, match="sample time must be finite"):
            compile_timeline([]).sample(float("nan"))
        with pytest.raises(ValidationError, match="fps must be"):
            compile_timeline([]).frame_times(0)

        # then: errors identify the invalid boundary rather than failing in a renderer
