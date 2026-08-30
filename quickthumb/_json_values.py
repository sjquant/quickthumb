"""Validation helpers for values that cross the JSON contract."""

from __future__ import annotations

import math
from collections.abc import Mapping


def validate_json_value(value: object, path: str, *, context: str) -> None:
    """Reject values that cannot be represented by canonical JSON."""
    if value is None or isinstance(value, (bool, int, str)):
        return
    if isinstance(value, float):
        if math.isfinite(value):
            return
        raise ValueError(f"{context} at {path} must be finite")
    if isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            validate_json_value(item, f"{path}/{index}", context=context)
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{context} object keys at {path} must be strings")
            validate_json_value(item, f"{path}/{key}", context=context)
        return
    raise ValueError(f"{context} at {path} must be JSON-serializable, got {type(value).__name__}")
