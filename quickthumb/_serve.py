"""Local development server for quickthumb HTML slideshows."""

from __future__ import annotations

import json
import re
import runpy
import sys
import threading
import webbrowser
from dataclasses import dataclass
from functools import cache
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import invalidate_caches
from importlib.resources import files
from importlib.util import cache_from_source, source_from_cache
from pathlib import Path
from types import ModuleType
from urllib.parse import parse_qs, urlsplit

from jinja2 import Environment, Template

from quickthumb.canvas import _VAR_RE, Canvas, _is_theme_reference
from quickthumb.deck import Deck
from quickthumb.errors import ValidationError

_DEFAULT_SOURCES = ("slides.py", "slides.json", "slides.html", "slides.htm")
_HTML_PATHS = {"/", "/index.html", "/presenter"}
_VERSION_PATH = "/__quickthumb_version"
_PACKAGE_ROOT = Path(__file__).resolve().parent
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

    while not stop_event.is_set():
        paths = source.watch_paths
        restart = False
        try:
            changes = watch(
                *paths,
                debounce=100,
                recursive=False,
                step=100,
                stop_event=stop_event,
                yield_on_timeout=True,
            )
            for changed_paths in changes:
                if source.watch_paths != paths:
                    restart = True
                    break
                if changed_paths:
                    source.invalidate()
                    restart = True
                    break
        except OSError:
            # The browser's version endpoint still provides a polling fallback when
            # native filesystem watching is unavailable on the current platform.
            return
        if not restart:
            return


def _module_path(module: ModuleType) -> Path | None:
    """Return a module's source path, translating cached bytecode when needed."""
    module_file = module.__dict__.get("__file__")
    if not isinstance(module_file, str):
        return None
    path = Path(module_file)
    if path.suffix == ".pyc":
        try:
            path = Path(source_from_cache(str(path)))
        except ValueError:
            return None
    try:
        return path.resolve()
    except OSError:
        return None


def _remove_bytecode_cache(source_path: Path) -> None:
    """Remove a local source module's bytecode so same-second edits are reloaded."""
    if source_path.suffix != ".py":
        return
    try:
        Path(cache_from_source(str(source_path))).unlink(missing_ok=True)
    except (OSError, ValueError):
        return


def _is_path_within(path: Path, directory: Path) -> bool:
    """Return whether a path is the directory itself or one of its descendants."""
    return path == directory or directory in path.parents


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
        self.path = path.resolve()
        self.variables = variables
        self._render_lock = threading.Lock()
        self._cached_version: str | None = None
        self._cached_html: str | None = None
        self._generation = 0
        self._python_dependency_paths: frozenset[Path] = frozenset()
        self._watch_paths: frozenset[Path] = frozenset({self.path})

    @property
    def watch_paths(self) -> frozenset[Path]:
        """Return the source and local dependencies that should trigger reloads."""
        return self._watch_paths

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
        source_dir = self.path.parent
        source_dir_string = str(source_dir)
        self._forget_python_dependencies()
        sys.path.insert(0, source_dir_string)
        try:
            try:
                namespace = runpy.run_path(str(self.path), run_name="__quickthumb_serve__")
            finally:
                self._python_dependency_paths = self._collect_python_dependency_paths(source_dir)
                self._watch_paths = frozenset({self.path, *self._python_dependency_paths})
        finally:
            sys.path.remove(source_dir_string)

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

    def _forget_python_dependencies(self) -> None:
        """Remove previously loaded local modules before rerunning the source."""
        if not self._python_dependency_paths:
            return
        dependency_paths = self._python_dependency_paths
        for dependency_path in dependency_paths:
            _remove_bytecode_cache(dependency_path)
        for name, module in list(sys.modules.items()):
            if module is not None and _module_path(module) in dependency_paths:
                sys.modules.pop(name, None)
        invalidate_caches()

    def _collect_python_dependency_paths(self, source_dir: Path) -> frozenset[Path]:
        """Collect local module files imported while executing the source."""
        dependencies: set[Path] = set()
        for module in list(sys.modules.values()):
            if module is None:
                continue
            module_path = _module_path(module)
            if (
                module_path is None
                or not _is_path_within(module_path, source_dir)
                or _is_path_within(module_path, _PACKAGE_ROOT)
            ):
                continue
            dependencies.add(module_path)
        return frozenset(dependencies)

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
