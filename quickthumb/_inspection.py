from typing import TYPE_CHECKING

from quickthumb._measurements import BBox, LayerMeasurement, measure_layers
from quickthumb.models import CanvasInspection, InspectionBBox, LayerInspection, TextInspection

if TYPE_CHECKING:
    from quickthumb.canvas import Canvas


def inspect_canvas(canvas: "Canvas") -> CanvasInspection:
    """Build a deterministic layout inspection report from measured layers."""
    canvas._validate_image_paths()
    canvas._ctx.begin_render_pass()
    return CanvasInspection(
        width=canvas.width,
        height=canvas.height,
        layers=[
            _inspect_layer(measured)
            for measured in measure_layers(canvas, include_text_layout=True)
        ],
    )


def _inspect_layer(measured: LayerMeasurement) -> LayerInspection:
    return LayerInspection(
        id=measured.layer_id,
        index=measured.index,
        order=measured.order,
        z_order=measured.z_order,
        type=_layer_type(measured),
        name=measured.name,
        visible=measured.visible,
        bbox=_inspect_bbox(measured.bbox),
        text=_inspect_text(measured),
        children=[_inspect_layer(child) for child in measured.children],
    )


def _layer_type(measured: LayerMeasurement) -> str:
    raw_type = getattr(measured.raw_layer, "type", None)
    if raw_type:
        return str(raw_type)
    if measured.raw_layer.__class__.__name__ == "CustomLayer":
        return "custom"
    return measured.layer_type


def _inspect_bbox(box: BBox | None) -> InspectionBBox | None:
    if box is None:
        return None
    return InspectionBBox(x=box.x, y=box.y, width=box.width, height=box.height)


def _inspect_text(measured: LayerMeasurement) -> TextInspection | None:
    if measured.layer_type != "text":
        return None
    metadata = measured.metadata
    return TextInspection(
        wrapped_lines=list(metadata["wrapped_lines"]),
        effective_font_size=metadata["effective_font_size"],
        effective_font_sizes=list(metadata["effective_font_sizes"]),
        max_width=metadata.get("max_width"),
        auto_scaled=bool(metadata.get("auto_scaled", False)),
    )
