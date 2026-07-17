"""Local development server for quickthumb HTML slideshows."""

from __future__ import annotations

import json
import re
import runpy
import sys
import threading
import webbrowser
from collections.abc import Callable
from dataclasses import dataclass
from functools import cache
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import parse_qs, urlsplit

from jinja2 import Environment, Template

from quickthumb.canvas import _VAR_RE, Canvas, _is_theme_reference
from quickthumb.deck import Deck
from quickthumb.errors import ValidationError

if TYPE_CHECKING:
    from watchfiles import Change

_DEFAULT_SOURCES = ("slides.py", "slides.json", "slides.html", "slides.htm")
_HTML_PATHS = {"/", "/index.html", "/presenter"}
_VERSION_PATH = "/__quickthumb_version"
_SERVE_TEMPLATES = Environment(autoescape=True)


@dataclass(frozen=True)
class RenderedSource:
    """Rendered source HTML paired with the exact version used to render it."""

    html: str
    version: str


def serve_slides(
    source: Path | None,
    host: str,
    port: int,
    open_browser: bool,
    variables: dict[str, str] | None = None,
) -> None:
    """Render a slide source and serve it until interrupted."""
    slide_source = SlideSource(resolve_source(source), variables or {})
    slide_source.render()
    server = ThreadingHTTPServer((host, port), slide_request_handler(slide_source))
    actual_port = server.server_address[1]
    display_host = "localhost" if host in {"127.0.0.1", "0.0.0.0", "::"} else host
    url = f"http://{display_host}:{actual_port}"

    print(f"Serving {slide_source.path} at {url}", flush=True)
    print(f"Presenter mode: {url}/?presenter", flush=True)
    if open_browser:
        threading.Timer(0.05, webbrowser.open, args=(url,)).start()

    stop_event = threading.Event()
    watcher = threading.Thread(
        target=_watch_source,
        args=(slide_source, stop_event),
        name="quickthumb-slide-watcher",
        daemon=True,
    )
    watcher.start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop_event.set()
        server.server_close()
        watcher.join(timeout=1)


def _watch_source(source: SlideSource, stop_event: threading.Event) -> None:
    """Invalidate the rendered source whenever watchfiles detects an edit."""
    try:
        from watchfiles import watch
    except ImportError:
        stop_event.wait()
        return

    try:
        changes = watch(
            source.path.parent,
            watch_filter=_source_watch_filter(source.path),
            debounce=100,
            stop_event=stop_event,
        )
        for changed_paths in changes:
            if changed_paths:
                source.invalidate()
    except OSError:
        # The browser's version endpoint still provides a polling fallback when
        # native filesystem watching is unavailable on the current platform.
        return


def _source_watch_filter(source_path: Path) -> Callable[[Change, str], bool]:
    """Return a watchfiles filter that accepts only the selected source file."""
    source_path = source_path.resolve()

    def is_source_change(_change: Change, changed_path: str) -> bool:
        return Path(changed_path).resolve() == source_path

    return is_source_change


def resolve_source(source: Path | None) -> Path:
    """Resolve an explicit source or the first conventional slides filename."""
    if source is not None:
        path = source.expanduser().resolve()
        if not path.is_file():
            raise ValidationError(f"Slide source not found: {source}")
        return path

    for filename in _DEFAULT_SOURCES:
        candidate = Path(filename).resolve()
        if candidate.is_file():
            return candidate
    choices = ", ".join(_DEFAULT_SOURCES)
    raise ValidationError(f"No slide source found. Create one of {choices}, or pass a source path.")


class SlideSource:
    """A reloadable Python, JSON, or standalone HTML slide source."""

    def __init__(self, path: Path, variables: dict[str, str]):
        self.path = path
        self.variables = variables
        self._render_lock = threading.Lock()
        self._cached_version: str | None = None
        self._cached_html: str | None = None
        self._generation = 0

    def render(self, *, presenter: bool = True) -> str:
        """Render the latest source contents to a standalone HTML document."""
        return self.render_with_version(presenter=presenter).html

    def render_with_version(self, *, presenter: bool = True) -> RenderedSource:
        """Render source HTML and return the matching source version atomically."""
        with self._render_lock:
            while True:
                version = self.version()
                if self._cached_html is not None and version == self._cached_version:
                    html = self._cached_html
                else:
                    html = self._render()
                    if self.version() != version:
                        continue
                    self._cached_version = version
                    self._cached_html = html
                if not presenter:
                    html = _without_speaker_notes(html)
                return RenderedSource(html=html, version=version)

    def invalidate(self) -> None:
        """Discard cached HTML and advance the source generation."""
        self._cached_version = None
        self._cached_html = None
        self._generation += 1

    def _render(self) -> str:
        suffix = self.path.suffix.lower()
        if self.variables and suffix != ".json":
            raise ValidationError("--var is only supported for JSON slide sources.")
        if suffix == ".py":
            return self._render_python()
        if suffix == ".json":
            return self._render_json()
        if suffix in {".html", ".htm"}:
            return self.path.read_text(encoding="utf-8")
        raise ValidationError(
            f"Unsupported slide source {self.path.name!r}. Use .py, .json, .html, or .htm."
        )

    def _render_python(self) -> str:
        source_dir = str(self.path.parent)
        sys.path.insert(0, source_dir)
        try:
            namespace = runpy.run_path(str(self.path), run_name="__quickthumb_serve__")
        finally:
            sys.path.remove(source_dir)

        document = None
        for name in ("deck", "slides", "canvas"):
            candidate = namespace.get(name)
            if isinstance(candidate, (Deck, Canvas)):
                document = candidate
                break
        if not isinstance(document, (Deck, Canvas)):
            candidates = {
                id(value): value
                for value in namespace.values()
                if isinstance(value, (Deck, Canvas))
            }
            if len(candidates) == 1:
                document = next(iter(candidates.values()))
            else:
                raise ValidationError(
                    f"{self.path.name} must define `deck`, `slides`, or `canvas` as a "
                    "quickthumb Deck or Canvas."
                )
        return document.to_html()

    def _render_json(self) -> str:
        text = self.path.read_text(encoding="utf-8")
        if self.variables:
            text = _substitute_variables(text, self.variables)
        payload = json.loads(text)
        if isinstance(payload, dict) and "slides" in payload:
            return Deck.from_json(text).to_html()
        return Canvas.from_json(text).to_html()

    def version(self) -> str:
        """Return a cheap change token used by the browser reload poller."""
        try:
            stat = self.path.stat()
        except OSError:
            return "missing"
        return f"{stat.st_mtime_ns}:{stat.st_size}:{self._generation}"


def _substitute_variables(text: str, variables: dict[str, str]) -> str:
    def replace(match) -> str:
        if _is_theme_reference(match):
            return match.group(0)
        key = match.group(1) or match.group(2)
        return variables.get(key, match.group(0))

    result = _VAR_RE.sub(replace, text)
    unresolved = [
        match.group(1) or match.group(2)
        for match in _VAR_RE.finditer(result)
        if not _is_theme_reference(match)
    ]
    if unresolved:
        raise ValidationError(f"Unresolved placeholder(s): {', '.join(unresolved)}")
    return result


def slide_request_handler(source: SlideSource) -> type[BaseHTTPRequestHandler]:
    """Build an HTTP handler bound to one reloadable slide source."""

    class SlideRequestHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            """Serve the slideshow, presenter alias, or live-reload version."""
            request = urlsplit(self.path)
            path = request.path
            if path == _VERSION_PATH:
                self._send(200, source.version(), "text/plain; charset=utf-8")
                return
            if path == "/favicon.ico":
                self.send_response(204)
                self.end_headers()
                return
            if path not in _HTML_PATHS:
                self._send(404, "Not found\n", "text/plain; charset=utf-8")
                return

            try:
                rendered = source.render_with_version(
                    presenter=_is_presenter_request(path, request.query)
                )
                html = _with_live_reload(rendered.html, rendered.version)
            except Exception as error:  # Keep the server alive while the source is being edited.
                html = _with_live_reload(_error_document(error), source.version())
                self._send(500, html, "text/html; charset=utf-8")
                return
            self._send(200, html, "text/html; charset=utf-8")

        def _send(self, status: int, content: str, content_type: str) -> None:
            payload = content.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format: str, *args) -> None:
            return

    return SlideRequestHandler


def _with_live_reload(html: str, version: str) -> str:
    script = _serve_template("serve_reload.html").render(
        version=version,
        version_path=_VERSION_PATH,
    )
    marker = "</body>"
    if marker in html:
        return html.replace(marker, script + "\n" + marker, 1)
    return html + "\n" + script


def _is_presenter_request(path: str, query: str) -> bool:
    """Return whether an HTTP request asks for the presenter document variant."""
    if path == "/presenter":
        return True
    value = parse_qs(query, keep_blank_values=True).get("presenter", [None])[0]
    return value is not None and value not in {"0", "false"}


def _without_speaker_notes(html: str) -> str:
    """Remove generated presenter-only notes from an audience document."""
    return re.sub(r'\sdata-qt-notes="[^"]*"', "", html)


def _error_document(error: Exception) -> str:
    return _serve_template("serve_error.html").render(message=f"{type(error).__name__}: {error}")


@cache
def _serve_template(name: str) -> Template:
    """Load and cache a Jinja template shipped with the quickthumb package."""
    template = files("quickthumb.html").joinpath(name).read_text(encoding="utf-8")
    return _SERVE_TEMPLATES.from_string(template)
