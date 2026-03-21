from __future__ import annotations

import sys


def main() -> None:
    try:
        import typer as _  # noqa: F401
    except ImportError:
        print(
            "typer is not installed. Install it with:\n  pip install 'quickthumb[cli]'",
            file=sys.stderr,
        )
        sys.exit(1)

    from quickthumb.cli import main as _main

    _main()
