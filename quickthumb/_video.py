"""Small FFmpeg-backed helpers for constrained video-layer composition."""

from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
from bisect import bisect_right
from collections import OrderedDict
from dataclasses import dataclass
from fractions import Fraction

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
    frame_rate: float
    frame_times: tuple[float, ...] = ()


class VideoDecoder:
    """A sequential raw-frame decoder reused across timeline samples."""

    def __init__(self, source: str, info: VideoInfo):
        self.source = source
        self.info = info
        self._process: subprocess.Popen[bytes] | None = None
        self._next_index = 0

    def close(self) -> None:
        if self._process is None:
            return
        self._process.stdout.close() if self._process.stdout else None
        self._process.terminate()
        try:
            self._process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self._process.kill()
            self._process.wait()
        self._process = None

    def frame_at(self, time: float) -> Image.Image:
        if self.info.frame_times:
            target_index = min(
                len(self.info.frame_times) - 1,
                max(0, bisect_right(self.info.frame_times, time) - 1),
            )
        else:
            max_index = max(0, math.ceil(self.info.duration * self.info.frame_rate) - 1)
            target_index = min(max_index, max(0, int(time * self.info.frame_rate + 0.5)))
        if target_index < self._next_index:
            self.close()
            self._next_index = target_index
            self._process = self._start(self._timestamp_for_index(target_index))
        if self._process is None:
            self._process = self._start()
        frame_size = self.info.width * self.info.height * 4
        raw = b""
        while self._next_index <= target_index:
            raw = self._process.stdout.read(frame_size) if self._process.stdout else b""
            if len(raw) != frame_size:
                self.close()
                raise RenderingError(f"Could not decode video frame from {self.source!r}")
            self._next_index += 1
        return Image.frombytes("RGBA", (self.info.width, self.info.height), raw)

    def _timestamp_for_index(self, index: int) -> float:
        if self.info.frame_times:
            return self.info.frame_times[index]
        return index / self.info.frame_rate

    def _start(self, start_time: float = 0.0) -> subprocess.Popen[bytes]:
        ffmpeg = _tool("ffmpeg", "QUICKTHUMB_FFMPEG")
        try:
            seek = ["-ss", f"{start_time:.6f}"] if start_time > 0 else []
            return subprocess.Popen(
                [
                    ffmpeg,
                    "-v",
                    "error",
                    "-i",
                    self.source,
                    *seek,
                    "-map",
                    "0:v:0",
                    "-f",
                    "rawvideo",
                    "-pix_fmt",
                    "rgba",
                    "pipe:1",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
        except OSError as error:
            raise RenderingError(f"Could not start FFmpeg for {self.source!r}") from error


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
            "stream=codec_type,width,height,duration,avg_frame_rate:format=duration",
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
        frame_rate_raw = stream.get("avg_frame_rate") or "30/1"
        frame_rate = _parse_frame_rate(frame_rate_raw)
    except (
        KeyError,
        IndexError,
        TypeError,
        ValueError,
        ZeroDivisionError,
        json.JSONDecodeError,
    ) as error:
        raise RenderingError(f"Video source has no usable video stream: {source!r}") from error
    if duration <= 0 or width <= 0 or height <= 0:
        raise RenderingError(f"Video source has invalid dimensions or duration: {source!r}")
    frame_times = _probe_frame_times(ffprobe, source)
    return VideoInfo(duration, width, height, has_audio, frame_rate, frame_times)


def _parse_frame_rate(value: str) -> float:
    try:
        parsed = float(Fraction(value))
    except (TypeError, ValueError, ZeroDivisionError):
        return 30.0
    return parsed if math.isfinite(parsed) and parsed > 0 else 30.0


def _probe_frame_times(ffprobe: str, source: str) -> tuple[float, ...]:
    """Read presentation timestamps when available, retaining CFR fallback support."""
    result = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_frames",
            "-show_entries",
            "frame=best_effort_timestamp_time",
            "-of",
            "csv=p=0",
            source,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return ()
    values: list[float] = []
    for line in result.stdout.splitlines():
        try:
            timestamp = float(line.strip())
        except ValueError:
            continue
        if math.isfinite(timestamp) and (not values or timestamp >= values[-1]):
            values.append(timestamp)
    return tuple(values)


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


def render_video_layer(
    image: Image.Image,
    layer: VideoLayer,
    time: float,
    info: VideoInfo,
    frame_cache: OrderedDict[tuple[str, float], Image.Image],
    decoder_cache: dict[str, VideoDecoder],
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
        decoder = decoder_cache.get(layer.source)
        if decoder is None:
            decoder = VideoDecoder(layer.source, info)
            decoder_cache[layer.source] = decoder
        frame = decoder.frame_at(sample_time)
        frame_cache[key] = frame
    frame_cache.move_to_end(key)
    while len(frame_cache) > 8:
        frame_cache.popitem(last=False)
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
