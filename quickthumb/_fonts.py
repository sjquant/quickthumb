import contextlib
import hashlib
import os
import re
import tempfile
import warnings
from typing import Any, cast
from urllib.parse import quote_plus, urlparse
from urllib.request import Request, urlopen

from PIL import ImageFont

from quickthumb._base import DEFAULT_TEXT_SIZE, is_url
from quickthumb.errors import RenderingError
from quickthumb.font_cache import FontCache
from quickthumb.models import TextLayer


class FontEngine:
    """Font loading with webfont download caching and system font discovery."""

    def __init__(self):
        self._variant_cache: dict[tuple, ImageFont.FreeTypeFont | ImageFont.ImageFont] = {}

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
            layer.font_source,
            layer.font_variations,
        )

    def load_font_variant(
        self,
        font_name: str | None,
        size: int,
        bold: bool | None,
        italic: bool | None,
        weight: int | str | None = None,
        font_source: str = "auto",
        font_variations: dict[str, float] | None = None,
    ) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        normalized_variations = tuple(sorted((font_variations or {}).items()))
        key = (font_name, size, bold, italic, weight, font_source, normalized_variations)
        cached = self._variant_cache.get(key)
        if cached is not None:
            return cached

        font = self._load_font_variant_uncached(
            font_name,
            size,
            bold,
            italic,
            weight,
            font_source,
            dict(normalized_variations),
        )
        self._variant_cache[key] = font
        return font

    def _load_font_variant_uncached(
        self,
        font_name: str | None,
        size: int,
        bold: bool | None,
        italic: bool | None,
        weight: int | str | None,
        font_source: str,
        font_variations: dict[str, float],
    ) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        try:
            if font_name and font_name.lower().startswith("google:"):
                font_source = "google"
                font_name = font_name.split(":", 1)[1].strip()

            if font_name and is_url(font_name):
                if bold or italic or weight:
                    warnings.warn(
                        "Bold/italic/weight flags are ignored for webfont URLs. "
                        "Provide separate font URLs for styled variants.",
                        UserWarning,
                        stacklevel=3,
                    )
                font_path = self._download_and_cache_font(font_name)
                font = ImageFont.truetype(font_path, size)
                return self._apply_font_variations(font, font_variations, weight)

            if font_name and font_source == "google":
                font_path = self._download_and_cache_google_font(
                    font_name, bold or False, italic or False, weight
                )
                font = ImageFont.truetype(font_path, size)
                return self._apply_font_variations(font, font_variations, weight)

            if font_name:
                with contextlib.suppress(OSError):
                    font = ImageFont.truetype(font_name, size)
                    return self._apply_font_variations(font, font_variations, weight)

                font_path = FontCache.get_instance().find_font(
                    font_name, bold or False, italic or False, weight=weight
                )

                if font_path:
                    font = ImageFont.truetype(font_path, size)
                    return self._apply_font_variations(font, font_variations, weight)

            default_font_path = FontCache.get_instance().default_font()

            font = (
                ImageFont.truetype(default_font_path, size)
                if default_font_path
                else ImageFont.load_default(size)
            )
            return self._apply_font_variations(font, font_variations, weight)

        except OSError as e:
            raise RenderingError(f"Could not load font '{font_name}'.") from e

    def _download_and_cache_google_font(
        self,
        family: str,
        bold: bool,
        italic: bool,
        weight: int | str | None,
    ) -> str:
        target_weight = self._normalize_weight(weight, bold)
        family = family.strip()
        if not family:
            raise RenderingError("Google font family cannot be empty.")

        cache_key = f"{family}|{target_weight}|{int(italic)}"
        cache_hash = hashlib.md5(cache_key.encode()).hexdigest()
        cache_dir = self._font_cache_dir()

        cached_font = self._valid_cached_google_font_path(cache_dir, cache_hash)
        if cached_font:
            return cached_font

        css_path = os.path.join(cache_dir, f"quickthumb_google_{cache_hash}.css")
        css = self._read_cached_css(css_path)
        if css is None:
            css = self._fetch_google_font_css(family, target_weight, italic)
            with open(css_path, "w", encoding="utf-8") as f:
                f.write(css)

        font_url = self._select_google_font_url(css)
        if not font_url:
            with contextlib.suppress(OSError):
                os.remove(css_path)
            css = self._fetch_google_font_css(family, target_weight, italic)
            with open(css_path, "w", encoding="utf-8") as f:
                f.write(css)
            font_url = self._select_google_font_url(css)

        if not font_url:
            raise RenderingError(f"Google Fonts did not return a font file for '{family}'.")

        extension = self._font_extension(font_url)
        cache_path = os.path.join(cache_dir, f"quickthumb_google_{cache_hash}{extension}")
        return self._download_font_url_to_cache(font_url, cache_path, f"Google font '{family}'")

    def _fetch_google_font_css(self, family: str, weight: int, italic: bool) -> str:
        family_query = quote_plus(family)
        css_url = (
            "https://fonts.googleapis.com/css2?"
            f"family={family_query}:ital,wght@{int(italic)},{weight}&display=swap"
        )
        try:
            request = Request(css_url, headers={"User-Agent": "quickthumb/1.0"})
            with urlopen(request) as response:
                return response.read().decode("utf-8")
        except Exception as e:
            raise RenderingError(f"Failed to fetch Google font '{family}'.") from e

    def _read_cached_css(self, css_path: str) -> str | None:
        try:
            with open(css_path, encoding="utf-8") as f:
                return f.read()
        except OSError:
            return None

    def _select_google_font_url(self, css: str) -> str | None:
        urls = re.findall(r"url\((https://[^)]+)\)", css)
        if not urls:
            return None
        return next((url for url in urls if ".woff2" in url), urls[0])

    def _valid_cached_google_font_path(self, cache_dir: str, cache_hash: str) -> str | None:
        for extension in (".woff2", ".woff", ".ttf", ".otf"):
            cache_path = os.path.join(cache_dir, f"quickthumb_google_{cache_hash}{extension}")
            if self._is_valid_cached_font(cache_path):
                return cache_path
        return None

    def _download_and_cache_font(self, url: str) -> str:
        url_hash = hashlib.md5(url.encode()).hexdigest()
        extension = self._font_extension(url)
        cache_filename = f"quickthumb_font_{url_hash}{extension}"
        cache_dir = self._font_cache_dir()
        cache_path = os.path.join(cache_dir, cache_filename)

        if self._is_valid_cached_font(cache_path):
            return cache_path
        if os.path.exists(cache_path):
            with contextlib.suppress(OSError):
                os.remove(cache_path)  # stale invalid cache; re-download below.

        return self._download_font_url_to_cache(url, cache_path, f"font from '{url}'")

    def _font_cache_dir(self) -> str:
        cache_dir = os.environ.get("QUICKTHUMB_FONT_CACHE_DIR", tempfile.gettempdir())
        os.makedirs(cache_dir, exist_ok=True)
        return cache_dir

    def _font_extension(self, url: str) -> str:
        extension = os.path.splitext(urlparse(url).path)[1].lower()
        if extension in {".ttf", ".otf", ".woff", ".woff2"}:
            return extension
        return ".ttf"

    def _is_valid_cached_font(self, cache_path: str) -> bool:
        if not os.path.exists(cache_path):
            return False
        with open(cache_path, "rb") as f:
            cached_header = f.read(4)
        return any(cached_header.startswith(magic) for magic in self._VALID_FONT_MAGIC)

    def _download_font_url_to_cache(self, url: str, cache_path: str, description: str) -> str:
        try:
            request = Request(url, headers={"User-Agent": "quickthumb/1.0"})
            with urlopen(request) as response:
                font_data = response.read()
        except Exception as e:
            raise RenderingError(f"Failed to download {description}.") from e

        if not any(font_data.startswith(magic) for magic in self._VALID_FONT_MAGIC):
            raise RenderingError(f"Downloaded content for {description} is not a valid font file.")

        with open(cache_path, "wb") as f:
            f.write(font_data)
        return cache_path

    def _normalize_weight(self, weight: int | str | None, bold: bool) -> int:
        if isinstance(weight, int):
            return weight
        if isinstance(weight, str):
            return FontCache.get_instance()._normalize_weight(weight)
        return 700 if bold else 400

    def _apply_font_variations(
        self,
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        requested_variations: dict[str, float],
        weight: int | str | None,
    ) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        if not isinstance(font, ImageFont.FreeTypeFont):
            return font

        variations = {axis.lower(): value for axis, value in requested_variations.items()}
        if weight is not None and "wght" not in variations:
            variations["wght"] = float(self._normalize_weight(weight, bold=False))
        if not variations:
            return font

        try:
            axes = font.get_variation_axes()
        except (AttributeError, OSError):
            if requested_variations:
                warnings.warn(
                    "font_variations were ignored because the selected font is not variable.",
                    UserWarning,
                    stacklevel=3,
                )
            return font

        if not axes:
            if requested_variations:
                warnings.warn(
                    "font_variations were ignored because the selected font has no variable axes.",
                    UserWarning,
                    stacklevel=3,
                )
            return font

        resolved_values = []
        used_axes: set[str] = set()
        for axis in axes:
            axis_data = cast(Any, axis)
            axis_name = self._variation_axis_name(axis_data)
            axis_tag = self._variation_axis_tag(axis_name)
            default = self._axis_number(
                axis_data, "default", self._axis_number(axis_data, "minimum", 0)
            )
            value = variations.get(axis_tag, default)
            minimum = self._axis_number(axis_data, "minimum", value)
            maximum = self._axis_number(axis_data, "maximum", value)
            value = min(max(float(value), minimum), maximum)
            resolved_values.append(value)
            used_axes.add(axis_tag)

        ignored = sorted(set(variations) - used_axes)
        if ignored and requested_variations:
            warnings.warn(
                "font_variations axes were ignored because the font does not expose them: "
                + ", ".join(ignored),
                UserWarning,
                stacklevel=3,
            )

        try:
            font.set_variation_by_axes(resolved_values)
        except (AttributeError, OSError, ValueError):
            if requested_variations:
                warnings.warn(
                    "font_variations were ignored because Pillow could not apply them.",
                    UserWarning,
                    stacklevel=3,
                )
        return font

    def _variation_axis_name(self, axis: dict) -> str:
        name = axis.get("name", "")
        if isinstance(name, bytes):
            return name.decode("utf-8", errors="ignore").lower()
        return str(name).lower()

    def _axis_number(self, axis: dict, key: str, default: float) -> float:
        value = axis.get(key, default)
        if value is None:
            return default
        return float(value)

    def _variation_axis_tag(self, name: str) -> str:
        if "weight" in name:
            return "wght"
        if "width" in name:
            return "wdth"
        if "slant" in name:
            return "slnt"
        if "italic" in name:
            return "ital"
        if "optical" in name:
            return "opsz"
        return name[:4].ljust(4, "_")
