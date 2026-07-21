from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from pathlib import Path
from typing import TypeAlias

from PIL import Image, ImageChops, UnidentifiedImageError

ImageSource: TypeAlias = str | Path | Image.Image

DEFAULT_HASH_SIZE = 8
DEFAULT_HASH_THRESHOLD = 0.95
DEFAULT_PIXEL_TOLERANCE = 2
DEFAULT_MAX_DIFFERENT_PIXEL_RATIO = 0.0


@dataclass(frozen=True)
class ImageDiff:
    """Structured comparison result for two raster images."""

    matches: bool
    expected_size: tuple[int, int]
    actual_size: tuple[int, int]
    exact: bool
    pixel_count: int | None
    different_pixels: int | None
    different_pixel_ratio: float | None
    mean_absolute_error: float | None
    max_channel_delta: int | None
    expected_hash: str
    actual_hash: str
    hash_distance: int
    hash_similarity: float
    threshold: float
    pixel_tolerance: int
    max_different_pixel_ratio: float
    reason: str | None = None

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable representation of the comparison."""
        return {
            "matches": self.matches,
            "expected_size": list(self.expected_size),
            "actual_size": list(self.actual_size),
            "exact": self.exact,
            "pixel_count": self.pixel_count,
            "different_pixels": self.different_pixels,
            "different_pixel_ratio": self.different_pixel_ratio,
            "mean_absolute_error": self.mean_absolute_error,
            "max_channel_delta": self.max_channel_delta,
            "expected_hash": self.expected_hash,
            "actual_hash": self.actual_hash,
            "hash_distance": self.hash_distance,
            "hash_similarity": self.hash_similarity,
            "threshold": self.threshold,
            "pixel_tolerance": self.pixel_tolerance,
            "max_different_pixel_ratio": self.max_different_pixel_ratio,
            "reason": self.reason,
        }

    def format_text(self) -> str:
        """Return a concise human-readable comparison summary."""
        status = "MATCH" if self.matches else "MISMATCH"
        lines = [
            status,
            f"size: expected={self.expected_size[0]}x{self.expected_size[1]} "
            f"actual={self.actual_size[0]}x{self.actual_size[1]}",
            f"exact: {'yes' if self.exact else 'no'}",
            f"hash similarity: {self.hash_similarity:.4f} (distance {self.hash_distance})",
        ]
        if self.different_pixel_ratio is not None:
            lines.extend(
                [
                    f"different pixels: {self.different_pixels}/{self.pixel_count} "
                    f"({self.different_pixel_ratio:.2%})",
                    f"mean absolute error: {self.mean_absolute_error:.6f}",
                    f"max channel delta: {self.max_channel_delta}",
                ]
            )
        if self.reason is not None:
            lines.append(f"reason: {self.reason}")
        return "\n".join(lines)


@dataclass(frozen=True)
class _PixelMetrics:
    """Internal pixel-level metrics for same-sized images."""

    pixel_count: int
    different_pixels: int
    different_pixel_ratio: float
    mean_absolute_error: float
    max_channel_delta: int


def assert_image_similar(
    expected: ImageSource,
    actual: ImageSource,
    *,
    threshold: float = DEFAULT_HASH_THRESHOLD,
    pixel_tolerance: int = DEFAULT_PIXEL_TOLERANCE,
    max_different_pixel_ratio: float = DEFAULT_MAX_DIFFERENT_PIXEL_RATIO,
    hash_size: int = DEFAULT_HASH_SIZE,
) -> ImageDiff:
    """Assert that an actual image is close enough to a golden image for CI."""
    comparison = compare_images(
        expected,
        actual,
        threshold=threshold,
        pixel_tolerance=pixel_tolerance,
        max_different_pixel_ratio=max_different_pixel_ratio,
        hash_size=hash_size,
    )
    if not comparison.matches:
        raise AssertionError(comparison.format_text())
    return comparison


def compare_images(
    expected: ImageSource,
    actual: ImageSource,
    *,
    threshold: float = DEFAULT_HASH_THRESHOLD,
    pixel_tolerance: int = DEFAULT_PIXEL_TOLERANCE,
    max_different_pixel_ratio: float = DEFAULT_MAX_DIFFERENT_PIXEL_RATIO,
    hash_size: int = DEFAULT_HASH_SIZE,
) -> ImageDiff:
    """Compare two raster images with pixel metrics and a perceptual hash.

    ``threshold`` is the minimum average-hash similarity. ``pixel_tolerance``
    ignores per-channel differences up to that value when counting changed
    pixels. ``max_different_pixel_ratio`` limits the fraction of pixels that
    may exceed that tolerance.
    """
    _validate_options(threshold, pixel_tolerance, max_different_pixel_ratio, hash_size)
    expected_image = _load_image(expected)
    actual_image = _load_image(actual)
    expected_hash = _perceptual_hash_image(expected_image, hash_size)
    actual_hash = _perceptual_hash_image(actual_image, hash_size)
    hash_distance = _hamming_distance(expected_hash, actual_hash)
    hash_similarity = 1.0 - hash_distance / (hash_size * hash_size)
    expected_size = expected_image.size
    actual_size = actual_image.size

    if expected_size != actual_size:
        return ImageDiff(
            matches=False,
            expected_size=expected_size,
            actual_size=actual_size,
            exact=False,
            pixel_count=None,
            different_pixels=None,
            different_pixel_ratio=None,
            mean_absolute_error=None,
            max_channel_delta=None,
            expected_hash=expected_hash,
            actual_hash=actual_hash,
            hash_distance=hash_distance,
            hash_similarity=hash_similarity,
            threshold=threshold,
            pixel_tolerance=pixel_tolerance,
            max_different_pixel_ratio=max_different_pixel_ratio,
            reason="image dimensions differ",
        )

    expected_composited = _composite_for_comparison(expected_image)
    actual_composited = _composite_for_comparison(actual_image)
    metrics = _pixel_metrics(expected_composited, actual_composited, pixel_tolerance)
    exact = metrics.max_channel_delta == 0
    matches = (
        hash_similarity >= threshold and metrics.different_pixel_ratio <= max_different_pixel_ratio
    )
    return ImageDiff(
        matches=matches,
        expected_size=expected_size,
        actual_size=actual_size,
        exact=exact,
        pixel_count=metrics.pixel_count,
        different_pixels=metrics.different_pixels,
        different_pixel_ratio=metrics.different_pixel_ratio,
        mean_absolute_error=metrics.mean_absolute_error,
        max_channel_delta=metrics.max_channel_delta,
        expected_hash=expected_hash,
        actual_hash=actual_hash,
        hash_distance=hash_distance,
        hash_similarity=hash_similarity,
        threshold=threshold,
        pixel_tolerance=pixel_tolerance,
        max_different_pixel_ratio=max_different_pixel_ratio,
        reason=None if matches else "comparison is outside the configured tolerances",
    )


def _validate_options(
    threshold: float,
    pixel_tolerance: int,
    max_different_pixel_ratio: float,
    hash_size: int,
) -> None:
    if not isfinite(threshold) or not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must be between 0 and 1")
    if not isinstance(pixel_tolerance, int) or not 0 <= pixel_tolerance <= 255:
        raise ValueError("pixel_tolerance must be between 0 and 255")
    if not isfinite(max_different_pixel_ratio) or not 0.0 <= max_different_pixel_ratio <= 1.0:
        raise ValueError("max_different_pixel_ratio must be between 0 and 1")
    _validate_hash_size(hash_size)


def _validate_hash_size(hash_size: int) -> None:
    if not isinstance(hash_size, int) or not 2 <= hash_size <= 32:
        raise ValueError("hash_size must be between 2 and 32")


def _load_image(source: ImageSource) -> Image.Image:
    if isinstance(source, Image.Image):
        return source.convert("RGBA")

    try:
        with Image.open(source) as image:
            return image.convert("RGBA")
    except (OSError, UnidentifiedImageError) as error:
        raise ValueError(f"unable to read image '{source}': {error}") from error


def _composite_for_comparison(image: Image.Image) -> Image.Image:
    white_background = Image.new("RGBA", image.size, (255, 255, 255, 255))
    return Image.alpha_composite(white_background, image).convert("RGB")


def _pixel_metrics(
    expected: Image.Image,
    actual: Image.Image,
    pixel_tolerance: int,
) -> _PixelMetrics:
    total_pixels = expected.width * expected.height
    different_pixels = 0
    total_delta = 0
    max_channel_delta = 0
    for expected_pixel, actual_pixel in zip(
        expected.get_flattened_data(), actual.get_flattened_data(), strict=True
    ):
        deltas = [
            abs(expected_channel - actual_channel)
            for expected_channel, actual_channel in zip(expected_pixel, actual_pixel, strict=True)
        ]
        max_channel_delta = max(max_channel_delta, *deltas)
        total_delta += sum(deltas)
        if any(delta > pixel_tolerance for delta in deltas):
            different_pixels += 1

    channel_count = total_pixels * 3
    return _PixelMetrics(
        pixel_count=total_pixels,
        different_pixels=different_pixels,
        different_pixel_ratio=different_pixels / total_pixels,
        mean_absolute_error=total_delta / (channel_count * 255),
        max_channel_delta=max_channel_delta,
    )


def _perceptual_hash_image(image: Image.Image, hash_size: int) -> str:
    composited = _composite_for_comparison(image).convert("L")
    resized = composited.resize((hash_size, hash_size), Image.Resampling.LANCZOS)
    pixels = list(resized.get_flattened_data())
    average = sum(pixels) / len(pixels)
    value = 0
    for pixel in pixels:
        value = (value << 1) | int(pixel >= average)
    hex_width = (hash_size * hash_size + 3) // 4
    return f"{value:0{hex_width}x}"


def _hamming_distance(first: str, second: str) -> int:
    return (int(first, 16) ^ int(second, 16)).bit_count()


def create_diff_image(expected: ImageSource, actual: ImageSource) -> Image.Image:
    """Create a raw RGBA difference image for two same-sized raster images."""
    expected_image = _load_image(expected)
    actual_image = _load_image(actual)
    if expected_image.size != actual_image.size:
        raise ValueError("cannot create an image diff for different dimensions")
    return ImageChops.difference(expected_image, actual_image)


def perceptual_hash(source: ImageSource, *, hash_size: int = DEFAULT_HASH_SIZE) -> str:
    """Return a stable average perceptual hash for an image or image path."""
    _validate_hash_size(hash_size)
    return _perceptual_hash_image(_load_image(source), hash_size)
