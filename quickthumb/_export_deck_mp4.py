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

_MAX_SLIDES_PER_FFMPEG_BATCH = 32
_MAX_STATIC_DECK_FPS = 120.0


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
        resolve_audio_duration(audio, duration, default_duration, ffprobe)
        for audio, duration in zip(audio_paths, durations, strict=True)
    ]
    width, height = _even_size(slides[0].width, slides[0].height)
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(dir=destination.parent) as temp_dir:
        workspace = Path(temp_dir)
        batches = []
        for start in range(0, len(slides), _MAX_SLIDES_PER_FFMPEG_BATCH):
            end = start + _MAX_SLIDES_PER_FFMPEG_BATCH
            image_paths = []
            for index, canvas in enumerate(slides[start:end], start=start):
                image_path = workspace / f"slide-{index:03d}.png"
                canvas.render(str(image_path))
                image_paths.append(image_path)
            batch_path = workspace / f"batch-{len(batches):03d}.mp4"
            _encode_deck_batch(
                ffmpeg,
                image_paths,
                audio_paths[start:end],
                resolved_durations[start:end],
                fps,
                width,
                height,
                batch_path,
            )
            for image_path in image_paths:
                image_path.unlink()
            batches.append(batch_path)
        encoded = workspace / "deck.mp4"
        if len(batches) == 1:
            os.replace(batches[0], encoded)
        else:
            _concatenate_batches(ffmpeg, batches, encoded)
        os.replace(encoded, destination)


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
    if fps > _MAX_STATIC_DECK_FPS:
        raise ValidationError(f"fps must be <= {_MAX_STATIC_DECK_FPS:g}")
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


def _even_size(width: int, height: int) -> tuple[int, int]:
    """Round odd first-slide dimensions down for yuv420p encoding."""
    return max(2, width - width % 2), max(2, height - height % 2)


def _encode_deck_batch(
    ffmpeg: str,
    image_paths: list[Path],
    audio_tracks: list[AudioTrack | None],
    durations: list[float],
    fps: float,
    width: int,
    height: int,
    output_path: Path,
) -> None:
    """Encode a bounded group of still-image and narration pairs."""
    inputs: list[str] = []
    filters: list[str] = []
    concat_inputs: list[str] = []
    input_index = 0
    for slide_index, (image_path, audio, duration) in enumerate(
        zip(image_paths, audio_tracks, durations, strict=True)
    ):
        encoded_duration = max(duration, 1.0 / fps)
        inputs.extend(["-loop", "1", "-i", str(image_path)])
        video_index = input_index
        input_index += 1
        if audio is None:
            inputs.extend(["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"])
        else:
            inputs.extend(["-i", audio.path])
        audio_index = input_index
        input_index += 1

        video_label = f"v{slide_index}"
        audio_label = f"a{slide_index}"
        filters.append(
            f"[{video_index}:v]scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black,"
            f"fps={fps:g},trim=duration={encoded_duration:.9f},"
            f"setpts=PTS-STARTPTS[{video_label}]"
        )
        volume = f"volume={audio.volume}," if audio is not None else ""
        filters.append(
            f"[{audio_index}:a]{volume}atrim=duration={duration:.9f},apad,"
            f"atrim=duration={encoded_duration:.9f},"
            "aformat=sample_rates=48000:channel_layouts=stereo,"
            f"asetpts=PTS-STARTPTS[{audio_label}]"
        )
        concat_inputs.extend((f"[{video_label}]", f"[{audio_label}]"))
    filters.append(f"{''.join(concat_inputs)}concat=n={len(image_paths)}:v=1:a=1[video][audio]")
    _run_ffmpeg(
        [
            ffmpeg,
            "-y",
            *inputs,
            "-filter_complex",
            ";".join(filters),
            "-map",
            "[video]",
            "-map",
            "[audio]",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-ar",
            "48000",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
    )


def _concatenate_batches(ffmpeg: str, batches: list[Path], output_path: Path) -> None:
    """Stream-copy normalized batch files into the final static Deck MP4."""
    manifest = output_path.with_suffix(".ffconcat")
    manifest.write_text(
        "ffconcat version 1.0\n" + "".join(f"file '{batch.name}'\n" for batch in batches),
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
