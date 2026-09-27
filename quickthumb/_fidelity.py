from __future__ import annotations

from functools import reduce
from typing import TypeAlias

from PIL import Image, ImageChops

from quickthumb._diff import (
    DEFAULT_HASH_SIZE,
    ImageSource,
    _hamming_distance,
    _load_image,
    _perceptual_hash_image,
    _validate_hash_size,
)
from quickthumb.errors import InputError
from quickthumb.models import (
    CanonicalFrame,
    FidelityComparison,
    FidelityMeasurements,
    FidelityPolicy,
    FidelityTolerance,
    FidelityViolation,
)

FidelitySource: TypeAlias = ImageSource | CanonicalFrame


def compare_fidelity(
    expected: FidelitySource,
    actual: FidelitySource,
    *,
    output_format: str | None = None,
    policy: FidelityPolicy | None = None,
    hash_size: int = DEFAULT_HASH_SIZE,
) -> FidelityComparison:
    """Judge an output against a canonical sample under a fidelity policy.

    `expected` is usually a `CanonicalFrame` from `sample()`, and `actual` a
    raster of the exported output. The tolerance for `output_format` is taken
    from `policy` (the default `FidelityPolicy()` when omitted), so one policy
    can hold stricter limits for PNG and looser ones for browser-rendered or
    lossy formats. The result separates exact matches, tolerated differences,
    and out-of-policy output, and names every criterion that failed.
    """
    _validate_hash_size(hash_size)
    policy = policy or FidelityPolicy()
    tolerance = policy.tolerance_for(output_format)
    expected_image = _visible_rgba(_load(expected, "expected"))
    actual_image = _visible_rgba(_load(actual, "actual"))

    expected_hash = _perceptual_hash_image(expected_image, hash_size)
    actual_hash = _perceptual_hash_image(actual_image, hash_size)
    hash_distance = _hamming_distance(expected_hash, actual_hash)
    pixels = (
        _pixel_measurements(expected_image, actual_image, tolerance.pixel_tolerance)
        if expected_image.size == actual_image.size
        else {}
    )
    measurements = FidelityMeasurements(
        expected_size=expected_image.size,
        actual_size=actual_image.size,
        expected_hash=expected_hash,
        actual_hash=actual_hash,
        hash_distance=hash_distance,
        hash_similarity=1.0 - hash_distance / (hash_size * hash_size),
        **pixels,
    )

    violations = _violations(measurements, tolerance)
    if violations:
        verdict = "out_of_policy"
    elif measurements.max_channel_delta == 0:
        verdict = "exact"
    else:
        verdict = "tolerated"
    return FidelityComparison(
        # The model spells the format canonically; tolerance_for() already rejected unknown ones.
        output_format=output_format,  # ty: ignore[invalid-argument-type]
        verdict=verdict,
        tolerance=tolerance,
        measurements=measurements,
        violations=violations,
    )


def _load(source: FidelitySource, name: str) -> Image.Image:
    if isinstance(source, CanonicalFrame):
        return source.to_image()
    try:
        return _load_image(source)
    except ValueError as error:
        raise InputError(
            f"{name} image: {error}",
            code="unreadable_image",
            suggestion="pass a readable raster image path, PIL image, or CanonicalFrame",
        ) from error


def _visible_rgba(image: Image.Image) -> Image.Image:
    """Clear the hidden color of fully transparent pixels."""
    alpha = image.getchannel("A")
    if alpha.histogram()[0] == 0:
        return image
    visible = Image.new("RGBA", image.size)
    visible.paste(image, mask=alpha.point([0] + [255] * 255))
    return visible


def _pixel_measurements(expected: Image.Image, actual: Image.Image, pixel_tolerance: int) -> dict:
    difference = ImageChops.difference(expected, actual)
    # Per-pixel largest channel delta: a pixel differs when any channel exceeds the tolerance.
    peak = reduce(ImageChops.lighter, difference.split())
    # The RGBA histogram holds 256 bins per band, so a bin's delta is its index mod 256.
    total_delta = sum((index % 256) * count for index, count in enumerate(difference.histogram()))
    pixel_count = expected.width * expected.height
    different_pixels = sum(peak.histogram()[pixel_tolerance + 1 :])
    return {
        "pixel_count": pixel_count,
        "different_pixels": different_pixels,
        "different_pixel_ratio": different_pixels / pixel_count,
        "mean_absolute_error": total_delta / (pixel_count * 4 * 255),
        "max_channel_delta": peak.getextrema()[1],
    }


def _violations(
    measurements: FidelityMeasurements, tolerance: FidelityTolerance
) -> list[FidelityViolation]:
    violations: list[FidelityViolation] = []
    if measurements.expected_size != measurements.actual_size:
        expected_width, expected_height = measurements.expected_size
        actual_width, actual_height = measurements.actual_size
        violations.append(
            FidelityViolation(
                criterion="dimensions",
                measured=measurements.actual_size,
                limit=measurements.expected_size,
                message=(
                    f"output is {actual_width}x{actual_height} but the sample is "
                    f"{expected_width}x{expected_height}"
                ),
            )
        )
    ratio = measurements.different_pixel_ratio
    if ratio is not None and ratio > tolerance.max_different_pixel_ratio:
        violations.append(
            FidelityViolation(
                criterion="different_pixel_ratio",
                measured=ratio,
                limit=tolerance.max_different_pixel_ratio,
                message=(
                    f"{ratio:.2%} of pixels differ by more than "
                    f"{tolerance.pixel_tolerance}, above the "
                    f"{tolerance.max_different_pixel_ratio:.2%} allowed"
                ),
            )
        )
    error = measurements.mean_absolute_error
    limit = tolerance.max_mean_absolute_error
    if error is not None and limit is not None and error > limit:
        violations.append(
            FidelityViolation(
                criterion="mean_absolute_error",
                measured=error,
                limit=limit,
                message=f"mean absolute error {error:.6f} is above the {limit:.6f} allowed",
            )
        )
    similarity = measurements.hash_similarity
    if similarity < tolerance.min_hash_similarity:
        violations.append(
            FidelityViolation(
                criterion="hash_similarity",
                measured=similarity,
                limit=tolerance.min_hash_similarity,
                message=(
                    f"perceptual hash similarity {similarity:.4f} is below the "
                    f"{tolerance.min_hash_similarity:.4f} required"
                ),
            )
        )
    return violations
