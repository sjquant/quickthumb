"""Layout-connected, independently owned text fragments for the motion compositor."""

from __future__ import annotations

import math
import re
import unicodedata
from typing import TYPE_CHECKING

from PIL import Image, ImageChops, ImageDraw

from quickthumb.errors import RenderingError
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

    A candidate layout is used only when its nonoverlapping crops reconstruct
    the source pixels. Callers decide whether other layouts allow a partial route.
    """
    from quickthumb._export_base import compute_text_layout
    from quickthumb.motion import _canonical_timeline, _text_selector

    if not isinstance(layer, TextLayer):
        return None
    timeline = _canonical_timeline(layer)
    stagger = (
        next((event.stagger for event in timeline.events if event.stagger), None)
        if timeline
        else None
    )
    selector = _text_selector(layer)
    target = selector.target if selector else stagger["target"] if stagger else None
    if target not in {"characters", "words", "lines"}:
        return None
    effective = canvas._text.effective_layer(layer)
    content = effective.content
    if not isinstance(content, str):
        if target == "characters":
            raise RenderingError("Character targets require plain text, not rich text")
        return None
    if (
        effective.effects
        or effective.fill
        or effective.rotation
        or effective.letter_spacing
        or effective.value is not None
        or any(unicodedata.bidirectional(char) in {"R", "AL", "AN"} for char in content)
    ):
        if target == "characters":
            raise RenderingError(
                "Character targets require plain, unrotated text without effects, fills, "
                "letter spacing, animated values or bidirectional shaping"
            )
        return None
    layout = compute_text_layout(canvas, effective)
    if target == "characters":
        staggers = [event.stagger for event in timeline.events if event.stagger] if timeline else []
        if (
            any(item["target"] != "characters" for item in staggers)
            or len({item["order"] for item in staggers}) > 1
        ):
            raise RenderingError("Character targets require one consistent target basis and order")
        fragments = _character_fragments(canvas, effective, layout, surface, offset)
        return (
            tuple(reversed(fragments)) if stagger and stagger["order"] == "reverse" else fragments
        )
    boxes = []
    values = []
    for line in layout.lines:
        if not line:
            if target == "lines":
                boxes.append(None)
            continue
        (run,) = line
        if target == "lines":
            boxes.append(run.ink_box)
            continue
        for match in re.finditer(r"\S+", run.text):
            values.append(match.group())
            pen = run.pen_x + run.font.getlength(run.text[: match.start()])
            left, top, right, bottom = run.font.getbbox(match.group(), anchor="ls")
            boxes.append((pen + left, run.baseline_y + top, pen + right, run.baseline_y + bottom))
    if target == "words" and values != re.findall(r"\S+", content):
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
    if stagger and stagger["order"] == "reverse":
        fragments.reverse()
    return tuple(fragments)


def _character_fragments(canvas, layer, layout, surface, offset):
    """Prove source-codepoint ownership with independent glyphs, never rectangular bands."""
    content = layer.content
    if any(unicodedata.category(char).startswith(("M", "C")) and char != "\n" for char in content):
        raise RenderingError(
            "Character targets cannot separate combining marks or control/format joined sequences; "
            "use word or line targets"
        )
    # Opaque paint proves ownership even when authored paint is transparent.
    reference = Image.new("RGBA", (canvas.width, canvas.height))
    canvas._render_layer(
        reference, layer.model_copy(update={"animation": None, "color": "#FFFFFF", "opacity": 1})
    )
    reconstructed = Image.new("RGBA", reference.size)
    occupied = Image.new("1", reference.size)
    fragments = [(Image.new("RGBA", (1, 1)), (0, 0)) for _ in content]
    cursor = 0
    for line in layout.lines:
        for run in line:
            start = content.find(run.text, cursor)
            if start < 0 or any(not char.isspace() for char in content[cursor:start]):
                raise RenderingError(
                    "Character targets cannot map wrapped text back to source codepoints; "
                    "use word or line targets"
                )
            for index, char in enumerate(run.text):
                # Include kerning with this character when the font provides it.
                pen = (
                    run.pen_x + run.font.getlength(run.text[: index + 1]) - run.font.getlength(char)
                )
                left, top, right, bottom = run.font.getbbox(char, anchor="ls")
                bounds = (
                    math.floor(pen + left),
                    math.floor(run.baseline_y + top),
                    math.ceil(pen + right),
                    math.ceil(run.baseline_y + bottom),
                )
                if bounds[2] <= bounds[0] or bounds[3] <= bounds[1]:
                    continue
                glyph = Image.new("RGBA", (bounds[2] - bounds[0], bounds[3] - bounds[1]))
                ImageDraw.Draw(glyph).text(
                    (pen - bounds[0], run.baseline_y - bounds[1]),
                    char,
                    font=run.font,
                    fill="#FFFFFF",
                    anchor="ls",
                )
                ink_bounds = glyph.getbbox()
                if ink_bounds is None:
                    continue
                glyph = glyph.crop(ink_bounds)
                x, y = bounds[0] + ink_bounds[0], bounds[1] + ink_bounds[1]
                bounds = (x, y, x + glyph.width, y + glyph.height)
                if x < 0 or y < 0 or bounds[2] > canvas.width or bounds[3] > canvas.height:
                    raise RenderingError(
                        "Character targets require glyph ink inside the canvas; "
                        "move the text inward"
                    )
                ink = glyph.getchannel("A").point(lambda value: 255 if value else 0, "1")
                previous = occupied.crop(bounds)
                if ImageChops.logical_and(previous, ink).getbbox() is not None:
                    raise RenderingError(
                        "Character targets have overlapping glyph ink; use word or line targets"
                    )
                # Color motion crops the full recolored source into these rectangles.
                # Require every rectangle to contain only its independently rendered glyph.
                if reference.crop(bounds).tobytes() != glyph.tobytes():
                    raise RenderingError(
                        "Character targets cannot isolate glyph paint in this font/layout; "
                        "use word or line targets"
                    )
                occupied.paste(ImageChops.logical_or(previous, ink), (x, y))
                reconstructed.alpha_composite(glyph, (x, y))
                fragment = surface.crop(
                    (x - offset[0], y - offset[1], bounds[2] - offset[0], bounds[3] - offset[1])
                )
                fragments[start + index] = (fragment, (x, y))
            cursor = start + len(run.text)
    if any(not char.isspace() for char in content[cursor:]):
        raise RenderingError(
            "Character targets cannot map all source codepoints to the text layout"
        )
    if reconstructed.tobytes() != reference.tobytes():
        raise RenderingError(
            "Character targets cannot reconstruct this font's shaping exactly; "
            "use word or line targets"
        )
    return tuple(fragments)
