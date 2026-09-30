import math
from typing import Any, cast

import pytest
from quickthumb import (
    AnimationSpec,
    ColorTrack,
    KeyframeSpec,
    ScaleTrack,
)
from quickthumb.errors import ValidationError
from quickthumb.motion import (
    LayerState,
    apply_transform,
    compile_timeline,
    easing_value,
    transform_matrix,
    validate_easing_name,
)


class TestMotionInterpolation:
    """Black-box coverage for deterministic easing and transform interpolation."""

    def test_should_apply_named_easing_to_all_track_segments(self):
        """A timeline easing changes each segment while preserving exact boundaries."""
        # given: a cubic-eased scale track with two segments
        animation = AnimationSpec.timeline(
            ScaleTrack(
                keyframes=[
                    KeyframeSpec(time=0, value=0),
                    KeyframeSpec(time=1, value=1),
                    KeyframeSpec(time=2, value=2),
                ]
            ),
            timing=cast(Any, {"duration": 2}),
            easing="ease_in_quad",
        )

        # when: the timeline is sampled at boundaries and between keyframes
        timeline = compile_timeline(animation)

        # then: the normalized sample is eased within each segment
        assert timeline.sample(0).scale == 0
        assert timeline.sample(0.5).scale == pytest.approx(0.25)
        assert timeline.sample(1).scale == 1
        assert timeline.sample(1.5).scale == pytest.approx(1.25)

    def test_should_validate_easing_names_and_clamp_progress_boundaries(self):
        """Supported names are deterministic and invalid names fail clearly."""
        # given: finite progress values and an unknown easing name
        # when: easing helpers are called
        # then: endpoints remain fixed and invalid input is rejected
        assert validate_easing_name(None) == "linear"
        assert easing_value("ease_out_cubic", 0) == 0
        assert easing_value("ease_out_cubic", 1) == 1
        assert easing_value("ease_out_cubic", 2) == 1
        with pytest.raises(ValidationError, match="finite"):
            easing_value("linear", math.nan)
        with pytest.raises(ValidationError, match="finite"):
            easing_value("linear", math.inf)
        with pytest.raises(ValidationError, match="unknown easing"):
            validate_easing_name("spring")

        # given: an invalid easing through the public animation contract
        # when: the timeline animation is constructed
        # then: the model rejects the invalid name before sampling
        with pytest.raises(ValidationError, match="ease_in_quad"):
            AnimationSpec.timeline(
                ScaleTrack(keyframes=[KeyframeSpec(time=0, value=1)]), easing=cast(Any, "spring")
            )

        # given: an effect combined with timeline-only easing
        # when: the public animation contract is constructed
        # then: mutually ambiguous easing configuration is rejected
        with pytest.raises(ValidationError, match="only valid with tracks"):
            AnimationSpec(effect=cast(Any, {"type": "fade"}), easing="ease_in_quad")

    def test_should_sample_each_supported_easing_family(self):
        """Every public easing family produces finite deterministic progress."""
        # given: one representative from every supported easing branch
        names = [
            "linear",
            "ease",
            "ease_in",
            "ease_out",
            "ease_in_out",
            "ease_in_quad",
            "ease_out_quad",
            "ease_in_out_quad",
            "ease_in_cubic",
            "ease_out_cubic",
            "ease_in_out_cubic",
            "ease_in_quart",
            "ease_out_quart",
            "ease_in_out_quart",
            "ease_in_quint",
            "ease_out_quint",
            "ease_in_out_quint",
            "ease_in_sine",
            "ease_out_sine",
            "ease_in_out_sine",
            "ease_in_back",
            "ease_out_back",
            "ease_in_out_back",
        ]

        # when: each easing is evaluated at an interior progress
        values = [easing_value(name, 0.25) for name in names]

        # then: all supported curves return deterministic finite values
        assert all(math.isfinite(value) for value in values)

    def test_should_keep_bounded_properties_valid_with_overshooting_easing(self):
        """Back easing cannot produce invalid bounded or color state."""
        # given: valid bounded presets and tracks using overshooting easing curves
        # when: each animation is sampled at its overshoot point
        # then: the state remains within its declared bounds
        for easing in ("ease_in_back", "ease_out_back", "ease_in_out_back"):
            state = compile_timeline(AnimationSpec.fade(duration=1, easing=easing)).sample(0.25)
            assert 0.0 <= state.opacity <= 1.0
            clip = compile_timeline(AnimationSpec.typewriter(duration=1, easing=easing)).sample(
                0.25
            )
            assert 0.0 <= clip.clip_progress <= 1.0
            color = compile_timeline(
                AnimationSpec.timeline(
                    ColorTrack(
                        keyframes=[
                            KeyframeSpec(time=0, value="#000000"),
                            KeyframeSpec(time=1, value="#FFFFFF"),
                        ]
                    ),
                    easing=easing,
                )
            ).sample(0.25)
            assert color.color is not None and len(color.color) == 7

    def test_should_interpolate_mixed_rgb_and_rgba_colors_deterministically(self):
        """Missing alpha is treated as opaque and output channels remain stable."""
        # given: a color track changing from RGB to transparent RGBA
        animation = AnimationSpec.timeline(
            ColorTrack(
                keyframes=[
                    KeyframeSpec(time=0, value="#000000"),
                    KeyframeSpec(time=1, value="#FFFFFFFF"),
                ]
            )
        )

        # when: the midpoint is sampled
        state = compile_timeline(animation).sample(0.5)

        # then: RGB and alpha channels are interpolated with canonical casing
        assert state.color == "#808080FF"

    def test_should_compose_transforms_as_scale_then_rotation_then_translation(self):
        """Transform composition uses the documented T·R·S order."""
        # given: a state with scale, quarter-turn rotation, and translation
        state = LayerState(position=(10, 20), scale=2, rotation=90)

        # when: a local point and the matrix are resolved
        transformed = apply_transform((1, 0), state)
        matrix = transform_matrix(state)

        # then: scale, rotation, and translation produce the same result
        assert transformed == pytest.approx((10, 22))
        assert matrix[0][2] == 10
        assert matrix[1][2] == 20

    def test_should_reject_non_finite_transform_coordinates(self):
        """Transform construction rejects non-finite state and point coordinates."""
        # given: non-finite coordinates at both public transform boundaries
        # when: layer state and point transforms are constructed
        # then: both fail with clear validation errors
        with pytest.raises(ValueError, match="finite"):
            LayerState(position=(math.nan, 0))
        with pytest.raises(ValidationError, match="finite"):
            apply_transform((math.inf, 0), LayerState())

    def test_should_reject_invalid_bases_and_restored_easing_metadata(self):
        """Sampling and timeline deserialization reject invalid runtime metadata."""
        # given: an empty timeline and a serialized event with an unknown easing
        # when: callers provide invalid base state or restore invalid metadata
        # then: both invalid inputs fail before rendering
        with pytest.raises(ValidationError, match="LayerState"):
            compile_timeline([]).sample(0, base=cast(Any, {}))
        with pytest.raises(ValidationError, match="unknown easing"):
            compile_timeline([]).model_validate(
                {
                    "events": [
                        {
                            "source": "timeline",
                            "start": 0,
                            "delay": 0,
                            "duration": 0,
                            "options": {"easing": "spring"},
                        }
                    ]
                }
            )


class TestCustomEasingAndKeyframeTiming:
    """Custom cubic-bezier easing, per-keyframe easing, and hold keyframes."""

    @staticmethod
    def _scale(keyframes, **timeline):
        return compile_timeline(AnimationSpec.timeline(ScaleTrack(keyframes=keyframes), **timeline))

    def test_should_accept_custom_cubic_bezier_matching_named_ease(self):
        """A bezier with the named curve's points reproduces that curve."""
        # given: the points behind the named "ease" easing
        curve = {"type": "cubic_bezier", "points": [0.25, 0.1, 0.25, 1.0]}

        # when/then: both forms agree and endpoints stay fixed
        for progress in (0.0, 0.2, 0.5, 0.8, 1.0):
            assert easing_value(curve, progress) == pytest.approx(easing_value("ease", progress))
        assert validate_easing_name(curve) == "cubic_bezier"

    def test_should_allow_overshoot_but_reject_invalid_bezier_points(self):
        """y may overshoot while x outside [0, 1] and bad shapes are rejected."""
        # given/when: an overshooting curve
        overshoot = {"type": "cubic_bezier", "points": [0.34, 1.56, 0.64, 1.0]}

        # then: it rises above 1 mid-way, and invalid points fail clearly
        assert max(easing_value(overshoot, i / 20) for i in range(21)) > 1.0
        with pytest.raises(ValidationError, match="x1 and x2"):
            easing_value({"type": "cubic_bezier", "points": [1.5, 0, 0.5, 1]}, 0.5)
        with pytest.raises(ValidationError):
            validate_easing_name({"type": "cubic_bezier", "points": [0, 0, 1]})

    def test_should_use_custom_easing_on_an_animation_and_round_trip_json(self):
        """An animation-level bezier samples through and serializes stably."""
        # given: a timeline eased by a custom curve
        animation = AnimationSpec.timeline(
            ScaleTrack(keyframes=[KeyframeSpec(time=0, value=0), KeyframeSpec(time=1, value=1)]),
            easing=cast(Any, {"type": "cubic_bezier", "points": [0.5, 0, 0.5, 1]}),
        )

        # when: it is sampled and re-parsed from JSON
        restored = AnimationSpec.model_validate_json(animation.model_dump_json())

        # then: the curve is symmetric and survives the round trip
        assert compile_timeline(restored).sample(0.5).scale == pytest.approx(0.5)
        assert compile_timeline(restored).sample(0.25).scale < 0.25

    def test_should_ease_each_segment_with_its_own_keyframe_easing(self):
        """A keyframe easing shapes the segment leaving it; others use the default."""
        # given: a first segment eased by quad and a second that inherits linear
        timeline = self._scale(
            [
                KeyframeSpec(time=0, value=0, easing="ease_in_quad"),
                KeyframeSpec(time=1, value=1),
                KeyframeSpec(time=2, value=2),
            ],
            timing=cast(Any, {"duration": 2}),
            easing="linear",
        )

        # when/then: segment one is eased, segment two follows the animation
        assert timeline.sample(0.5).scale == pytest.approx(0.25)
        assert timeline.sample(1.5).scale == pytest.approx(1.5)

    def test_should_step_at_the_next_keyframe_for_hold_keyframes(self):
        """A hold keeps its value until the next keyframe, then steps."""
        # given: a held first keyframe followed by a smooth segment
        timeline = self._scale(
            [
                KeyframeSpec(time=0, value=0, hold=True),
                KeyframeSpec(time=1, value=1),
                KeyframeSpec(time=2, value=2),
            ],
            timing=cast(Any, {"duration": 2}),
        )

        # when/then: nothing moves until t=1, where it steps, then interpolates
        assert timeline.sample(0.99).scale == 0
        assert timeline.sample(1).scale == 1
        assert timeline.sample(1.5).scale == pytest.approx(1.5)

    def test_should_render_identically_when_new_fields_are_omitted(self):
        """Omitting easing/hold serializes exactly as before."""
        # given/when: a keyframe using only the original fields
        dumped = KeyframeSpec(time=1, value=2).model_dump(mode="json")

        # then: the new fields do not appear in the document
        assert dumped == {"type": "keyframe", "time": 1.0, "value": 2}
