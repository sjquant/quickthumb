from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Annotated

import typer

from quickthumb.canvas import Canvas
from quickthumb.errors import RenderingError, ValidationError

_VALID_FORMATS = {"PNG", "JPEG", "WEBP"}

app = typer.Typer(help="quickthumb — programmatic thumbnail generation")


@app.callback()
def _callback() -> None:
    """quickthumb CLI."""


def main() -> None:
    app()


@app.command()
def render(
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
    var: Annotated[
        list[str] | None,
        typer.Option("--var", help="Variable substitution as KEY=VALUE"),
    ] = None,
) -> None:
    """Render a JSON spec file to an image."""
    # Validate --format early
    if fmt is not None and fmt.upper() not in _VALID_FORMATS:
        typer.echo(f"Invalid format '{fmt}'. Must be one of: PNG, JPEG, WEBP", err=True)
        raise typer.Exit(1)

    # Validate --quality range
    if quality is not None and not (1 <= quality <= 95):
        typer.echo(f"Invalid quality {quality}. Must be between 1 and 95.", err=True)
        raise typer.Exit(1)

    try:
        try:
            text = spec.read_text()
        except (FileNotFoundError, PermissionError) as e:
            typer.echo(str(e), err=True)
            raise typer.Exit(1) from e

        if var:
            variables: dict[str, str] = {}
            for item in var:
                key, sep, value = item.partition("=")
                if not sep:
                    typer.echo(f"Invalid --var '{item}': expected KEY=VALUE format.", err=True)
                    raise typer.Exit(1)
                variables[key] = value
            text = _substitute_vars(text, variables)

        try:
            canvas = Canvas.from_json(text)
        except (json.JSONDecodeError, ValidationError) as e:
            typer.echo(str(e), err=True)
            raise typer.Exit(1) from e

    except typer.Exit:
        raise

    try:
        canvas.render(
            str(output),
            format=fmt.upper() if fmt else None,  # type: ignore[arg-type]
            quality=quality,
        )
    except (RenderingError, OSError) as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(2) from e

    typer.echo(str(output))


def _is_theme_reference(match: re.Match) -> bool:
    """$theme.* references are resolved later by Canvas.from_json, not by --var."""
    return match.group(2) == "theme" and match.string[match.end() : match.end() + 1] == "."


def _substitute_vars(text: str, variables: dict[str, str]) -> str:
    def replace(match: re.Match) -> str:
        if _is_theme_reference(match):
            return match.group(0)
        key = match.group(1) or match.group(2)
        return variables.get(key, match.group(0))

    result = re.sub(r"\$\{(\w+)\}|\$(\w+)", replace, text)

    unresolved = [
        match.group(1) or match.group(2)
        for match in re.finditer(r"\$\{(\w+)\}|\$(\w+)", result)
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
    var: Annotated[
        list[str] | None,
        typer.Option("--var", help="Variable substitution as KEY=VALUE"),
    ] = None,
) -> None:
    """Watch a JSON spec file and re-render on changes."""
    try:
        from watchfiles import watch as _watch  # type: ignore[import-untyped]
    except ImportError:
        typer.echo(
            "watchfiles is not installed. Install it with: pip install 'quickthumb[cli]'",
            err=True,
        )
        raise typer.Exit(1) from None

    if fmt is not None and fmt.upper() not in _VALID_FORMATS:
        typer.echo(f"Invalid format '{fmt}'. Must be one of: PNG, JPEG, WEBP", err=True)
        raise typer.Exit(1)

    if quality is not None and not (1 <= quality <= 95):
        typer.echo(f"Invalid quality {quality}. Must be between 1 and 95.", err=True)
        raise typer.Exit(1)

    variables: dict[str, str] = {}
    if var:
        for item in var:
            key, sep, value = item.partition("=")
            if not sep:
                typer.echo(f"Invalid --var '{item}': expected KEY=VALUE format.", err=True)
                raise typer.Exit(1)
            variables[key] = value

    def _render_once() -> None:
        try:
            text = spec.read_text()
        except (FileNotFoundError, PermissionError) as e:
            typer.echo(str(e), err=True)
            return

        if variables:
            try:
                text = _substitute_vars(text, variables)
            except ValidationError as e:
                typer.echo(str(e), err=True)
                return

        try:
            canvas = Canvas.from_json(text)
        except (json.JSONDecodeError, ValidationError) as e:
            typer.echo(str(e), err=True)
            return

        try:
            canvas.render(
                str(output),
                format=fmt.upper() if fmt else None,  # type: ignore[arg-type]
                quality=quality,
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
