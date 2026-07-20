"""Shared validation for top-level JSON document discriminators."""

from __future__ import annotations

from typing import Literal, cast

from quickthumb.errors import ValidationError

DocumentKind = Literal["canvas", "deck"]


def require_document_kind(raw: object) -> DocumentKind:
    """Validate and return the top-level kind of a JSON document."""
    if not isinstance(raw, dict):
        raise ValidationError("JSON document must be an object with a 'kind' field.")

    document = cast(dict[str, object], raw)
    kind = document.get("kind")
    if kind not in ("canvas", "deck"):
        raise ValidationError("JSON document 'kind' must be either 'canvas' or 'deck'.")
    if kind == "canvas" and "slides" in raw:
        raise ValidationError("Canvas JSON must not contain a top-level 'slides' field.")
    if kind == "deck" and "layers" in raw:
        raise ValidationError("Deck JSON must not contain a top-level 'layers' field.")
    return cast(DocumentKind, kind)
