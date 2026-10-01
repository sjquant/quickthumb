"""Scene-local explicit transform-parent graph validation.

Group layout is separate from transform parenting. Only top-level animatable
layers can participate; retaining this boundary prevents ambiguous double layout.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from quickthumb.errors import RenderingError, ValidationError
from quickthumb.models.common import _AnimatableLayerModel

if TYPE_CHECKING:
    from quickthumb.canvas import Canvas


def validate_parent_graph(layers: Sequence[object]) -> None:
    """Reject duplicate identities, missing/non-transform parents and cycles.

    Complete scenes allow forward references. Fluent builders validate on append,
    so their parents must already exist. Cycle detection is iterative and linear
    in the graph size, including chains longer than Python's recursion limit.
    """
    identities: dict[str, tuple[object, str, bool]] = {}
    linked: list[tuple[object, str, bool]] = []
    pending = [(layer, f"/layers/{index}", True) for index, layer in enumerate(layers)]
    while pending:
        layer, pointer, top_level = pending.pop()
        layer_id = getattr(layer, "id", None)
        if layer_id is not None:
            if layer_id in identities:
                raise ValidationError(f"duplicate layer id: {layer_id}")
            identities[layer_id] = layer, pointer, top_level
        if getattr(layer, "parent", None) is not None:
            linked.append((layer, pointer, top_level))
        pending.extend(
            (child, f"{pointer}/children/{index}", False)
            for index, child in enumerate(getattr(layer, "children", ()))
        )

    if not linked:
        return

    for layer, pointer, top_level in linked:
        parent = getattr(layer, "parent", None)
        assert isinstance(parent, str)
        target = identities.get(parent)
        message = None
        code = "invalid_parent"
        if not top_level:
            message = "parent links are not supported on auto-layout group descendants"
        elif target is None:
            message = f"parent layer '{parent}' does not exist in this scene"
            code = "missing_parent"
        elif not target[2]:
            message = f"parent layer '{parent}' is an auto-layout group descendant"
        elif not isinstance(target[0], _AnimatableLayerModel):
            message = f"parent layer '{parent}' must be an animatable layer"
        if message is not None:
            raise ValidationError(
                message, code=code, path=pointer + "/parent", layer_id=getattr(layer, "id", None)
            )

    complete: set[str] = set()
    for layer_id in identities:
        path: list[str] = []
        active: set[str] = set()
        current = layer_id
        while current is not None and current not in complete:
            if current in active:
                layer, pointer, _ = identities[current]
                cycle = " -> ".join([*path[path.index(current) :], current])
                raise ValidationError(
                    f"parent cycle: {cycle}",
                    code="parent_cycle",
                    path=pointer + "/parent",
                    layer_id=current,
                )
            path.append(current)
            active.add(current)
            current = getattr(identities[current][0], "parent", None)
        complete.update(path)


def has_parent_links(canvas: Canvas) -> bool:
    return any(getattr(layer, "parent", None) is not None for layer in canvas._iter_layers_deep())


def require_parent_rendering(canvas: Canvas) -> None:
    """Reject document/layout paths until their graph-aware adapter is available."""
    # The unlinked path remains unchanged, including its grouping and pixels.
    if not has_parent_links(canvas):
        return
    validate_parent_graph(canvas.layers)
    raise RenderingError(
        "Parent-linked rendering is available for raster/video only; document-format "
        "and world-layout adapters do not yet support parent transforms.",
        code="unsupported_parent_rendering",
    )
