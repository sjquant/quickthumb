"""Regression checks for the standalone installed-wheel release gate."""

import importlib.util
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from PIL import Image, UnidentifiedImageError
from quickthumb import Canvas, Deck

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


@pytest.mark.parametrize("corruption", ["invalid", "duplicate"])
def test_canonical_exports_reject_corrupt_second_deck_png(tmp_path, monkeypatch, corruption):
    original = Deck.export

    def export(self, output, *args, **kwargs):
        result = original(self, output, *args, **kwargs)
        if Path(output).suffix == ".png":
            first, second = (Path(path) for path in result.written_paths)
            second.write_bytes(b"not a PNG" if corruption == "invalid" else first.read_bytes())
        return result

    monkeypatch.setattr(Deck, "export", export)
    error = UnidentifiedImageError if corruption == "invalid" else AssertionError
    message = "cannot identify image file" if corruption == "invalid" else "Wrong pixels"
    with pytest.raises(error, match=message):
        smoke.check_documents(tmp_path)


@pytest.mark.parametrize("corruption", ["missing", "invalid", "wrong_size", "wrong_root"])
def test_canonical_exports_reject_broken_deck_svg(tmp_path, monkeypatch, corruption):
    original = Canvas.export

    def export(self, output, *args, **kwargs):
        result = original(self, output, *args, **kwargs)
        path = Path(output)
        if path.name == "deck-slide-1.svg":
            if corruption == "missing":
                path.unlink()
            elif corruption == "invalid":
                path.write_text("not SVG", encoding="utf-8")
            elif corruption == "wrong_root":
                path.write_text('<notsvg width="128" height="96"><x/></notsvg>', encoding="utf-8")
            else:
                root = ET.fromstring(path.read_text(encoding="utf-8"))
                root.set("height", "1")
                path.write_text(ET.tostring(root, encoding="unicode"), encoding="utf-8")
        return result

    monkeypatch.setattr(Canvas, "export", export)
    error = ET.ParseError if corruption == "invalid" else AssertionError
    message = {
        "missing": "Missing SVG output",
        "invalid": "syntax error",
        "wrong_size": "SVG height",
        "wrong_root": "Invalid SVG root",
    }[corruption]
    with pytest.raises(error, match=message):
        smoke.check_documents(tmp_path)


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
