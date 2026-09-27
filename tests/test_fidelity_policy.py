"""Black-box specifications for the pixel and hash fidelity policy."""

import json
from pathlib import Path

import pytest
from PIL import Image
from quickthumb import (
    Canvas,
    FidelityComparison,
    FidelityPolicy,
    FidelityTolerance,
    compare_fidelity,
)
from quickthumb.errors import InputError, ValidationError


def card() -> Canvas:
    """A white 40x30 card with a red rectangle."""
    return Canvas(40, 30).background(color="#FFFFFF").shape("rectangle", (5, 5), 20, 15, "#FF2D55")


def shifted(image: Image.Image, delta: int) -> Image.Image:
    """Darken every RGB channel by `delta` while keeping alpha."""
    red, green, blue, alpha = image.split()
    red, green, blue = (
        band.point(lambda value: max(0, value - delta)) for band in (red, green, blue)
    )
    return Image.merge("RGBA", (red, green, blue, alpha))


def with_block(image: Image.Image, box: tuple[int, int, int, int], color) -> Image.Image:
    """Paint an opaque block over part of an image."""
    changed = image.copy()
    changed.paste(color, box)
    return changed


def test_png_export_matches_its_canonical_sample_exactly(tmp_path: Path):
    """A PNG export of a canvas is an exact match for its canonical still sample."""
    # given: a canvas, its canonical still sample, and its PNG export
    canvas = card()
    frame = canvas.sample().frames[0]
    output = tmp_path / "card.png"
    canvas.render(str(output))

    # when: the export is judged against the sample under the default policy
    comparison = compare_fidelity(frame, output, output_format="png")

    # then: every visible channel matches and nothing is violated
    assert comparison.verdict == "exact"
    assert comparison.within_policy is True
    assert comparison.violations == []
    assert comparison.measurements.different_pixels == 0
    assert comparison.measurements.max_channel_delta == 0
    assert comparison.measurements.hash_similarity == 1.0


def test_small_channel_drift_is_tolerated_and_measured():
    """Channel drift within pixel_tolerance is tolerated, not reported as exact."""
    # given: an output whose channels all drift by 2 from the sample
    frame = card().sample().frames[0]
    output = shifted(frame.to_image(), 2)

    # when: it is judged under the default tolerance of 2
    comparison = compare_fidelity(frame, output)

    # then: the difference is visible in the measurements but within policy
    assert comparison.verdict == "tolerated"
    assert comparison.within_policy is True
    assert comparison.violations == []
    assert comparison.measurements.max_channel_delta == 2
    assert comparison.measurements.different_pixels == 0
    assert comparison.measurements.mean_absolute_error == pytest.approx(3 * 2 / (4 * 255))


def test_localized_changes_within_the_allowed_ratio_are_tolerated():
    """A few changed pixels are tolerated while their share stays under the limit."""
    # given: an output with a 2x2 block (4 of 1200 pixels) repainted black
    frame = card().sample().frames[0]
    output = with_block(frame.to_image(), (30, 20, 32, 22), (0, 0, 0, 255))
    policy = FidelityPolicy(default=FidelityTolerance(max_different_pixel_ratio=0.01))

    # when: it is judged under a policy that allows 1% of pixels to differ
    comparison = compare_fidelity(frame, output, policy=policy)

    # then: the changed pixels are counted and still accepted
    assert comparison.verdict == "tolerated"
    assert comparison.measurements.different_pixels == 4
    assert comparison.measurements.different_pixel_ratio == pytest.approx(4 / 1200)
    assert comparison.measurements.max_channel_delta == 255


def test_changes_beyond_the_allowed_ratio_are_out_of_policy():
    """Changed pixels above the allowed share are out of policy with a named reason."""
    # given: the same localized change under the default zero-ratio policy
    frame = card().sample().frames[0]
    output = with_block(frame.to_image(), (30, 20, 32, 22), (0, 0, 0, 255))

    # when: it is judged
    comparison = compare_fidelity(frame, output)

    # then: the verdict names the pixel-ratio criterion with its measurement and limit
    assert comparison.verdict == "out_of_policy"
    assert comparison.within_policy is False
    [violation] = comparison.violations
    assert violation.criterion == "different_pixel_ratio"
    assert violation.measured == pytest.approx(4 / 1200)
    assert violation.limit == 0.0
    assert "0.33% of pixels differ by more than 2" in violation.message


def test_perceptually_different_output_violates_the_hash_criterion():
    """A structurally different output fails the perceptual similarity criterion."""
    # given: an output whose left half is painted black
    frame = card().sample().frames[0]
    output = with_block(frame.to_image(), (0, 0, 20, 30), (0, 0, 0, 255))
    policy = FidelityPolicy(default=FidelityTolerance(max_different_pixel_ratio=1.0))

    # when: it is judged under a policy that ignores the pixel ratio
    comparison = compare_fidelity(frame, output, policy=policy)

    # then: only the perceptual criterion fails
    assert comparison.verdict == "out_of_policy"
    assert [violation.criterion for violation in comparison.violations] == ["hash_similarity"]
    assert comparison.measurements.hash_similarity < 0.95


def test_mean_error_limit_rejects_widespread_drift():
    """An optional mean-error limit rejects drift that the pixel tolerance allows."""
    # given: drift of 20 on every channel and a tolerance that ignores per-pixel deltas
    frame = card().sample().frames[0]
    output = shifted(frame.to_image(), 20)
    policy = FidelityPolicy(
        default=FidelityTolerance(pixel_tolerance=255, max_mean_absolute_error=0.01)
    )

    # when: it is judged
    comparison = compare_fidelity(frame, output, policy=policy)

    # then: the mean-error criterion fails with its measured value
    assert comparison.verdict == "out_of_policy"
    [violation] = comparison.violations
    assert violation.criterion == "mean_absolute_error"
    assert violation.measured == comparison.measurements.mean_absolute_error
    assert violation.limit == 0.01


def test_dimension_mismatch_is_out_of_policy_without_pixel_measurements():
    """Outputs of another size cannot be compared pixel by pixel."""
    # given: an output rendered at a different size
    frame = card().sample().frames[0]
    output = frame.to_image().resize((80, 60))

    # when: it is judged
    comparison = compare_fidelity(frame, output)

    # then: the dimensions criterion fails and pixel measurements are absent
    assert comparison.verdict == "out_of_policy"
    assert comparison.violations[0].criterion == "dimensions"
    assert comparison.violations[0].measured == (80, 60)
    assert comparison.violations[0].limit == (40, 30)
    assert comparison.measurements.different_pixel_ratio is None
    assert comparison.measurements.max_channel_delta is None


def test_format_specific_tolerance_applies_without_changing_the_sample():
    """One policy judges the same output differently per export format."""
    # given: one sample, one slightly changed output, and a looser SVG tolerance
    frame = card().sample().frames[0]
    output = with_block(frame.to_image(), (30, 20, 32, 22), (0, 0, 0, 255))
    policy = FidelityPolicy(
        formats={"svg": FidelityTolerance(pixel_tolerance=8, max_different_pixel_ratio=0.02)}
    )

    # when: the output is judged as PNG and as SVG
    as_png = compare_fidelity(frame, output, output_format="png", policy=policy)
    as_svg = compare_fidelity(frame, output, output_format=".SVG", policy=policy)

    # then: each verdict uses its format's tolerance and reports which one applied
    assert as_png.verdict == "out_of_policy"
    assert as_png.tolerance == policy.default
    assert as_svg.verdict == "tolerated"
    assert as_svg.output_format == "svg"
    assert as_svg.tolerance.max_different_pixel_ratio == 0.02
    assert as_png.measurements.different_pixels == as_svg.measurements.different_pixels


def test_jpeg_output_uses_the_jpg_tolerance():
    """The jpeg spelling resolves to the jpg format tolerance."""
    # given: a policy with a JPG-specific tolerance
    policy = FidelityPolicy(formats={"jpg": FidelityTolerance(pixel_tolerance=12)})

    # when / then: both spellings resolve to it
    assert policy.tolerance_for("jpeg").pixel_tolerance == 12
    assert policy.tolerance_for("JPG").pixel_tolerance == 12
    assert policy.tolerance_for("png") == policy.default


def test_policy_format_keys_accept_the_same_spellings_as_lookups():
    """Policy keys are spelled canonically, so aliases and suffixes work as keys too."""
    # when: a policy is written with alias and suffix spellings
    policy = FidelityPolicy.model_validate(
        {"formats": {"jpeg": {"pixel_tolerance": 12}, ".SVG": {}, "htm": {}}}
    )

    # then: the keys are stored canonically and resolve from any spelling
    assert set(policy.formats) == {"jpg", "svg", "html"}
    assert policy.tolerance_for(".jpg").pixel_tolerance == 12
    assert policy.tolerance_for("htm") == policy.formats["html"]


@pytest.mark.parametrize("output_format", ["jepg", "tiff", "image/jpeg", ""])
def test_unknown_output_format_is_rejected_instead_of_using_the_default(output_format):
    """A misspelled or unsupported format fails instead of silently using the default."""
    # given: a policy whose JPG tolerance is stricter than its default
    policy = FidelityPolicy(
        default=FidelityTolerance(max_different_pixel_ratio=1.0, min_hash_similarity=0.0),
        formats={"jpg": FidelityTolerance()},
    )
    frame = card().sample().frames[0]

    # when: the output is judged under a format the policy cannot describe
    with pytest.raises(InputError) as error:
        compare_fidelity(frame, frame, output_format=output_format, policy=policy)

    # then: the error names the problem and lists the supported formats
    detail = error.value.details[0]
    assert detail.code == "unsupported_output_format"
    assert detail.suggestion is not None
    assert "jpg" in detail.suggestion


def test_hidden_color_is_ignored_but_alpha_changes_count():
    """Transparent pixels compare as transparent, while visible alpha changes count."""
    # given: a transparent sample, a copy with different hidden color, and an opaque copy
    sample = Image.new("RGBA", (4, 4), (0, 0, 0, 0))
    hidden_color = Image.new("RGBA", (4, 4), (255, 0, 0, 0))
    flattened = Image.new("RGBA", (4, 4), (255, 255, 255, 255))

    # when: both are judged against the sample
    hidden = compare_fidelity(sample, hidden_color)
    opaque = compare_fidelity(sample, flattened)

    # then: hidden color is exact, but losing transparency is a real difference
    assert hidden.verdict == "exact"
    assert opaque.verdict == "out_of_policy"
    assert opaque.measurements.different_pixels == 16


def test_policy_and_comparison_round_trip_through_json():
    """Policies are JSON-configurable and comparisons are JSON-serializable."""
    # given: a policy written as JSON
    policy = FidelityPolicy.model_validate_json(
        json.dumps(
            {
                "default": {"pixel_tolerance": 1},
                "formats": {"pdf": {"pixel_tolerance": 6, "max_different_pixel_ratio": 0.01}},
            }
        )
    )
    frame = card().sample().frames[0]

    # when: a comparison under it is serialized and loaded back
    comparison = compare_fidelity(
        frame, shifted(frame.to_image(), 4), output_format="pdf", policy=policy
    )
    payload = json.loads(comparison.model_dump_json())
    restored = FidelityComparison.model_validate(payload)

    # then: the JSON keeps the verdict, the applied tolerance, and the measurements
    assert payload["verdict"] == "tolerated"
    assert payload["tolerance"]["pixel_tolerance"] == 6
    assert payload["measurements"]["max_channel_delta"] == 4
    assert restored == comparison


@pytest.mark.parametrize(
    "payload",
    [
        {"formats": {"bmp": {}}},
        {"default": {"pixel_tolerance": 256}},
        {"default": {"max_different_pixel_ratio": 1.5}},
        {"default": {"min_hash_similarity": float("nan")}},
        {"default": {"unknown": 1}},
    ],
)
def test_invalid_policies_are_rejected(payload):
    """Unknown formats and out-of-range limits are rejected when the policy loads."""
    with pytest.raises(ValidationError):
        FidelityPolicy.model_validate(payload)


def test_unreadable_output_is_an_input_error(tmp_path: Path):
    """A missing or unreadable output raises a structured input error."""
    frame = card().sample().frames[0]

    with pytest.raises(InputError) as error:
        compare_fidelity(frame, tmp_path / "missing.png")

    assert error.value.details[0].code == "unreadable_image"
