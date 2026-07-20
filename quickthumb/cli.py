from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Annotated, Protocol, TypeAlias

import typer
from PIL import Image

from quickthumb._diff import (
    DEFAULT_HASH_SIZE,
    DEFAULT_HASH_THRESHOLD,
    DEFAULT_MAX_DIFFERENT_PIXEL_RATIO,
    DEFAULT_PIXEL_TOLERANCE,
    _load_image,
    compare_images,
    create_diff_image,
)
from quickthumb.canvas import _VAR_RE, Canvas, _is_theme_reference
from quickthumb.deck import Deck, DeckDiagnostic
from quickthumb.errors import RenderingError, ValidationError
from quickthumb.schema import canvas_json_schema

_VALID_FORMATS = {"PNG", "JPEG", "WEBP"}
_DIAGNOSTIC_CODES = {
    "off-canvas",
    "tiny-text",
    "text-overflow",
    "text-clipped",
    "missing-glyph",
    "low-contrast",
    "layer-overlap",
    "layer-hidden",
    "edge-crowding",
    "mixed-slide-size",
}
_FAIL_ON_VALUES = {"warning", "error", "never"}
Diagnosable: TypeAlias = Canvas | Deck


class _DiagnosticLike(Protocol):
    code: str
    severity: str
    layer_index: int | None
    layer_id: str | None
    message: str
    suggestion: str | None

    def model_dump(self, *, mode: str, exclude_none: bool) -> dict: ...


app = typer.Typer(help="quickthumb — programmatic thumbnail generation")


def _validate_render_options(fmt: str | None, quality: int | None) -> None:
    if fmt is not None and fmt.upper() not in _VALID_FORMATS:
        typer.echo(f"Invalid format '{fmt}'. Must be one of: PNG, JPEG, WEBP", err=True)
        raise typer.Exit(1)
    if quality is not None and not (1 <= quality <= 95):
        typer.echo(f"Invalid quality {quality}. Must be between 1 and 95.", err=True)
        raise typer.Exit(1)


def _parse_var_options(var: list[str] | None) -> dict[str, str]:
    variables: dict[str, str] = {}
    for item in var or []:
        key, sep, value = item.partition("=")
        if not sep:
            raise ValidationError(f"Invalid --var '{item}': expected KEY=VALUE format.")
        variables[key] = value
    return variables


def _load_canvas(spec: Path, variables: dict[str, str]) -> Diagnosable:
    """Read, substitute, and parse a Canvas or Deck JSON source."""
    text = spec.read_text()

    if variables:
        text = _substitute_vars(text, variables)

    raw = json.loads(text)
    if isinstance(raw, dict) and "slides" in raw:
        return Deck.from_json(text)
    return Canvas.from_json(text)


def _echo_input_error(
    error: Exception, output_format: str = "text", code: str = "invalid-spec"
) -> None:
    if output_format == "json":
        typer.echo(json.dumps({"error": {"code": code, "message": str(error)}}))
    else:
        typer.echo(str(error), err=True)


def _validate_diagnostic_options(
    fail_on: str, ignored_codes: list[str] | None, output_format: str
) -> tuple[str, set[str]]:
    normalized_fail_on = fail_on.lower()
    if normalized_fail_on not in _FAIL_ON_VALUES:
        _echo_input_error(
            ValidationError(
                f"Invalid --fail-on '{fail_on}'. Must be one of: warning, error, never"
            ),
            output_format,
            code="invalid-options",
        )
        raise typer.Exit(1) from None

    ignored = {code.lower() for code in ignored_codes or []}
    unknown = sorted(ignored - _DIAGNOSTIC_CODES)
    if unknown:
        _echo_input_error(
            ValidationError(f"Unknown diagnostic code(s): {', '.join(unknown)}"),
            output_format,
            code="invalid-options",
        )
        raise typer.Exit(1) from None
    return normalized_fail_on, ignored


def _diagnostic_payload(finding: _DiagnosticLike) -> dict:
    return finding.model_dump(mode="json", exclude_none=True)


def _filter_diagnostics(
    findings: list[_DiagnosticLike], ignored_codes: set[str]
) -> list[_DiagnosticLike]:
    return [finding for finding in findings if finding.code not in ignored_codes]


def _should_fail(findings: list[_DiagnosticLike], fail_on: str) -> bool:
    if fail_on == "never":
        return False
    return any(
        finding.severity == "error"
        or (fail_on == "warning" and finding.severity == "warning")
        for finding in findings
    )


def _format_finding(finding: _DiagnosticLike) -> str:
    location = "deck" if finding.layer_index is None else f"layer {finding.layer_index}"
    slide_index = finding.slide_index if isinstance(finding, DeckDiagnostic) else None
    if slide_index is not None:
        location = f"slide {slide_index}, {location}"
    layer_id = finding.layer_id
    if layer_id:
        location = f"{location} ({layer_id})"
    message = f"[{finding.severity}] {location}: {finding.code} — {finding.message}"
    suggestion = finding.suggestion
    if suggestion and suggestion not in finding.message:
        message += f" Suggestion: {suggestion}."
    return message


def _run_lint(
    spec: Path,
    output_format: str,
    var: list[str] | None,
    fail_on: str,
    ignored_codes: list[str] | None,
) -> None:
    lint_format = output_format.lower()
    if lint_format not in ("text", "json"):
        typer.echo(
            f"Invalid lint format '{output_format}'. Must be one of: text, json",
            err=True,
        )
        raise typer.Exit(1)
    normalized_fail_on, ignored = _validate_diagnostic_options(
        fail_on, ignored_codes, lint_format
    )

    try:
        source = _load_canvas(spec, _parse_var_options(var))
    except (OSError, UnicodeError, json.JSONDecodeError, ValidationError) as error:
        _echo_input_error(error, lint_format)
        raise typer.Exit(1) from None

    try:
        diagnostics = _filter_diagnostics(source.diagnose(), ignored)
    except FileNotFoundError as error:
        _echo_input_error(FileNotFoundError(f"Referenced file not found: {error}"), lint_format)
        raise typer.Exit(1) from None
    except (RenderingError, OSError) as error:
        if lint_format == "json":
            typer.echo(json.dumps({"error": {"code": "rendering-failure", "message": str(error)}}))
        else:
            typer.echo(str(error), err=True)
        raise typer.Exit(2) from None

    if lint_format == "json":
        error_count = sum(1 for finding in diagnostics if finding.severity == "error")
        warning_count = sum(
            1 for finding in diagnostics if finding.severity == "warning"
        )
        typer.echo(
            json.dumps(
                {
                    "summary": {
                        "diagnostic_count": len(diagnostics),
                        "error_count": error_count,
                        "warning_count": warning_count,
                    },
                    "diagnostics": [_diagnostic_payload(finding) for finding in diagnostics],
                },
                indent=2,
            )
        )
    elif not diagnostics:
        typer.echo("No issues found.")
    else:
        for finding in diagnostics:
            typer.echo(_format_finding(finding))

    if _should_fail(diagnostics, normalized_fail_on):
        raise typer.Exit(3)


@app.callback()
def _callback() -> None:
    """quickthumb CLI."""


def main() -> None:
    app()


@app.command()
def schema(
    output: Annotated[
        Path | None,
        typer.Option("-o", "--output", help="Write schema JSON to a file instead of stdout"),
    ] = None,
) -> None:
    """Emit the JSON Schema for quickthumb canvas specs."""
    payload = json.dumps(canvas_json_schema(), indent=2, sort_keys=True) + "\n"
    if output is None:
        typer.echo(payload, nl=False)
        return

    try:
        output.write_text(payload)
    except OSError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1) from e
    typer.echo(str(output))


@app.command()
def render(
    spec: Annotated[Path, typer.Argument(help="Path to a JSON spec file")],
    output: Annotated[
        Path,
        typer.Option(
            "-o",
            "--output",
            help="Output file path (.png/.jpg/.webp/.svg/.pptx/.pdf/.html/.gif/.mp4/.webm)",
        ),
    ] = Path("output.png"),
    fmt: Annotated[
        str | None,
        typer.Option("--format", help="Output format: PNG, JPEG, or WEBP"),
    ] = None,
    quality: Annotated[
        int | None,
        typer.Option("--quality", help="Quality for JPEG/WEBP (1-95)"),
    ] = None,
    debug: Annotated[
        bool,
        typer.Option("--debug", help="Overlay public layer-id bounding boxes on raster output"),
    ] = False,
    var: Annotated[
        list[str] | None,
        typer.Option("--var", help="Variable substitution as KEY=VALUE"),
    ] = None,
) -> None:
    """Render a JSON spec file to an image, to SVG/PPTX/PDF/HTML, or to an
    animated GIF/MP4/WebM that plays the spec's layer animations, by extension."""
    _validate_render_options(fmt, quality)
    try:
        source = _load_canvas(spec, _parse_var_options(var))
    except (OSError, UnicodeError, json.JSONDecodeError, ValidationError) as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(1) from None

    try:
        if isinstance(source, Deck):
            if debug:
                typer.echo("--debug is only supported for Canvas specs.", err=True)
                raise typer.Exit(1)
            written = source.render(
                str(output),
                format=fmt.upper() if fmt else None,  # type: ignore[arg-type]
                quality=quality,
            )
            for path in written:
                typer.echo(path)
            return
        source.render(
            str(output),
            format=fmt.upper() if fmt else None,  # type: ignore[arg-type]
            quality=quality,
            debug=debug,
        )
    except (RenderingError, OSError) as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(2) from e

    typer.echo(str(output))


@app.command()
def diff(
    expected: Annotated[Path, typer.Argument(help="Path to the golden image")],
    actual: Annotated[Path, typer.Argument(help="Path to the image under test")],
    output: Annotated[
        Path | None,
        typer.Option("-o", "--output", help="Write a raw pixel-difference image"),
    ] = None,
    threshold: Annotated[
        float,
        typer.Option("--threshold", min=0.0, max=1.0, help="Minimum perceptual-hash similarity"),
    ] = DEFAULT_HASH_THRESHOLD,
    pixel_tolerance: Annotated[
        int,
        typer.Option(
            "--pixel-tolerance",
            min=0,
            max=255,
            help="Ignore per-channel deltas up to this value",
        ),
    ] = DEFAULT_PIXEL_TOLERANCE,
    max_diff_ratio: Annotated[
        float,
        typer.Option(
            "--max-diff-ratio",
            min=0.0,
            max=1.0,
            help="Maximum fraction of pixels allowed to differ",
        ),
    ] = DEFAULT_MAX_DIFFERENT_PIXEL_RATIO,
    hash_size: Annotated[
        int,
        typer.Option("--hash-size", min=2, max=32, help="Perceptual hash width and height"),
    ] = DEFAULT_HASH_SIZE,
    output_format: Annotated[
        str,
        typer.Option("--format", help="Output format: text or json"),
    ] = "text",
) -> None:
    """Compare a golden image with an image under test for CI or review."""
    diff_format = output_format.lower()
    if diff_format not in ("text", "json"):
        typer.echo(
            f"Invalid diff format '{output_format}'. Must be one of: text, json",
            err=True,
        )
        raise typer.Exit(1)

    try:
        expected_image = _load_image(expected)
        actual_image = _load_image(actual)
        comparison = compare_images(
            expected_image,
            actual_image,
            threshold=threshold,
            pixel_tolerance=pixel_tolerance,
            max_different_pixel_ratio=max_diff_ratio,
            hash_size=hash_size,
        )
        if output is not None:
            _save_diff_image(expected_image, actual_image, output)
    except (OSError, ValueError) as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(1) from error

    if diff_format == "json":
        payload = comparison.to_dict()
        if output is not None:
            payload["diff_output"] = str(output)
        typer.echo(json.dumps(payload, indent=2, sort_keys=True))
    else:
        typer.echo(comparison.format_text())
        if output is not None:
            typer.echo(f"diff image: {output}")

    if not comparison.matches:
        raise typer.Exit(1)


def _save_diff_image(expected: Image.Image, actual: Image.Image, output: Path) -> None:
    diff_image = create_diff_image(expected, actual)
    if output.suffix.lower() in {".jpg", ".jpeg"}:
        diff_image = diff_image.convert("RGB")
    diff_image.save(output)


@app.command("diagnose")
@app.command("lint")
def lint(
    spec: Annotated[Path, typer.Argument(help="Path to a JSON spec file")],
    output_format: Annotated[
        str,
        typer.Option("--format", help="Output format: text or json"),
    ] = "text",
    var: Annotated[
        list[str] | None,
        typer.Option("--var", help="Variable substitution as KEY=VALUE"),
    ] = None,
    fail_on: Annotated[
        str,
        typer.Option("--fail-on", help="Fail on warning, error, or never"),
    ] = "warning",
    ignore: Annotated[
        list[str] | None,
        typer.Option("--ignore", help="Ignore a diagnostic code (repeatable)"),
    ] = None,
) -> None:
    """Check a JSON spec for layout and legibility issues without rendering a file.

    Exit codes: 0 no issues, 1 invalid spec, 2 rendering failure, 3 issues found.
    """
    _run_lint(spec, output_format, var, fail_on, ignore)


def _substitute_vars(text: str, variables: dict[str, str]) -> str:
    def replace(match: re.Match) -> str:
        if _is_theme_reference(match):
            return match.group(0)
        key = match.group(1) or match.group(2)
        assert key is not None
        fallback = match.group(0)
        assert fallback is not None
        if key in variables:
            return variables[key]
        return fallback

    result = _VAR_RE.sub(replace, text)

    unresolved = [
        match.group(1) or match.group(2)
        for match in _VAR_RE.finditer(result)
        if not _is_theme_reference(match)
    ]
    if unresolved:
        raise ValidationError(f"Unresolved placeholder(s): {', '.join(unresolved)}")

    return result


@app.command()
def serve(
    source: Annotated[
        Path | None,
        typer.Argument(help="Slide source (.py, .json, or standalone .html); defaults to slides.*"),
    ] = None,
    host: Annotated[
        str,
        typer.Option("--host", help="Address to bind"),
    ] = "127.0.0.1",
    port: Annotated[
        int,
        typer.Option("--port", min=0, max=65535, help="Port to bind (0 chooses a free port)"),
    ] = 3030,
    open_browser: Annotated[
        bool,
        typer.Option("--open/--no-open", help="Open the slideshow in a browser"),
    ] = True,
    var: Annotated[
        list[str] | None,
        typer.Option("--var", help="Variable substitution for JSON sources as KEY=VALUE"),
    ] = None,
) -> None:
    """Serve HTML slides with live reload and a ?presenter view."""
    from quickthumb._serve import serve_slides

    try:
        variables = _parse_var_options(var)
        serve_slides(
            source=source,
            host=host,
            port=port,
            open_browser=open_browser,
            variables=variables,
        )
    except RenderingError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(2) from error
    except (json.JSONDecodeError, OSError, ValidationError) as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(1) from error
    except Exception as error:
        typer.echo(f"{type(error).__name__}: {error}", err=True)
        raise typer.Exit(1) from error


@app.command()
def watch(
    spec: Annotated[Path, typer.Argument(help="Path to a JSON spec file")],
    output: Annotated[
        Path,
        typer.Option("-o", "--output", help="Output file path"),
    ] = Path("output.png"),
    fmt: Annotated[
        str | None,
        typer.Option("--format", help="Output format: PNG, JPEG, or WEBP"),
    ] = None,
    quality: Annotated[
        int | None,
        typer.Option("--quality", help="Quality for JPEG/WEBP (1-95)"),
    ] = None,
    debug: Annotated[
        bool,
        typer.Option("--debug", help="Overlay public layer-id bounding boxes on raster output"),
    ] = False,
    var: Annotated[
        list[str] | None,
        typer.Option("--var", help="Variable substitution as KEY=VALUE"),
    ] = None,
) -> None:
    """Watch a JSON spec file and re-render on changes."""
    try:
        from watchfiles import watch as _watch
    except ImportError:
        typer.echo(
            "watchfiles is not installed. Install it with: pip install 'quickthumb[cli]'",
            err=True,
        )
        raise typer.Exit(1) from None

    _validate_render_options(fmt, quality)
    try:
        variables = _parse_var_options(var)
    except ValidationError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(1) from None

    def _render_once() -> None:
        try:
            canvas = _load_canvas(spec, variables)
        except typer.Exit:
            return  # error already echoed; keep watching for the next change
        except (OSError, UnicodeError, json.JSONDecodeError, ValidationError) as error:
            typer.echo(str(error), err=True)
            return

        try:
            if isinstance(canvas, Deck):
                if debug:
                    typer.echo("--debug is only supported for Canvas specs.", err=True)
                    return
                for path in canvas.render(
                    str(output),
                    format=fmt.upper() if fmt else None,  # type: ignore[arg-type]
                    quality=quality,
                ):
                    typer.echo(path)
                return
            canvas.render(
                str(output),
                format=fmt.upper() if fmt else None,  # type: ignore[arg-type]
                quality=quality,
                debug=debug,
            )
            typer.echo(str(output))
        except (RenderingError, OSError) as e:
            typer.echo(str(e), err=True)

    typer.echo(f"Watching {spec} … (Ctrl+C to stop)")
    _render_once()

    try:
        for _ in _watch(spec):
            _render_once()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
