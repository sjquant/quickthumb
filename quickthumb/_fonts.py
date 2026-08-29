import contextlib
import hashlib
import os
import re
import warnings
from collections.abc import Iterable
from typing import Any, cast
from urllib.parse import quote_plus, urlparse
from urllib.request import urlopen

from PIL import ImageFont

from quickthumb._base import DEFAULT_TEXT_SIZE, is_url
from quickthumb.asset_cache import AssetResolver, ResolvedAsset
from quickthumb.errors import RenderingError
from quickthumb.font_cache import FontCache
from quickthumb.models import TextLayer, VideoLayer


class FontEngine:
    """Font loading with webfont download caching and system font discovery."""

    def __init__(self, asset_resolver: AssetResolver | None = None):
        self._variant_cache: dict[tuple, ImageFont.FreeTypeFont | ImageFont.ImageFont] = {}
        self._asset_resolver = asset_resolver or AssetResolver()

    def resolve_remote_references(self, layers: Iterable[object]) -> None:
        """Resolve all remote font references found in document layers."""
        for (
            font_name,
            font_source,
            bold,
            italic,
            weight,
            font_variations,
        ) in self._remote_font_references(layers):
            self.resolve_remote_font_reference(
                font_name,
                font_source=font_source,
                bold=bold,
                italic=italic,
                weight=weight,
                font_variations=font_variations,
            )

    def resolve_remote_font_reference(
        self,
        font_name: str,
        *,
        font_source: str = "auto",
        bold: bool = False,
        italic: bool = False,
        weight: int | str | None = None,
        font_variations: dict[str, float] | None = None,
    ) -> ResolvedAsset:
        """Resolve a URL or Google font and retain its semantic reference metadata."""
        if font_source == "google":
            asset = self._resolve_google_font_asset(
                font_name,
                bold,
                italic,
                weight,
                font_variations,
            )
        else:
            asset = self._asset_resolver.resolve_font(font_name, fetcher=self._fetch)
        self._remember_reference(font_name, asset)
        return asset

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
        normalized_variations = tuple(
            sorted((axis.lower(), float(value)) for axis, value in (font_variations or {}).items())
        )
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
                requested_variations = {
                    axis.lower(): float(value) for axis, value in font_variations.items()
                }
                font_path = self._download_and_cache_google_font(
                    font_name,
                    bold or False,
                    italic or False,
                    weight,
                    requested_variations,
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
        font_variations: dict[str, float] | None = None,
    ) -> str:
        asset = self._resolve_google_font_asset(
            family,
            bold,
            italic,
            weight,
            font_variations,
        )
        self._remember_reference(family, asset)
        return asset.cache_path or os.path.join(str(self._asset_resolver.cache_dir), family)

    def _resolve_google_font_asset(
        self,
        family: str,
        bold: bool,
        italic: bool,
        weight: int | str | None,
        font_variations: dict[str, float] | None,
    ) -> ResolvedAsset:
        requested_variations = {
            axis.lower(): float(value) for axis, value in (font_variations or {}).items()
        }
        target_weight = self._normalize_weight(weight, bold)
        if "wght" in requested_variations:
            target_weight = min(1000, max(1, int(round(requested_variations["wght"]))))
        family = family.strip()
        if not family:
            raise RenderingError("Google font family cannot be empty.")

        cache_hash = self._google_cache_hash(family, target_weight, italic, requested_variations)
        css = self._fetch_google_font_css(family, target_weight, italic, requested_variations)
        font_url = self._select_google_font_url(css, target_weight, italic)
        if not font_url:
            css = self._fetch_google_font_css(
                family,
                target_weight,
                italic,
                requested_variations,
                force_refresh=True,
            )
            font_url = self._select_google_font_url(css, target_weight, italic)

        if not font_url:
            raise RenderingError(f"Google Fonts did not return a font file for '{family}'.")

        extension = self._font_extension(font_url)
        cache_filename = f"quickthumb_google_{cache_hash}{extension}"
        return self._asset_resolver.resolve_font(
            font_url,
            extension=extension,
            cache_filename=cache_filename,
            fetcher=self._fetch,
        )

    def _fetch_google_font_css(
        self,
        family: str,
        weight: int,
        italic: bool,
        font_variations: dict[str, float] | None = None,
        *,
        force_refresh: bool = False,
    ) -> str:
        requested_variations = {
            axis.lower(): float(value) for axis, value in (font_variations or {}).items()
        }
        css_url = self._google_css_url(family, weight, italic, requested_variations)
        cache_hash = self._google_cache_hash(family, weight, italic, requested_variations)
        cache_filename = f"quickthumb_google_{cache_hash}.css"
        try:
            if force_refresh:
                self._asset_resolver.invalidate(
                    css_url,
                    "font-css",
                    extension=".css",
                    cache_filename=cache_filename,
                )
            asset = self._asset_resolver.resolve(
                css_url,
                "font-css",
                extension=".css",
                cache_filename=cache_filename,
                fetcher=self._fetch,
            )
            return asset.data.decode("utf-8")
        except Exception as e:
            if requested_variations:
                warnings.warn(
                    "Google Fonts could not resolve the requested variation axes; "
                    "falling back to the requested weight/style face.",
                    UserWarning,
                    stacklevel=3,
                )
                return self._fetch_google_font_css(family, weight, italic)
            raise RenderingError(f"Failed to fetch Google font '{family}'.") from e

    def _google_css_url(
        self,
        family: str,
        weight: int,
        italic: bool,
        requested_variations: dict[str, float],
    ) -> str:
        family_query = quote_plus(family)
        axes = set(requested_variations)
        axes.add("wght")
        axes.add("ital")
        axis_tags = sorted(axes)
        axis_values = []
        for axis in axis_tags:
            if axis == "ital":
                axis_values.append(str(int(italic)))
            elif axis == "wght":
                axis_values.append(str(weight))
            else:
                axis_values.append(f"{requested_variations[axis]:g}")
        axis_spec = f"{','.join(axis_tags)}@{','.join(axis_values)}"
        return f"https://fonts.googleapis.com/css2?family={family_query}:{axis_spec}&display=swap"

    @staticmethod
    def _google_cache_hash(
        family: str,
        weight: int,
        italic: bool,
        font_variations: dict[str, float] | None = None,
    ) -> str:
        requested_variations = {
            axis.lower(): float(value) for axis, value in (font_variations or {}).items()
        }
        variation_key = ",".join(
            f"{axis}={value:g}" for axis, value in sorted(requested_variations.items())
        )
        cache_key = f"{family}|{weight}|{int(italic)}"
        if variation_key:
            cache_key += f"|{variation_key}"
        return hashlib.md5(cache_key.encode()).hexdigest()

    def _select_google_font_url(
        self, css: str, target_weight: int = 400, italic: bool = False
    ) -> str | None:
        candidates: list[tuple[int, float, int, int, str]] = []
        blocks = re.findall(r"@font-face\s*\{([^}]*)\}", css, flags=re.IGNORECASE | re.DOTALL)
        for block_index, block in enumerate(blocks):
            urls = re.findall(r"url\(\s*['\"]?(https://[^)'\"]+)['\"]?\s*\)", block)
            if not urls:
                continue

            style_match = re.search(r"font-style\s*:\s*([^;]+)", block, flags=re.IGNORECASE)
            block_italic = style_match is not None and "italic" in style_match.group(1).lower()
            style_penalty = int(block_italic != italic)

            weight_match = re.search(r"font-weight\s*:\s*([^;]+)", block, flags=re.IGNORECASE)
            weight_distance = self._google_weight_distance(
                weight_match.group(1) if weight_match else "400", target_weight
            )
            for url_index, url in enumerate(urls):
                format_penalty = 0 if ".woff2" in url.lower() else 1
                candidates.append(
                    (style_penalty, weight_distance, format_penalty, block_index + url_index, url)
                )

        if candidates:
            return min(candidates)[-1]

        urls = re.findall(r"url\(\s*['\"]?(https://[^)'\"]+)['\"]?\s*\)", css)
        if not urls:
            return None
        return next((url for url in urls if ".woff2" in url.lower()), urls[0])

    def _google_weight_distance(self, declaration: str, target_weight: int) -> float:
        normalized = declaration.strip().lower()
        named_weights = {"normal": 400.0, "bold": 700.0}
        if normalized in named_weights:
            return abs(named_weights[normalized] - target_weight)

        values = [float(value) for value in re.findall(r"\d+(?:\.\d+)?", normalized)]
        if not values:
            return float("inf")
        if len(values) >= 2 and values[0] <= target_weight <= values[1]:
            return 0.0
        return min(abs(value - target_weight) for value in values)

    def _download_and_cache_font(self, url: str) -> str:
        extension = self._font_extension(url)
        try:
            cache_key = self._asset_resolver.cache_key(url)
        except ValueError as error:
            raise RenderingError(f"Invalid remote asset URL '{url}'.") from error
        cache_filename = f"quickthumb_font_{cache_key}{extension}"
        asset = self._asset_resolver.resolve_font(
            url,
            extension=extension,
            cache_filename=cache_filename,
            fetcher=self._fetch,
        )
        return asset.cache_path or cache_filename

    def _remember_reference(self, reference: str, asset: ResolvedAsset) -> None:
        self._asset_resolver.remember_reference(reference, "font", asset)

    def _remote_font_references(self, layers: Iterable[object]):
        for layer in layers:
            if isinstance(layer, VideoLayer):
                for caption in layer.captions:
                    if caption.font and is_url(caption.font):
                        yield (caption.font, "auto", False, False, None, None)
                continue

            if not isinstance(layer, TextLayer):
                continue

            if layer.font and (is_url(layer.font) or layer.font_source == "google"):
                font_source = "auto" if is_url(layer.font) else layer.font_source
                yield (
                    layer.font,
                    font_source,
                    layer.bold,
                    layer.italic,
                    layer.weight,
                    layer.font_variations,
                )

            if not isinstance(layer.content, list):
                continue
            for part in layer.content:
                if not part.font:
                    continue
                font_source = part.font_source or layer.font_source
                if not (is_url(part.font) or font_source == "google"):
                    continue
                yield (
                    part.font,
                    "auto" if is_url(part.font) else font_source,
                    part.bold if part.bold is not None else layer.bold,
                    part.italic if part.italic is not None else layer.italic,
                    part.weight if part.weight is not None else layer.weight,
                    part.font_variations
                    if part.font_variations is not None
                    else layer.font_variations,
                )

    def _font_extension(self, url: str) -> str:
        extension = os.path.splitext(urlparse(url).path)[1].lower()
        if extension in {".ttf", ".otf", ".woff", ".woff2"}:
            return extension
        return ".ttf"

    @staticmethod
    def _fetch(request, timeout: float):
        return urlopen(request, timeout=timeout)

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
