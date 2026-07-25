"""Document-level discriminated unions and schema models."""

# Shared model primitives are intentionally re-exported by ``common``.
# ruff: noqa: F405

from typing import Annotated, Any, Literal

from pydantic import (
    Discriminator,
    Field,
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
)
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
