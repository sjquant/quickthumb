"""Data-driven visualization and QR-code models."""

# Visualization fields use the shared model vocabulary re-exported by ``common``.
# ruff: noqa: F405

import math
from collections.abc import Sequence
from typing import Annotated, Any, Literal

from pydantic import (
    ConfigDict,
    Discriminator,
    Field,
    NonNegativeInt,
    PositiveInt,
    field_serializer,
    field_validator,
)

from .common import *  # noqa: F401,F403
from .motion import AnimationInput


class ChartData(quickthumbModel):
    """Validated numeric samples shared by the chart layer models."""

    values: list[float] = Field(default_factory=list)

    @field_validator("values", mode="before")
    @classmethod
    def validate_values(cls, value: Any) -> list[float]:
        if not isinstance(value, (list, tuple)):
            raise ValueError("chart values must be a list of numbers")

        normalized: list[float] = []
        for item in value:
            if isinstance(item, bool) or not isinstance(item, (int, float)):
                raise ValueError("chart values must contain only numbers")
            try:
                number = float(item)
            except (OverflowError, ValueError):
                raise ValueError("chart values must contain only finite numbers") from None
            if not math.isfinite(number):
                raise ValueError("chart values must be finite numbers")
            normalized.append(number)
        return normalized


class VisualizationLayerBase(quickthumbModel):
    """Common positioning and composition contract for visualization layers."""

    position: Position = (0, 0)
    align: AlignWithHVTuple = Align.TOP_LEFT
    opacity: OpacityField = 1.0
    clip: LayerClip | None = None
    mask: LayerMask | None = None
    animation: AnimationInput | None = None

    @field_serializer("align")
    def serialize_align(self, align: Align | None) -> str | None:
        if align is None:
            return None
        return align.value


class BarChartStyle(quickthumbModel):
    """Deterministic paint and geometry options for bar charts."""

    model_config = ConfigDict(extra="forbid")

    color: HexColor = "#2563EB"
    negative_color: HexColor | None = None
    bar_gap: Annotated[float, Field(ge=0.0, lt=1.0)] = 0.2
    padding: NonNegativeInt = 0
    opacity: OpacityField = 1.0


class LineChartStyle(quickthumbModel):
    """Deterministic paint and geometry options for line charts."""

    model_config = ConfigDict(extra="forbid")

    color: HexColor = "#2563EB"
    fill: HexColor | None = None
    fill_opacity: OpacityField = 0.16
    stroke_width: PositiveInt = 2
    point_radius: NonNegativeInt = 2
    show_points: bool = True
    padding: NonNegativeInt = 0
    opacity: OpacityField = 1.0


class _ChartSpecBase(quickthumbModel):
    """Shared data normalization and serialization for chart specifications."""

    data: ChartData | Sequence[int | float]

    @field_validator(
        "data",
        mode="before",
        json_schema_input_type=list[float] | ChartData,
    )
    @classmethod
    def validate_data(cls, value: Any) -> ChartData:
        return value if isinstance(value, ChartData) else ChartData(values=value)

    @field_serializer("data")
    def serialize_data(self, data: ChartData) -> list[float]:
        return data.values


class BarChartSpec(_ChartSpecBase):
    """Validated bar chart data and bar-specific options."""

    type: Literal["bar"] = "bar"
    style: BarChartStyle = Field(default_factory=BarChartStyle)


class LineChartSpec(_ChartSpecBase):
    """Validated line chart data and line-specific options."""

    type: Literal["line"] = "line"
    style: LineChartStyle = Field(default_factory=LineChartStyle)


ChartSpec = Annotated[BarChartSpec | LineChartSpec, Discriminator("type")]


class ChartLayer(VisualizationLayerBase):
    """A deterministic data visualization layer selected by its spec."""

    type: Literal["chart"] = "chart"
    width: PositiveInt
    height: PositiveInt
    spec: ChartSpec


class QRCodeLayer(VisualizationLayerBase):
    """A deterministic QR code rendered into a square canvas region."""

    type: Literal["qr_code"] = "qr_code"
    data: str = Field(min_length=1)
    size: PositiveInt
    foreground: HexColor = "#000000"
    background: HexColor | None = "#FFFFFF"
    error_correction: Literal["L", "M", "Q", "H"] = "M"
    quiet_zone: NonNegativeInt = 4
