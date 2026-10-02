"""Publish a prepared directory without replacing an existing destination.

There is deliberately no check-then-rename or copying fallback on Unix. These
primitives protect competing destinations, not crash durability or hostile
same-user replacement of the parent directory.
"""

from __future__ import annotations

import ctypes
import errno
import os
import shutil
import stat
import sys
from pathlib import Path

from quickthumb.errors import RenderingError


def normalize_destination(path: str | os.PathLike[str]) -> Path:
    """Resolve the existing parent, leaving the final component unfollowed."""
    destination = Path(path)
    parent = destination.parent.resolve(strict=True)
    if not parent.is_dir():
        raise NotADirectoryError(errno.ENOTDIR, os.strerror(errno.ENOTDIR), str(parent))
    destination = parent / destination.name
    if os.path.lexists(destination):
        raise FileExistsError(errno.EEXIST, os.strerror(errno.EEXIST), str(destination))
    return destination


def rename_exclusive(source: Path, destination: Path) -> None:
    """Atomically rename a sibling directory, failing if any destination exists."""
    if sys.platform == "win32":
        # Python documents that Windows rename always fails when dst exists.
        # Sibling staging keeps the rename on the same volume.
        # https://docs.python.org/3/library/os.html#os.rename
        os.rename(source, destination)
        return
    if sys.platform not in {"linux", "darwin"}:
        raise RenderingError("Exclusive directory publication is unsupported on this platform")
    try:
        library = ctypes.CDLL(None, use_errno=True)
        if sys.platform == "linux":
            # https://man7.org/linux/man-pages/man2/rename.2.html
            rename = library.renameat2
            rename.argtypes = [
                ctypes.c_int,
                ctypes.c_char_p,
                ctypes.c_int,
                ctypes.c_char_p,
                ctypes.c_uint,
            ]
            rename.restype = ctypes.c_int
            result = rename(-100, os.fsencode(source), -100, os.fsencode(destination), 1)
        else:
            # Apple xnu bsd/sys/stdio.h: renamex_np(..., unsigned int), RENAME_EXCL=4.
            # https://github.com/apple-oss-distributions/xnu/blob/main/bsd/sys/stdio.h
            rename = library.renamex_np
            rename.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
            rename.restype = ctypes.c_int
            result = rename(os.fsencode(source), os.fsencode(destination), 4)
    except (AttributeError, OSError) as error:
        raise RenderingError(
            "Exclusive directory publication is unavailable on this system"
        ) from error
    if result != 0:
        code = ctypes.get_errno()
        if code in {errno.ENOSYS, errno.EINVAL, errno.ENOTSUP, errno.EOPNOTSUPP}:
            raise RenderingError(
                "Exclusive directory publication is unsupported by this system or filesystem"
            )
        raise OSError(code, os.strerror(code), str(destination))


def cleanup_owned_staging(staging: Path, identity: tuple[int, int]) -> None:
    """Best-effort cleanup of only the directory we created, preserving errors."""
    try:
        current = staging.lstat()
        if stat.S_ISDIR(current.st_mode) and (current.st_dev, current.st_ino) == identity:
            shutil.rmtree(staging)
    except OSError:
        pass
