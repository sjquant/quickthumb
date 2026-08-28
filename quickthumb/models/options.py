"""Render, export, audio, and motion policy options."""

# Option fields use the shared model vocabulary re-exported by ``common``.
# ruff: noqa: F405

from typing import Annotated, Literal

from pydantic import (
    ConfigDict,
    Field,
    NonNegativeInt,
    PositiveInt,
    field_validator,
)

from quickthumb.errors import ValidationError

from .common import *  # noqa: F401,F403
from .common import _MotionModel


class AudioTrack(quickthumbModel):
    """An audio source with deterministic export-time mix controls."""

    model_config = ConfigDict(extra="forbid")

    path: str
    volume: Annotated[float, Field(ge=0, allow_inf_nan=False)] = 1.0
    loop: bool = False
    fade_out: Annotated[
        float, Field(ge=0, allow_inf_nan=False, exclude_if=lambda value: value == 0.0)
    ] = 0.0


class GifOptions(quickthumbModel):
    """Options specific to animated GIF output."""

    model_config = ConfigDict(extra="forbid")

    fps: Annotated[float, Field(gt=0, allow_inf_nan=False)] | None = None
    loop: NonNegativeInt = 0
    matte: str = "#000000"
    max_size: tuple[PositiveInt, PositiveInt] | None = None
    colors: int | None = None

    @field_validator("loop")
    @classmethod
    def validate_loop(cls, value: int) -> int:
        if value > 65535:
            raise ValueError("loop must be <= 65535")
        return value

    @field_validator("colors")
    @classmethod
    def validate_colors(cls, value: int | None) -> int | None:
        if value is not None and not 2 <= value <= 256:
            raise ValueError("colors must be between 2 and 256")
        return value


class VideoOptions(quickthumbModel):
    """Options specific to animated MP4 and WebM output."""

    model_config = ConfigDict(extra="forbid")

    fps: Annotated[float, Field(gt=0, allow_inf_nan=False)] | None = None
    matte: str = "#000000"
    soundtrack: AudioTrack | None = None
    loop_audio: bool | None = None


def coerce_audio_track(value: AudioTrack | str | dict | None) -> AudioTrack | None:
    """Normalize legacy path strings and mapping specs into an audio track."""
    if value is None:
        return None
    if isinstance(value, AudioTrack):
        return value
    if isinstance(value, str):
        return AudioTrack(path=value)
    if isinstance(value, dict):
        return AudioTrack(**value)
    raise ValidationError("audio must be a path string or AudioTrack configuration")


class MotionProfile(_MotionModel):
    """Deck-wide defaults for motion speed and visual feel."""

    name: Literal["presentation", "social", "cinematic", "minimal"]
    speed: FinitePositiveFloat = 1.0
    feel: Literal["gentle", "soft", "snappy", "dramatic", "minimal"] = "soft"


class ExportPolicy(_MotionModel):
    """Policy controlling how an exporter handles unsupported motion."""

    unsupported_motion: Literal["error", "warn", "rasterize", "static"] = "warn"
    pptx: dict[str, Literal["native", "rasterize", "static"]] = {}
    reduced_motion: bool = False


class ExportDiagnostic(_MotionModel):
    """Structured explanation of exporter support or fallback behavior."""

    layer_id: str | None = None
    feature: str
    target: str
    support: Literal["full", "native", "partial", "fallback", "unsupported"]
    fallback: Literal["fade", "rasterize", "static"] | None = None
    message: str
