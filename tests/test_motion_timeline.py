import math

import pytest
from pydantic import ValidationError as PydanticValidationError
from quickthumb import (
    AnimationSpec,
    BlurTrack,
    ClipProgressTrack,
    ColorTrack,
    ImagePanTrack,
    ImageZoomTrack,
    KeyframeSpec,
    OpacityTrack,
    PositionTrack,
    RotationTrack,
    ScaleTrack,
    TimingSpec,
)
from quickthumb.errors import ValidationError
from quickthumb.motion import (
    LayerState,
    Timeline,
    compile_timeline,
    compile_transition_timeline,
    resolve_staggered_timelines,
    resolve_target_order,
    resolve_targets,
    resolve_text_targets,
    sample_frames,
)
from quickthumb.transitions import Fade as SlideFade


class TestMotionTimeline:
    """Black-box coverage for normalized timeline compilation and sampling."""

    def test_should_resolve_text_targets_in_document_order_without_relaying_out_text(self):
        """Given text members, when semantic targets resolve, then source order is preserved."""
        # given
        text = "Hello world"

        # when
        characters = resolve_text_targets(text, "characters")
        words = resolve_text_targets(text, "words")
        lines = resolve_text_targets(text, "lines", lines=("Hello", "world"))

        # then
        assert [target.value for target in characters] == list(text)
        assert [target.value for target in words] == ["Hello", "world"]
        assert [target.value for target in lines] == ["Hello", "world"]
        assert [target.index for target in characters] == list(range(len(text)))

    def test_should_preserve_empty_trailing_line_targets(self):
        """Given a trailing newline, when lines resolve, then the empty line remains addressable."""
        # given / when
        targets = resolve_text_targets("first\n", "lines")

        # then
        assert [target.value for target in targets] == ["first", ""]
        assert [target.source_range for target in targets] == [(0, 5), (6, 6)]

    def test_should_resolve_text_and_group_orders_deterministically(self):
        """Given semantic ordering, when targets resolve, then ties retain document order."""
        # given
        positions = ((10, 20), (10, 10), (4, 10), (4, 10))

        # when
        top_to_bottom = resolve_target_order(4, "top_to_bottom", positions)
        left_to_right = resolve_target_order(4, "left_to_right", positions)
        reverse = resolve_targets(("a", "b", "c"), order="reverse")

        # then
        assert top_to_bottom == (1, 2, 3, 0)
        assert left_to_right == (2, 3, 0, 1)
        assert [target.value for target in reverse] == ["c", "b", "a"]

    def test_should_expand_stagger_metadata_into_independent_runtime_timelines(self):
        """Given stagger metadata, when runtime timelines expand, then each target starts later."""
        # given
        timeline = compile_timeline(AnimationSpec.rise(duration=0.5, stagger=0.1, target="words"))

        # when
        expanded = resolve_staggered_timelines(timeline, 3)

        # then
        assert [item.events[0].start for item in expanded] == [0.0, 0.1, 0.2]
        assert [item.events[0].stagger for item in expanded] == [None, None, None]
        assert [item.duration for item in expanded] == [0.5, 0.6, 0.7]
        assert timeline.events[0].stagger == {"delay": 0.1, "target": "words", "order": "document"}

    @pytest.mark.parametrize(
        ("factory", "property", "blend", "values"),
        [
            ("fade", "opacity", "multiply", (0.0, 1.0)),
            ("rise", "position", "add", ((0.0, 24.0), (0.0, 0.0))),
            ("fall", "position", "add", ((0.0, -24.0), (0.0, 0.0))),
            ("slide", "position", "add", ((-24.0, 0.0), (0.0, 0.0))),
            ("zoom", "scale", "multiply", (0.8, 1.0)),
            ("pop", "scale", "multiply", (0.8, 1.0)),
            ("float", "position", "add", "sine"),
            ("pulse", "scale", "multiply", "sine"),
            ("shake", "position", "add", "sine"),
            ("ken_burns", "scale", "multiply", (1.0, 1.1)),
            ("typewriter", "clip_progress", "multiply", (0.0, 1.0)),
        ],
    )
    def test_should_compile_each_preset_into_a_normalized_track(
        self, factory, property, blend, values
    ):
        """Given a public preset, when compiled, then its normalized track is explicit."""
        # given: a semantic preset with explicit timing and easing
        spec = getattr(AnimationSpec, factory)(
            distance=24, duration=0.8, delay=0.2, easing="ease_out_cubic"
        )

        # when: the preset is lowered into the shared timeline
        event = compile_timeline(spec).events[0]

        # then: the event preserves metadata and exposes renderer-independent track semantics
        assert event.source == "effect"
        assert event.effect == factory
        assert event.start == 0.0
        assert event.active_start == 0.2
        assert event.end == 1.0
        assert event.options["easing"] == "ease_out_cubic"
        assert len(event.tracks) == 1
        assert event.tracks[0].property == property
        assert event.tracks[0].blend == blend
        assert event.tracks[0].keyframes[-1].time == pytest.approx(0.8)
        actual_values = [keyframe.value for keyframe in event.tracks[0].keyframes]
        if values == "sine":
            assert len(actual_values) == 17
            for index, value in enumerate(actual_values):
                progress = index / 16
                if factory == "float":
                    expected = (0.0, -24.0 * math.sin(progress * math.tau))
                elif factory == "shake":
                    expected = (24.0 * math.sin(progress * math.tau), 0.0)
                else:
                    expected = 1.0 + 0.1 * math.sin(progress * math.pi)
                assert value == pytest.approx(expected)
        else:
            assert actual_values == list(values)

    def test_should_compile_image_viewport_tracks_and_sample_them_deterministically(self):
        """Given image viewport tracks, when sampled, then pan and zoom are stable."""
        # Given: a canonical image viewport timeline
        spec = AnimationSpec.timeline(
            ImagePanTrack(
                keyframes=[
                    KeyframeSpec(time=0, value=(-1, 0)),
                    KeyframeSpec(time=1, value=(1, 0)),
                ]
            ),
            ImageZoomTrack(
                keyframes=[KeyframeSpec(time=0, value=1), KeyframeSpec(time=1, value=1.2)]
            ),
        )

        # When: the shared timeline is sampled twice at the same instant
        timeline = compile_timeline(spec)
        first = timeline.sample(0.5)
        second = timeline.sample(0.5)

        # Then: image state is interpolated and reproducible
        assert first == second
        assert first.image_pan == pytest.approx((0.0, 0.0))
        assert first.image_zoom == pytest.approx(1.1)

    @pytest.mark.parametrize("factory", ["rise", "fall", "slide", "float", "shake"])
    def test_should_sample_positional_presets_from_the_default_origin(self, factory):
        """Given no base position, positional presets use the deterministic origin."""
        # given: a positional preset and the default LayerState
        timeline = compile_timeline(getattr(AnimationSpec, factory)(duration=1, distance=12))

        # when: the preset is sampled during its active interval
        state = timeline.sample(0.25)

        # then: the preset still produces a concrete positional state
        assert state.position is not None

    def test_should_resolve_feel_profiles_without_changing_canonical_preset_json(self):
        """Given a feel, when compiled, then easing resolves only in the normalized timeline."""
        # given: a preset authored with a semantic feel
        spec = AnimationSpec.rise(feel="soft", duration=0.6)

        # when: both the authoring model and normalized timeline are serialized
        authored = spec.model_dump(mode="json", by_alias=True)
        event = compile_timeline(spec).events[0]

        # then: canonical authoring JSON keeps the feel while the IR carries resolved easing
        assert authored["effect"]["feel"] == "soft"
        assert authored["effect"]["easing"] is None
        assert event.options["feel"] == "soft"
        assert event.options["easing"] == "ease_out_cubic"

    @pytest.mark.parametrize(
        "factory",
        [
            "fade",
            "rise",
            "fall",
            "slide",
            "zoom",
            "pop",
            "float",
            "pulse",
            "shake",
            "ken_burns",
            "typewriter",
        ],
    )
    def test_should_round_trip_every_compiled_preset_without_changing_samples(self, factory):
        """Given a compiled preset, restoring Timeline JSON preserves all samples."""
        # given: a preset with options that exercise timing, direction, and stagger metadata
        spec = getattr(AnimationSpec, factory)(
            from_="right" if factory in {"rise", "fall", "slide"} else None,
            distance=24,
            duration=0.75,
            delay=0.1,
            easing="ease_in_out_sine",
            stagger=0.04,
            target="words",
            order="reverse",
        )
        timeline = compile_timeline(spec)

        # when: both the authoring model and normalized timeline are serialized and restored
        restored_spec = AnimationSpec.model_validate_json(spec.model_dump_json())
        restored = Timeline.model_validate_json(timeline.model_dump_json())

        # then: canonical authoring and IR round-trips preserve all behavior
        assert restored_spec == spec
        assert compile_timeline(restored_spec) == timeline
        assert restored == timeline
        base = LayerState(position=(30, 40), opacity=0.7, scale=1.5)
        for time in (0.0, 0.1, 0.35, 0.85, 2.0):
            assert restored.sample(time, base) == timeline.sample(time, base)

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
            RotationTrack(
                keyframes=[KeyframeSpec(time=0, value=0), KeyframeSpec(time=1, value=90)]
            ),
            ClipProgressTrack(
                keyframes=[KeyframeSpec(time=0, value=0), KeyframeSpec(time=1, value=1)]
            ),
            BlurTrack(keyframes=[KeyframeSpec(time=0, value=0), KeyframeSpec(time=1, value=10)]),
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
        assert state.rotation == 45.0
        assert state.clip_progress == 0.5
        assert state.blur == 5.0
        assert state.color == "#808080"

        # given: an RGBA color track
        rgba = AnimationSpec.timeline(
            ColorTrack(
                keyframes=[
                    KeyframeSpec(time=0, value="#00000000"),
                    KeyframeSpec(time=1, value="#FFFFFFFF"),
                ]
            )
        )

        # when: the RGBA track is sampled halfway through
        rgba_state = compile_timeline(rgba).sample(0.5)

        # then: the alpha channel is interpolated as part of the color
        assert rgba_state.color == "#80808080"

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
        assert timeline.events[0].stagger is None

    @pytest.mark.parametrize("trigger", ["on_click", "after_previous", "with_previous"])
    def test_should_resolve_every_supported_trigger(self, trigger):
        """Every trigger resolves to a deterministic event anchor."""
        # given: a previous event and a second event using one trigger
        first = AnimationSpec.timeline(
            OpacityTrack(keyframes=[KeyframeSpec(time=0, value=0), KeyframeSpec(time=1, value=1)]),
            timing=TimingSpec(duration=1),
        )
        second = AnimationSpec.timeline(
            ScaleTrack(keyframes=[KeyframeSpec(time=0, value=1), KeyframeSpec(time=1, value=2)]),
            timing=TimingSpec(duration=1, trigger=trigger),
        )
        follower = AnimationSpec.timeline(
            RotationTrack(
                keyframes=[KeyframeSpec(time=0, value=0), KeyframeSpec(time=1, value=90)]
            ),
            timing=TimingSpec(duration=1, trigger="with_previous"),
        )

        # when: the boundary and a parallel follower are compiled
        events = compile_timeline([first, second, follower]).events

        # then: only with_previous overlaps, and its follower joins the new group
        assert events[1].start == (0.0 if trigger == "with_previous" else 1.0)
        assert events[2].start == (0.0 if trigger == "with_previous" else 1.0)

    def test_should_sequence_after_the_longest_parallel_companion(self):
        """A sequence group settles at its longest member before the next group starts."""
        # given: one click group with two parallel effects of different lengths
        first = AnimationSpec.timeline(
            OpacityTrack(keyframes=[KeyframeSpec(time=0, value=0), KeyframeSpec(time=1, value=1)]),
            timing=TimingSpec(duration=1, trigger="on_click", delay=0.25),
        )
        companion = AnimationSpec.timeline(
            ScaleTrack(keyframes=[KeyframeSpec(time=0, value=1), KeyframeSpec(time=1, value=2)]),
            timing=TimingSpec(duration=2, trigger="with_previous"),
        )
        next_group = AnimationSpec.timeline(
            RotationTrack(
                keyframes=[KeyframeSpec(time=0, value=0), KeyframeSpec(time=1, value=90)]
            ),
            timing=TimingSpec(duration=1, trigger="after_previous"),
        )

        # when: the composition is compiled
        events = compile_timeline([first, companion, next_group]).events

        # then: companions share a start and the next group waits for the longest settled end
        assert [(event.start, event.active_start, event.end) for event in events] == [
            (0.0, 0.25, 1.25),
            (0.0, 0.0, 2.0),
            (2.0, 2.0, 3.0),
        ]

    def test_should_keep_absolute_anchor_without_corrupting_relative_sequence(self):
        """An absolute event remains anchored while later relative events follow the cursor."""
        # given: an absolute event placed before an already settled composition
        first = AnimationSpec.timeline(
            OpacityTrack(keyframes=[KeyframeSpec(time=0, value=0), KeyframeSpec(time=1, value=1)]),
            timing=TimingSpec(duration=1),
        )
        absolute = AnimationSpec.timeline(
            ScaleTrack(keyframes=[KeyframeSpec(time=0, value=1), KeyframeSpec(time=0.5, value=2)]),
            timing=TimingSpec(start=0.25, duration=0.5),
        )
        following = AnimationSpec.timeline(
            RotationTrack(
                keyframes=[KeyframeSpec(time=0, value=0), KeyframeSpec(time=0.5, value=90)]
            ),
            timing=TimingSpec(duration=0.5),
        )

        # when: all three events are lowered in input order
        events = compile_timeline([first, absolute, following]).events

        # then: the explicit anchor overlaps, but does not move the serial cursor backwards
        assert [event.start for event in events] == [0.0, 0.25, 1.0]

    def test_should_apply_deterministic_last_event_precedence_during_overlap(self):
        """Later events deterministically win when overlapping tracks target one property."""
        # given: two opacity tracks with an overlapping absolute window
        first = AnimationSpec.timeline(
            OpacityTrack(keyframes=[KeyframeSpec(time=0, value=0), KeyframeSpec(time=1, value=1)]),
            timing=TimingSpec(start=0, duration=1),
        )
        second = AnimationSpec.timeline(
            OpacityTrack(keyframes=[KeyframeSpec(time=0, value=1), KeyframeSpec(time=1, value=0)]),
            timing=TimingSpec(start=0.25, duration=1),
        )

        # when: the overlap is sampled
        timeline = compile_timeline([first, second])

        # then: event order is stable before, during, and after the overlap
        assert timeline.sample(0.1).opacity == pytest.approx(0.1)
        assert timeline.sample(0.5).opacity == pytest.approx(0.75)
        assert timeline.sample(1.5).opacity == pytest.approx(0.0)

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
        restored = Timeline.model_validate_json(timeline.model_dump_json())
        frames = sample_frames(restored, 4)

        # then: serialization and deterministic frame sampling are stable
        assert restored == timeline
        assert [time for time, _ in frames] == [0.0, 0.25, 0.5, 0.75]
        assert frames[-1][1].scale == 2.0

    def test_should_preserve_stagger_metadata_without_inventing_target_cardinality(self):
        """Compilation preserves stagger metadata for consumers that know target cardinality."""
        # given: a preset with explicit stagger configuration
        spec = AnimationSpec.rise(stagger=0.1, target="words", order="reverse")

        # when: it is compiled into the normalized IR
        event = compile_timeline(spec).events[0]

        # then: metadata survives, while the compiler keeps the declared event window
        assert event.stagger == {"delay": 0.1, "target": "words", "order": "reverse"}
        assert event.duration == 0.5

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

    @pytest.mark.parametrize(
        ("effect", "field"),
        [("float", "position"), ("shake", "position"), ("pulse", "scale"), ("ken_burns", "scale")],
    )
    def test_should_sample_every_state_representable_preset(self, effect, field):
        """Every state-representable public preset changes a LayerState deterministically."""
        # given: a preset and a base state with position for positional effects
        spec = getattr(AnimationSpec, effect)(duration=1, distance=12)
        base = LayerState(position=(10, 20))

        # when: the effect is sampled at its midpoint
        state = compile_timeline(spec).sample(0.25, base)

        # then: the preset maps to an explicit state property
        assert getattr(state, field) != getattr(base, field)

    @pytest.mark.parametrize(
        ("factory", "origin", "expected"),
        [
            ("rise", "top", (10.0, -4.0)),
            ("fall", "bottom", (10.0, 44.0)),
            ("slide", "left", (-14.0, 20.0)),
        ],
    )
    def test_should_honor_preset_direction_from_the_base_position(self, factory, origin, expected):
        """Directional presets apply their offset from the supplied base position."""
        # given: a directional preset with a non-default base position
        spec = getattr(AnimationSpec, factory)(from_=origin, duration=1, distance=24)

        # when: the preset is sampled at its start
        state = compile_timeline(spec).sample(0, LayerState(position=(10, 20)))

        # then: the explicit direction determines the starting offset
        assert state.position == expected

    def test_should_compose_presets_with_non_default_base_values(self):
        """Preset sampling preserves the settled base values at the end of motion."""
        # given: a fade and pulse applied to non-default base state values
        fade = compile_timeline(AnimationSpec.fade(duration=1))
        pulse = compile_timeline(AnimationSpec.pulse(duration=1))
        base = LayerState(opacity=0.4, scale=2)

        # when: both presets are sampled at their settled endpoints
        fade_state = fade.sample(1, base)
        pulse_state = pulse.sample(1, base)

        # then: preset transforms compose with rather than replace base values
        assert fade_state.opacity == 0.4
        assert pulse_state.scale == 2.0

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

        with pytest.raises(PydanticValidationError, match="finite"):
            Timeline.model_validate(
                {
                    "events": [
                        {
                            "source": "timeline",
                            "start": float("inf"),
                            "delay": 0,
                            "duration": 1,
                        }
                    ]
                }
            )

        with pytest.raises(ValidationError, match="opacity keyframes"):
            Timeline.model_validate(
                {
                    "events": [
                        {
                            "source": "timeline",
                            "start": 0,
                            "delay": 0,
                            "duration": 1,
                            "tracks": [
                                {
                                    "property": "opacity",
                                    "keyframes": [{"time": 0, "value": "invalid"}],
                                }
                            ],
                        }
                    ]
                }
            )

        with pytest.raises(ValidationError, match="opacity"):
            LayerState().with_values(opacity=2)
        with pytest.raises(ValidationError, match="hex color"):
            LayerState().with_values(color="not-a-color")

    def test_should_coerce_transition_inputs_and_reject_invalid_transitions(self):
        """Transition compilation accepts public shorthand and rejects invalid timing."""
        # given: shorthand and malformed transition inputs
        # when: each input is normalized
        shorthand = compile_transition_timeline("fade")
        directional = compile_transition_timeline({"effect": "push", "direction": "right"})

        # then: shorthand preserves the transition effect and invalid duration fails clearly
        assert shorthand.events[0].effect == "fade"
        assert directional.events[0].options["direction"] == "right"
        with pytest.raises(ValidationError, match="greater than 0"):
            compile_transition_timeline({"effect": "fade", "duration": 0})
        with pytest.raises(PydanticValidationError, match="Invalid JSON"):
            Timeline.model_validate_json("{")

        # then: errors identify the invalid boundary rather than failing in a renderer
