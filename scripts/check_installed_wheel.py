"""Check the installed quickthumb wheel before it is uploaded to PyPI.

Run this with the interpreter of an environment that contains only the built wheel and no
optional extras. The package-location check rejects an import from outside that environment.
"""

import sys
import tempfile
from pathlib import Path
from typing import NoReturn

import quickthumb
from quickthumb import Canvas
from quickthumb.errors import RenderingError


def main() -> None:
    check_package_location()
    canvas = Canvas(128, 96).background(color="#ff0000")
    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory)
        check_core_exports(canvas, output)
        check_missing_extra_hint(canvas, output)
    print("installed wheel: PNG and HTML export work, and missing extras report their install hint")


def check_package_location() -> None:
    environment = Path(sys.prefix).resolve()
    package = Path(quickthumb.__file__).resolve()
    if not package.is_relative_to(environment):
        fail(f"imported {package}, which is outside the test environment {environment}")


def check_core_exports(canvas: Canvas, output: Path) -> None:
    png_path = output / "wheel.png"
    canvas.export(png_path)
    if png_path.stat().st_size == 0:
        fail("PNG export wrote an empty file")

    # HTML export reads the packaged templates and assets, so a missing file raises here.
    html_path = output / "wheel.html"
    canvas.export(html_path)
    if html_path.stat().st_size == 0:
        fail("HTML export wrote an empty file")


def check_missing_extra_hint(canvas: Canvas, output: Path) -> None:
    try:
        canvas.export(output / "wheel.pdf")
    except RenderingError as error:
        if "quickthumb[pdf]" not in str(error):
            fail(f"PDF export without the pdf extra gave no install hint: {error}")
    else:
        fail("PDF export succeeded without the pdf extra")


def fail(message: str) -> NoReturn:
    raise SystemExit(f"installed wheel check failed: {message}")


if __name__ == "__main__":
    main()
