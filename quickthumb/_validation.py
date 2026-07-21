"""Shared validation helpers for public document models."""

from __future__ import annotations

from typing import Any

from quickthumb.errors import ValidationError


def validate_dimensions(width: Any, height: Any) -> None:
    """Validate an optional width/height pair used by Canvas and Deck."""
    for name, value in (("width", width), ("height", height)):
        if value is not None and (isinstance(value, bool) or not isinstance(value, int)):
            raise ValidationError(f"{name} must be an integer")
    if (width is None) != (height is None):
        raise ValidationError("Provide both width and height, or neither.")
    if width is not None and width <= 0:
        raise ValidationError("width must be > 0")
    if height is not None and height <= 0:
        raise ValidationError("height must be > 0")
