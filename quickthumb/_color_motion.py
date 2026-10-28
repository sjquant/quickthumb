"""Perceptual interpolation for color tracks, without renderer dependencies."""

from functools import lru_cache


@lru_cache(maxsize=256)
def _oklab(color: str) -> tuple[float, float, float, float]:
    """Decode sRGB to Oklab, keeping straight alpha separately.

    Matrices: https://bottosson.github.io/posts/oklab/ (public-domain reference).
    The small bounded cache reuses authored endpoints rather than rendered frames.
    """
    channels = [int(color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
    red, green, blue = [
        channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    cone_l = (0.4122214708 * red + 0.5363325363 * green + 0.0514459929 * blue) ** (1 / 3)
    cone_m = (0.2119034982 * red + 0.6806995451 * green + 0.1073969566 * blue) ** (1 / 3)
    cone_s = (0.0883024619 * red + 0.2817188376 * green + 0.6299787005 * blue) ** (1 / 3)
    return (
        0.2104542553 * cone_l + 0.7936177850 * cone_m - 0.0040720468 * cone_s,
        1.9779984951 * cone_l - 2.4285922050 * cone_m + 0.4505937099 * cone_s,
        0.0259040371 * cone_l + 0.7827717662 * cone_m - 0.8086757660 * cone_s,
        int(color[7:9], 16) / 255 if len(color) == 9 else 1.0,
    )


def interpolate_color(left: str, right: str, ratio: float) -> str:
    """Blend premultiplied Oklab and linear alpha, clipping to the sRGB gamut."""
    if ratio <= 0:
        return left
    if ratio >= 1:
        return right
    source, target = _oklab(left), _oklab(right)
    alpha = source[3] + (target[3] - source[3]) * ratio
    lab = [
        ((1 - ratio) * source[index] * source[3] + ratio * target[index] * target[3]) / alpha
        if alpha > 0
        else 0.0
        for index in range(3)
    ]
    lightness, a, b = lab
    cone_l = (lightness + 0.3963377774 * a + 0.2158037573 * b) ** 3
    cone_m = (lightness - 0.1055613458 * a - 0.0638541728 * b) ** 3
    cone_s = (lightness - 0.0894841775 * a - 1.2914855480 * b) ** 3
    linear = (
        4.0767416621 * cone_l - 3.3077115913 * cone_m + 0.2309699292 * cone_s,
        -1.2684380046 * cone_l + 2.6097574011 * cone_m - 0.3413193965 * cone_s,
        -0.0041960863 * cone_l - 0.7034186147 * cone_m + 1.7076147010 * cone_s,
    )
    channels = []
    for channel in linear:
        channel = min(1.0, max(0.0, channel))
        encoded = 12.92 * channel if channel <= 0.0031308 else 1.055 * channel ** (1 / 2.4) - 0.055
        channels.append(round(encoded * 255))
    if len(left) == 9 or len(right) == 9:
        channels.append(round(alpha * 255))
    return "#" + "".join(f"{channel:02X}" for channel in channels)
