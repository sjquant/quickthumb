"""HTML document exporter.

Produces a standalone HTML page with the canvas embedded as inline SVG, so the
output stays selectable and editable in the browser. Fonts are embedded by
default to keep the document self-contained, like a rendered image file.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from xml.sax.saxutils import escape

from quickthumb._export_svg import SvgExporter

if TYPE_CHECKING:
    from quickthumb.canvas import Canvas

_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
body {{ margin: 0; min-height: 100vh; display: grid; place-items: center; background: #1a1a1a; }}
svg {{ max-width: 100%; height: auto; display: block; }}
</style>
</head>
<body>
{svg}
</body>
</html>
"""


def render_html(canvas: Canvas, embed_fonts: bool = True, title: str = "quickthumb") -> str:
    svg = SvgExporter(canvas, embed_fonts=embed_fonts).export()
    return _HTML_TEMPLATE.format(title=escape(title), svg=svg)
