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
