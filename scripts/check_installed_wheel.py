"""Check the installed quickthumb wheel before it is uploaded to PyPI.

Run this with the interpreter of an environment that contains only the built wheel and no
optional extras. Run it from outside the source checkout so the checkout cannot shadow the
installed package; the import check below also rejects a package outside this environment.
"""

import sys
import tempfile
from pathlib import Path
from typing import NoReturn

import quickthumb
from quickthumb import Canvas
from quickthumb.errors import RenderingError


def fail(message: str) -> NoReturn:
    raise SystemExit(f"installed wheel check failed: {message}")


def check_package_location() -> None:
    environment = Path(sys.prefix).resolve()
    package = Path(quickthumb.__file__).resolve()
    if not package.is_relative_to(environment):
        fail(f"imported {package}, which is outside the test environment {environment}")


def check_core_exports(output: Path) -> None:
    canvas = Canvas(128, 96).background(color="#ff0000")

    canvas.export(output / "wheel.png")
    if (output / "wheel.png").stat().st_size == 0:
        fail("PNG export wrote an empty file")

    # HTML export reads the packaged templates and assets, so a wheel missing them fails here.
    canvas.export(output / "wheel.html")
    html = (output / "wheel.html").read_text(encoding="utf-8")
    if "qt-stage" not in html or "{{" in html:
        fail("HTML export lost its packaged templates")


def check_missing_extra_hint(output: Path) -> None:
    canvas = Canvas(128, 96).background(color="#ff0000")
    try:
        canvas.export(output / "wheel.pdf")
    except RenderingError as error:
        if "quickthumb[pdf]" not in str(error):
            fail(f"PDF export without the pdf extra gave no install hint: {error}")
        return
    fail("PDF export succeeded without the pdf extra")


def main() -> None:
    check_package_location()
    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory)
        check_core_exports(output)
        check_missing_extra_hint(output)
    print("installed wheel: PNG and HTML export work, and missing extras report their install hint")


if __name__ == "__main__":
    main()
