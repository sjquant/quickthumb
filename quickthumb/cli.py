from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Annotated

import typer

from quickthumb.canvas import _VAR_RE, Canvas, _is_theme_reference
from quickthumb.errors import RenderingError, ValidationError
from quickthumb.schema import canvas_json_schema

_VALID_FORMATS = {"PNG", "JPEG", "WEBP"}

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
            typer.echo(f"Invalid --var '{item}': expected KEY=VALUE format.", err=True)
            raise typer.Exit(1)
        variables[key] = value
    return variables


def _load_canvas(spec: Path, variables: dict[str, str]) -> Canvas:
    """Read, substitute, and parse a spec file; any input error exits with code 1."""
    try:
        text = spec.read_text()
    except (FileNotFoundError, PermissionError) as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1) from e

    if variables:
        try:
            text = _substitute_vars(text, variables)
        except ValidationError as e:
            typer.echo(str(e), err=True)
            raise typer.Exit(1) from e

    try:
        return Canvas.from_json(text)
    except (json.JSONDecodeError, ValidationError) as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1) from e


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
        typer.Option("-o", "--output", help="Output file path (.png/.jpg/.webp/.svg/.pptx/.pdf)"),
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
    """Render a JSON spec file to an image, or to SVG/PPTX/PDF by file extension."""
    _validate_render_options(fmt, quality)
    canvas = _load_canvas(spec, _parse_var_options(var))

    try:
        canvas.render(
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
) -> None:
    """Check a JSON spec for layout and legibility issues without rendering a file.

    Exit codes: 0 no issues, 1 invalid spec, 2 rendering failure, 3 issues found.
    """
    lint_format = output_format.lower()
    if lint_format not in ("text", "json"):
        typer.echo(
            f"Invalid lint format '{output_format}'. Must be one of: text, json",
            err=True,
        )
        raise typer.Exit(1)

    canvas = _load_canvas(spec, _parse_var_options(var))

    try:
        diagnostics = canvas.diagnose()
    except FileNotFoundError as e:
        typer.echo(f"Referenced file not found: {e}", err=True)
        raise typer.Exit(1) from e
    except (RenderingError, OSError) as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(2) from e

    if lint_format == "json":
        error_count = sum(1 for finding in diagnostics if finding.severity == "error")
        warning_count = sum(1 for finding in diagnostics if finding.severity == "warning")
        typer.echo(
            json.dumps(
                {
                    "summary": {
                        "diagnostic_count": len(diagnostics),
                        "error_count": error_count,
                        "warning_count": warning_count,
                    },
                    "diagnostics": [
                        finding.model_dump(mode="json", exclude_none=True)
                        for finding in diagnostics
                    ],
                },
                indent=2,
            )
        )
        if diagnostics:
            raise typer.Exit(3)
        return

    if not diagnostics:
        typer.echo("No issues found.")
        return

    for finding in diagnostics:
        typer.echo(
            f"[{finding.severity}] layer {finding.layer_index}: {finding.code} — {finding.message}"
        )
    raise typer.Exit(3)


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
    variables = _parse_var_options(var)

    def _render_once() -> None:
        try:
            canvas = _load_canvas(spec, variables)
        except typer.Exit:
            return  # error already echoed; keep watching for the next change

        try:
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
