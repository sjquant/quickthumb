"""Shared validation for top-level JSON document discriminators."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, Protocol, cast, runtime_checkable

from quickthumb.canvas import Canvas
from quickthumb.deck import Deck
from quickthumb.errors import RenderingError, ValidationError
from quickthumb.models import (
    AssetManifestEntry,
    CanonicalFrame,
    DiagnosticReport,
    ExportPolicy,
    ExportResult,
    FallbackDiagnostic,
    FrameSequence,
    PixelMetrics,
    ResolvedDocument,
    TimingMetrics,
    ValidationIssue,
    ValidationReport,
)

if TYPE_CHECKING:
    from quickthumb.models import CanvasInspection, DeckInspection

DocumentKind = Literal["canvas", "deck"]


@runtime_checkable
class Document(Protocol):
    """Stable document-level contract shared by Canvas and Deck.

    Renderer-specific compilers, timelines, and exporter implementations are
    deliberately absent from this protocol.
    """

    def validate(self) -> ValidationReport: ...

    def inspect(self) -> CanvasInspection | DeckInspection: ...

    def diagnose(self) -> DiagnosticReport: ...

    def resolve_assets(self) -> ResolvedDocument: ...

    def sample(self, time: float = 0.0) -> CanonicalFrame | FrameSequence: ...

    def export(
        self,
        output_path: str | os.PathLike[str],
        policy: ExportPolicy | None = None,
        **options: Any,
    ) -> ExportResult: ...


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


def build_export_result(
    source: Document,
    output_path: str,
    written_paths: list[str],
    policy: ExportPolicy | None = None,
) -> ExportResult:
    """Build the shared result envelope after an existing exporter succeeds."""
    target = _export_target(output_path)
    capability_report = _capability_report(source, target, policy)
    timing = _timing_metrics(source, target, policy)
    dimensions = _document_dimensions(source)
    asset_manifest = _asset_manifest(source)
    return ExportResult(
        kind="deck" if hasattr(source, "slides") else "canvas",
        target=target,
        written_paths=written_paths,
        capability_report=capability_report,
        fallback_diagnostics=_fallback_diagnostics(capability_report),
        pixel_metrics=PixelMetrics(
            width=dimensions[0],
            height=dimensions[1],
            frame_count=max(1, len(written_paths)),
        ),
        timing_metrics=timing,
        asset_manifest=asset_manifest,
    )


def validation_report(source: Document, *, kind: DocumentKind) -> ValidationReport:
    """Run the shared validation checks and capture failures as report issues."""
    errors: list[ValidationIssue] = []
    try:
        if kind == "canvas":
            if not source.has_size:  # type: ignore[attr-defined]
                raise ValidationError("canvas has no size")
            source._validate_layer_identities()  # type: ignore[attr-defined]
            source._validate_image_paths()  # type: ignore[attr-defined]
            source.inspect()
        else:
            slides = source.slides  # type: ignore[attr-defined]
            if not slides:
                raise ValidationError("deck has no slides")
            for index, slide in enumerate(slides):
                report = slide.validate()
                errors.extend(
                    issue.model_copy(update={"path": f"/slides/{index}{issue.path or ''}"})
                    for issue in report.errors
                )
    except Exception as error:
        errors.append(_validation_issue(error))
    return ValidationReport(valid=not errors, errors=errors)


def resolved_document(source: Document, *, kind: DocumentKind) -> ResolvedDocument:
    """Resolve/check asset references without changing the renderer's loading path."""
    if kind == "canvas":
        source._validate_image_paths()  # type: ignore[attr-defined]
    else:
        for slide in source.slides:  # type: ignore[attr-defined]
            slide._validate_image_paths()
    return ResolvedDocument(kind=kind, asset_manifest=_asset_manifest(source))


def _export_target(output_path: str) -> str:
    extension = Path(output_path).suffix.lower().lstrip(".")
    return {
        "png": "raster",
        "jpg": "raster",
        "jpeg": "raster",
        "webp": "raster",
        "svg": "raster",
        "pdf": "raster",
    }.get(extension, "video" if extension in {"gif", "mp4", "webm"} else extension)


def _capability_report(source: Document, target: str, policy: ExportPolicy | None) -> list:
    from quickthumb.motion import validate_export

    try:
        return validate_export(cast(Canvas | Deck, source), target, policy)
    except (RenderingError, ValidationError, ValueError):
        return []


def _fallback_diagnostics(capability_report: list) -> list[FallbackDiagnostic]:
    return [
        FallbackDiagnostic(
            target=item.target,
            layer_id=item.layer_id,
            reason=item.message,
            native_attempt=item.support in {"native", "partial"},
            suggestion="inspect the capability report for a native alternative",
        )
        for item in capability_report
        if item.support == "fallback" or item.fallback is not None
    ]


def _timing_metrics(source: Document, target: str, policy: ExportPolicy | None) -> TimingMetrics:
    try:
        report = source.inspect_motion(target=target, policy=policy)  # type: ignore[attr-defined]
    except (RenderingError, ValidationError, ValueError, RuntimeError):
        return TimingMetrics(frame_count=1)
    return TimingMetrics(
        duration=report.duration,
        fps=report.fps,
        frame_count=max(1, len(report.sample_times)),
    )


def _document_dimensions(source: Document) -> tuple[int | None, int | None]:
    if isinstance(source, Deck):
        slides = source.slides
        if not slides:
            return None, None
        return slides[0].width, slides[0].height
    return cast(Canvas, source).width, cast(Canvas, source).height


def _asset_manifest(source: Document) -> list[AssetManifestEntry]:
    canvases = source.slides if isinstance(source, Deck) else [cast(Canvas, source)]
    entries: list[AssetManifestEntry] = []
    seen: set[tuple[str, str]] = set()
    for canvas in canvases:
        for layer in canvas._iter_layers_deep():
            for asset_type, value in _layer_asset_values(layer):
                key = (asset_type, value)
                if key in seen:
                    continue
                seen.add(key)
                entries.append(
                    AssetManifestEntry(
                        source=value,
                        asset_type=asset_type,
                        status="remote" if _is_url(value) else "local",
                        content_hash=_local_hash(value),
                    )
                )
    return entries


def _layer_asset_values(layer: object):
    for field in ("path", "source"):
        value = getattr(layer, field, None)
        if isinstance(value, str):
            yield field, value
    image = getattr(layer, "image", None)
    if isinstance(image, str):
        yield "image", image
    fill = getattr(layer, "fill", None)
    fill_path = getattr(fill, "path", None)
    if isinstance(fill_path, str):
        yield "text-fill", fill_path


def _is_url(value: str) -> bool:
    return value.startswith("http://") or value.startswith("https://")


def _local_hash(value: str) -> str | None:
    if _is_url(value) or not os.path.isfile(value):
        return None
    digest = hashlib.sha256()
    try:
        with open(value, "rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
    except OSError:
        return None
    return digest.hexdigest()


def _validation_issue(error: Exception) -> ValidationIssue:
    code = "asset_missing" if isinstance(error, FileNotFoundError) else "invalid_document"
    return ValidationIssue(code=code, message=str(error))
