"""Layout-connected word and line fragments for the existing motion compositor."""

from __future__ import annotations

import math
import re
import unicodedata
from typing import TYPE_CHECKING

from PIL import Image

from quickthumb.models import TextLayer

if TYPE_CHECKING:
    from quickthumb.canvas import Canvas


def text_target_fragments(
    canvas: Canvas,
    layer: object,
    surface: Image.Image,
    offset: tuple[int, int] = (0, 0),
):
    """Keep separable text targets at their authored, fully laid-out positions.

    Complex styles keep the existing partial route. A candidate layout is used
    only when its nonoverlapping crops reconstruct the actual source pixels.
    """
    from quickthumb._export_base import compute_text_layout
    from quickthumb.motion import _canonical_timeline

    if not isinstance(layer, TextLayer) or not isinstance(layer.content, str):
        return None
    timeline = _canonical_timeline(layer)
    stagger = (
        next((event.stagger for event in timeline.events if event.stagger), None)
        if timeline
        else None
    )
    if stagger is None or stagger["target"] not in {"words", "lines"}:
        return None
    effective = canvas._text.effective_layer(layer)
    content = effective.content
    if not isinstance(content, str):
        return None
    if (
        effective.effects
        or effective.fill
        or effective.rotation
        or effective.letter_spacing
        or effective.value is not None
        or any(unicodedata.bidirectional(char) in {"R", "AL", "AN"} for char in content)
    ):
        return None
    layout = compute_text_layout(canvas, effective)
    boxes = []
    values = []
    for line in layout.lines:
        if not line:
            if stagger["target"] == "lines":
                boxes.append(None)
            continue
        (run,) = line
        if stagger["target"] == "lines":
            boxes.append(run.ink_box)
            continue
        for match in re.finditer(r"\S+", run.text):
            values.append(match.group())
            pen = run.pen_x + run.font.getlength(run.text[: match.start()])
            left, top, right, bottom = run.font.getbbox(match.group(), anchor="ls")
            boxes.append((pen + left, run.baseline_y + top, pen + right, run.baseline_y + bottom))
    if stagger["target"] == "words" and values != re.findall(r"\S+", content):
        # A word split across wrapped lines needs multiple placed runs, rather
        # than changing its semantic target cardinality.
        return None
    fragments = []
    reconstructed = Image.new("RGBA", surface.size)
    for box in boxes:
        if box is None:
            fragments.append((Image.new("RGBA", (1, 1)), (0, 0)))
            continue
        left, top, right, bottom = box
        bounds = (
            math.floor(left) - offset[0],
            math.floor(top) - offset[1],
            math.ceil(right) - offset[0],
            math.ceil(bottom) - offset[1],
        )
        if bounds[2] <= bounds[0] or bounds[3] <= bounds[1]:
            fragments.append((Image.new("RGBA", (1, 1)), (0, 0)))
            continue
        fragment = surface.crop(bounds)
        reconstructed.alpha_composite(fragment, bounds[:2])
        fragments.append((fragment, (bounds[0] + offset[0], bounds[1] + offset[1])))
    if reconstructed.tobytes() != surface.tobytes():
        return None
    if stagger["order"] == "reverse":
        fragments.reverse()
    return tuple(fragments)
