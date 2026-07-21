"""Shared validation for top-level JSON document discriminators."""

from __future__ import annotations

import json
from typing import Literal, cast

from quickthumb.canvas import Canvas
from quickthumb.deck import Deck
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


def load_document(text: str) -> Canvas | Deck:
    """Parse a discriminated Canvas or Deck JSON document."""
    raw = json.loads(text)
    kind = require_document_kind(raw)
    if kind == "deck":
        return Deck.from_json(text)
    return Canvas.from_json(text)
