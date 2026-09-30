"""Regression checks for the standalone installed-wheel release gate."""

import importlib.util
import json
from pathlib import Path

import pytest
from PIL import Image

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "release_smoke.py"
_SPEC = importlib.util.spec_from_file_location("release_smoke", _SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
smoke = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(smoke)


def test_canonical_exports_and_timing(tmp_path):
    details = smoke.check_documents(tmp_path)
    assert "deck.gif" in details
    assert "Render slides individually" in details["deck.svg"]["unsupported_guidance"]
    assert (tmp_path / "canvas-sample.json").is_file()
    assert (tmp_path / "deck-slide-1.svg").is_file()


def test_pixel_check_rejects_blank_output():
    with pytest.raises(AssertionError, match="Wrong pixels"):
        smoke.assert_pixels(Image.new("RGB", smoke.SIZE, "white"))


def test_guidance_must_be_actionable():
    def broken():
        raise RuntimeError("module missing")

    with pytest.raises(AssertionError, match="Unhelpful error"):
        smoke.expect_guidance(broken, "quickthumb[pdf]")
    with pytest.raises(AssertionError, match="Expected failure"):
        smoke.expect_guidance(lambda: None, "quickthumb[pdf]")


def test_core_rejects_installed_extras(tmp_path, monkeypatch):
    # Test the guard, not simulated missing-dependency behavior. The actual
    # missing imports are exercised only in the fresh core wheel environment.
    monkeypatch.setattr(smoke.importlib.util, "find_spec", lambda name: object())
    with pytest.raises(AssertionError, match="core needs absent extras"):
        smoke.check_profile("core", tmp_path)


def test_full_rejects_missing_extras(tmp_path, monkeypatch):
    monkeypatch.setattr(smoke.importlib.util, "find_spec", lambda name: None)
    with pytest.raises(AssertionError, match="full needs present extras"):
        smoke.check_profile("full", tmp_path)


def test_full_rejects_missing_ffmpeg(tmp_path, monkeypatch):
    monkeypatch.setattr(smoke.shutil, "which", lambda name: None)
    with pytest.raises(AssertionError, match="requires ffmpeg and ffprobe"):
        smoke.check_full(tmp_path)


def test_profile_rejects_missing_console_entrypoint(tmp_path, monkeypatch):
    monkeypatch.setattr(smoke.importlib.util, "find_spec", lambda name: object())
    monkeypatch.setattr(smoke.sys, "executable", str(tmp_path / "python"))
    with pytest.raises(AssertionError, match="console entry point is missing"):
        smoke.check_profile("full", tmp_path)


def test_missing_ffmpeg_isolated_from_parent_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("QUICKTHUMB_FFMPEG", "/parent/ffmpeg")
    result = smoke.check_missing_ffmpeg(tmp_path)
    assert result["isolated_process"]
    assert smoke.os.environ["QUICKTHUMB_FFMPEG"] == "/parent/ffmpeg"


def test_failed_check_writes_report_and_returns_nonzero(tmp_path, monkeypatch):
    def broken(*args):
        raise RuntimeError("broken wheel")

    monkeypatch.setattr(smoke, "check_profile", broken)
    monkeypatch.setattr(smoke, "check_documents", lambda *args: {"ran": True})
    monkeypatch.setattr(smoke, "check_missing_ffmpeg", lambda *args: {"ran": True})
    assert smoke.main(["--profile", "core", "--output", str(tmp_path)]) == 1
    report = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert report["status"] == "failed"
    assert report["checks"][0]["error"] == "RuntimeError: broken wheel"
    assert report["checks"][1]["status"] == "passed"
    assert report["package_path"]
