"""Shared validation for top-level JSON document discriminators."""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, Protocol, cast, runtime_checkable

from quickthumb.errors import RenderingError, ValidationError
from quickthumb.models import (
    AssetManifestEntry,
    CanonicalFrame,
    DiagnosticReport,
    ExportDiagnostic,
    ExportPolicy,
    ExportResult,
    FallbackDiagnostic,
    FrameSequence,
    GifOptions,
    PixelMetrics,
    ResolvedDocument,
    TimingMetrics,
    ValidationIssue,
    ValidationReport,
    VideoOptions,
)

if TYPE_CHECKING:
    from quickthumb.canvas import Canvas
    from quickthumb.deck import Deck
    from quickthumb.models import CanvasInspection, DeckInspection

DocumentKind = Literal["canvas", "deck"]


def canonical_json(payload: object) -> str:
    """Serialize a document payload using the stable JSON wire format.

    Canonical document JSON is deliberately independent of renderer objects:
    callers hand this helper ordinary JSON-compatible values and receive one
    deterministic representation regardless of whether the values originated
    in Python authoring or a parsed JSON document.
    """
    try:
        return json.dumps(
            payload,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as error:
        raise ValidationError(f"Document JSON contains non-serializable values: {error}") from error


def decode_json_object(data: str) -> dict[str, Any]:
    """Decode one JSON object and normalize syntax/type failures."""
    if not isinstance(data, str):
        raise ValidationError("JSON document must be a string.")
    try:
        raw = json.loads(data)
    except json.JSONDecodeError as error:
        raise ValidationError(
            f"Invalid JSON document: {error.msg} at position {error.pos}."
        ) from error
    if not isinstance(raw, dict):
        raise ValidationError("JSON document must be an object.")
    return cast(dict[str, Any], raw)


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
        *,
        format: str | None = None,
        quality: int | None = None,
        animation: GifOptions | VideoOptions | None = None,
    ) -> ExportResult: ...


def require_document_kind(raw: object, *, expected: DocumentKind | None = None) -> DocumentKind:
    """Validate and return the top-level kind of a JSON document."""
    if not isinstance(raw, dict):
        raise ValidationError("JSON document must be an object with a 'kind' field.")

    document = cast(dict[str, object], raw)
    if "kind" not in document:
        raise ValidationError("JSON document must contain a 'kind' discriminator.")
    kind = document["kind"]
    if kind not in ("canvas", "deck"):
        raise ValidationError("JSON document 'kind' must be either 'canvas' or 'deck'.")
    if expected is not None and kind != expected:
        raise ValidationError(f"JSON document 'kind' must be '{expected}'.")
    if kind == "canvas" and "slides" in raw:
        raise ValidationError("Canvas JSON must not contain a top-level 'slides' field.")
    if kind == "deck" and "layers" in raw:
        raise ValidationError("Deck JSON must not contain a top-level 'layers' field.")
    return cast(DocumentKind, kind)


def load_document(text: str) -> Canvas | Deck:
    """Parse a discriminated Canvas or Deck JSON document."""
    from quickthumb.canvas import Canvas
    from quickthumb.deck import Deck

    raw = decode_json_object(text)
    kind = require_document_kind(raw)
    if kind == "deck":
        return Deck.from_json(text)
    return Canvas.from_json(text)


def build_export_result(
    source: Document,
    output_path: str,
    written_paths: list[str],
    policy: ExportPolicy | None = None,
    *,
    format: str | None = None,
    animation: GifOptions | VideoOptions | None = None,
) -> ExportResult:
    """Build the shared result envelope after an existing exporter succeeds."""
    output_format = _output_format(output_path, format)
    target = _export_target(output_format)
    capability_report = _capability_report(source, target, policy)
    timing = _timing_metrics(source, target, output_format, policy, animation)
    dimensions = _document_dimensions(source)
    asset_manifest = _asset_manifest(source)
    pixel_frame_count = _pixel_frame_count(source, target, output_format, written_paths, timing)
    if output_format == "gif" and written_paths:
        timing = timing.model_copy(update={"frame_count": pixel_frame_count})
    return ExportResult(
        kind=_contract_kind(source),
        target=target,
        output_format=output_format,
        written_paths=written_paths,
        capability_report=capability_report,
        fallback_diagnostics=_fallback_diagnostics(capability_report),
        pixel_metrics=PixelMetrics(
            width=dimensions[0],
            height=dimensions[1],
            frame_count=pixel_frame_count,
        ),
        timing_metrics=timing,
        asset_manifest=asset_manifest,
    )


def preflight_export(
    source: Document,
    output_path: str,
    policy: ExportPolicy | None = None,
    *,
    format: str | None = None,
) -> None:
    """Validate target capabilities before an exporter writes any files."""
    output_format = _output_format(output_path, format)
    _capability_report(source, _export_target(output_format), policy)


def validation_report(source: Document, *, kind: DocumentKind) -> ValidationReport:
    """Run the shared validation checks and capture failures as report issues."""
    errors: list[ValidationIssue] = []
    try:
        if kind == "canvas":
            _contract_validate_structure(source)
            _contract_validate_assets(source)
            source.inspect()
        else:
            slides = _contract_canvases(source)
            _contract_validate_structure(source)
            for index, slide in enumerate(slides):
                report = slide.validate()
                errors.extend(
                    issue.model_copy(update={"path": f"/slides/{index}{issue.path or ''}"})
                    for issue in report.errors
                )
                audio_paths = _contract_audio_paths(source)
                audio_path = audio_paths[index] if index < len(audio_paths) else None
                if audio_path is not None and not _is_local_asset(audio_path):
                    errors.append(
                        ValidationIssue(
                            code="asset_missing",
                            message=audio_path,
                            path=f"/slides/{index}/audio",
                        )
                    )
    except Exception as error:
        errors.append(_validation_issue(error))
    return ValidationReport(valid=not errors, errors=errors)


def resolved_document(source: Document, *, kind: DocumentKind) -> ResolvedDocument:
    """Resolve/check asset references without changing the renderer's loading path."""
    _contract_validate_assets(source)
    return ResolvedDocument(kind=kind, asset_manifest=_asset_manifest(source))


def _contract_kind(source: Document) -> DocumentKind:
    return cast(DocumentKind, cast(Any, source)._contract_kind())


def _contract_canvases(source: Document) -> list[Any]:
    return list(cast(Any, source)._contract_canvases())


def _contract_layers(source: Document):
    return cast(Any, source)._contract_layers()


def _contract_audio_paths(source: Document) -> tuple[str | None, ...]:
    return tuple(cast(Any, source)._contract_audio_paths())


def _contract_validate_assets(source: Document) -> None:
    cast(Any, source)._contract_validate_assets()


def _contract_validate_structure(source: Document) -> None:
    cast(Any, source)._contract_validate_structure()


def _contract_motion_report(source: Document, target: str, policy, fps: float):
    return cast(Any, source)._contract_motion_report(target, policy, fps)


def _contract_static_timing(source: Document) -> tuple[float, float] | None:
    return cast(Any, source)._contract_static_timing()


def _output_format(output_path: str, format: str | None = None) -> str:
    if format is not None:
        return format.lower()
    extension = Path(output_path).suffix.lower().lstrip(".")
    return "html" if extension == "htm" else extension


def _export_target(output_format: str) -> str:
    return {
        "png": "raster",
        "jpg": "raster",
        "jpeg": "raster",
        "webp": "raster",
        "svg": "raster",
        "pdf": "raster",
        "html": "html",
        "pptx": "pptx",
    }.get(output_format, "video" if output_format in {"gif", "mp4", "webm"} else output_format)


def _capability_report(
    source: Document, target: str, policy: ExportPolicy | None
) -> list[ExportDiagnostic]:
    from quickthumb.motion import validate_export

    if target not in {"raster", "video", "html", "pptx"}:
        return []
    return validate_export(cast(Any, source), target, policy)


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


def _timing_metrics(
    source: Document,
    target: str,
    output_format: str,
    policy: ExportPolicy | None,
    animation: GifOptions | VideoOptions | None,
) -> TimingMetrics:
    if target != "video":
        return TimingMetrics()
    fps = _animation_fps(output_format, animation)
    if _contract_kind(source) == "deck" and output_format == "mp4" and animation is None:
        static_timing = _contract_static_timing(source)
        assert static_timing is not None
        duration, static_fps = static_timing
        return TimingMetrics(
            duration=duration,
            fps=static_fps,
            frame_count=max(1, math.ceil(duration * static_fps)),
        )
    try:
        report = _contract_motion_report(source, target, policy, fps)
    except (RenderingError, ValidationError, ValueError, RuntimeError):
        return TimingMetrics(frame_count=1)
    duration = report.duration
    if _contract_kind(source) == "canvas":
        duration += 3.0
    return TimingMetrics(
        duration=duration,
        fps=fps,
        frame_count=max(1, math.ceil(duration * fps)),
    )


def _animation_fps(output_format: str, animation: GifOptions | VideoOptions | None) -> float:
    if animation is not None and animation.fps is not None:
        return float(animation.fps)
    return 20.0 if output_format == "gif" else 30.0


def _pixel_frame_count(
    source: Document,
    target: str,
    output_format: str,
    written_paths: list[str],
    timing: TimingMetrics,
) -> int:
    if target == "video":
        if output_format == "gif" and written_paths:
            return _gif_frame_count(written_paths[0]) or timing.frame_count
        return timing.frame_count
    if output_format in {"pdf", "pptx"} and _contract_kind(source) == "deck":
        return len(_contract_canvases(source))
    return max(1, len(written_paths))


def _gif_frame_count(path: str) -> int | None:
    try:
        from PIL import Image

        with Image.open(path) as image:
            return int(getattr(image, "n_frames", 1))
    except (OSError, ValueError):
        return None


def _document_dimensions(source: Document) -> tuple[int | None, int | None]:
    canvases = _contract_canvases(source)
    if not canvases:
        return None, None
    return canvases[0].width, canvases[0].height


def _asset_manifest(source: Document) -> list[AssetManifestEntry]:
    entries: list[AssetManifestEntry] = []
    seen: set[tuple[str, str]] = set()
    for layer in _contract_layers(source):
        for asset_type, value in _layer_asset_values(layer):
            _append_asset_entry(entries, seen, asset_type, value)
    for path in _contract_audio_paths(source):
        if path is not None:
            _append_asset_entry(entries, seen, "audio", path)
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
    content = getattr(layer, "content", None)
    if isinstance(content, list):
        for part in content:
            part_fill_path = getattr(getattr(part, "fill", None), "path", None)
            if isinstance(part_fill_path, str):
                yield "text-fill", part_fill_path


def _append_asset_entry(
    entries: list[AssetManifestEntry], seen: set[tuple[str, str]], asset_type: str, value: str
) -> None:
    key = (asset_type, value)
    if key in seen:
        return
    seen.add(key)
    entries.append(
        AssetManifestEntry(
            source=value,
            asset_type=asset_type,
            status="remote" if _is_url(value) else "local",
            content_hash=_local_hash(value),
        )
    )


def _is_url(value: str) -> bool:
    return value.startswith("http://") or value.startswith("https://")


def _is_local_asset(value: str) -> bool:
    return _is_url(value) or os.path.isfile(value)


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
