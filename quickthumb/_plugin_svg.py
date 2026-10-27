"""A local SVG observation for trusted plugins, never a remote resource loader."""

import base64
import xml.etree.ElementTree as ET
from io import BytesIO

from PIL import Image

from quickthumb._svg_fidelity import compare_pixels
from quickthumb.errors import RenderingError


def validate_plugin_svg(document: str) -> None:
    """Require static SVG with internal references; retain data-image ID isolation."""
    import tinycss2

    if not isinstance(document, str) or any(
        token in document.lower() for token in ("<!doctype", "<!entity", "<?xml-stylesheet")
    ):
        raise RenderingError("Plugin SVG must be a self-contained static SVG document")
    root = ET.fromstring(document)
    if root.tag != "{http://www.w3.org/2000/svg}svg":
        raise RenderingError("Plugin SVG must have an SVG namespace root")

    def check_css(tokens):
        tokens = [token for token in tokens if token.type not in {"whitespace", "comment"}]
        for index, token in enumerate(tokens):
            if token.type == "at-keyword" and (
                token.value.lower() == "import" or token.value.lower().endswith("keyframes")
            ):
                raise RenderingError("Plugin SVG cannot import stylesheets or animate")
            if (
                token.type == "ident"
                and token.value.lower().startswith(("animation", "transition"))
                and index + 1 < len(tokens)
                and tokens[index + 1].type == "literal"
                and tokens[index + 1].value == ":"
            ):
                raise RenderingError("Plugin SVG CSS must remain static")
            if token.type == "url" and not token.value.startswith("#"):
                raise RenderingError("Plugin SVG URLs must be internal references")
            if token.type == "function":
                if token.lower_name == "url" and not tinycss2.serialize(token.arguments).strip(
                    " \t\n\r\"'"
                ).startswith("#"):
                    raise RenderingError("Plugin SVG URLs must be internal references")
                check_css(token.arguments)
            elif hasattr(token, "content"):
                check_css(token.content)

    for node in root.iter():
        name = node.tag.rsplit("}", 1)[-1]
        if name.startswith("animate") or name in {"script", "foreignObject", "set", "discard"}:
            raise RenderingError("Plugin SVG must be static and cannot contain active content")
        for key, value in node.attrib.items():
            attribute = key.rsplit("}", 1)[-1]
            if attribute.lower().startswith("on") or (
                attribute in {"href", "src", "base"} and not value.startswith("#")
            ):
                raise RenderingError("Plugin SVG references must remain internal")
            check_css(tinycss2.parse_component_value_list(value))
        if name == "style":
            check_css(tinycss2.parse_component_value_list(node.text or ""))


def observe_plugin_svg(expected: Image.Image, document: str, limits) -> dict:
    from cairosvg.surface import PNGSurface

    def deny_fetch(url, resource_type):
        prefix = "data:image/svg+xml;base64,"
        if url.startswith(prefix):
            return base64.b64decode(url[len(prefix) :], validate=True)
        raise RenderingError("Plugin SVG cannot fetch external resources")

    encoded = PNGSurface.convert(bytestring=document.encode(), url_fetcher=deny_fetch)
    with Image.open(BytesIO(encoded)) as image:
        return compare_pixels(expected, image.convert("RGBA"), limits)
