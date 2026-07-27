"""Small FFmpeg-backed helpers for constrained video-layer composition."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from io import BytesIO

from PIL import Image, ImageColor, ImageDraw, ImageFont

from quickthumb._base import parse_coordinate
from quickthumb._images import ImageEngine
from quickthumb.errors import RenderingError, ValidationError
from quickthumb.models import VideoCaption, VideoLayer


@dataclass(frozen=True)
class VideoInfo:
    duration: float
    width: int
    height: int
    has_audio: bool


def _tool(name: str, setting: str) -> str:
    configured = os.environ.get(setting)
    path = configured or shutil.which(name)
    if path is None:
        raise RenderingError(f"Video layers require {name}. Install FFmpeg or set {setting}.")
    return path


def probe_video(source: str) -> VideoInfo:
    """Probe the first video stream and convert codec failures to a safe error."""
    if not source.startswith(("http://", "https://")) and not os.path.exists(source):
        raise FileNotFoundError(source)
    ffprobe = _tool("ffprobe", "QUICKTHUMB_FFPROBE")
    result = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "stream=codec_type,width,height,duration:format=duration",
            "-of",
            "json",
            source,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.strip()[-500:]
        raise RenderingError(f"Could not read video source {source!r}: {detail}")
    try:
        payload = json.loads(result.stdout)
        streams = payload["streams"]
        stream = next(item for item in streams if item.get("codec_type") == "video")
        duration = float(stream.get("duration") or payload["format"]["duration"])
        width, height = int(stream["width"]), int(stream["height"])
        has_audio = any(item.get("codec_type") == "audio" for item in streams)
    except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise RenderingError(f"Video source has no usable video stream: {source!r}") from error
    if duration <= 0 or width <= 0 or height <= 0:
        raise RenderingError(f"Video source has invalid dimensions or duration: {source!r}")
    return VideoInfo(duration, width, height, has_audio)


def effective_duration(layer: VideoLayer, info: VideoInfo) -> float:
    if layer.trim_start >= info.duration:
        raise ValidationError(
            f"trim_start {layer.trim_start} is outside source duration {info.duration:.6f}"
        )
    source_end = layer.trim_end if layer.trim_end is not None else info.duration
    if source_end > info.duration + 1e-6:
        raise ValidationError(
            f"trim_end {source_end} exceeds source duration "
            f"{info.duration:.6f} for {layer.source!r}"
        )
    available = max(0.0, source_end - layer.trim_start) / layer.speed
    return layer.duration if layer.duration is not None else available


def source_time(layer: VideoLayer, time: float, info: VideoInfo) -> float:
    duration = effective_duration(layer, info)
    local = 0.0 if time <= layer.start else min(time - layer.start, duration)
    return min(info.duration, layer.trim_start + local * layer.speed)


def extract_frame(source: str, time: float) -> Image.Image:
    ffmpeg = _tool("ffmpeg", "QUICKTHUMB_FFMPEG")
    result = subprocess.run(
        [
            ffmpeg,
            "-v",
            "error",
            "-ss",
            f"{max(0.0, time):.6f}",
            "-i",
            source,
            "-frames:v",
            "1",
            "-f",
            "image2pipe",
            "-vcodec",
            "png",
            "pipe:1",
        ],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0 or not result.stdout:
        detail = result.stderr.decode(errors="replace").strip()[-500:]
        raise RenderingError(f"Could not decode video source {source!r}: {detail}")
    try:
        return Image.open(BytesIO(result.stdout)).convert("RGBA")
    except Exception as error:
        raise RenderingError(f"FFmpeg returned an invalid frame for {source!r}") from error


def render_video_layer(
    image: Image.Image,
    layer: VideoLayer,
    time: float,
    info: VideoInfo,
    frame_cache: dict[tuple[str, float], Image.Image],
    font_loader=None,
) -> None:
    """Composite one sampled clip and its active captions onto a canvas."""
    duration = effective_duration(layer, info)
    if time < layer.start or time > layer.start + duration + 1e-9:
        return
    sample_time = source_time(layer, time, info)
    key = (layer.source, round(sample_time, 6))
    frame = frame_cache.get(key)
    if frame is None:
        frame = extract_frame(layer.source, sample_time)
        frame_cache[key] = frame
    fitted = ImageEngine._fit_image(
        frame, (layer.width, layer.height), layer.fit, Image.Resampling.BICUBIC
    )
    x = parse_coordinate(layer.position[0], image.width)
    y = parse_coordinate(layer.position[1], image.height)
    image.alpha_composite(fitted, (x, y))
    _render_captions(image, layer.captions, time - layer.start, font_loader)


def _render_captions(
    image: Image.Image, captions: list[VideoCaption], time: float, font_loader
) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    for caption in captions:
        if not caption.start <= time < caption.end:
            continue
        font = (
            font_loader(None, caption.size, False, False)
            if font_loader
            else ImageFont.load_default()
        )
        x = parse_coordinate(caption.position[0], image.width)
        y = parse_coordinate(caption.position[1], image.height)
        bbox = draw.textbbox((0, 0), caption.text, font=font)
        left = x - (bbox[2] - bbox[0]) // 2
        top = y - (bbox[3] - bbox[1]) // 2
        draw.text((left + 2, top + 2), caption.text, font=font, fill=(0, 0, 0, 180))
        draw.text(
            (left, top),
            caption.text,
            font=font,
            fill=ImageColor.getrgb(caption.color) + (255,),
        )
