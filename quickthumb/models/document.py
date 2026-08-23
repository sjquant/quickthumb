"""Document-level discriminated unions and stable result models."""

# Shared model primitives are intentionally re-exported by ``common``.
# ruff: noqa: F405

import base64 as _base64
import json as _json
from typing import Annotated, Any, Literal

from pydantic import (
    ConfigDict,
    Discriminator,
    Field,
    NonNegativeInt,
    PositiveInt,
)

from .common import *  # noqa: F401,F403
from .layers import (
    BackgroundLayer,
    GroupLayer,
    ImageLayer,
    OutlineLayer,
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


class DiagnosticReport(list[Any]):
    """List-compatible diagnostic envelope shared by Canvas and Deck."""

    version = "1"

    @property
    def findings(self) -> list[Any]:
        return list(self)

    def model_dump(self, *, mode: str = "python", exclude_none: bool = False) -> dict:
        return {
            "version": self.version,
            "findings": [_diagnostic_payload(item, mode) for item in self],
        }

    def model_dump_json(self, *, exclude_none: bool = False) -> str:
        return _json.dumps(self.model_dump(mode="json", exclude_none=exclude_none))


class AssetManifestEntry(quickthumbModel):
    """A deterministic description of one document asset reference."""

    source: str
    asset_type: str = "asset"
    status: str
    content_hash: str | None = None


class ResolvedDocument(quickthumbModel):
    """Asset-resolution metadata returned without exposing renderer internals."""

    model_config = ConfigDict(extra="forbid")

    version: Literal["1"] = "1"
    kind: Literal["canvas", "deck"]
    asset_manifest: list[AssetManifestEntry] = Field(default_factory=list)


class CanonicalFrame(quickthumbModel):
    """A JSON-safe canonical RGBA raster frame."""

    model_config = ConfigDict(extra="forbid")

    version: Literal["1"] = "1"
    time: float = 0.0
    width: PositiveInt
    height: PositiveInt
    mode: Literal["RGBA"] = "RGBA"
    data: str

    @classmethod
    def from_image(cls, image, *, time: float = 0.0) -> "CanonicalFrame":
        """Encode a PIL image as the canonical RGBA payload."""
        rgba = image.convert("RGBA")
        return cls(
            time=time,
            width=rgba.width,
            height=rgba.height,
            data=_base64.b64encode(_rgba_bytes(rgba)).decode("ascii"),
        )

    def to_bytes(self) -> bytes:
        """Decode the frame's raw RGBA bytes."""
        return _base64.b64decode(self.data)

    def to_image(self):
        """Decode the frame as a PIL image for convenience callers."""
        from PIL import Image

        return Image.frombytes(self.mode, (self.width, self.height), self.to_bytes())


class FrameSequence(quickthumbModel):
    """A JSON-safe ordered sequence of canonical frames."""

    model_config = ConfigDict(extra="forbid")

    version: Literal["1"] = "1"
    fps: float | None = None
    duration: float = 0.0
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
    written_paths: list[str] = Field(default_factory=list)
    capability_report: list[ExportDiagnostic] = Field(default_factory=list)
    fallback_diagnostics: list[FallbackDiagnostic] = Field(default_factory=list)
    pixel_metrics: PixelMetrics = Field(default_factory=PixelMetrics)
    timing_metrics: TimingMetrics = Field(default_factory=TimingMetrics)
    asset_manifest: list[AssetManifestEntry] = Field(default_factory=list)


def _rgba_bytes(image) -> bytes:
    """Return raw bytes without leaking a PIL object into public models."""
    return image.tobytes()


def _diagnostic_payload(item: Any, mode: str) -> Any:
    model_dump = getattr(item, "model_dump", None)
    if callable(model_dump):
        return model_dump(mode=mode, exclude_none=True)
    return item
