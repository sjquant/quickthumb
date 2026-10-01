"""Shared authored-static document fallback for parent-linked scenes."""

from io import BytesIO
from typing import TYPE_CHECKING

from quickthumb._export_base import RasterFragment

if TYPE_CHECKING:
    from quickthumb.canvas import Canvas


def static_parent_fragment(canvas: "Canvas") -> RasterFragment:
    """Capture the complete authored still through the shared raster adapter."""
    image = canvas._render_to_image()
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return RasterFragment(buffer.getvalue(), 0, 0, image.width, image.height)
