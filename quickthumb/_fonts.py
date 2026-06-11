import contextlib
import hashlib
import os
import tempfile
import warnings
from urllib.request import urlopen

from PIL import ImageFont

from quickthumb._base import DEFAULT_TEXT_SIZE, is_url
from quickthumb.errors import RenderingError
from quickthumb.font_cache import FontCache
from quickthumb.models import TextLayer


class FontEngine:
    """Font loading with webfont download caching and system font discovery."""

    _VALID_FONT_MAGIC = (
        b"\x00\x01\x00\x00",  # TrueType
        b"true",  # TrueType (macOS)
        b"OTTO",  # OpenType/CFF
        b"ttcf",  # TrueType Collection
        b"wOFF",  # WOFF
        b"wOF2",  # WOFF2
    )

    def load_font(self, layer: TextLayer) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        return self.load_font_variant(
            layer.font,
            layer.size or DEFAULT_TEXT_SIZE,
            layer.bold,
            layer.italic,
            layer.weight,
        )

    def load_font_variant(
        self,
        font_name: str | None,
        size: int,
        bold: bool | None,
        italic: bool | None,
        weight: int | str | None = None,
    ) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        try:
            if font_name and is_url(font_name):
                if bold or italic or weight:
                    warnings.warn(
                        "Bold/italic/weight flags are ignored for webfont URLs. "
                        "Provide separate font URLs for styled variants.",
                        UserWarning,
                        stacklevel=3,
                    )
                font_path = self._download_and_cache_font(font_name)
                return ImageFont.truetype(font_path, size)

            if font_name:
                with contextlib.suppress(OSError):
                    return ImageFont.truetype(font_name, size)

                font_path = FontCache.get_instance().find_font(
                    font_name, bold or False, italic or False, weight=weight
                )

                if font_path:
                    return ImageFont.truetype(font_path, size)

            default_font_path = FontCache.get_instance().default_font()

            return (
                ImageFont.truetype(default_font_path, size)
                if default_font_path
                else ImageFont.load_default(size)
            )

        except OSError as e:
            raise RenderingError(f"Could not load font '{font_name}'.") from e

    def _download_and_cache_font(self, url: str) -> str:
        url_hash = hashlib.md5(url.encode()).hexdigest()
        extension = os.path.splitext(url)[1] or ".ttf"
        cache_filename = f"quickthumb_font_{url_hash}{extension}"
        cache_dir = os.environ.get("QUICKTHUMB_FONT_CACHE_DIR", tempfile.gettempdir())
        os.makedirs(cache_dir, exist_ok=True)
        cache_path = os.path.join(cache_dir, cache_filename)

        if os.path.exists(cache_path):
            with open(cache_path, "rb") as f:
                cached_header = f.read(4)
            if any(cached_header.startswith(magic) for magic in self._VALID_FONT_MAGIC):
                return cache_path
            try:
                os.remove(cache_path)  # stale invalid cache — re-download
            except OSError:
                pass  # non-fatal: proceed to re-download; write will overwrite or fail cleanly

        try:
            with urlopen(url) as response:
                font_data = response.read()
        except Exception as e:
            raise RenderingError(f"Failed to download font from '{url}'.") from e

        if not any(font_data.startswith(magic) for magic in self._VALID_FONT_MAGIC):
            raise RenderingError(f"Downloaded content from '{url}' is not a valid font file.")

        with open(cache_path, "wb") as f:
            f.write(font_data)
        return cache_path
