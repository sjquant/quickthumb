"""Document-level discriminated unions and stable result models."""

# Shared model primitives are intentionally re-exported by `common`.
# ruff: noqa: F405

import base64 as _base64
import hashlib as _hashlib
from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import (
    ConfigDict,
    Discriminator,
    Field,
    NonNegativeInt,
    PositiveInt,
    model_validator,
)

from quickthumb.errors import ErrorDetail

from .common import *  # noqa: F401,F403
from .layers import (
    BackgroundLayer,
    GroupLayer,
    ImageLayer,
    NullLayer,
    OutlineLayer,
    PluginLayer,
    ShapeLayer,
    SvgLayer,
    TextLayer,
    VideoLayer,
)
from .options import ExportDiagnostic, _FidelityLimits
from .visualizations import ChartLayer, QRCodeLayer

LayerType = Annotated[
    BackgroundLayer
    | TextLayer
    | OutlineLayer
    | ImageLayer
    | ShapeLayer
    | SvgLayer
    | ChartLayer
    | QRCodeLayer
    | VideoLayer
    | PluginLayer
    | NullLayer
    | GroupLayer,
    Discriminator("type"),
]


class CanvasModel(quickthumbModel):
    kind: Literal["canvas"] = "canvas"
    width: PositiveInt | None = None
    height: PositiveInt | None = None
    platform: str | None = None
    layers: list[LayerType]

    @model_validator(mode="after")
    def validate_parent_graph(self):
        from quickthumb._parenting import validate_parent_graph

        validate_parent_graph(self.layers)
        return self


class CanvasSpecModel(quickthumbModel):
    kind: Literal["canvas"] = "canvas"
    width: PositiveInt | None = None
    height: PositiveInt | None = None
    platform: str | None = None
    theme: dict[str, Any] = Field(default_factory=dict)
    layers: list[LayerType]

    @model_validator(mode="after")
    def validate_parent_graph(self):
        from quickthumb._parenting import validate_parent_graph

        validate_parent_graph(self.layers)
        return self


class ValidationReport(quickthumbModel):
    """Stable result of a document-level validation pass."""

    model_config = ConfigDict(extra="forbid")

    version: Literal["1"] = "1"
    valid: bool
    errors: list[ErrorDetail] = Field(default_factory=list)
    warnings: list[ErrorDetail] = Field(default_factory=list)

    @property
    def ok(self) -> bool:
        """Alias useful when a report is consumed as a guard clause."""
        return self.valid


class DiagnosticReport(quickthumbModel):
    """Stable diagnostic envelope shared by Canvas and Deck."""

    model_config = ConfigDict(extra="forbid")

    version: Literal["1"] = "1"
    findings: list[Any] = Field(default_factory=list)


class AssetStatus(StrEnum):
    """Resolution outcome of one asset reference; compares equal to its string value.

    - `LOCAL`: an existing local file; `content_hash` is its SHA-256.
    - `MISSING`: a local path that does not exist.
    - `NETWORK`: downloaded during this resolution and written to the cache.
    - `FRESH`: served from a cache entry within the configured `max_age`.
    - `STALE`: served from an expired cache entry (or while offline) because
      a refresh was not possible; see `stale_reason` and `fetched_at`.
    - `UNRESOLVED`: a remote reference that has not been resolved yet.
    """

    LOCAL = "local"
    MISSING = "missing"
    NETWORK = "network"
    FRESH = "fresh"
    STALE = "stale"
    UNRESOLVED = "unresolved"


class AssetManifestEntry(quickthumbModel):
    """A deterministic description of one document asset reference.

    `source` is the reference as written in the document and `asset_type` its
    semantic role (`image`, `svg`, `font`, `text-fill`, `video`, `audio`, `plugin`).
    `status` is the resolution outcome (see `AssetStatus`); for a `stale`
    value, `stale_reason` says why it was not refreshed and `fetched_at` how
    old it is, so callers can decide whether to proceed.

    `source_key` is the canonical URL, `cache_key`/`cache_path` identify the
    cache entry, `content_hash` is the SHA-256 of the bytes used, and
    `fetched_at` is the UTC ISO-8601 time the remote bytes were downloaded.
    """

    source: str
    asset_type: str = "asset"
    status: AssetStatus
    source_key: str | None = None
    cache_key: str | None = None
    cache_path: str | None = None
    content_hash: str | None = None
    fetched_at: str | None = None
    stale_reason: str | None = None


class PrefetchResult(quickthumbModel):
    """Stable, JSON-serializable result returned by `Document.prefetch_assets()`."""

    model_config = ConfigDict(extra="forbid")

    version: Literal["1"] = "1"
    kind: Literal["canvas", "deck"]
    asset_manifest: list[AssetManifestEntry] = Field(default_factory=list)


class CanonicalFrame(quickthumbModel):
    """One canonical RGBA raster observation.

    `data` is base64 of the raw pixel buffer: `width * height` pixels in
    row-major order from the top-left corner, four 8-bit channels per pixel
    in R, G, B, A order, sRGB-encoded with straight (non-premultiplied) alpha.
    `sha256` is the hex digest of that decoded buffer, so two frames drew
    identical pixels exactly when their digests match.
    """

    model_config = ConfigDict(extra="forbid")

    index: NonNegativeInt
    slide: NonNegativeInt = 0
    time: float | None = None
    width: PositiveInt
    height: PositiveInt
    mode: Literal["RGBA"] = "RGBA"
    sha256: str
    data: str

    @model_validator(mode="after")
    def _payload_matches_digest(self) -> "CanonicalFrame":
        raw = self.to_bytes()
        if len(raw) != self.width * self.height * 4:
            raise ValueError("data must hold width * height RGBA pixels")
        if _hashlib.sha256(raw).hexdigest() != self.sha256:
            raise ValueError("sha256 must be the digest of the decoded data")
        return self

    def to_bytes(self) -> bytes:
        """Decode the frame's raw RGBA bytes."""
        return _base64.b64decode(self.data)

    def to_image(self):
        """Decode the frame as a PIL image for convenience callers."""
        from PIL import Image

        return Image.frombytes(self.mode, (self.width, self.height), self.to_bytes())


class RenderEnvironment(quickthumbModel):
    """Rendering-environment facts that can change canonical pixels.

    Identical documents sampled under identical environments produce
    identical frame digests. `ffmpeg_version` is set only for documents
    with video layers, whose pixels FFmpeg decodes. Font and image inputs are
    described by the document's asset manifest rather than here.
    """

    model_config = ConfigDict(extra="forbid")

    renderer: Literal["quickthumb"] = "quickthumb"
    quickthumb_version: str
    pillow_version: str
    freetype_version: str | None = None
    text_layout: Literal["basic", "raqm"]
    ffmpeg_version: str | None = None


class TimelineSegment(quickthumbModel):
    """Where one slide sits on the normalized document timeline.

    All values are absolute seconds from the start of the document timeline.
    The slide is on screen over `[start, end)`: its incoming transition
    plays over `[start, transition_end)`, its layer animations settle at
    `animation_end`, and its settled state holds until `end`.
    """

    model_config = ConfigDict(extra="forbid")

    slide: NonNegativeInt
    start: float
    transition_end: float
    animation_end: float
    end: float


class FrameSequence(quickthumbModel):
    """An ordered, JSON-safe set of canonical frames and their sampling context.

    A `still` capture holds one authored-static frame per page (one for a
    Canvas, one per Deck slide), matching the untimed raster renderer rather
    than seeking the animation endpoint. Each frame keeps that page's own size
    and transparency; `duration` is 0, `timeline` is empty, and frame `time`
    is `None`.

    A `timeline` capture observes instants of the normalized document
    timeline that animated exports play. Every frame has the document's first
    page size and is composited onto the opaque `matte` color, and frames
    are ordered by ascending `time`. `duration` is the full timeline
    length in seconds; `fps` is the uniform sampling rate when the capture
    used one, else `None`. This observation grid is not an encoded frame index:
    codecs can quantize timing and coalesce or repeat frames. Deck timeline
    capture uses narration-aware video timing; GIF ignores slide narration
    and explicit slide durations.
    """

    model_config = ConfigDict(extra="forbid")

    version: Literal["1"] = "1"
    kind: Literal["canvas", "deck"]
    capture: Literal["still", "timeline"]
    color_space: Literal["srgb"] = "srgb"
    alpha: Literal["straight"] = "straight"
    matte: str | None = None
    fps: float | None = None
    duration: float = 0.0
    timeline: list[TimelineSegment] = Field(default_factory=list)
    environment: RenderEnvironment
    frames: list[CanonicalFrame] = Field(default_factory=list)


class _FidelityMetrics(quickthumbModel):
    """An explicitly requested renderer observation of authored-static output."""

    model_config = ConfigDict(extra="forbid")

    renderer: Literal["cairosvg", "pdfium"]
    renderer_version: str
    cairo_version: str | None = Field(default=None, exclude_if=lambda value: value is None)
    binding_version: str | None = Field(default=None, exclude_if=lambda value: value is None)
    page_count: PositiveInt | None = Field(default=None, exclude_if=lambda value: value is None)
    page_size_points: tuple[float, float] | None = Field(
        default=None, exclude_if=lambda value: value is None
    )
    render_scale: Literal[1] | None = Field(default=None, exclude_if=lambda value: value is None)
    scope: Literal["authored_static"] = "authored_static"
    hash_algorithm: Literal["average_hash_8x8"] = "average_hash_8x8"
    canonical_environment: RenderEnvironment
    verdict: Literal["exact", "tolerated", "out_of_policy"]
    limits: _FidelityLimits
    actual_width: PositiveInt
    actual_height: PositiveInt
    pixel_diff_ratio: float | None = None
    hash_similarity: float
    mean_absolute_error: float | None = None
    max_channel_delta: int | None = None


class PixelMetrics(quickthumbModel):
    """Canonical pixel metadata and any explicitly requested fidelity observation."""

    mode: Literal["RGBA"] = "RGBA"
    width: PositiveInt | None = None
    height: PositiveInt | None = None
    frame_count: NonNegativeInt = 0
    fidelity: _FidelityMetrics | None = Field(default=None, exclude_if=lambda value: value is None)


class TimingMetrics(quickthumbModel):
    """Encoded visual timing; interactive HTML has no fixed playback duration."""

    duration: float = Field(
        default=0.0,
        description="Encoded visual playback seconds, excluding audio container padding.",
    )
    fps: float | None = Field(
        default=None,
        description="Selected sampling rate; GIF stored frames can differ from duration times fps.",
    )
    frame_count: NonNegativeInt = Field(
        default=0,
        description="Actual encoded frames, after GIF coalescing or video hold repetition.",
    )


class FallbackDiagnostic(quickthumbModel):
    """Structured explanation for a capability fallback."""

    code: str = "export_fallback"
    target: str
    layer_id: str | None = None
    slide_index: NonNegativeInt | None = Field(default=None, exclude_if=lambda value: value is None)
    layer_ids: list[str] = Field(default_factory=list, exclude_if=lambda value: not value)
    reason: str
    native_attempt: bool | None = None
    pixel_diff_ratio: float | None = None
    hash_similarity: float | None = None
    suggestion: str | None = None


class ExportResult(quickthumbModel):
    """Stable, JSON-serializable result returned by `Document.export()`."""

    model_config = ConfigDict(extra="forbid")

    version: Literal["1"] = "1"
    kind: Literal["canvas", "deck"]
    target: str
    output_format: str
    written_paths: list[str] = Field(default_factory=list)
    capability_report: list[ExportDiagnostic] = Field(default_factory=list)
    fallback_diagnostics: list[FallbackDiagnostic] = Field(default_factory=list)
    pixel_metrics: PixelMetrics = Field(default_factory=PixelMetrics)
    timing_metrics: TimingMetrics = Field(default_factory=TimingMetrics)
    asset_manifest: list[AssetManifestEntry] = Field(default_factory=list)


class ImageSequenceManifest(quickthumbModel):
    """Actual image encoding and logical decoded pixels, without a color-profile claim.

    RGBA/straight describes alpha-preserving PNG and WebP decoding; an opaque
    WebP file may omit its redundant alpha plane and open as RGB in some readers.
    """

    model_config = ConfigDict(extra="forbid")

    version: Literal["1"] = "1"
    kind: Literal["canvas", "deck"]
    format: Literal["image_sequence"] = "image_sequence"
    encoding: Literal["png", "jpeg", "webp"]
    filename_pattern: str
    start_index: Literal[0] = 0
    frame_count: PositiveInt
    fps: Annotated[float, Field(gt=0, le=120, allow_inf_nan=False)]
    duration: Annotated[float, Field(gt=0, allow_inf_nan=False)]
    width: PositiveInt
    height: PositiveInt
    mode: Literal["RGB", "RGBA"]
    bit_depth: Literal[8] = 8
    alpha: Literal["straight", "none"]
    lossless: bool
    quality: Annotated[int, Field(strict=True, ge=1, le=95)] | None = None
    matte: str | None = None


class ImageSequenceResult(ImageSequenceManifest):
    """The sequence manifest plus its published location and motion diagnostics."""

    output_directory: str
    manifest_path: str
    capability_report: list[ExportDiagnostic] = Field(default_factory=list)
