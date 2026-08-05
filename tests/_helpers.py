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


LIT = 200


def is_lit(image: Image.Image, point: tuple[int, int], threshold: int = LIT) -> bool:
    """Whether a pixel carries ink, summed across its colour channels."""
    return sum(pixel_rgb(image, point)) > threshold


def lit_columns(image: Image.Image, row: int | None = None, threshold: int = LIT) -> list[int]:
    """Return the x positions carrying ink, on one row or anywhere in the frame."""
    rows = [row] if row is not None else range(image.height)
    return [x for x in range(image.width) if any(is_lit(image, (x, y), threshold) for y in rows)]


def lit_span(
    image: Image.Image, row: int | None = None, threshold: int = LIT
) -> tuple[int, int] | None:
    """Return the horizontal extent of the ink, or None when there is none."""
    columns = lit_columns(image, row, threshold)
    return (columns[0], columns[-1]) if columns else None


def ink_bounds(image: Image.Image, threshold: int = LIT) -> tuple[int, int, int, int] | None:
    """Return the bounding box of everything brighter than the background."""
    points = [
        (x, y)
        for x in range(image.width)
        for y in range(image.height)
        if is_lit(image, (x, y), threshold)
    ]
    if not points:
        return None
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return min(xs), min(ys), max(xs), max(ys)


def require_ink_bounds(image: Image.Image, threshold: int = LIT) -> tuple[int, int, int, int]:
    """Return the ink bounding box, failing the spec when the frame carries none."""
    bounds = ink_bounds(image, threshold)
    if bounds is None:
        raise AssertionError("expected the frame to carry ink, found none")
    return bounds


def ink_bands(image: Image.Image, threshold: int = LIT) -> list[list[int]]:
    """Group the rows carrying ink into runs separated by blank rows."""
    bands: list[list[int]] = []
    for y in range(image.height):
        if not any(is_lit(image, (x, y), threshold) for x in range(image.width)):
            continue
        if bands and y == bands[-1][-1] + 1:
            bands[-1].append(y)
        else:
            bands.append([y])
    return bands


def solid_pixels(image: Image.Image, threshold: int = 400) -> int:
    """Count the pixels bright enough to be a layer's core rather than its halo."""
    return sum(
        1
        for x in range(image.width)
        for y in range(image.height)
        if is_lit(image, (x, y), threshold)
    )
