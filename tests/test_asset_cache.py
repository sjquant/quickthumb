"""Black-box specifications for the shared remote asset cache."""

from __future__ import annotations

import hashlib
import io
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from PIL import Image
from quickthumb import Canvas
from quickthumb.asset_cache import AssetResolver
from quickthumb.errors import RenderingError
from quickthumb.models import TextFillImage


@pytest.fixture
def local_assets():
    image_buffer = io.BytesIO()
    Image.new("RGBA", (4, 4), (12, 34, 56, 255)).save(image_buffer, format="PNG")
    payloads = {
        "/asset.png": image_buffer.getvalue(),
        "/font.ttf": Path("assets/fonts/Roboto-Regular.ttf").read_bytes(),
    }

    class Handler(BaseHTTPRequestHandler):
        requests: list[str] = []

        def do_GET(self):  # noqa: N802
            path = urlsplit(self.path).path
            self.requests.append(self.path)
            payload = payloads.get(path)
            if payload is None:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *_args):
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"
    try:
        yield base_url, Handler.requests, server, payloads
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_remote_image_manifest_persists_network_result_and_reuses_fresh_cache(
    tmp_path, monkeypatch, local_assets
):
    """Given a remote image, resolution fetches once and a later context uses fresh cache."""
    base_url, requests, server, payloads = local_assets
    monkeypatch.setenv("QUICKTHUMB_ASSET_CACHE_DIR", str(tmp_path / "assets"))
    first_url = f"{base_url}/asset.png?b=2&a=1"
    equivalent_url = f"{base_url}/asset.png?a=1&b=2"

    first = Canvas(4, 4).background(image=first_url)
    first_manifest = first.resolve_assets().asset_manifest[0]
    first.render(tmp_path / "first.png")

    # When: the same source is requested with its query parameters reordered
    second = Canvas(4, 4).background(image=equivalent_url)
    second_manifest = second.resolve_assets().asset_manifest[0]
    server.shutdown()
    server.server_close()
    second.render(tmp_path / "second.png")

    # Then: the persisted entry is fresh, deterministic, and no second fetch occurred
    assert len(requests) == 1
    assert first_manifest.status == "network"
    assert second_manifest.status == "fresh"
    assert second_manifest.source_key == first_manifest.source_key
    assert second_manifest.cache_key == first_manifest.cache_key
    assert second_manifest.content_hash == first_manifest.content_hash
    assert second_manifest.source_key == f"{base_url}/asset.png?a=1&b=2"
    assert second_manifest.source_key is not None
    assert second_manifest.cache_key == AssetResolver.cache_key(second_manifest.source_key)
    assert second_manifest.content_hash == hashlib.sha256(payloads["/asset.png"]).hexdigest()
    assert second_manifest.cache_path is not None
    assert Path(second_manifest.cache_path).is_file()


def test_remote_font_render_uses_the_shared_cache_after_network_becomes_unavailable(
    tmp_path, monkeypatch, local_assets
):
    """Given a URL font, rendering succeeds from the persisted cache without a second request."""
    base_url, requests, server, _payloads = local_assets
    monkeypatch.setenv("QUICKTHUMB_ASSET_CACHE_DIR", str(tmp_path / "assets"))
    font_url = f"{base_url}/font.ttf"

    first = Canvas(160, 80).text("cached", font=font_url, size=24, position=(0, 0))
    first_manifest = first.resolve_assets().asset_manifest[0]
    first.render(tmp_path / "first.png")

    server.shutdown()
    server.server_close()
    second = Canvas(160, 80).text("cached", font=font_url, size=24, position=(0, 0))
    second_manifest = second.resolve_assets().asset_manifest[0]
    second.render(tmp_path / "second.png")

    assert len(requests) == 1
    assert first_manifest.asset_type == second_manifest.asset_type == "font"
    assert first_manifest.status == "network"
    assert second_manifest.status == "fresh"
    assert first_manifest.content_hash == second_manifest.content_hash
    assert first_manifest.cache_key == second_manifest.cache_key
    assert second_manifest.cache_path is not None
    assert Path(second_manifest.cache_path).is_file()


def test_remote_text_fill_reuses_the_image_cache_after_resolution(
    tmp_path, monkeypatch, local_assets
):
    """Given a remote text-fill image, resolution leaves rendering network-independent."""
    base_url, requests, server, _payloads = local_assets
    monkeypatch.setenv("QUICKTHUMB_ASSET_CACHE_DIR", str(tmp_path / "assets"))
    canvas = Canvas(120, 80).text(
        "cached",
        fill=TextFillImage(path=f"{base_url}/asset.png"),
        size=24,
        position=(0, 0),
    )

    manifest = canvas.resolve_assets().asset_manifest[0]
    server.shutdown()
    server.server_close()
    canvas.render(tmp_path / "text-fill.png")

    assert len(requests) == 1
    assert manifest.asset_type == "text-fill"
    assert manifest.status == "network"


def test_google_font_reference_is_resolved_in_the_manifest(tmp_path, monkeypatch):
    """Given a cached Google font, resolution reports its semantic family reference."""
    cache_dir = tmp_path / "assets"
    cache_dir.mkdir()
    monkeypatch.setenv("QUICKTHUMB_ASSET_CACHE_DIR", str(cache_dir))
    css_hash = hashlib.md5(b"Roboto|400|0").hexdigest()
    font_url = "https://fonts.gstatic.com/s/roboto/v1/Roboto-Regular.ttf"
    css_path = cache_dir / f"quickthumb_google_{css_hash}.css"
    css_path.write_text(
        "@font-face{font-family:'Roboto';font-style:normal;font-weight:400;"
        f"src:url({font_url}) format('truetype');}}",
        encoding="utf-8",
    )
    font_path = cache_dir / f"quickthumb_google_{css_hash}.ttf"
    font_bytes = Path("assets/fonts/Roboto-Regular.ttf").read_bytes()
    font_path.write_bytes(font_bytes)

    canvas = Canvas(160, 80).text(
        "cached", font="Roboto", font_source="google", size=24, position=(0, 0)
    )
    manifest = canvas.resolve_assets().asset_manifest

    assert len(manifest) == 1
    assert manifest[0].source == "Roboto"
    assert manifest[0].asset_type == "font"
    assert manifest[0].status == "fresh"
    assert manifest[0].cache_key == AssetResolver.cache_key(font_url)
    assert manifest[0].content_hash == hashlib.sha256(font_bytes).hexdigest()


def test_remote_invalid_payload_is_rejected_without_persisting_cache(
    tmp_path, monkeypatch, local_assets
):
    """Given invalid remote image and font bytes, resolution rejects both without cache files."""
    base_url, requests, server, _payloads = local_assets
    monkeypatch.setenv("QUICKTHUMB_ASSET_CACHE_DIR", str(tmp_path / "assets"))

    with pytest.raises(RenderingError, match="not a valid image"):
        Canvas(4, 4).background(image=f"{base_url}/font.ttf").resolve_assets()

    with pytest.raises(RenderingError, match="not a valid font"):
        Canvas(80, 40).text("invalid", font=f"{base_url}/asset.png").resolve_assets()

    server.shutdown()
    server.server_close()
    assert requests == ["/font.ttf", "/asset.png"]
    assert not list((tmp_path / "assets").glob("*"))


def test_invalid_cached_image_is_replaced_by_a_valid_network_result(
    tmp_path, monkeypatch, local_assets
):
    """Given a corrupt cached image, resolution removes it and persists a valid download."""
    base_url, requests, server, payloads = local_assets
    cache_dir = tmp_path / "assets"
    monkeypatch.setenv("QUICKTHUMB_ASSET_CACHE_DIR", str(cache_dir))
    source = f"{base_url}/asset.png"
    cache_path = cache_dir / f"quickthumb_image_{AssetResolver.cache_key(source)}.png"
    cache_dir.mkdir()
    cache_path.write_bytes(b"not an image")

    manifest = Canvas(4, 4).background(image=source).resolve_assets().asset_manifest[0]

    server.shutdown()
    server.server_close()
    assert requests == ["/asset.png"]
    assert manifest.status == "network"
    assert cache_path.read_bytes() == payloads["/asset.png"]


def test_invalid_remote_port_is_rejected_before_cache_lookup(tmp_path, monkeypatch):
    """Given a malformed remote port, resolution fails instead of aliasing another URL."""
    monkeypatch.setenv("QUICKTHUMB_ASSET_CACHE_DIR", str(tmp_path / "assets"))

    with pytest.raises(RenderingError, match="Invalid remote asset URL"):
        Canvas(4, 4).background(image="http://example.com:bad/asset.png").resolve_assets()


def test_asset_resolver_enforces_a_response_size_limit(tmp_path):
    """Given an oversized response, the resolver rejects it without writing a cache entry."""

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self, _size=-1):
            return b"12345"

    resolver = AssetResolver(tmp_path, max_bytes=4, fetcher=lambda *_args, **_kwargs: Response())

    with pytest.raises(RenderingError, match="exceeds the 4-byte limit"):
        resolver.resolve_image("http://example.com/asset.png")
    assert not list(tmp_path.glob("*"))


def test_remote_asset_without_cache_surfaces_network_failure(tmp_path, monkeypatch, local_assets):
    """Given a missing remote asset, resolution fails without creating a cache entry."""
    base_url, requests, server, _payloads = local_assets
    monkeypatch.setenv("QUICKTHUMB_ASSET_CACHE_DIR", str(tmp_path / "assets"))

    with pytest.raises(RenderingError, match="Failed to fetch remote"):
        Canvas(4, 4).background(image=f"{base_url}/missing.png").resolve_assets()

    server.shutdown()
    server.server_close()
    assert requests == ["/missing.png"]
    assert not list((tmp_path / "assets").glob("*"))
