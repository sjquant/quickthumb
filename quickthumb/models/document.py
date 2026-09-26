"""Document-level discriminated unions and stable result models."""

# Shared model primitives are intentionally re-exported by ``common``.
# ruff: noqa: F405

import base64 as _base64
import hashlib as _hashlib
from typing import Annotated, Any, Literal

from pydantic import (
    ConfigDict,
    Discriminator,
    Field,
    NonNegativeInt,
    PositiveInt,
    model_validator,
)

from .common import *  # noqa: F401,F403
from .layers import (
    BackgroundLayer,
    GroupLayer,
    ImageLayer,
    OutlineLayer,
    PluginLayer,
    ShapeLayer,
    SvgLayer,
    TextLayer,
    VideoLayer,
)
from .options import ExportDiagnostic
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
    | GroupLayer,
    Discriminator("type"),
]


class CanvasModel(quickthumbModel):
    kind: Literal["canvas"] = "canvas"
    width: PositiveInt | None = None
    height: PositiveInt | None = None
    platform: str | None = None
    layers: list[LayerType]


class CanvasSpecModel(quickthumbModel):
    kind: Literal["canvas"] = "canvas"
    width: PositiveInt | None = None
    height: PositiveInt | None = None
    platform: str | None = None
    theme: dict[str, Any] = Field(default_factory=dict)
    layers: list[LayerType]


class ValidationIssue(quickthumbModel):
    """One actionable document validation issue."""

    code: str
    message: str
    path: str | None = None
    suggestion: str | None = None


class ValidationReport(quickthumbModel):
    """Stable result of a document-level validation pass."""

    model_config = ConfigDict(extra="forbid")

    version: Literal["1"] = "1"
    valid: bool
    errors: list[ValidationIssue] = Field(default_factory=list)
    warnings: list[ValidationIssue] = Field(default_factory=list)

    @property
    def ok(self) -> bool:
        """Alias useful when a report is consumed as a guard clause."""
        return self.valid


class DiagnosticReport(quickthumbModel):
    """Stable diagnostic envelope shared by Canvas and Deck."""

    model_config = ConfigDict(extra="forbid")

    version: Literal["1"] = "1"
    findings: list[Any] = Field(default_factory=list)


class AssetManifestEntry(quickthumbModel):
    """A deterministic description of one document asset reference."""

    source: str
    asset_type: str = "asset"
    status: str
    source_key: str | None = None
    cache_key: str | None = None
    cache_path: str | None = None
    content_hash: str | None = None


class ResolvedDocument(quickthumbModel):
    """Asset-resolution metadata returned without exposing renderer internals."""

    model_config = ConfigDict(extra="forbid")

    version: Literal["1"] = "1"
    kind: Literal["canvas", "deck"]
    asset_manifest: list[AssetManifestEntry] = Field(default_factory=list)


class CanonicalFrame(quickthumbModel):
    """One canonical RGBA raster observation.

    ``data`` is base64 of the raw pixel buffer: ``width * height`` pixels in
    row-major order from the top-left corner, four 8-bit channels per pixel
    in R, G, B, A order, sRGB-encoded with straight (non-premultiplied) alpha.
    ``sha256`` is the hex digest of that decoded buffer, so two frames drew
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
    identical frame digests. ``ffmpeg_version`` is set only for documents
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
    The slide is on screen over ``[start, end)``: its incoming transition
    plays over ``[start, transition_end)``, its layer animations settle at
    ``animation_end``, and its settled state holds until ``end``.
    """

    model_config = ConfigDict(extra="forbid")

    slide: NonNegativeInt
    start: float
    transition_end: float
    animation_end: float
    end: float


class FrameSequence(quickthumbModel):
    """An ordered, JSON-safe set of canonical frames and their sampling context.

    A ``still`` capture holds one settled frame per page (one for a Canvas,
    one per Deck slide), each at that page's own size and with transparency
    preserved; its ``duration`` is 0, ``timeline`` is empty, and frame
    ``time`` is ``None``.

    A ``timeline`` capture observes instants of the normalized document
    timeline that animated exports play. Every frame has the document's first
    page size and is composited onto the opaque ``matte`` color, and frames
    are ordered by ascending ``time``. ``duration`` is the full timeline
    length in seconds; ``fps`` is the uniform sampling rate when the capture
    used one, else ``None``.
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


class PixelMetrics(quickthumbModel):
    """Pixel metadata captured at the export boundary.

    Fidelity comparisons add measured diff fields in the later conformance
    work; A1 fixes the JSON shape and canonical raster dimensions.
    """

    mode: Literal["RGBA"] = "RGBA"
    width: PositiveInt | None = None
    height: PositiveInt | None = None
    frame_count: NonNegativeInt = 0


class TimingMetrics(quickthumbModel):
    """Timing metadata captured at the export boundary."""

    duration: float = 0.0
    fps: float | None = None
    frame_count: NonNegativeInt = 0


class FallbackDiagnostic(quickthumbModel):
    """Structured explanation for a capability fallback."""

    code: str = "export_fallback"
    target: str
    layer_id: str | None = None
    reason: str
    native_attempt: bool | None = None
    pixel_diff_ratio: float | None = None
    hash_similarity: float | None = None
    suggestion: str | None = None


class ExportResult(quickthumbModel):
    """Stable, JSON-serializable result returned by ``Document.export()``."""

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
