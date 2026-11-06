"""Discover declared layer inputs without resolving or caching their bytes."""

import os
from collections.abc import Iterator
from dataclasses import dataclass
from typing import ClassVar

from quickthumb._base import is_url
from quickthumb.errors import json_pointer
from quickthumb.models import (
    BackgroundLayer,
    ImageLayer,
    PluginLayer,
    SvgLayer,
    TextFillImage,
    TextLayer,
    VideoLayer,
)


@dataclass(frozen=True)
class FileReference:
    asset_type: str
    source: str
    path: str


@dataclass(frozen=True)
class FontReference:
    source: str
    path: str
    font_source: str = "auto"
    bold: bool = False
    italic: bool = False
    weight: int | str | None = None
    font_variations: dict[str, float] | None = None
    asset_type: ClassVar[str] = "font"

    @property
    def is_remote(self) -> bool:
        return bool(self.source) and (is_url(self.source) or self.font_source == "google")

    @property
    def is_asset(self) -> bool:
        # System family names are not missing file dependencies. Google names
        # are semantic remote references even when they do not look like URLs.
        return is_url(self.source) or self.font_source == "google" or os.path.isfile(self.source)


def layer_dependencies(layer: object) -> Iterator[FileReference | FontReference]:
    """Yield known input fields in manifest order, with layer-relative pointers.

    Group traversal belongs to the document. Plugin params, custom callbacks,
    text content and other arbitrary strings never declare dependencies here.
    """
    if isinstance(layer, BackgroundLayer):
        if layer.image:
            yield FileReference("image", layer.image, "/image")
    elif isinstance(layer, ImageLayer):
        yield FileReference("image", layer.path, "/path")
    elif isinstance(layer, SvgLayer):
        yield FileReference("svg", layer.path, "/path")
    elif isinstance(layer, VideoLayer):
        yield FileReference("video", layer.source, "/source")
        for index, caption in enumerate(layer.captions):
            if caption.font is not None:
                yield FontReference(caption.font, f"/captions/{index}/font")
    elif isinstance(layer, PluginLayer):
        for name, source in layer.assets.items():
            yield FileReference("plugin", source, json_pointer("assets", name))
    elif isinstance(layer, TextLayer):
        if layer.font is not None:
            yield FontReference(
                layer.font,
                "/font",
                "auto" if is_url(layer.font) else layer.font_source,
                layer.bold,
                layer.italic,
                layer.weight,
                layer.font_variations,
            )
        if isinstance(layer.fill, TextFillImage):
            yield FileReference("text-fill", layer.fill.path, "/fill/path")
        if isinstance(layer.content, list):
            for index, part in enumerate(layer.content):
                if isinstance(part.fill, TextFillImage):
                    yield FileReference("text-fill", part.fill.path, f"/content/{index}/fill/path")
                if part.font is not None:
                    yield FontReference(
                        part.font,
                        f"/content/{index}/font",
                        "auto" if is_url(part.font) else (part.font_source or layer.font_source),
                        part.bold if part.bold is not None else layer.bold,
                        part.italic if part.italic is not None else layer.italic,
                        part.weight if part.weight is not None else layer.weight,
                        part.font_variations
                        if part.font_variations is not None
                        else layer.font_variations,
                    )
