"""Render, export, audio, and motion policy options."""

# Option fields use the shared model vocabulary re-exported by `common`.
# ruff: noqa: F405

from typing import Annotated, Literal

from pydantic import (
    ConfigDict,
    Field,
    NonNegativeInt,
    PositiveInt,
    field_validator,
    with_config,
)
from typing_extensions import TypedDict

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
    hold: Annotated[
        float, Field(strict=True, ge=0, allow_inf_nan=False, exclude_if=lambda value: value == 3.0)
    ] = 3.0
    loop: NonNegativeInt = 0
    matte: str = "#000000"
    max_size: tuple[PositiveInt, PositiveInt] | None = None
    colors: int | None = None
    workers: Annotated[int, Field(strict=True, ge=1, le=8)] = 1
    render_quality: Literal["standard", "high"] = "standard"

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
    """Options specific to animated MP4, WebM, and MOV output."""

    model_config = ConfigDict(extra="forbid")

    fps: Annotated[float, Field(gt=0, allow_inf_nan=False)] | None = None
    hold: Annotated[
        float, Field(strict=True, ge=0, allow_inf_nan=False, exclude_if=lambda value: value == 3.0)
    ] = 3.0
    matte: str = "#000000"
    soundtrack: AudioTrack | None = None
    loop_audio: bool | None = None
    workers: Annotated[int, Field(strict=True, ge=1, le=8)] = 1
    render_quality: Literal["standard", "high"] = "standard"
    transparent: Annotated[bool, Field(strict=True)] = False


class LottieOptions(quickthumbModel):
    """Vector pose sampling rate and nonnegative final playback hold for Lottie output."""

    model_config = ConfigDict(extra="forbid")

    fps: Annotated[float, Field(strict=True, gt=0, le=120, allow_inf_nan=False)] = 30.0
    hold: Annotated[float, Field(strict=True, ge=0, allow_inf_nan=False)] = 3.0


class ImageSequenceOptions(quickthumbModel):
    """Timing and compositing for silent PNG, JPEG, or WebP animation frames."""

    model_config = ConfigDict(extra="forbid")

    fps: Annotated[float, Field(strict=True, gt=0, le=120, allow_inf_nan=False)] = 30.0
    hold: Annotated[float, Field(strict=True, ge=0, allow_inf_nan=False)] = 3.0
    workers: Annotated[int, Field(strict=True, ge=1, le=8)] = 1
    render_quality: Literal["standard", "high"] = "standard"


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


@with_config(ConfigDict(extra="forbid"))
class _FidelityLimits(TypedDict):
    """Caller-selected acceptance limits for an optional static comparison."""

    pixel_tolerance: Annotated[int, Field(strict=True, ge=0, le=255)]
    max_different_pixel_ratio: Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
    min_hash_similarity: Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]


class ExportPolicy(_MotionModel):
    """Motion handling and opt-in, report-only static fidelity checks."""

    unsupported_motion: Literal["error", "warn", "rasterize", "static"] = "warn"
    pptx: dict[str, Literal["native", "rasterize", "static"]] = {}
    reduced_motion: bool = False
    fidelity: dict[Literal["svg", "pdf"], _FidelityLimits] = Field(
        default_factory=dict, exclude_if=lambda value: not value
    )


class ExportDiagnostic(_MotionModel):
    """Structured explanation of exporter support or fallback behavior."""

    layer_id: str | None = None
    slide_index: NonNegativeInt | None = Field(default=None, exclude_if=lambda value: value is None)
    layer_ids: list[str] = Field(default_factory=list, exclude_if=lambda value: not value)
    native_attempt: bool | None = Field(default=None, exclude_if=lambda value: value is None)
    feature: str
    target: str
    support: Literal["full", "native", "partial", "fallback", "unsupported"]
    fallback: Literal["fade", "rasterize", "static"] | None = None
    message: str
