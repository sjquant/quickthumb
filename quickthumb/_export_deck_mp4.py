"""Static Deck-to-MP4 export with one optional audio track per slide."""

from __future__ import annotations

import math
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from quickthumb.errors import RenderingError, ValidationError
from quickthumb.models import AudioTrack

if TYPE_CHECKING:
    from quickthumb.canvas import Canvas


def render_deck_mp4(
    slides: list[Canvas],
    audio_paths: list[AudioTrack | None],
    durations: list[float | None],
    output_path: str,
    default_duration: float = 3.0,
    fps: float = 30.0,
) -> None:
    """Render static slides and concatenate their AAC narration into an MP4 file."""
    _validate_settings(slides, audio_paths, durations, default_duration, fps)
    ffmpeg, ffprobe = _media_tools()
    resolved_durations = [
        _resolved_duration(audio, duration, default_duration, ffprobe)
        for audio, duration in zip(audio_paths, durations, strict=True)
    ]
    width, height = _even_size(slides[0].width, slides[0].height)
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(dir=destination.parent) as temp_dir:
        workspace = Path(temp_dir)
        segments = []
        for index, (canvas, audio, duration) in enumerate(
            zip(slides, audio_paths, resolved_durations, strict=True)
        ):
            image_path = workspace / f"slide-{index:03d}.png"
            segment_path = workspace / f"segment-{index:03d}.mp4"
            canvas.render(str(image_path))
            _encode_segment(ffmpeg, image_path, audio, duration, fps, width, height, segment_path)
            segments.append(segment_path)
        concatenated = workspace / "deck.mp4"
        _concatenate_segments(ffmpeg, segments, concatenated)
        os.replace(concatenated, destination)


def _validate_settings(
    slides: list[Canvas],
    audio_paths: list[AudioTrack | None],
    durations: list[float | None],
    default_duration: float,
    fps: float,
) -> None:
    """Validate slide metadata before creating any output file."""
    if not slides:
        raise RenderingError("Deck has no slides to render.")
    if len(slides) != len(audio_paths) or len(slides) != len(durations):
        raise RenderingError("Deck slide metadata is out of sync.")
    if not _is_positive_finite(default_duration):
        raise ValidationError("default_duration must be a finite value > 0")
    if not _is_positive_finite(fps):
        raise ValidationError("fps must be a finite value > 0")
    for audio, duration in zip(audio_paths, durations, strict=True):
        if audio is not None and not os.path.isfile(audio.path):
            raise ValidationError(f"Audio file not found: {audio.path!r}")
        if duration is not None and not _is_positive_finite(duration):
            raise ValidationError("duration must be a finite value > 0")


def _is_positive_finite(value: object) -> bool:
    """Return whether an export timing value is a positive finite number."""
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and value > 0
    )


def _media_tools() -> tuple[str, str]:
    """Resolve ffmpeg and ffprobe with an actionable installation message."""
    ffmpeg = _configured_tool("QUICKTHUMB_FFMPEG", "ffmpeg")
    ffprobe = _configured_tool("QUICKTHUMB_FFPROBE", "ffprobe")
    if ffmpeg and ffprobe:
        return ffmpeg, ffprobe
    raise RenderingError(
        "MP4 export requires both ffmpeg and ffprobe. Install FFmpeg "
        "(macOS: brew install ffmpeg; Ubuntu/Debian: sudo apt install ffmpeg)."
    )


def _configured_tool(variable: str, fallback: str) -> str | None:
    """Resolve an optional configured executable or the standard PATH tool."""
    configured = os.environ.get(variable)
    if configured is not None:
        return shutil.which(configured)
    return shutil.which(fallback)


def _resolved_duration(
    audio: AudioTrack | None, duration: float | None, default_duration: float, ffprobe: str
) -> float:
    """Use explicit timing, otherwise probe audio, otherwise use the silent default."""
    if duration is not None:
        return duration
    if audio is None:
        return default_duration
    try:
        probe = subprocess.run(
            [
                ffprobe,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=nw=1:nk=1",
                audio.path,
            ],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as error:
        raise _media_tools_error() from error
    try:
        result = float(probe.stdout.strip())
    except ValueError as error:
        raise RenderingError(f"ffprobe could not read audio duration: {audio.path!r}") from error
    if probe.returncode != 0 or not math.isfinite(result) or result <= 0:
        raise RenderingError(f"ffprobe could not read audio duration: {audio.path!r}")
    return result


def _even_size(width: int, height: int) -> tuple[int, int]:
    """Round odd first-slide dimensions down for yuv420p encoding."""
    return max(2, width - width % 2), max(2, height - height % 2)


def _encode_segment(
    ffmpeg: str,
    image_path: Path,
    audio: AudioTrack | None,
    duration: float,
    fps: float,
    width: int,
    height: int,
    output_path: Path,
) -> None:
    """Encode one still image and one finite AAC track into a normalized segment."""
    command = [ffmpeg, "-y", "-loop", "1", "-i", str(image_path)]
    if audio is None:
        command.extend(["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"])
    else:
        command.extend(["-i", audio.path])
    video_filter = (
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black"
    )
    command.extend(
        [
            "-t",
            str(duration),
            "-r",
            str(fps),
            "-vf",
            video_filter,
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-ar",
            "48000",
            "-af",
            f"volume={audio.volume},apad" if audio is not None else "apad",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
    )
    _run_ffmpeg(command)


def _concatenate_segments(ffmpeg: str, segments: list[Path], output_path: Path) -> None:
    """Stream-copy normalized segments using FFmpeg's concat demuxer."""
    manifest = output_path.with_suffix(".concat.txt")
    manifest.write_text(
        "".join(_concat_manifest_entry(segment) for segment in segments),
        encoding="utf-8",
    )
    _run_ffmpeg(
        [
            ffmpeg,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(manifest),
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
    )


def _concat_manifest_entry(segment: Path) -> str:
    """Quote one segment path for FFmpeg's concat manifest syntax."""
    return "file '" + str(segment).replace("'", r"'\''") + "'\n"


def _run_ffmpeg(command: list[str]) -> None:
    """Run ffmpeg safely and surface its concise diagnostic on failure."""
    try:
        result = subprocess.run(command, check=False, capture_output=True, text=True)
    except OSError as error:
        raise _media_tools_error() from error
    if result.returncode != 0:
        detail = (
            result.stderr.strip().splitlines()[-1] if result.stderr.strip() else "unknown error"
        )
        raise RenderingError(f"ffmpeg failed: {detail}")


def _media_tools_error() -> RenderingError:
    """Build the shared installation guidance for unavailable media tools."""
    return RenderingError(
        "MP4 export requires both ffmpeg and ffprobe. Install FFmpeg "
        "(macOS: brew install ffmpeg; Ubuntu/Debian: sudo apt install ffmpeg)."
    )
