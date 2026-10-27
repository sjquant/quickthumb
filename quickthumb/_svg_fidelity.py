"""Optional SVG observation and shared visible-RGBA measurement helpers.

The SVG bytes are compared before publication; a failed tolerance does not
change the document's native/raster representation.
"""

from __future__ import annotations

from functools import reduce
from io import BytesIO
from typing import TYPE_CHECKING

from PIL import Image, ImageChops

from quickthumb._diff import DEFAULT_HASH_SIZE, _hamming_distance, _perceptual_hash_image
from quickthumb.errors import RenderingError
from quickthumb.models.document import _FidelityMetrics
from quickthumb.models.options import _FidelityLimits

if TYPE_CHECKING:
    from quickthumb.canvas import Canvas


def measure_svg_fidelity(
    canvas: Canvas, document: str, limits: _FidelityLimits
) -> _FidelityMetrics:
    """Measure one static SVG using the current optional Cairo/font environment."""
    limits = limits.copy()
    try:
        import cairocffi
        import cairosvg
    except (ImportError, OSError) as error:
        raise RenderingError(
            f"SVG fidelity comparison requires CairoSVG and Cairo: {error}",
            code="fidelity_unavailable",
            suggestion=(
                "install quickthumb[svg] and the system Cairo library, "
                "or omit the SVG fidelity policy"
            ),
        ) from error

    reference = canvas.sample()
    expected = reference.frames[0].to_image()
    try:
        encoded = cairosvg.svg2png(bytestring=document.encode("utf-8"))
        with Image.open(BytesIO(encoded)) as output:
            actual = output.convert("RGBA")
    except Exception as error:
        raise RenderingError(
            f"CairoSVG could not compare the authored-static SVG: {error}",
            code="fidelity_comparison_failed",
            suggestion="check the SVG and the Cairo/font environment; no output was written",
        ) from error

    return _FidelityMetrics(
        renderer="cairosvg",
        renderer_version=cairosvg.__version__,
        cairo_version=cairocffi.cairo_version_string(),
        canonical_environment=reference.environment,
        limits=limits,
        actual_width=actual.width,
        actual_height=actual.height,
        **compare_pixels(expected, actual, limits),
    )


def compare_pixels(expected: Image.Image, actual: Image.Image, limits: _FidelityLimits) -> dict:
    expected, actual = _visible_rgba(expected), _visible_rgba(actual)
    expected_hash = _perceptual_hash_image(expected, DEFAULT_HASH_SIZE)
    actual_hash = _perceptual_hash_image(actual, DEFAULT_HASH_SIZE)
    similarity = 1 - _hamming_distance(expected_hash, actual_hash) / DEFAULT_HASH_SIZE**2
    metrics = (
        _pixel_measurements(expected, actual, limits["pixel_tolerance"])
        if expected.size == actual.size
        else {}
    )
    within_policy = (
        expected.size == actual.size
        and metrics["pixel_diff_ratio"] <= limits["max_different_pixel_ratio"]
        and similarity >= limits["min_hash_similarity"]
    )
    verdict = "out_of_policy"
    if within_policy:
        verdict = "exact" if metrics["max_channel_delta"] == 0 else "tolerated"
    return {"verdict": verdict, "hash_similarity": similarity, **metrics}


def _visible_rgba(image: Image.Image) -> Image.Image:
    """Ignore hidden RGB only where a pixel is completely transparent."""
    alpha = image.getchannel("A")
    if alpha.histogram()[0] == 0:
        return image
    visible = Image.new("RGBA", image.size)
    visible.paste(image, mask=alpha.point([0] + [255] * 255))
    return visible


def _pixel_measurements(expected: Image.Image, actual: Image.Image, tolerance: int) -> dict:
    difference = ImageChops.difference(expected, actual)
    peak = reduce(ImageChops.lighter, difference.split())
    different = sum(peak.histogram()[tolerance + 1 :])
    total_delta = sum((index % 256) * count for index, count in enumerate(difference.histogram()))
    pixels = expected.width * expected.height
    return {
        "pixel_diff_ratio": different / pixels,
        "mean_absolute_error": total_delta / (pixels * 4 * 255),
        "max_channel_delta": peak.getextrema()[1],
    }
