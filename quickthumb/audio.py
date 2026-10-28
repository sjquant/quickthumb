"""Authoring-time source-audio analysis; renderers consume baked numeric motion."""

from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from quickthumb._slide_audio import _configured_tool
from quickthumb.errors import RenderingError, ValidationError
from quickthumb.models.motion import KeyframeSpec, ScaleTrack

_SAMPLE_RATE = 8000
_HOP = 160
_MAX_DURATION = 600
_MAX_BYTES = 64 * 1024 * 1024
_PARAMETERS = {
    "sample_rate": _SAMPLE_RATE,
    "hop_samples": _HOP,
    "baseline_windows": 10,
    "attack_ratio": 2.0,
    "minimum_rms": 0.01,
    "minimum_interval": 0.1,
}
_ALGORITHM = "rms-onsets-v1"
_Amplitude = Annotated[float, Field(ge=0, allow_inf_nan=False)]
_Time = Annotated[float, Field(ge=0, allow_inf_nan=False)]


class AudioAnalysis(BaseModel):
    """Stored source-clock onsets and linear RMS amplitudes, not a musical beat grid.

    RMS entry ``i`` describes the source window starting at ``i * 0.02`` seconds.
    The last window can be shorter. Export gain, looping, fades, narration and
    other mixed audio are outside this analysis. Numeric motion baked from this
    record can be sampled or rendered without the analyzer or FFmpeg.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    version: Literal["1"] = "1"
    algorithm: Literal["rms-onsets-v1"] = _ALGORITHM
    source_sha256: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    ffmpeg_version: str = Field(min_length=1, max_length=1024)
    sample_rate: Literal[8000] = _SAMPLE_RATE
    hop_samples: Literal[160] = _HOP
    duration: Annotated[float, Field(gt=0, le=_MAX_DURATION, allow_inf_nan=False)]
    onsets: tuple[_Time, ...] = Field(max_length=6000)
    rms: tuple[_Amplitude, ...] = Field(min_length=1, max_length=30000)

    @model_validator(mode="after")
    def validate_clock(self) -> AudioAnalysis:
        if len(self.rms) != math.ceil(
            round(self.duration * self.sample_rate, 6) / self.hop_samples
        ):
            raise ValueError("RMS window count does not match the source duration")
        if tuple(sorted(set(self.onsets))) != self.onsets:
            raise ValueError("onsets must be strictly increasing")
        if any(time >= self.duration for time in self.onsets):
            raise ValueError("onsets must be inside the source duration")
        return self

    def scale_track(self, *, min_scale: float = 1.0, max_scale: float = 1.15) -> ScaleTrack:
        """Bake peak-normalized RMS into a source-clock object-scale track.

        Each 20ms source window holds its scale until the next window. Silence
        maps to ``min_scale``; the loudest window maps to ``max_scale``. At the
        exact source end the track returns to ``min_scale`` and stays there.
        No audio source, decoder or renderer is consulted by this operation.
        """
        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value <= 0
            for value in (min_scale, max_scale)
        ):
            raise ValidationError("scale bounds must be finite positive numbers")
        if max_scale < min_scale:
            raise ValidationError("max_scale must be greater than or equal to min_scale")
        peak = max(self.rms)
        keyframes = [
            KeyframeSpec(
                time=round(index * self.hop_samples / self.sample_rate, 9),
                value=min_scale + (max_scale - min_scale) * (amplitude / peak if peak else 0),
                hold=True,
            )
            for index, amplitude in enumerate(self.rms)
        ]
        keyframes.append(KeyframeSpec(time=self.duration, value=min_scale))
        return ScaleTrack(keyframes=keyframes)


def analyze_audio(
    path: str | os.PathLike[str], *, cache_dir: str | os.PathLike[str] | None = None
) -> AudioAnalysis:
    """Analyze a local source into cached 20ms RMS windows and transient onsets.

    Requires FFmpeg (or ``QUICKTHUMB_FFMPEG``). Inputs are limited to 64 MiB,
    ten minutes of decoded audio and a 60-second analysis timeout. Exceeding a
    limit raises an error; audio is never silently truncated. Cache entries are
    keyed by source bytes, algorithm, fixed parameters and FFmpeg version.
    Use ``AudioAnalysis.model_validate_json`` to load a saved record offline.
    """
    source = Path(path).expanduser().resolve()
    source_hash = _source_hash(source)
    ffmpeg = _configured_tool("QUICKTHUMB_FFMPEG", "ffmpeg")
    if ffmpeg is None:
        raise RenderingError(
            "Audio analysis requires FFmpeg. Install FFmpeg or set QUICKTHUMB_FFMPEG."
        )
    try:
        version = subprocess.run(
            [ffmpeg, "-version"], capture_output=True, text=True, check=True, timeout=5
        ).stdout.splitlines()[0]
    except (OSError, subprocess.SubprocessError, IndexError) as error:
        raise RenderingError("Could not identify FFmpeg for audio analysis.") from error
    identity = {
        "source_sha256": source_hash,
        "algorithm": _ALGORITHM,
        "ffmpeg_version": version,
        "parameters": _PARAMETERS,
    }
    key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    directory = (
        Path(cache_dir)
        if cache_dir is not None
        else Path(tempfile.gettempdir()) / "quickthumb-audio"
    )
    cached = directory.expanduser() / f"{key}.json"
    if cached.exists():
        try:
            with cached.open("rb") as stream:
                payload = stream.read(2 * 1024 * 1024 + 1)
            if len(payload) > 2 * 1024 * 1024:
                raise ValueError("cache record exceeds its bounded analysis size")
            record = AudioAnalysis.model_validate_json(payload)
            if record.source_sha256 != source_hash or record.ffmpeg_version != version:
                raise ValueError("cache source or decoder identity differs")
            return record
        except (OSError, ValueError) as error:
            raise RenderingError(
                f"Invalid audio analysis cache entry '{cached}'. Remove it and analyze again."
            ) from error

    record = _analyze_source(source, source_hash, ffmpeg, version)
    if _source_hash(source) != source_hash:
        raise RenderingError(
            "Audio source changed during analysis. Analyze the settled file again."
        )
    _store_analysis(cached, record)
    return record


def _source_hash(source: Path) -> str:
    if not source.is_file():
        raise RenderingError(f"Audio analysis source is not a local file: '{source}'.")
    digest = hashlib.sha256()
    total = 0
    try:
        with source.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                total += len(chunk)
                if total > _MAX_BYTES:
                    raise RenderingError("Audio analysis source exceeds the 64 MiB limit.")
                digest.update(chunk)
    except OSError as error:
        raise RenderingError(f"Cannot read audio analysis source '{source}'.") from error
    return digest.hexdigest()


def _analyze_source(source: Path, source_hash: str, ffmpeg: str, version: str) -> AudioAnalysis:
    filters = (
        f"aresample={_SAMPLE_RATE},aformat=channel_layouts=mono,asetpts=N/SR/TB,"
        f"asetnsamples=n={_HOP}:p=0,"
        "astats=metadata=1:reset=1:measure_perchannel=none:"
        "measure_overall=RMS_level+Number_of_samples,ametadata=print:file=-"
    )
    try:
        result = subprocess.run(
            [
                ffmpeg,
                "-nostdin",
                "-v",
                "error",
                "-i",
                str(source),
                "-map",
                "0:a:0",
                "-t",
                str(_MAX_DURATION + _HOP / _SAMPLE_RATE),
                "-af",
                filters,
                "-f",
                "null",
                "-",
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired as error:
        raise RenderingError(
            "Audio analysis exceeded the 60-second limit. Use a shorter source."
        ) from error
    except (OSError, subprocess.CalledProcessError) as error:
        raise RenderingError(
            f"FFmpeg could not analyze audio in '{source}'. Use a readable audio file and "
            "an FFmpeg build with astats and ametadata filters."
        ) from error

    rms = []
    samples = 0
    try:
        for line in result.stdout.splitlines():
            if line.startswith("lavfi.astats.Overall.RMS_level="):
                db = float(line.split("=", 1)[1])
                rms.append(0.0 if db == -math.inf else 10 ** (db / 20))
            elif line.startswith("lavfi.astats.Overall.Number_of_samples="):
                samples += int(float(line.split("=", 1)[1]))
        if samples > _MAX_DURATION * _SAMPLE_RATE:
            raise RenderingError(
                "Audio analysis exceeds the ten-minute limit. Use a shorter source."
            )
        return AudioAnalysis(
            source_sha256=source_hash,
            ffmpeg_version=version,
            duration=samples / _SAMPLE_RATE,
            rms=tuple(rms),
            onsets=_onsets(rms),
        )
    except (ValueError, OverflowError) as error:
        raise RenderingError("FFmpeg returned invalid or empty audio analysis data.") from error


def _onsets(rms: list[float]) -> tuple[float, ...]:
    onsets: list[float] = []
    baseline_windows = int(_PARAMETERS["baseline_windows"])
    for index, amplitude in enumerate(rms):
        history = rms[max(0, index - baseline_windows) : index]
        baseline = sum(history) / len(history) if history else 0.0
        previous = history[-1] if history else 0.0
        time = round(index * _HOP / _SAMPLE_RATE, 9)
        if (
            amplitude >= _PARAMETERS["minimum_rms"]
            and amplitude > _PARAMETERS["attack_ratio"] * max(baseline, previous)
            and (not onsets or time - onsets[-1] >= _PARAMETERS["minimum_interval"] - 1e-9)
        ):
            onsets.append(time)
    return tuple(onsets)


def _store_analysis(path: Path, record: AudioAnalysis) -> None:
    temporary = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
            temporary = stream.name
            stream.write(record.model_dump_json().encode())
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except OSError as error:
        raise RenderingError(f"Could not persist audio analysis cache '{path}'.") from error
    finally:
        if temporary is not None:
            Path(temporary).unlink(missing_ok=True)
