"""Deterministic resolution and caching for remote document assets.

Resolution statuses are documented on
:class:`quickthumb.models.AssetManifestEntry`.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Literal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from PIL import Image

from quickthumb.errors import RenderingError

_DEFAULT_TIMEOUT = 15
_DEFAULT_MAX_BYTES = 64 * 1024 * 1024
_CACHE_DIR_ENV = "QUICKTHUMB_ASSET_CACHE_DIR"
_MAX_AGE_ENV = "QUICKTHUMB_ASSET_MAX_AGE"
_OFFLINE_ENV = "QUICKTHUMB_ASSET_OFFLINE"
_OFFLINE_VALUES = {
    "": False,
    "0": False,
    "false": False,
    "no": False,
    "off": False,
    "1": True,
    "true": True,
    "yes": True,
    "on": True,
}
ResolvedStatus = Literal["local", "network", "fresh", "stale"]
_CACHE_LOCK_GUARD = Lock()
_CACHE_LOCKS: dict[str, Lock] = {}
_FONT_MAGIC = (
    b"\x00\x01\x00\x00",
    b"true",
    b"OTTO",
    b"ttcf",
    b"wOFF",
    b"wOF2",
)


@dataclass(frozen=True)
class ResolvedAsset:
    """Bytes and deterministic metadata for one resolved asset reference."""

    source: str
    asset_type: str
    source_key: str
    cache_key: str | None
    cache_path: str | None
    content_hash: str
    status: ResolvedStatus
    data: bytes = field(repr=False)
    fetched_at: float | None = None
    stale_reason: str | None = None


class AssetResolver:
    """Resolve local or remote bytes through one deterministic cache boundary.

    ``max_age`` (seconds, default: no expiry) marks older cache entries stale so
    they are refreshed from the network; if the refresh fails, the stale entry
    is used and reported with ``status="stale"``. ``offline=True`` never makes
    network requests. Both default to the ``QUICKTHUMB_ASSET_MAX_AGE`` and
    ``QUICKTHUMB_ASSET_OFFLINE`` environment variables.
    """

    def __init__(
        self,
        cache_dir: str | os.PathLike[str] | None = None,
        *,
        timeout: float = _DEFAULT_TIMEOUT,
        max_bytes: int = _DEFAULT_MAX_BYTES,
        max_age: float | None = None,
        offline: bool | None = None,
        fetcher: Callable[..., object] | None = None,
    ) -> None:
        if not isinstance(max_bytes, int) or isinstance(max_bytes, bool) or max_bytes <= 0:
            raise ValueError("max_bytes must be a positive integer")
        selected_dir = cache_dir or os.environ.get(_CACHE_DIR_ENV)
        if selected_dir is None:
            selected_dir = os.environ.get("QUICKTHUMB_FONT_CACHE_DIR", tempfile.gettempdir())
        self.cache_dir = Path(selected_dir).expanduser()
        self.timeout = timeout
        self.max_bytes = max_bytes
        self.max_age = _max_age_setting(max_age)
        self.offline = _offline_setting(offline)
        self._fetcher = fetcher or urlopen
        self._records: dict[tuple[str, str], ResolvedAsset] = {}

    def resolve_image(
        self,
        source: str,
        *,
        asset_type: str = "image",
        fetcher: Callable[..., object] | None = None,
    ) -> ResolvedAsset:
        """Resolve an image and reject cached or downloaded non-image bytes."""
        return self.resolve(
            source,
            asset_type,
            validator=self._is_image,
            fetcher=fetcher,
            invalid_message=f"Downloaded content for image '{source}' is not a valid image.",
        )

    def resolve_font(
        self,
        source: str,
        *,
        extension: str | None = None,
        cache_filename: str | None = None,
        fetcher: Callable[..., object] | None = None,
    ) -> ResolvedAsset:
        """Resolve a font and reject cached or downloaded non-font bytes."""
        return self.resolve(
            source,
            "font",
            extension=extension,
            cache_filename=cache_filename,
            validator=self.is_font_data,
            fetcher=fetcher,
            invalid_message=(
                f"Downloaded content for font from '{source}' is not a valid font file."
            ),
        )

    def resolve(
        self,
        source: str,
        asset_type: str = "asset",
        *,
        extension: str | None = None,
        cache_filename: str | None = None,
        validator: Callable[[bytes], bool] | None = None,
        invalid_message: str | None = None,
        fetcher: Callable[..., object] | None = None,
    ) -> ResolvedAsset:
        """Resolve one source, preferring a fresh cache entry before network access.

        A resolver keeps its first result per source, so repeated renders and
        exports of one document report the same status without re-reading the
        cache or retrying a failed refresh.
        """
        if not _is_url(source):
            return self._resolve_local(source, asset_type, validator)

        try:
            source_key = self.source_key(source)
        except ValueError as error:
            raise RenderingError(f"Invalid remote asset URL '{source}'.") from error
        record_key = (asset_type, source_key)
        record = self._records.get(record_key)
        if record is not None:
            return record
        cache_key = self.cache_key(source_key)
        path = self._cache_path(source_key, asset_type, extension, cache_filename)
        with self._lock_for(path):
            result = self._resolve_remote(
                source,
                source_key,
                asset_type,
                cache_key,
                path,
                validator,
                invalid_message,
                fetcher,
            )
            self._records[record_key] = result
            return result

    def _resolve_remote(
        self,
        source: str,
        source_key: str,
        asset_type: str,
        cache_key: str,
        path: Path,
        validator: Callable[[bytes], bool] | None,
        invalid_message: str | None,
        fetcher: Callable[..., object] | None,
    ) -> ResolvedAsset:
        cached = self._read_cached(source, source_key, asset_type, cache_key, path, validator)
        if cached is not None and not self._is_stale(cached):
            return cached
        if self.offline:
            if cached is None:
                raise self._uncached_error(
                    f"Remote {asset_type} '{source}' is not cached and offline mode is "
                    f"enabled ({_OFFLINE_ENV})."
                )
            return self._mark_stale(cached, "offline mode is enabled")

        try:
            downloaded = self._download(source, asset_type, fetcher=fetcher)
            if validator is not None and not validator(downloaded):
                raise RenderingError(invalid_message or f"Downloaded {asset_type} is invalid.")
        except RenderingError as error:
            if cached is None:
                raise self._uncached_error(str(error)) from error
            return self._mark_stale(cached, f"refresh failed: {error}")
        content_hash = _content_hash(downloaded)
        if cached is None or cached.content_hash != content_hash:
            self._persist(path, downloaded)
        result = ResolvedAsset(
            source=source,
            asset_type=asset_type,
            source_key=source_key,
            cache_key=cache_key,
            cache_path=str(path),
            content_hash=content_hash,
            status="network",
            data=downloaded,
            fetched_at=float(int(time.time())),
        )
        self._persist_metadata(path, result)
        return result

    def _uncached_error(self, message: str) -> RenderingError:
        return RenderingError(
            f"{message} No usable cached copy exists in '{self.cache_dir}'; check the URL "
            f"and network access, or point {_CACHE_DIR_ENV} at a cache that holds it."
        )

    def describe(self, source: str, asset_type: str = "asset") -> ResolvedAsset | None:
        """Return metadata for a valid cached URL without making a network request."""
        if not _is_url(source):
            return self._resolve_local(source, asset_type, None)
        source_key = self.source_key(source)
        record = self._records.get((asset_type, source_key))
        if record is not None:
            return record
        cache_key = self.cache_key(source_key)
        path = self._cache_path(source_key, asset_type, None, None)
        result = self._read_cached(source, source_key, asset_type, cache_key, path, None)
        if result is not None and self._is_stale(result):
            return self._mark_stale(result)
        return result

    def invalidate(
        self,
        source: str,
        asset_type: str = "asset",
        *,
        extension: str | None = None,
        cache_filename: str | None = None,
    ) -> None:
        """Remove one URL's cache entry so the next resolution fetches it again."""
        if not _is_url(source):
            return
        source_key = self.source_key(source)
        path = self._cache_path(source_key, asset_type, extension, cache_filename)
        with self._lock_for(path):
            self._remove_cache(path)
            self._records.pop((asset_type, source_key), None)

    def records(self) -> dict[tuple[str, str], ResolvedAsset]:
        """Return a snapshot of assets resolved by this resolver."""
        return dict(self._records)

    def record_for(self, source: str, asset_type: str = "asset") -> ResolvedAsset | None:
        """Return the resolved record for a semantic source reference.

        Callers do not need to know whether a URL is stored under its
        canonical source key or whether a semantic type shares another
        storage type (for example, text-fill images use the image cache).
        """
        record = self._records.get((asset_type, source))
        if record is not None:
            return record
        if not _is_url(source):
            return None
        try:
            source_key = self.source_key(source)
        except ValueError:
            return None
        record = self._records.get((asset_type, source_key))
        if record is not None:
            return record
        if asset_type == "text-fill":
            return self._records.get(("image", source_key))
        return None

    def remember_reference(self, source: str, asset_type: str, asset: ResolvedAsset) -> None:
        """Register a semantic reference against an already-resolved asset."""
        record = replace(asset, source=source, asset_type=asset_type)
        self._records[(asset_type, source)] = record
        if _is_url(source):
            try:
                source_key = self.source_key(source)
            except ValueError:
                return
            self._records[(asset_type, source_key)] = record

    @staticmethod
    def source_key(source: str) -> str:
        """Canonicalize a URL into a stable key while preserving its meaning."""
        try:
            parsed = urlsplit(source.strip())
            hostname = parsed.hostname
            port = parsed.port
        except ValueError as error:
            raise ValueError(f"Invalid URL '{source}'.") from error
        scheme = parsed.scheme.lower()
        if hostname is None:
            return source.strip()
        netloc = hostname.lower()
        if parsed.username is not None:
            credentials = parsed.username
            if parsed.password is not None:
                credentials += f":{parsed.password}"
            netloc = f"{credentials}@{netloc}"
        default_port = (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
        if port is not None and not default_port:
            netloc += f":{port}"
        query = urlencode(sorted(parse_qsl(parsed.query, keep_blank_values=True)))
        return urlunsplit((scheme, netloc, parsed.path or "/", query, ""))

    @staticmethod
    def cache_key(source: str) -> str:
        """Return the stable filename key for a canonical source URL."""
        source_key = AssetResolver.source_key(source)
        return hashlib.md5(source_key.encode("utf-8"), usedforsecurity=False).hexdigest()

    def _resolve_local(
        self,
        source: str,
        asset_type: str,
        validator: Callable[[bytes], bool] | None,
    ) -> ResolvedAsset:
        path = Path(source)
        try:
            data = path.read_bytes()
        except OSError as error:
            raise RenderingError(f"Could not read {asset_type} '{source}'.") from error
        if validator is not None and not validator(data):
            raise RenderingError(f"Local {asset_type} '{source}' is invalid.")
        result = ResolvedAsset(
            source=source,
            asset_type=asset_type,
            source_key=source,
            cache_key=None,
            cache_path=str(path),
            content_hash=_content_hash(data),
            status="local",
            data=data,
        )
        self._records[(asset_type, source)] = result
        return result

    def _cache_path(
        self,
        source_key: str,
        asset_type: str,
        extension: str | None,
        cache_filename: str | None,
    ) -> Path:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        if cache_filename is None:
            suffix = _normalise_extension(extension or _url_extension(source_key))
            cache_filename = f"quickthumb_{asset_type}_{self.cache_key(source_key)}{suffix}"
        else:
            cache_filename = os.path.basename(cache_filename)
        return self.cache_dir / cache_filename

    def _read_cached(
        self,
        source: str,
        source_key: str,
        asset_type: str,
        cache_key: str,
        path: Path,
        validator: Callable[[bytes], bool] | None,
    ) -> ResolvedAsset | None:
        try:
            data = path.read_bytes()
        except OSError:
            return None
        if validator is not None and not validator(data):
            self._remove_cache(path)
            return None
        metadata = self._read_metadata(path)
        if metadata is not None and metadata.get("source_key") != source_key:
            return None
        content_hash = _content_hash(data)
        fetched_at: float | None = None
        if metadata is not None:
            if metadata.get("asset_type") not in (None, asset_type):
                return None
            if metadata.get("cache_key") not in (None, cache_key):
                return None
            if metadata.get("content_hash") not in (None, content_hash):
                return None
            fetched_at = _parse_timestamp(metadata.get("fetched_at"))
        if fetched_at is None:
            # Entries written before fetch times were recorded age from the file.
            with contextlib.suppress(OSError):
                fetched_at = path.stat().st_mtime
        return ResolvedAsset(
            source=source,
            asset_type=asset_type,
            source_key=source_key,
            cache_key=cache_key,
            cache_path=str(path),
            content_hash=content_hash,
            status="fresh",
            data=data,
            fetched_at=fetched_at,
        )

    def _is_stale(self, asset: ResolvedAsset) -> bool:
        if self.max_age is None:
            return False
        return asset.fetched_at is None or time.time() - asset.fetched_at > self.max_age

    def _mark_stale(self, cached: ResolvedAsset, cause: str | None = None) -> ResolvedAsset:
        """Report an expired (or offline) cache entry, with why it was not refreshed."""
        if cached.fetched_at is None:
            reason = "cache entry has no fetch time"
        else:
            reason = f"cache entry fetched at {format_timestamp(cached.fetched_at)}"
        if self.max_age is not None:
            reason += f" is older than max_age {self.max_age:g}s"
        if cause is not None:
            reason += f"; {cause}"
        return replace(cached, status="stale", stale_reason=reason)

    def _download(
        self,
        source: str,
        asset_type: str,
        *,
        fetcher: Callable[..., object] | None,
    ) -> bytes:
        request = Request(source, headers={"User-Agent": "quickthumb/1.0"})
        try:
            with (fetcher or self._fetcher)(request, timeout=self.timeout) as response:
                return self._read_response(response, source, asset_type)
        except RenderingError:
            raise
        except Exception as error:
            raise RenderingError(
                f"Failed to fetch remote {asset_type} '{source}': {error}."
            ) from error

    def _read_response(self, response: Any, source: str, asset_type: str) -> bytes:
        data = response.read(self.max_bytes + 1)
        if not isinstance(data, bytes):
            raise RenderingError(f"Remote {asset_type} '{source}' returned non-byte content.")
        if len(data) > self.max_bytes:
            raise RenderingError(
                f"Remote {asset_type} '{source}' exceeds the {self.max_bytes}-byte limit."
            )
        return data

    def _persist(self, path: Path, data: bytes) -> None:
        self._atomic_write(path, data)

    def _persist_metadata(self, path: Path, asset: ResolvedAsset) -> None:
        payload = {
            "asset_type": asset.asset_type,
            "cache_key": asset.cache_key,
            "content_hash": asset.content_hash,
            "fetched_at": format_timestamp(asset.fetched_at),
            "source": asset.source,
            "source_key": asset.source_key,
        }
        self._atomic_write(
            self._metadata_path(path),
            json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(),
        )

    def _read_metadata(self, path: Path) -> dict[str, object] | None:
        try:
            payload = json.loads(self._metadata_path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return None
        return payload if isinstance(payload, dict) else None

    @staticmethod
    def _metadata_path(path: Path) -> Path:
        return path.with_name(path.name + ".json")

    def _remove_cache(self, path: Path) -> None:
        for candidate in (path, self._metadata_path(path)):
            with contextlib.suppress(OSError):
                candidate.unlink()

    def _atomic_write(self, path: Path, data: bytes) -> None:
        temporary: str | None = None
        try:
            with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
                temporary = stream.name
            os.replace(temporary, path)
        except OSError as error:
            if temporary is not None:
                with contextlib.suppress(OSError):
                    os.unlink(temporary)
            raise RenderingError(f"Could not persist asset cache entry '{path}'.") from error

    @staticmethod
    def _lock_for(path: Path) -> Lock:
        key = str(path.absolute())
        with _CACHE_LOCK_GUARD:
            return _CACHE_LOCKS.setdefault(key, Lock())

    @staticmethod
    def _is_image(data: bytes) -> bool:
        try:
            with Image.open(io.BytesIO(data)) as image:
                image.verify()
            return True
        except (OSError, ValueError):
            return False

    @staticmethod
    def is_font_data(data: bytes) -> bool:
        return any(data.startswith(magic) for magic in _FONT_MAGIC)


def _is_url(value: str) -> bool:
    return value.startswith(("http://", "https://"))


def _content_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def format_timestamp(seconds: float | None) -> str | None:
    """Format epoch seconds as a UTC ISO-8601 instant with second precision."""
    if seconds is None:
        return None
    return datetime.fromtimestamp(int(seconds), timezone.utc).isoformat()


def _parse_timestamp(value: object) -> float | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


def _max_age_setting(value: float | None) -> float | None:
    if value is None:
        raw = os.environ.get(_MAX_AGE_ENV, "").strip()
        if not raw:
            return None
        try:
            value = float(raw)
        except ValueError:
            raise ValueError(f"{_MAX_AGE_ENV} must be a number of seconds, got {raw!r}") from None
    if isinstance(value, bool) or not value >= 0:
        raise ValueError("max_age must be a non-negative number of seconds")
    return float(value)


def _offline_setting(value: bool | None) -> bool:
    if value is not None:
        return bool(value)
    raw = os.environ.get(_OFFLINE_ENV, "").strip().lower()
    if raw not in _OFFLINE_VALUES:
        allowed = ", ".join(sorted(repr(key) for key in _OFFLINE_VALUES))
        raise ValueError(f"{_OFFLINE_ENV} must be one of {allowed}; got {raw!r}")
    return _OFFLINE_VALUES[raw]


def _url_extension(source: str) -> str:
    extension = Path(urlsplit(source).path).suffix.lower()
    allowed = {".css", ".png", ".jpg", ".jpeg", ".webp", ".svg", ".ttf", ".otf", ".woff", ".woff2"}
    return extension if extension in allowed else ".bin"


def _normalise_extension(extension: str) -> str:
    if not extension:
        return ".bin"
    return extension if extension.startswith(".") else f".{extension}"
