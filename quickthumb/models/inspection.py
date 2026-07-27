"""Inspection and diagnostic result models."""

# Inspection fields use the shared model vocabulary re-exported by ``common``.
# ruff: noqa: F405

from typing import Any, Literal

from pydantic import (
    Field,
    NonNegativeInt,
    PositiveInt,
)

from .common import *  # noqa: F401,F403
from .options import ExportDiagnostic


class InspectionBBox(quickthumbModel):
    x: int
    y: int
    width: NonNegativeInt
    height: NonNegativeInt


DiagnosticBBox = InspectionBBox


class Diagnostic(quickthumbModel):
    code: Literal[
        "off-canvas",
        "tiny-text",
        "text-overflow",
        "text-clipped",
        "missing-glyph",
        "low-contrast",
        "layer-overlap",
        "near-alignment",
        "layer-hidden",
        "edge-crowding",
    ]
    severity: Literal["warning", "error"]
    layer_index: int
    message: str
    layer_id: str | None = Field(default=None, repr=False)
    layer_name: str | None = Field(default=None, repr=False)
    bbox: DiagnosticBBox | None = Field(default=None, repr=False)
    related_layers: list[str] = Field(default_factory=list, repr=False)
    measured: dict[str, Any] = Field(default_factory=dict, repr=False)
    suggestion: str | None = Field(default=None, repr=False)


class TextInspection(quickthumbModel):
    wrapped_lines: list[str]
    effective_font_size: PositiveInt | None = None
    effective_font_sizes: list[PositiveInt] = []
    max_width: int | str | None = None
    max_height: int | str | None = None
    min_size: PositiveInt = 1
    balance_lines: bool = False
    font_source: FontSource = "auto"
    font_variations: FontVariations = Field(default_factory=dict)
    emoji_style: EmojiStyle = "monochrome"
    auto_scaled: bool = False


class LayerInspection(quickthumbModel):
    id: str
    index: NonNegativeInt
    order: NonNegativeInt
    z_order: NonNegativeInt
    type: str
    name: str | None = None
    visible: bool
    bbox: InspectionBBox | None = None
    text: TextInspection | None = None
    children: list["LayerInspection"] = []


class CanvasInspection(quickthumbModel):
    width: PositiveInt
    height: PositiveInt
    layers: list[LayerInspection]


class MotionKeyframeInspection(quickthumbModel):
    """One normalized keyframe exposed by motion inspection."""

    time: float
    value: Any


class MotionTrackInspection(quickthumbModel):
    """A resolved property track in canonical timeline order."""

    type: str
    keyframes: list[MotionKeyframeInspection]


class MotionEventInspection(quickthumbModel):
    """A resolved timeline event, including its effective timing."""

    source: Literal["effect", "timeline", "legacy", "transition"]
    start: float
    delay: float
    active_start: float
    duration: float
    end: float
    trigger: str | None = None
    effect: str | None = None
    tracks: list[MotionTrackInspection] = Field(default_factory=list)
    stagger: dict[str, Any] | None = None
    progress: list[float] = Field(default_factory=list)


class MotionTargetInspection(quickthumbModel):
    """A deterministic semantic target resolved from a layer."""

    target: str
    index: NonNegativeInt
    source_range: tuple[NonNegativeInt, NonNegativeInt] | None = None
    position: tuple[float, float] | None = None
    size: tuple[float, float] | None = None


class MotionLayerInspection(quickthumbModel):
    """Resolved motion for one stable layer identity."""

    layer_id: str
    layer_type: str
    events: list[MotionEventInspection] = Field(default_factory=list)
    duration: float = 0.0
    targets: list[MotionTargetInspection] = Field(default_factory=list)
    sample_times: list[float] = Field(default_factory=list)
    samples: list[dict[str, Any]] = Field(default_factory=list)
    static_state: dict[str, Any] = Field(default_factory=dict)
    initial_state: dict[str, Any] = Field(default_factory=dict)
    final_state: dict[str, Any] = Field(default_factory=dict)


class MotionCapabilityInspection(quickthumbModel):
    """Capability registry information for one exporter feature."""

    feature: str
    target: str
    support: Literal["full", "native", "partial", "fallback", "unsupported"]
    fallback: Literal["fade", "rasterize", "static"] | None = None


class MotionMatchInspection(quickthumbModel):
    """A deterministic cross-scene identity match."""

    source_id: str
    target_id: str
    motion_key: str
    behavior: Literal["match", "crossfade"] = "match"


class ReducedMotionInspection(quickthumbModel):
    """The effective accessibility policy applied to the inspected result."""

    enabled: bool = False
    mode: Literal["normal", "static"] = "normal"
    original_duration: float = 0.0
    resolved_duration: float = 0.0
    removed_features: list[str] = Field(default_factory=list)


class MotionSlideInspection(quickthumbModel):
    """Motion inspection for one canvas, optionally within a deck."""

    slide_index: NonNegativeInt | None = None
    width: PositiveInt
    height: PositiveInt
    duration: float = 0.0
    layers: list[MotionLayerInspection] = Field(default_factory=list)
    transition: MotionEventInspection | None = None
    matches: list[MotionMatchInspection] = Field(default_factory=list)


class MotionInspection(quickthumbModel):
    """Public, JSON-serializable motion inspection report."""

    version: Literal["1"] = "1"
    width: PositiveInt
    height: PositiveInt
    duration: float = 0.0
    fps: float
    max_samples: PositiveInt = 10_000
    sample_times: list[float] = Field(default_factory=list)
    slides: list[MotionSlideInspection] = Field(default_factory=list)
    capabilities: list[MotionCapabilityInspection] = Field(default_factory=list)
    diagnostics: list[ExportDiagnostic] = Field(default_factory=list)
    reduced_motion: ReducedMotionInspection = Field(default_factory=ReducedMotionInspection)
