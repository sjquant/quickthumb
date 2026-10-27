"""Silent image sequences from the existing canonical animation frame pipeline."""

from __future__ import annotations

import os
import stat
import tempfile
from io import BytesIO
from pathlib import Path
from typing import Literal, cast

from PIL import Image, ImageColor

from quickthumb._document import (
    Document,
    _capability_report,
    _contract_kind,
    _contract_timeline_inputs,
    _contract_validate_structure,
    _motion_blur_report,
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
    ImageSequenceManifest,
    ImageSequenceOptions,
    ImageSequenceResult,
)


def export_image_sequence(
    source: Document,
    output_directory: str | os.PathLike[str],
    *,
    format: str = "png",
    quality: int | None = None,
    matte: str | None = None,
    lossless: bool | None = None,
    options: ImageSequenceOptions | None = None,
    policy: ExportPolicy | None = None,
) -> ImageSequenceResult:
    """Render privately, close resources, then publish a complete fresh directory."""
    if options is not None and not isinstance(options, ImageSequenceOptions):
        raise ValidationError("options must be ImageSequenceOptions")
    # Revalidate even model_construct/model_copy inputs before touching output.
    settings = ImageSequenceOptions.model_validate(options.model_dump() if options else {})
    encoding, quality, matte, lossless = _validate_encoding(format, quality, matte, lossless)
    extension = {"png": "png", "jpeg": "jpg", "webp": "webp"}[encoding]
    destination = normalize_destination(output_directory)
    staging = None
    identity = None
    try:
        _contract_validate_structure(source)
        diagnostics = _capability_report(
            source,
            "video",
            policy,
            output_format="image_sequence",
            uses_authored_transitions=not bool(policy and policy.reduced_motion),
        )
        diagnostics += _motion_blur_report(settings.motion_blur, "video")
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
            quality=settings.render_quality,
            reduced_motion=bool(policy and policy.reduced_motion),
            motion_blur=settings.motion_blur,
        ) as prepared:
            staging = Path(tempfile.mkdtemp(prefix=".quickthumb-images-", dir=destination.parent))
            created = staging.lstat()
            identity = (created.st_dev, created.st_ino)
            for frame, indices in prepared.frame_runs():
                encoded = _encode_image_frame(
                    frame, encoding=encoding, quality=quality, matte=matte, lossless=lossless
                )
                for index in indices:
                    (staging / f"{index:06d}.{extension}").write_bytes(encoded)
                del encoded
            facts = prepared.frame_facts
            manifest = ImageSequenceManifest(
                kind=_contract_kind(source),
                encoding=encoding,
                filename_pattern=f"%06d.{extension}",
                mode="RGB" if encoding == "jpeg" else "RGBA",
                alpha="none" if encoding == "jpeg" else "straight",
                lossless=lossless,
                quality=quality,
                matte=matte,
                frame_count=facts.frame_count,
                fps=prepared.fps,
                duration=facts.duration,
                width=facts.width,
                height=facts.height,
            )
            (staging / "manifest.json").write_text(
                canonical_json(manifest.model_dump(mode="json")) + "\n", encoding="utf-8"
            )
            result = ImageSequenceResult(
                **manifest.model_dump(),
                output_directory=str(destination),
                manifest_path=str(destination / "manifest.json"),
                capability_report=diagnostics,
            )
        current = staging.lstat()
        if not stat.S_ISDIR(current.st_mode) or (current.st_dev, current.st_ino) != identity:
            raise RenderingError("Image sequence staging directory changed before publication")
        rename_exclusive(staging, destination)
        staging = None  # A known-success commit ends our cleanup ownership.
        return result
    finally:
        # A failed rename can have an ambiguous outcome (e.g. NFS). Never touch
        # destination. Only remove the still-present, verified staging inode.
        if staging is not None and identity is not None:
            cleanup_owned_staging(staging, identity)


def _validate_encoding(
    format: str, quality: int | None, matte: str | None, lossless: bool | None
) -> tuple[Literal["png", "jpeg", "webp"], int | None, str | None, bool]:
    """Resolve only meaningful encoder controls before inspecting the destination."""
    if not isinstance(format, str) or format.lower() not in {"png", "jpeg", "webp"}:
        raise ValidationError("format must be PNG, JPEG, or WebP")
    encoding = cast(Literal["png", "jpeg", "webp"], format.lower())
    if quality is not None and (type(quality) is not int or not 1 <= quality <= 95):
        raise ValidationError("quality must be an integer between 1 and 95")
    if lossless is not None and type(lossless) is not bool:
        raise ValidationError("lossless must be a boolean")
    if encoding != "webp" and lossless is not None:
        raise ValidationError("lossless is only supported for WebP")
    if matte is not None and encoding != "jpeg":
        raise ValidationError("matte is only supported for JPEG")
    if encoding == "png":
        if quality is not None:
            raise ValidationError("quality is only supported for JPEG and lossy WebP")
        return encoding, None, None, True
    if encoding == "webp":
        if lossless and quality is not None:
            raise ValidationError("quality is only supported for lossy WebP")
        return (
            encoding,
            None if lossless else (80 if quality is None else quality),
            None,
            bool(lossless),
        )
    if matte is not None and not isinstance(matte, str):
        raise ValidationError("matte must be an opaque color string")
    try:
        rgb = cast(
            tuple[int, int, int, int],
            ImageColor.getcolor("#FFFFFF" if matte is None else matte, "RGBA"),
        )
    except (TypeError, ValueError):
        raise ValidationError("matte must be an opaque color string") from None
    if any(not 0 <= channel <= 255 for channel in rgb[:3]):
        raise ValidationError("matte color channels must be between 0 and 255")
    if rgb[3] != 255:
        raise ValidationError("matte must be opaque")
    resolved_matte = "#" + "".join(f"{channel:02X}" for channel in rgb[:3])
    return encoding, 90 if quality is None else quality, resolved_matte, False


def _encode_image_frame(
    frame: Image.Image,
    *,
    encoding: str = "png",
    quality: int | None = None,
    matte: str | None = None,
    lossless: bool = True,
) -> bytes:
    """Encode one independent image without modifying source pixels or metadata."""
    if frame.mode != "RGBA":
        raise RenderingError("Image sequence renderer must produce RGBA frames")
    target = frame
    if encoding == "jpeg":
        target = Image.new("RGB", frame.size, matte or "#FFFFFF")
        target.paste(frame, mask=frame.getchannel("A"))
    # Pillow's encoderinfo overrides save kwargs. Restore this temporary state
    # even on failure; PNG and WebP need no raw RGBA pixel copy.
    previous = getattr(target, "encoderinfo", None)
    target.encoderinfo = {}
    try:
        with BytesIO() as output:
            if encoding == "png":
                target.save(
                    output,
                    format="PNG",
                    icc_profile=None,
                    pnginfo=None,
                    exif=b"",
                    transparency=None,
                )
            elif encoding == "jpeg":
                target.save(output, format="JPEG", quality=quality, icc_profile=None, exif=b"")
            else:
                target.save(
                    output,
                    format="WEBP",
                    lossless=lossless,
                    exact=True,
                    **({"quality": quality} if quality is not None else {}),
                    icc_profile=b"",
                    exif=b"",
                    xmp=b"",
                )
            return output.getvalue()
    finally:
        if previous is None:
            del target.encoderinfo
        else:
            target.encoderinfo = previous
        if target is not frame:
            target.close()
