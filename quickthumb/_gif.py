"""Bounded Pillow GIF writer for quickthumb's opaque, quantized RGB shots.

Pillow's ``save_all`` retains every normalized/difference image before writing.
Here only the previous full image and one pending difference image are needed:
the latter waits until the next distinct frame, so identical frames can extend
its duration. The first original image is retained until then for Pillow's
different single-frame encoding (including interlacing).

Private Pillow calls are deliberately isolated here. They preserve the palette,
delta bounding box and LZW bytes of Pillow 12.x, our supported dependency range;
legacy-save byte comparisons must pass when upgrading Pillow. This is not a
general GIF writer: inputs come from the exporter's opaque RGB matte, with no
source metadata, transparency or disposal setting.
"""

from __future__ import annotations

from collections.abc import Iterable
from functools import reduce
from typing import IO

from PIL import GifImagePlugin, Image, ImageChops

from quickthumb.errors import RenderingError


def write_gif_frames(
    frames: Iterable[tuple[Image.Image, int]], output: IO[bytes], loop: int
) -> tuple[int, int]:
    """Write bounded quantized frames; return encoded frame count and duration in ms."""
    iterator = iter(frames)
    try:
        first, duration = next(iterator)
    except StopIteration:
        raise RenderingError("GIF export produced no frames") from None

    info = {"duration": duration, "loop": loop, "optimize": True}
    pending = GifImagePlugin._normalize_palette(first.copy(), None, info)
    previous = pending
    offset = (0, 0)
    multiple = False
    frame_count = 0
    duration_ms = 0
    for image, duration in iterator:
        next_info = {"duration": duration, "loop": loop, "optimize": True}
        current = GifImagePlugin._normalize_palette(image.copy(), None, next_info)
        delta, bounds = GifImagePlugin._getbbox(previous, current)
        if bounds is None:
            info["duration"] += duration
            # Pillow keeps the last distinct normalized image in this case.
            continue

        if not multiple:
            for block in GifImagePlugin._get_global_header(pending, info):
                output.write(block)
            first = None
            multiple = True
        GifImagePlugin._write_frame_data(output, pending, offset, info)
        frame_count += 1
        # Pillow truncates to centiseconds after identical frames are merged.
        duration_ms += int(info["duration"] / 10) * 10

        pending = _delta_frame(current, delta, next_info)
        if bounds != (0, 0) + current.size:
            pending = pending.crop(bounds)
        next_info["include_color_table"] = True
        previous, offset, info = current, bounds[:2], next_info
        del delta

    if not multiple:
        # Calling the single-frame writer is essential for exact legacy bytes.
        assert first is not None
        first.save(output, format="GIF", **info)
    else:
        GifImagePlugin._write_frame_data(output, pending, offset, info)
        output.write(b";")
        output.flush()
    return frame_count + 1, duration_ms + int(info["duration"] / 10) * 10


def _delta_frame(image: Image.Image, delta: Image.Image, info: dict[str, int]) -> Image.Image:
    """Make unchanged pixels transparent when the palette has a spare index."""
    assert image.palette is not None
    try:
        transparency = image.palette._new_color_index(image)
    except ValueError:
        # A fully occupied 256-color palette cannot represent transparency.
        return image
    info["transparency"] = transparency
    if delta.mode == "RGBA":
        delta = reduce(ImageChops.lighter, delta.split())
    # P-mode point maps indices, not palette luminance. This has the same
    # nonzero mask as Pillow's ImageMath path without a Python tuple per pixel.
    unchanged = delta.point([255] + [0] * 255, mode="1")
    difference = image.copy()
    difference.paste(transparency, mask=unchanged)
    return difference
