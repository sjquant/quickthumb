from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Annotated

import typer

from quickthumb.canvas import Canvas
from quickthumb.errors import RenderingError, ValidationError

_VALID_FORMATS = {"PNG", "JPEG", "WEBP"}

app = typer.Typer(help="QuickThumb — programmatic thumbnail generation")


@app.callback()
def _callback() -> None:
    """QuickThumb CLI."""


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


def _substitute_vars(text: str, variables: dict[str, str]) -> str:
    def replace(match: re.Match) -> str:
        key = match.group(1) or match.group(2)
        return variables.get(key, match.group(0))

    result = re.sub(r"\$\{(\w+)\}|\$(\w+)", replace, text)

    unresolved = re.findall(r"\$\{(\w+)\}|\$(\w+)", result)
    if unresolved:
        names = [k1 or k2 for k1, k2 in unresolved]
        raise ValidationError(f"Unresolved placeholder(s): {', '.join(names)}")

    return result


if __name__ == "__main__":
    main()
