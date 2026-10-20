"""Common inspection entry point for generic document consumers."""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, cast

from quickthumb._document import Document, _asset_manifest
from quickthumb.models import CanvasInspection, DocumentInspection, ExportPolicy
from quickthumb.motion import inspect_motion

if TYPE_CHECKING:
    from quickthumb.canvas import Canvas
    from quickthumb.deck import Deck


def inspect_document(
    source: Canvas | Deck,
    *,
    target: str | Iterable[str] | None = None,
    policy: ExportPolicy | None = None,
    fps: float = 30.0,
    max_samples: int = 10_000,
) -> DocumentInspection:
    """Inspect layout, motion, diagnostics, and observed assets in one envelope.

    Existing `inspect()`, `inspect_motion()`, and `diagnose()` results keep
    their original shapes. No export is written. Layout/diagnostic inspection
    may resolve assets just as the individual methods do; the manifest reports
    the resolution state observed after those operations, without an extra
    prefetch. Unused/unresolved references are not claimed to be available.

    `target`, `policy`, `fps`, and `max_samples` have the same semantics as
    `inspect_motion()`. Empty decks and invalid options raise the same errors.
    """
    motion = inspect_motion(source, target=target, policy=policy, fps=fps, max_samples=max_samples)
    layout = source.inspect()
    pages = [layout] if isinstance(layout, CanvasInspection) else layout.slides
    diagnostics = source.diagnose()
    return DocumentInspection(
        kind=layout.kind,
        width=pages[0].width,
        height=pages[0].height,
        pages=pages,
        motion=motion,
        diagnostics=diagnostics,
        asset_manifest=_asset_manifest(cast(Document, source), source._contract_asset_record),
    )
