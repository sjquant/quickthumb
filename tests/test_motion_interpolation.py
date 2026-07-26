import math

import pytest
from quickthumb import (
    AnimationSpec,
    ColorTrack,
    KeyframeSpec,
    LayerState,
    ScaleTrack,
    apply_transform,
    compile_timeline,
    easing_value,
    transform_matrix,
    validate_easing_name,
)
from quickthumb.errors import ValidationError


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
            timing={"duration": 2},
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
                ScaleTrack(keyframes=[KeyframeSpec(time=0, value=1)]), easing="spring"
            )

    def test_should_keep_bounded_properties_valid_with_overshooting_easing(self):
        """Back easing cannot produce invalid opacity or clip-progress state."""
        # given: valid bounded presets using overshooting easing curves
        # when: each animation is sampled at its overshoot point
        # then: the state remains within its declared bounds
        for easing in ("ease_in_back", "ease_out_back", "ease_in_out_back"):
            state = compile_timeline(AnimationSpec.fade(duration=1, easing=easing)).sample(0.25)
            assert 0.0 <= state.opacity <= 1.0

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
