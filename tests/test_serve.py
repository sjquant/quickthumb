"""Black-box tests for the quickthumb slideshow development server."""

import json
import subprocess
import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

import pytest
from quickthumb._serve import SlideSource, resolve_source, serve_slides, slide_request_handler
from quickthumb.errors import RenderingError, ValidationError
from typer.testing import CliRunner


class TestSlideServer:
    """The server renders supported sources behind an HTTP boundary."""

    def test_should_serve_default_python_deck_and_rerender_after_edits(
        self, tmp_path: Path, monkeypatch
    ):
        """slides.py is served at audience and presenter URLs and reloads from disk."""
        # given: a conventional slides.py source and a real local HTTP server
        source_path = tmp_path / "slides.py"
        source_path.write_text(
            "from quickthumb import Canvas, Deck\n"
            "deck = Deck(320, 180).slide(\n"
            "    Canvas().background(color='#101820'), notes='First note'\n"
            ")\n",
            encoding="utf-8",
        )
        monkeypatch.chdir(tmp_path)
        source = SlideSource(resolve_source(None), {})
        server = ThreadingHTTPServer(("127.0.0.1", 0), slide_request_handler(source))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base_url = f"http://127.0.0.1:{server.server_address[1]}"

        try:
            # when: audience, presenter-query, and Slidev-style presenter paths are requested
            with urlopen(base_url + "/", timeout=2) as response:
                audience_html = response.read().decode()
            with urlopen(base_url + "/?presenter=true", timeout=2) as response:
                presenter_html = response.read().decode()
            with urlopen(base_url + "/presenter", timeout=2) as response:
                presenter_path_html = response.read().decode()
            with urlopen(base_url + "/__quickthumb_version", timeout=2) as response:
                version = response.read().decode()
            with urlopen(base_url + "/favicon.ico", timeout=2) as response:
                favicon_status = response.status
            with pytest.raises(HTTPError) as missing:
                urlopen(base_url + "/missing", timeout=2)
            source_path.write_text(
                "from quickthumb import Canvas, Deck\n"
                "deck = Deck(320, 180).slide(\n"
                "    Canvas().background(color='#101820'), notes='Updated speaker note'\n"
                ")\n",
                encoding="utf-8",
            )
            with urlopen(base_url + "/", timeout=2) as response:
                updated_html = response.read().decode()
            with urlopen(base_url + "/?presenter", timeout=2) as response:
                updated_presenter_html = response.read().decode()

            # then: audience HTML omits notes while both presenter paths include them
            assert response.status == 200
            assert audience_html.startswith("<!doctype html>")
            assert presenter_html == presenter_path_html
            assert 'data-qt-notes="First note"' not in audience_html
            assert 'data-qt-notes="First note"' in presenter_html
            assert "__quickthumb_version" in audience_html
            assert ":" in version
            assert favicon_status == 204
            assert missing.value.code == 404
            assert 'data-qt-notes="Updated speaker note"' not in updated_html
            assert 'data-qt-notes="Updated speaker note"' in updated_presenter_html
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_should_render_variable_substituted_json_decks(self, tmp_path: Path):
        """JSON slide sources support the same --var placeholders as other CLI commands."""
        # given: a deck JSON source containing a template variable
        source_path = tmp_path / "deck.json"
        source_path.write_text(
            json.dumps(
                {
                    "width": 320,
                    "height": 180,
                    "slides": [
                        {
                            "layers": [{"type": "background", "color": "$ACCENT"}],
                            "notes": "Use the accent color as the transition cue.",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        # when: the reloadable source is rendered with a variable value
        html = SlideSource(source_path, {"ACCENT": "#B8FF00"}).render()

        # then: the deck, color, and presenter notes all reach the HTML document
        assert "background:rgb(184,255,0)" in html
        assert 'data-qt-notes="Use the accent color as the transition cue."' in html

    def test_should_preserve_theme_references_while_substituting_json_variables(
        self, tmp_path: Path
    ):
        """Server substitution leaves theme references for Deck.from_json to resolve."""
        # given: a JSON deck using both a CLI variable and a theme token
        source_path = tmp_path / "deck.json"
        source_path.write_text(
            json.dumps(
                {
                    "width": 320,
                    "height": 180,
                    "theme": {"colors": {"background": "$ACCENT"}},
                    "slides": [
                        {"layers": [{"type": "background", "color": "$theme.colors.background"}]}
                    ],
                }
            ),
            encoding="utf-8",
        )

        # when: the source is rendered with a CLI variable
        html = SlideSource(source_path, {"ACCENT": "#B8FF00"}).render()

        # then: the theme token resolves after variable substitution
        assert "background:rgb(184,255,0)" in html

    def test_should_render_canvas_json_and_static_html_sources(self, tmp_path: Path):
        """Canvas JSON and pre-rendered HTML remain valid serve inputs."""
        # given: one canvas JSON document and one standalone HTML document
        canvas_path = tmp_path / "canvas.json"
        canvas_path.write_text(
            json.dumps({"width": 80, "height": 40, "layers": []}), encoding="utf-8"
        )
        html_path = tmp_path / "slides.html"
        html_path.write_text("<!doctype html><title>Existing slides</title>", encoding="utf-8")

        # when: each source is rendered through the common source boundary
        canvas_html = SlideSource(canvas_path, {}).render()
        static_html = SlideSource(html_path, {}).render()

        # then: canvas JSON is exported and existing HTML is returned unchanged
        assert 'class="qt-stage"' in canvas_html
        assert "data-qt-transition" not in canvas_html
        assert static_html == "<!doctype html><title>Existing slides</title>"

    def test_should_retry_when_source_changes_during_render(self, tmp_path: Path, monkeypatch):
        """A source edit during rendering cannot be stamped with an old HTML version."""
        # given: a source whose version changes while the first render is running
        source_path = tmp_path / "slides.html"
        source_path.write_text("<!doctype html><body>Slides</body>", encoding="utf-8")
        source = SlideSource(source_path, {})
        versions = iter(["old", "new", "new", "new"])
        monkeypatch.setattr(source, "version", lambda: next(versions))

        # when: HTML and its version are requested as one rendered result
        rendered = source.render_with_version()

        # then: the result carries the stable version sampled after the retry
        assert rendered.version == "new"
        assert rendered.html == "<!doctype html><body>Slides</body>"

    def test_should_validate_source_paths_and_template_variables(self, tmp_path: Path):
        """Explicit paths and substitutions fail with actionable validation errors."""
        # given: an absent path, static HTML with --var, and unresolved JSON
        missing_path = tmp_path / "missing.py"
        html_path = tmp_path / "slides.html"
        html_path.write_text("<!doctype html>", encoding="utf-8")
        json_path = tmp_path / "slides.json"
        json_path.write_text('{"width":80,"height":40,"layers":[],"title":"$MISSING"}')

        # when / then: each invalid public input is rejected before serving
        with pytest.raises(ValidationError, match="not found"):
            resolve_source(missing_path)
        with pytest.raises(ValidationError, match="only supported for JSON"):
            SlideSource(html_path, {"VALUE": "unused"}).render()
        with pytest.raises(ValidationError, match="Unresolved placeholder.*MISSING"):
            SlideSource(json_path, {"OTHER": "unused"}).render()

    def test_should_discover_a_single_unnamed_python_document(self, tmp_path: Path):
        """A Python source may expose one unambiguously named Deck or Canvas value."""
        # given: a Python source whose only quickthumb document uses a custom name
        source_path = tmp_path / "talk.py"
        source_path.write_text(
            "from quickthumb import Canvas, Deck\n"
            "presentation = Deck(80, 40).slide(Canvas().background(color='#112233'))\n",
            encoding="utf-8",
        )

        # when: the Python source is rendered
        html = SlideSource(source_path, {}).render()

        # then: the single document is discovered without requiring a reserved name
        assert 'data-qt-slide-index="0"' in html

    def test_should_reject_ambiguous_python_documents(self, tmp_path: Path):
        """Python sources with multiple unnamed documents require an explicit public name."""
        # given: two canvases with no deck, slides, or canvas variable
        source_path = tmp_path / "talk.py"
        source_path.write_text(
            "from quickthumb import Canvas\nfirst = Canvas(80, 40)\nsecond = Canvas(80, 40)\n",
            encoding="utf-8",
        )

        # when / then: source discovery refuses to guess which document to serve
        with pytest.raises(ValidationError, match="must define `deck`, `slides`, or `canvas`"):
            SlideSource(source_path, {}).render()

    def test_should_run_server_lifecycle_and_open_the_browser(
        self, tmp_path: Path, monkeypatch, capsys
    ):
        """The top-level server binds, reports both URLs, opens, and closes cleanly."""
        # given: a standalone source with deterministic fake server and timer boundaries
        import quickthumb._serve as serve_module

        source_path = tmp_path / "slides.html"
        source_path.write_text("<!doctype html><body>Slides</body>", encoding="utf-8")
        opened = []
        servers = []

        class FakeServer:
            server_address = ("0.0.0.0", 4321)

            def __init__(self, address, handler):
                assert address == ("0.0.0.0", 0)
                assert handler.__name__ == "SlideRequestHandler"
                self.closed = False
                servers.append(self)

            def serve_forever(self):
                raise KeyboardInterrupt

            def server_close(self):
                self.closed = True

        class ImmediateTimer:
            def __init__(self, interval, function, args):
                assert interval == 0.05
                self.function = function
                self.args = args

            def start(self):
                self.function(*self.args)

        monkeypatch.setattr(serve_module, "ThreadingHTTPServer", FakeServer)
        monkeypatch.setattr(serve_module.threading, "Timer", ImmediateTimer)
        monkeypatch.setattr(serve_module.webbrowser, "open", opened.append)

        # when: the public serve lifecycle runs until its simulated interrupt
        serve_slides(source_path, "0.0.0.0", 0, open_browser=True)

        # then: startup output, browser URL, and shutdown all use the bound port
        output = capsys.readouterr().out
        assert "http://localhost:4321" in output
        assert "http://localhost:4321/?presenter" in output
        assert opened == ["http://localhost:4321"]
        assert len(servers) == 1
        assert servers[0].closed is True

    def test_should_return_render_errors_without_stopping_the_server(self, tmp_path: Path):
        """A broken edit returns an explanatory 500 page while the server remains usable."""
        # given: a server whose Python source currently raises during execution
        source_path = tmp_path / "slides.py"
        source_path.write_text("raise RuntimeError('broken slide source')\n", encoding="utf-8")
        source = SlideSource(source_path, {})
        server = ThreadingHTTPServer(("127.0.0.1", 0), slide_request_handler(source))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        url = f"http://127.0.0.1:{server.server_address[1]}/"

        try:
            # when: the broken slideshow is requested
            with pytest.raises(HTTPError) as raised:
                urlopen(url, timeout=2)
            error_html = raised.value.read().decode()

            # then: the response explains the source error and uses HTTP 500
            assert raised.value.code == 500
            assert "RuntimeError: broken slide source" in error_html
            assert "server is still running" in error_html
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


class TestCLIServe:
    """The Typer command exposes the development server contract."""

    def test_should_forward_serve_options_to_the_server(self, monkeypatch, tmp_path: Path):
        """serve parses source, network, browser, and JSON variable options."""
        # given: a CLI invocation with every public serve option
        import quickthumb._serve as serve_module
        from quickthumb.cli import app

        calls = []

        def fake_serve_slides(**kwargs):
            calls.append(kwargs)

        monkeypatch.setattr(serve_module, "serve_slides", fake_serve_slides)
        source = tmp_path / "deck.json"

        # when: the user starts the server without opening a browser
        result = CliRunner().invoke(
            app,
            [
                "serve",
                str(source),
                "--host",
                "0.0.0.0",
                "--port",
                "4040",
                "--no-open",
                "--var",
                "ACCENT=#B8FF00",
            ],
        )

        # then: the parsed values are passed through exactly once
        assert result.exit_code == 0
        assert calls == [
            {
                "source": source,
                "host": "0.0.0.0",
                "port": 4040,
                "open_browser": False,
                "variables": {"ACCENT": "#B8FF00"},
            }
        ]

    def test_should_report_invalid_var_without_a_secondary_exit_message(self):
        """Malformed --var input reports only its actionable validation error."""
        # given: a serve invocation with a malformed variable
        from quickthumb.cli import app

        # when: the command parses its options
        result = CliRunner().invoke(app, ["serve", "slides.json", "--var", "BROKEN", "--no-open"])

        # then: the CLI keeps the validation output concise
        assert result.exit_code == 1
        assert result.output == "Invalid --var 'BROKEN': expected KEY=VALUE format.\n"

    def test_should_run_the_public_serve_entrypoint_against_a_real_http_server(
        self, tmp_path: Path
    ):
        """The public serve entrypoint binds a real server and serves its source."""
        # given: a valid Python deck and the installed CLI entrypoint
        source_path = tmp_path / "slides.py"
        source_path.write_text(
            "from quickthumb import Canvas, Deck\n"
            "deck = Deck(80, 40).slide(Canvas().background(color='#112233'))\n",
            encoding="utf-8",
        )
        process = subprocess.Popen(
            [
                sys.executable,
                "-c",
                "from quickthumb.cli import main; main()",
                "serve",
                str(source_path),
                "--port",
                "0",
                "--no-open",
            ],
            cwd=tmp_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        try:
            # when: the real CLI starts and its reported URL is requested
            assert process.stdout is not None
            output = process.stdout.readline()
            port = output.rsplit(":", 1)[-1].strip()
            with urlopen(f"http://127.0.0.1:{port}/", timeout=2) as response:
                html = response.read().decode()

            # then: the public command returns the rendered deck over HTTP
            assert response.status == 200
            assert 'data-qt-slide-index="0"' in html
        finally:
            process.terminate()
            process.wait(timeout=5)

    def test_should_explain_missing_default_slide_source(self):
        """serve exits with guidance when no conventional slide source exists."""
        # given: an empty working directory
        from quickthumb.cli import app

        # when: the user runs quickthumb serve without a source
        with CliRunner().isolated_filesystem():
            result = CliRunner().invoke(app, ["serve", "--no-open"])

        # then: the command fails before binding and lists the supported defaults
        assert result.exit_code == 1
        assert "No slide source found" in result.output
        assert "slides.py" in result.output

    @pytest.mark.parametrize(
        ("error", "exit_code", "message"),
        [
            pytest.param(RenderingError("render failed"), 2, "render failed", id="rendering"),
            pytest.param(
                RuntimeError("script failed"), 1, "RuntimeError: script failed", id="script"
            ),
        ],
    )
    def test_should_map_server_failures_to_cli_exit_codes(
        self, monkeypatch, error: Exception, exit_code: int, message: str
    ):
        """serve reports rendering and source execution failures with stable exit codes."""
        # given: a server boundary that raises before binding
        import quickthumb._serve as serve_module
        from quickthumb.cli import app

        def fail_serve(**kwargs):
            raise error

        monkeypatch.setattr(serve_module, "serve_slides", fail_serve)

        # when: the user invokes serve
        result = CliRunner().invoke(app, ["serve", "slides.py", "--no-open"])

        # then: the error class maps to the documented process status
        assert result.exit_code == exit_code
        assert message in result.output

    def test_should_reject_unsupported_source_extensions(self, tmp_path: Path):
        """Unsupported source types fail before an HTTP server is started."""
        # given: an existing source with an unsupported extension
        source_path = tmp_path / "slides.txt"
        source_path.write_text("not slides", encoding="utf-8")

        # when / then: source validation rejects it with actionable guidance
        with pytest.raises(ValidationError, match="Use .py, .json, .html, or .htm"):
            SlideSource(source_path, {}).render()
