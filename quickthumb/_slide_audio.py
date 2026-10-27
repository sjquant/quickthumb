"""Audio duration inference shared by Deck video exports."""

from __future__ import annotations

import math
import os
import shutil
import subprocess

from quickthumb.errors import RenderingError
from quickthumb.models import AudioTrack


def ffprobe_binary() -> str:
    """Resolve ffprobe for exports that infer a slide narration's duration."""
    ffprobe = _configured_tool("QUICKTHUMB_FFPROBE", "ffprobe")
    if ffprobe:
        return ffprobe
    raise RenderingError(
        "Audio duration inference requires ffprobe. Install FFmpeg "
        "(macOS: brew install ffmpeg; Ubuntu/Debian: sudo apt install ffmpeg)."
    )


def _configured_tool(variable: str, fallback: str) -> str | None:
    """Resolve an optional configured executable or the standard PATH tool."""
    configured = os.environ.get(variable)
    if configured is not None:
        return shutil.which(configured)
    return shutil.which(fallback)


def resolve_audio_duration(
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


def _media_tools_error() -> RenderingError:
    """Build the shared installation guidance for unavailable media tools."""
    return RenderingError(
        "MP4 export requires both ffmpeg and ffprobe. Install FFmpeg "
        "(macOS: brew install ffmpeg; Ubuntu/Debian: sudo apt install ffmpeg)."
    )
