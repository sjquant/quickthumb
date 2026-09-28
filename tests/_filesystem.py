import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager


@contextmanager
def isolated_filesystem() -> Iterator[str]:
    """Run the block inside a fresh temporary working directory."""
    previous = os.getcwd()
    with tempfile.TemporaryDirectory() as directory:
        os.chdir(directory)
        try:
            yield directory
        finally:
            os.chdir(previous)
