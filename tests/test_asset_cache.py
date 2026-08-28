"""Black-box specifications for the shared remote asset cache."""

from __future__ import annotations

import io
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from PIL import Image
from quickthumb import Canvas
from quickthumb.errors import RenderingError


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
        yield base_url, Handler.requests, server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_remote_image_manifest_persists_network_result_and_reuses_fresh_cache(
    tmp_path, monkeypatch, local_assets
):
    """Given a remote image, resolution fetches once and a later context uses fresh cache."""
    base_url, requests, server = local_assets
    monkeypatch.setenv("QUICKTHUMB_ASSET_CACHE_DIR", str(tmp_path / "assets"))
    first_url = f"{base_url}/asset.png?b=2&a=1"
    equivalent_url = f"{base_url}/asset.png?a=1&b=2"

    first = Canvas(4, 4).background(image=first_url)
    first_manifest = first.resolve_assets().asset_manifest[0]

    # When: the same source is requested with its query parameters reordered
    second = Canvas(4, 4).background(image=equivalent_url)
    second_manifest = second.resolve_assets().asset_manifest[0]
    server.shutdown()
    server.server_close()

    # Then: the persisted entry is fresh, deterministic, and no second fetch occurred
    assert len(requests) == 1
    assert first_manifest.status == "network"
    assert second_manifest.status == "fresh"
    assert second_manifest.source_key == first_manifest.source_key
    assert second_manifest.cache_key == first_manifest.cache_key
    assert second_manifest.content_hash == first_manifest.content_hash
    assert second_manifest.cache_path is not None
    assert Path(second_manifest.cache_path).is_file()


def test_remote_font_render_uses_the_shared_cache_after_network_becomes_unavailable(
    tmp_path, monkeypatch, local_assets
):
    """Given a URL font, rendering succeeds from the persisted cache without a second request."""
    base_url, requests, server = local_assets
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


def test_remote_asset_without_cache_surfaces_network_failure(tmp_path, monkeypatch, local_assets):
    """Given a missing remote asset, resolution fails without creating a cache entry."""
    base_url, requests, server = local_assets
    monkeypatch.setenv("QUICKTHUMB_ASSET_CACHE_DIR", str(tmp_path / "assets"))

    with pytest.raises(RenderingError, match="Failed to fetch remote"):
        Canvas(4, 4).background(image=f"{base_url}/missing.png").resolve_assets()

    server.shutdown()
    server.server_close()
    assert requests == ["/missing.png"]
    assert not list((tmp_path / "assets").glob("*"))
