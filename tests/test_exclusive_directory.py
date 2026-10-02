"""Exclusive publication contracts, including real Linux filesystem races.

macOS and Windows cases exercise dispatch/ABI contracts through mocks; they do
not establish native filesystem behavior on those platforms.
"""

import ctypes
import errno
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from quickthumb import _exclusive_directory as exclusive
from quickthumb.errors import RenderingError

native_linux = pytest.mark.skipif(sys.platform != "linux", reason="Native Linux renameat2 test")
OCCUPANTS = ["file", "directory", "empty-directory", "live-symlink", "dangling-symlink"]


def _identity(path: Path) -> tuple[int, int]:
    info = path.lstat()
    return info.st_dev, info.st_ino


def _snapshot(path: Path):
    """Record entry identity and contents without following symbolic links."""
    info = path.lstat()
    identity = (info.st_dev, info.st_ino, info.st_mode)
    if path.is_symlink():
        return identity, os.readlink(path)
    if path.is_dir():
        return identity, tuple((child.name, _snapshot(child)) for child in sorted(path.iterdir()))
    return identity, path.read_bytes()


def _occupy(path: Path, kind: str) -> Path | None:
    target = None
    if kind == "file":
        path.write_bytes(b"existing output")
    elif kind in {"directory", "empty-directory"}:
        path.mkdir()
        if kind == "directory":
            (path / "keep.txt").write_bytes(b"existing directory")
    else:
        target = path.with_name("symlink-target")
        if kind == "live-symlink":
            target.mkdir()
            (target / "keep.txt").write_bytes(b"existing target")
        path.symlink_to(target, target_is_directory=True)
    return target


def _staging(parent: Path, name: str = "staging") -> Path:
    source = parent / name
    source.mkdir()
    (source / "frame.png").write_bytes(name.encode())
    return source


def _mock_platform(monkeypatch, platform: str) -> None:
    # Replace the module reference, leaving pytest's actual platform untouched.
    monkeypatch.setattr(exclusive, "sys", SimpleNamespace(platform=platform))


def _forbid_ordinary_rename(monkeypatch) -> None:
    for name in ["rename", "replace"]:
        monkeypatch.setattr(
            exclusive.os, name, Mock(side_effect=AssertionError("Unsafe rename fallback"))
        )


@pytest.mark.parametrize("as_string", [False, True])
def test_normalize_relative_path_resolves_only_existing_parent(tmp_path, monkeypatch, as_string):
    (tmp_path / "working").mkdir()
    (tmp_path / "output").mkdir()
    monkeypatch.chdir(tmp_path / "working")
    relative = Path("../output/frames")

    result = exclusive.normalize_destination(str(relative) if as_string else relative)

    assert result == tmp_path / "output" / "frames"
    assert result.is_absolute()
    assert not result.exists()


def test_normalize_symlink_parent_returns_resolved_parent(tmp_path):
    real_parent = tmp_path / "real"
    real_parent.mkdir()
    link = tmp_path / "linked-parent"
    link.symlink_to(real_parent, target_is_directory=True)

    assert exclusive.normalize_destination(link / "frames") == real_parent / "frames"
    assert not (real_parent / "frames").exists()
    assert link.is_symlink()


@pytest.mark.parametrize("kind", OCCUPANTS)
def test_normalize_rejects_every_occupied_final_component(tmp_path, kind):
    destination = tmp_path / "frames"
    target = _occupy(destination, kind)
    before = _snapshot(destination)
    target_before = _snapshot(target) if target is not None and target.exists() else None

    with pytest.raises(FileExistsError):
        exclusive.normalize_destination(destination)

    assert _snapshot(destination) == before
    if target_before is not None:
        assert target is not None
        assert _snapshot(target) == target_before
    if kind == "dangling-symlink":
        assert target is not None and not target.exists()


@pytest.mark.parametrize("parent_kind", ["missing", "file", "dangling-symlink"])
def test_normalize_requires_an_existing_directory_parent(tmp_path, parent_kind):
    parent = tmp_path / "parent"
    if parent_kind == "file":
        parent.write_bytes(b"not a directory")
    elif parent_kind == "dangling-symlink":
        parent.symlink_to(tmp_path / "absent", target_is_directory=True)

    with pytest.raises(OSError):
        exclusive.normalize_destination(parent / "frames")

    assert not (parent / "frames").exists()
    if parent_kind == "missing":
        assert not parent.exists()
    elif parent_kind == "file":
        assert parent.read_bytes() == b"not a directory"
    else:
        assert parent.is_symlink() and not parent.exists()


@native_linux
def test_native_linux_publication_moves_complete_directory_once(tmp_path):
    source = _staging(tmp_path, "staging-\N{SNOWMAN}")
    nested = source / "nested"
    nested.mkdir()
    (nested / "metadata.json").write_bytes(b"metadata")
    destination = exclusive.normalize_destination(tmp_path / "frames-\N{SNOWMAN}")
    before = _snapshot(source)

    exclusive.rename_exclusive(source, destination)

    assert not source.exists()
    assert _snapshot(destination) == before


@native_linux
@pytest.mark.parametrize("kind", OCCUPANTS)
def test_native_linux_preserves_destination_created_after_validation(tmp_path, kind):
    source = _staging(tmp_path)
    source_before = _snapshot(source)
    destination = exclusive.normalize_destination(tmp_path / "frames")
    # Simulate another publisher claiming the name after our absence check.
    target = _occupy(destination, kind)
    destination_before = _snapshot(destination)
    target_before = _snapshot(target) if target is not None and target.exists() else None

    with pytest.raises(OSError):
        exclusive.rename_exclusive(source, destination)

    assert _snapshot(source) == source_before
    assert _snapshot(destination) == destination_before
    if target_before is not None:
        assert target is not None
        assert _snapshot(target) == target_before
    if kind == "dangling-symlink":
        assert target is not None and not target.exists()


@native_linux
@pytest.mark.parametrize("attempt", range(4))
def test_native_linux_two_publishers_have_one_winner(tmp_path, attempt):
    sources = [_staging(tmp_path, f"publisher-{attempt}-{index}") for index in range(2)]
    before = {source: _snapshot(source) for source in sources}
    destination = tmp_path / "frames"
    ready = Barrier(2)

    def publish(source: Path) -> tuple[Path, bool]:
        normalized = exclusive.normalize_destination(destination)
        ready.wait(timeout=5)
        try:
            exclusive.rename_exclusive(source, normalized)
        except FileExistsError:
            return source, False
        return source, True

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(publish, source) for source in sources]
        results = [future.result(timeout=10) for future in futures]

    winners = [source for source, won in results if won]
    losers = [source for source, won in results if not won]
    assert len(winners) == len(losers) == 1
    assert not winners[0].exists()
    assert _snapshot(destination) == before[winners[0]]
    assert _snapshot(losers[0]) == before[losers[0]]
    assert set(tmp_path.iterdir()) == {destination, losers[0]}


@pytest.mark.parametrize("platform", ["linux", "darwin"])
def test_mocked_native_call_uses_exact_abi_and_exclusive_flag(tmp_path, monkeypatch, platform):
    source = _staging(tmp_path, "staging-\N{SNOWMAN}")
    destination = tmp_path / "frames-\N{SNOWMAN}"
    native = Mock(return_value=0)
    library = SimpleNamespace(renameat2=native, renamex_np=native)
    loader = Mock(return_value=library)
    monkeypatch.setattr(exclusive.ctypes, "CDLL", loader)
    _mock_platform(monkeypatch, platform)
    _forbid_ordinary_rename(monkeypatch)

    exclusive.rename_exclusive(source, destination)

    loader.assert_called_once_with(None, use_errno=True)
    assert native.restype is ctypes.c_int
    if platform == "linux":
        assert native.argtypes == [
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        ]
        native.assert_called_once_with(-100, os.fsencode(source), -100, os.fsencode(destination), 1)
    else:
        assert native.argtypes == [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
        native.assert_called_once_with(os.fsencode(source), os.fsencode(destination), 4)


@pytest.mark.parametrize("platform", ["freebsd14", "cygwin"])
def test_unsupported_platform_fails_without_fallback(tmp_path, monkeypatch, platform):
    source = _staging(tmp_path)
    destination = tmp_path / "frames"
    _mock_platform(monkeypatch, platform)
    _forbid_ordinary_rename(monkeypatch)
    loader = Mock(side_effect=AssertionError("Unsupported platform must not load libc"))
    monkeypatch.setattr(exclusive.ctypes, "CDLL", loader)

    with pytest.raises(RenderingError, match="unsupported"):
        exclusive.rename_exclusive(source, destination)

    loader.assert_not_called()
    assert (source / "frame.png").read_bytes() == b"staging"
    assert not destination.exists()


@pytest.mark.parametrize("platform", ["linux", "darwin"])
@pytest.mark.parametrize("failure", ["missing-symbol", "unloadable-library"])
def test_unavailable_native_primitive_fails_without_fallback(
    tmp_path, monkeypatch, platform, failure
):
    source = _staging(tmp_path)
    destination = tmp_path / "frames"
    _mock_platform(monkeypatch, platform)
    _forbid_ordinary_rename(monkeypatch)
    loader = Mock(return_value=SimpleNamespace())
    if failure == "unloadable-library":
        loader.side_effect = OSError("Cannot load libc")
    monkeypatch.setattr(exclusive.ctypes, "CDLL", loader)

    with pytest.raises(RenderingError, match="unavailable"):
        exclusive.rename_exclusive(source, destination)

    assert (source / "frame.png").read_bytes() == b"staging"
    assert not destination.exists()


@pytest.mark.parametrize("platform", ["linux", "darwin"])
@pytest.mark.parametrize(
    "error_code", sorted({errno.ENOSYS, errno.EINVAL, errno.ENOTSUP, errno.EOPNOTSUPP})
)
def test_unsupported_native_errno_fails_without_fallback(
    tmp_path, monkeypatch, platform, error_code
):
    source = _staging(tmp_path)
    destination = tmp_path / "frames"
    native = Mock(return_value=-1)
    monkeypatch.setattr(
        exclusive.ctypes,
        "CDLL",
        Mock(return_value=SimpleNamespace(renameat2=native, renamex_np=native)),
    )
    monkeypatch.setattr(exclusive.ctypes, "get_errno", Mock(return_value=error_code))
    _mock_platform(monkeypatch, platform)
    _forbid_ordinary_rename(monkeypatch)

    with pytest.raises(RenderingError, match="unsupported"):
        exclusive.rename_exclusive(source, destination)

    assert native.call_count == 1
    assert (source / "frame.png").read_bytes() == b"staging"
    assert not destination.exists()


@pytest.mark.parametrize("platform", ["linux", "darwin"])
@pytest.mark.parametrize("error_code", [errno.EEXIST, errno.EACCES, errno.EXDEV])
def test_native_filesystem_error_is_preserved_without_fallback(
    tmp_path, monkeypatch, platform, error_code
):
    source = _staging(tmp_path)
    destination = tmp_path / "frames"
    native = Mock(return_value=-1)
    monkeypatch.setattr(
        exclusive.ctypes,
        "CDLL",
        Mock(return_value=SimpleNamespace(renameat2=native, renamex_np=native)),
    )
    monkeypatch.setattr(exclusive.ctypes, "get_errno", Mock(return_value=error_code))
    _mock_platform(monkeypatch, platform)
    _forbid_ordinary_rename(monkeypatch)

    with pytest.raises(OSError) as caught:
        exclusive.rename_exclusive(source, destination)

    assert caught.value.errno == error_code
    assert caught.value.filename == str(destination)
    assert native.call_count == 1
    assert (source / "frame.png").read_bytes() == b"staging"
    assert not destination.exists()


@pytest.mark.parametrize("collision", [False, True])
def test_mocked_windows_dispatch_uses_os_rename_and_preserves_errors(
    tmp_path, monkeypatch, collision
):
    source = _staging(tmp_path)
    destination = tmp_path / "frames"
    error = FileExistsError(errno.EEXIST, "destination exists", str(destination))
    rename = Mock(side_effect=error if collision else None)
    _mock_platform(monkeypatch, "win32")
    monkeypatch.setattr(exclusive.os, "rename", rename)
    monkeypatch.setattr(exclusive.os, "replace", Mock(side_effect=AssertionError("Unsafe replace")))
    monkeypatch.setattr(
        exclusive.ctypes, "CDLL", Mock(side_effect=AssertionError("Windows must not load libc"))
    )

    if collision:
        with pytest.raises(FileExistsError) as caught:
            exclusive.rename_exclusive(source, destination)
        assert caught.value is error
    else:
        exclusive.rename_exclusive(source, destination)

    rename.assert_called_once_with(source, destination)


def test_cleanup_removes_only_owned_staging_and_does_not_follow_nested_links(tmp_path):
    staging = _staging(tmp_path)
    target = tmp_path / "external"
    target.mkdir()
    (target / "keep.txt").write_bytes(b"keep")
    (staging / "link").symlink_to(target, target_is_directory=True)
    before = _snapshot(target)

    exclusive.cleanup_owned_staging(staging, _identity(staging))

    assert not os.path.lexists(staging)
    assert _snapshot(target) == before


@pytest.mark.parametrize("replacement", ["directory", "symlink", "file"])
def test_cleanup_preserves_replacement_at_staging_path(tmp_path, replacement):
    staging = _staging(tmp_path)
    identity = _identity(staging)
    moved = tmp_path / "moved-original"
    staging.rename(moved)
    if replacement == "directory":
        staging.mkdir()
        (staging / "keep.txt").write_bytes(b"replacement directory")
    elif replacement == "symlink":
        # Following this link would report the original directory's identity.
        staging.symlink_to(moved, target_is_directory=True)
    else:
        staging.write_bytes(b"replacement file")
    replacement_before, original_before = _snapshot(staging), _snapshot(moved)

    exclusive.cleanup_owned_staging(staging, identity)

    assert _snapshot(staging) == replacement_before
    assert _snapshot(moved) == original_before


@pytest.mark.parametrize("changed_component", [0, 1])
def test_cleanup_requires_both_device_and_inode_match(tmp_path, changed_component):
    staging = _staging(tmp_path)
    identity = list(_identity(staging))
    identity[changed_component] += 1
    before = _snapshot(staging)

    exclusive.cleanup_owned_staging(staging, (identity[0], identity[1]))

    assert _snapshot(staging) == before


def test_cleanup_accepts_staging_already_missing(tmp_path):
    exclusive.cleanup_owned_staging(tmp_path / "missing", (0, 0))


@pytest.mark.parametrize("operation", ["lstat", "rmtree"])
def test_cleanup_io_failure_preserves_original_rendering_error(tmp_path, monkeypatch, operation):
    staging = _staging(tmp_path)
    identity = _identity(staging)
    original_error = RenderingError("frame rendering failed")
    failure = Mock(side_effect=PermissionError("cleanup denied"))
    if operation == "lstat":
        monkeypatch.setattr(Path, "lstat", failure)
    else:
        monkeypatch.setattr(exclusive.shutil, "rmtree", failure)

    with pytest.raises(RenderingError) as caught:
        try:
            raise original_error
        finally:
            exclusive.cleanup_owned_staging(staging, identity)

    assert caught.value is original_error
    failure.assert_called_once()
