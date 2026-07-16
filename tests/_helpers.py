"""Shared test helpers with precise runtime type narrowing."""

from PIL import Image


def pixel_channel(image: Image.Image, point: tuple[int, int], channel: int) -> int:
    """Return one channel from an image pixel after narrowing Pillow's union type."""
    pixel = image.getpixel(point)
    if not isinstance(pixel, tuple):
        raise AssertionError(f"expected a multi-channel pixel, got {pixel!r}")
    return pixel[channel]


def pixel_rgb(image: Image.Image, point: tuple[int, int]) -> tuple[int, int, int]:
    """Return the first three channels from an image pixel."""
    pixel = image.getpixel(point)
    if not isinstance(pixel, tuple) or len(pixel) < 3:
        raise AssertionError(f"expected an RGB pixel, got {pixel!r}")
    return pixel[0], pixel[1], pixel[2]


def pixel_scalar(image: Image.Image, point: tuple[int, int]) -> int:
    """Return a scalar grayscale pixel after narrowing Pillow's pixel union."""
    pixel = image.getpixel(point)
    if not isinstance(pixel, (int, float)):
        raise AssertionError(f"expected a scalar pixel, got {pixel!r}")
    return int(pixel)
