"""Bounded static glyph outlines from the canonical resolved text layout."""

import math
from io import BytesIO
from pathlib import Path
from typing import Any, cast

from PIL import ImageColor, ImageFont
from typing_extensions import override

from quickthumb._export_base import compute_text_layout
from quickthumb._path_svg import _bounded_number
from quickthumb.errors import RenderingError


def text_problem(layer, linked):
    if not isinstance(layer.content, str) or any(not 32 <= ord(c) <= 126 for c in layer.content):
        return "content", "Lottie text requires plain single-line printable ASCII"
    if len(layer.content) > 1024:
        return "content", "Lottie text exceeds 1024 characters; split the text layer"
    if linked:
        return "parent", "Lottie text parenting is not supported"
    if (
        layer.color
        and cast(tuple[int, int, int, int], ImageColor.getcolor(layer.color, "RGBA"))[3] != 255
    ):
        return (
            "color",
            "Lottie text requires opaque solid paint; use layer opacity for translucency",
        )
    for field in (
        "animation",
        "rotation",
        "value",
        "max_width",
        "max_height",
        "auto_scale",
        "font_variations",
    ):
        if getattr(layer, field):
            return field, f"Lottie static outlined text does not support {field}"
    if layer.font_source == "google" or (
        layer.font and layer.font.startswith(("http://", "https://"))
    ):
        return (
            "font",
            "Lottie outlined text requires a resolved local font or Pillow's default face",
        )
    return None


def text_outlines(canvas, layer):
    """Return per-glyph native cubic contours and solid color, with no embedded font resource."""
    if not layer.content:
        return [], (0, 0, 0, 0)
    try:
        from fontTools.pens.basePen import BasePen
        from fontTools.ttLib import TTFont, TTLibError
    except ImportError as error:
        raise RenderingError(
            "Outlined Lottie text requires fonttools; install quickthumb[lottie]",
            path="/font",
        ) from error
    layout = compute_text_layout(canvas, layer)
    run = layout.lines[0][0]
    font = run.font
    if not isinstance(font, ImageFont.FreeTypeFont):
        raise RenderingError("Lottie text requires an outline FreeType font", path="/font")
    if run.char_xs is None:
        if len(run.text) > 1 and font.layout_engine == ImageFont.Layout.RAQM:
            raise RenderingError(
                "Unspaced RAQM text requires shaping; use explicit nonzero letter_spacing",
                path="/letter_spacing",
            )
        positions, advance = [], 0.0
        for index, character in enumerate(run.text):
            if font.getlength(run.text[:index]) != advance:
                raise RenderingError(
                    "Text advances are not additive; use explicit nonzero letter_spacing",
                    path="/letter_spacing",
                )
            positions.append(run.pen_x + advance)
            advance += font.getlength(character)
        if font.getlength(run.text) != advance:
            raise RenderingError(
                "Text advances are not additive; use letter_spacing", path="/letter_spacing"
            )
    else:
        positions = run.char_xs
    data = getattr(font, "font_bytes", None)
    path = getattr(font, "path", None)
    if isinstance(data, bytes):
        source = BytesIO(data)
        size = len(data)
    elif isinstance(path, (str, bytes)):
        source = path
        try:
            size = Path(path.decode() if isinstance(path, bytes) else path).stat().st_size
        except OSError as error:
            raise RenderingError(f"Cannot read resolved font: {error}", path="/font") from error
    else:
        raise RenderingError("Resolved font has no readable outline source", path="/font")
    if size > 64 * 1024 * 1024:
        raise RenderingError("Lottie font exceeds the 64 MiB outline-source budget", path="/font")
    outlined_glyphs = []
    work = 0

    class OutlinePen(BasePen):
        def __init__(self, glyphs, x, scale):
            super().__init__(glyphs)
            self.x, self.scale = x, scale
            self.points, self.incoming, self.outgoing = [], [], []

        def mapped(self, point):
            result = [self.x + point[0] * self.scale, run.baseline_y - point[1] * self.scale]
            if any(not _bounded_number(value, 1) for value in result):
                raise RenderingError(
                    "Lottie glyph exceeds native coordinate precision", path="/font"
                )
            return result

        def append(self, point, incoming=(0, 0)):
            nonlocal work
            work += 1
            if work > 65_536:
                raise RenderingError(
                    "Lottie text exceeds 65536 outline vertices; split the layer", path="/content"
                )
            self.points.append(point)
            self.incoming.append(list(incoming))
            self.outgoing.append([0, 0])

        @override
        def _moveTo(self, pt):
            self.append(self.mapped(pt))

        @override
        def _lineTo(self, pt):
            self.append(self.mapped(pt))

        @override
        def _curveToOne(self, pt1, pt2, pt3):
            first, second, end = map(self.mapped, (pt1, pt2, pt3))
            self.outgoing[-1] = [a - b for a, b in zip(first, self.points[-1], strict=True)]
            self.append(end, [a - b for a, b in zip(second, end, strict=True)])

        @override
        def _closePath(self):
            if len(self.points) > 1 and self.points[-1] == self.points[0]:
                self.incoming[0] = self.incoming.pop()
                self.points.pop()
                self.outgoing.pop()
            if self.points:
                contours.append(
                    {
                        "ty": "sh",
                        "ks": {
                            "a": 0,
                            "k": {
                                "v": self.points,
                                "i": self.incoming,
                                "o": self.outgoing,
                                "c": True,
                            },
                        },
                    }
                )
            self.points, self.incoming, self.outgoing = [], [], []

        @override
        def _endPath(self):
            raise RenderingError(
                "Open glyph outlines are not supported by Lottie text", path="/font"
            )

    try:
        with TTFont(source, fontNumber=getattr(font, "index", 0)) as face:
            if any(table in face for table in ("fvar", "COLR", "CBDT", "sbix", "SVG ")):
                raise RenderingError(
                    "Lottie text requires a static monochrome outline font", path="/font"
                )
            glyphs, cmap = face.getGlyphSet(), face.getBestCmap() or {}
            scale = font.size / cast(Any, face["head"]).unitsPerEm
            if not math.isfinite(scale) or scale <= 0:
                raise RenderingError("Lottie font has invalid units per em", path="/font")
            for character, x in zip(run.text, positions, strict=True):
                name = cmap.get(ord(character))
                if name is None:
                    raise RenderingError(
                        f"Resolved font has no glyph for {character!r}", path="/content"
                    )
                contours = []
                glyphs[name].draw(OutlinePen(glyphs, x, scale))
                if contours:
                    outlined_glyphs.append(contours)
    except (TTLibError, OSError, KeyError, ValueError, RecursionError) as error:
        raise RenderingError(
            f"Cannot read resolved font outlines: {error}", path="/font"
        ) from error
    return outlined_glyphs, run.color
