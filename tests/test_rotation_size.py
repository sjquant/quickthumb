"""Rotation bounds must match Pillow before they determine any placement."""

import math

import pytest
from PIL import Image
from quickthumb._base import expanded_rotation_size


@pytest.mark.parametrize("size", [(2, 1), (20, 30), (21, 30), (41, 31), (1, 1), (300, 171)])
@pytest.mark.parametrize("scale", [1, 4])
@pytest.mark.parametrize(
    "rotation",
    [
        -27.5,
        0,
        27.5,
        90,
        180,
        270,
        360,
        1e-14,
        -1e-14,
        *[
            math.nextafter(angle, direction)
            for angle in (90.0, 180.0, 270.0, 360.0)
            for direction in (-math.inf, math.inf)
        ],
    ],
)
def test_expanded_rotation_size_matches_pillow(size, scale, rotation):
    source = Image.new("L", (size[0] * scale, size[1] * scale))
    actual = source.rotate(-rotation, expand=True).size
    assert expanded_rotation_size(size, rotation, scale) == (
        round(actual[0] / scale),
        round(actual[1] / scale),
    )
