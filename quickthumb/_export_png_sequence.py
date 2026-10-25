"""Silent, exact RGBA8 frames from the existing animated-export shot pipeline."""

from __future__ import annotations

import os
import stat
import tempfile
from io import BytesIO
from pathlib import Path

from PIL import Image

from quickthumb._document import (
    Document,
    _capability_report,
    _contract_kind,
    _contract_timeline_inputs,
    _contract_validate_structure,
    canonical_json,
)
from quickthumb._exclusive_directory import (
    cleanup_owned_staging,
    normalize_destination,
    rename_exclusive,
)
from quickthumb._export_video import _PreparedAnimation
from quickthumb.errors import RenderingError, ValidationError
from quickthumb.models import (
    ExportPolicy,
    PngSequenceManifest,
    PngSequenceOptions,
    PngSequenceResult,
)


def export_png_sequence(
    source: Document,
    output_directory: str | os.PathLike[str],
    *,
    options: PngSequenceOptions | None = None,
    policy: ExportPolicy | None = None,
) -> PngSequenceResult:
    """Render privately, close resources, then publish a complete fresh directory."""
    if options is not None and not isinstance(options, PngSequenceOptions):
        raise ValidationError("options must be PngSequenceOptions")
    # Revalidate even model_construct/model_copy inputs before touching output.
    settings = PngSequenceOptions.model_validate(options.model_dump() if options else {})
    destination = normalize_destination(output_directory)
    staging = None
    identity = None
    try:
        _contract_validate_structure(source)
        diagnostics = _capability_report(
            source,
            "video",
            policy,
            output_format="png_sequence",
            uses_authored_transitions=not bool(policy and policy.reduced_motion),
        )
        canvases, transitions, durations = _contract_timeline_inputs(source, settings.hold)
        # Narration only determines visual timing. This renderer request is
        # native-size straight RGBA and has no codec or audio-mixer identity.
        with _PreparedAnimation(
            canvases,
            transitions,
            fps=settings.fps,
            slide_duration=settings.hold,
            slide_durations=durations,
            matte=None,
            workers=settings.workers,
            quality=settings.quality,
            reduced_motion=bool(policy and policy.reduced_motion),
        ) as prepared:
            staging = Path(tempfile.mkdtemp(prefix=".quickthumb-png-", dir=destination.parent))
            created = staging.lstat()
            identity = (created.st_dev, created.st_ino)
            for frame, indices in prepared.frame_runs():
                png = _encode_png_frame(frame)
                for index in indices:
                    (staging / f"{index:06d}.png").write_bytes(png)
                del png
            facts = prepared.frame_facts
            manifest = PngSequenceManifest(
                kind=_contract_kind(source),
                frame_count=facts.frame_count,
                fps=prepared.fps,
                duration=facts.duration,
                width=facts.width,
                height=facts.height,
            )
            (staging / "manifest.json").write_text(
                canonical_json(manifest.model_dump(mode="json")) + "\n", encoding="utf-8"
            )
            result = PngSequenceResult(
                **manifest.model_dump(),
                output_directory=str(destination),
                manifest_path=str(destination / "manifest.json"),
                capability_report=diagnostics,
            )
        current = staging.lstat()
        if not stat.S_ISDIR(current.st_mode) or (current.st_dev, current.st_ino) != identity:
            raise RenderingError("PNG sequence staging directory changed before publication")
        rename_exclusive(staging, destination)
        staging = None  # A known-success commit ends our cleanup ownership.
        return result
    finally:
        # A failed rename can have an ambiguous outcome (e.g. NFS). Never touch
        # destination. Only remove the still-present, verified staging inode.
        if staging is not None and identity is not None:
            cleanup_owned_staging(staging, identity)


def _encode_png_frame(frame: Image.Image) -> bytes:
    """Encode exactly the renderer's straight RGBA bytes, without inherited metadata."""
    if frame.mode != "RGBA":
        raise RenderingError("PNG sequence renderer must produce RGBA frames")
    # Pillow's existing encoderinfo overrides save kwargs. Clear only that
    # temporary encoder state, restoring it even on failure; pixels/info stay
    # untouched and no raw frame copy is needed to suppress inherited metadata.
    previous = getattr(frame, "encoderinfo", None)
    frame.encoderinfo = {}
    try:
        with BytesIO() as output:
            frame.save(
                output,
                format="PNG",
                icc_profile=None,
                pnginfo=None,
                exif=b"",
                transparency=None,
            )
            return output.getvalue()
    finally:
        if previous is None:
            del frame.encoderinfo
        else:
            frame.encoderinfo = previous
