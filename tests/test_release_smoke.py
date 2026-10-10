"""Regression checks for the standalone installed-wheel release gate."""

import importlib.resources
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import pytest
from PIL import Image, ImageSequence, UnidentifiedImageError
from quickthumb import Canvas, Deck

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "release_smoke.py"
_SPEC = importlib.util.spec_from_file_location("release_smoke", _SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
smoke = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(smoke)


def mutate_export(monkeypatch, filename, mutate):
    """Run `mutate(path)` on the named output right after the real export writes it."""
    for owner in (Canvas, Deck):
        original = owner.export

        def export(self, output, *args, _original=original, **kwargs):
            result = _original(self, output, *args, **kwargs)
            if Path(output).name == filename:
                mutate(Path(output))
            return result

        monkeypatch.setattr(owner, "export", export)


def _resource(name):
    return importlib.resources.files("quickthumb.html").joinpath(name).read_text(encoding="utf-8")


def _runtime(name):
    # Mirrors how the smoke check embeds the runtime script into the HTML.
    return _resource(name).replace("{{ responsive }}", "true").strip()


def _html(edit):
    return lambda path: path.write_text(edit(path.read_text(encoding="utf-8")), encoding="utf-8")


def _rewrite_gif(path, duration, keep=None):
    with Image.open(path) as image:
        frames = [frame.copy() for frame in ImageSequence.Iterator(image)]
    frames = frames[:keep]
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=duration, loop=0)


def _touch_unsampled_pixel(path):
    # (0, 0) is not a pixel the pixel check samples, so only the byte comparison catches this.
    with Image.open(path) as image:
        rgba = image.convert("RGBA")
    rgba.putpixel((0, 0), (1, 2, 3, 255))
    rgba.save(path)


def _drop_pdf_page(path):
    path.write_bytes(re.sub(rb"/Type\s*/Page\b", b"/Type /Pagx", path.read_bytes(), count=1))


def _rewrite_zip(path, edit):
    with zipfile.ZipFile(path) as archive:
        entries = [(info.filename, archive.read(info.filename)) for info in archive.infolist()]
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in entries:
            edited = edit(name, data)
            if edited is not None:
                archive.writestr(name, edited)


EMPTY_SLIDE = (
    b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    b'<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
    b"<p:cSld><p:spTree/></p:cSld></p:sld>"
)


def _drop_pptx_slide(path):
    _rewrite_zip(path, lambda name, data: None if name == "ppt/slides/slide2.xml" else data)


def _strip_pptx_shapes(path):
    _rewrite_zip(
        path,
        lambda name, data: (
            EMPTY_SLIDE if name.startswith("ppt/slides/slide") and name.endswith(".xml") else data
        ),
    )


def _trim_video(path, seconds):
    trimmed = path.with_name(f"trimmed-{path.name}")
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-i",
            str(path),
            "-t",
            str(seconds),
            "-c",
            "copy",
            str(trimmed),
        ],
        check=True,
        capture_output=True,
        timeout=60,
    )
    trimmed.replace(path)


def test_canonical_exports_and_timing(tmp_path):
    details = smoke.check_documents(tmp_path)
    assert "deck.gif" in details
    assert "Render slides individually" in details["deck.svg"]["unsupported_guidance"]
    assert (tmp_path / "canvas-sample.json").is_file()
    assert (tmp_path / "deck-slide-1.svg").is_file()


@pytest.mark.parametrize(
    ("corruption", "error", "message"),
    [("invalid", UnidentifiedImageError, None), ("duplicate", AssertionError, "Wrong pixels")],
)
def test_canonical_exports_reject_corrupt_second_deck_png(
    tmp_path, monkeypatch, corruption, error, message
):
    original = Deck.export

    def export(self, output, *args, **kwargs):
        result = original(self, output, *args, **kwargs)
        if Path(output).suffix == ".png":
            first, second = (Path(path) for path in result.written_paths)
            second.write_bytes(b"not a PNG" if corruption == "invalid" else first.read_bytes())
        return result

    monkeypatch.setattr(Deck, "export", export)
    with pytest.raises(error, match=message):
        smoke.check_documents(tmp_path)


@pytest.mark.parametrize(
    ("corruption", "error", "message"),
    [
        ("missing", AssertionError, "Missing SVG output"),
        ("invalid", ET.ParseError, None),
        ("wrong_size", AssertionError, "SVG height"),
        ("wrong_root", AssertionError, "Invalid SVG root"),
    ],
)
def test_canonical_exports_reject_broken_deck_svg(
    tmp_path, monkeypatch, corruption, error, message
):
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
    with pytest.raises(error, match=message):
        smoke.check_documents(tmp_path)


DOCUMENT_MUTATIONS = [
    pytest.param(
        "canvas.html",
        _html(lambda text: text + "{{ title }}"),
        "Unexpanded HTML template",
        id="html-template",
    ),
    pytest.param(
        "canvas.html",
        _html(lambda text: text.replace('class="qt-stage"', 'class="qt-other"')),
        "HTML stage count",
        id="html-stage-count",
    ),
    pytest.param(
        "canvas.html",
        _html(lambda text: text.replace(_resource("base.css").strip(), "")),
        "Missing embedded base.css",
        id="html-base-css",
    ),
    pytest.param(
        "canvas.html",
        _html(lambda text: text.replace(_runtime("canvas_runtime.js"), "")),
        "Missing embedded canvas_runtime.js",
        id="html-runtime",
    ),
    pytest.param(
        "deck.gif",
        lambda path: _rewrite_gif(path, duration=150),
        "GIF timing",
        id="deck-gif-timing",
    ),
    pytest.param(
        "canvas.gif",
        lambda path: _rewrite_gif(path, duration=200),
        "GIF timing",
        id="canvas-gif-timing",
    ),
    pytest.param(
        "deck.gif",
        lambda path: _rewrite_gif(path, duration=800, keep=1),
        "Deck GIF lost slide change",
        id="deck-gif-slide-change",
    ),
    pytest.param(
        "canvas.png",
        _touch_unsampled_pixel,
        "PNG differs from canonical settled sample",
        id="png-bytes",
    ),
]


@pytest.mark.parametrize(("filename", "mutate", "message"), DOCUMENT_MUTATIONS)
def test_canonical_exports_reject_broken_document_output(
    tmp_path, monkeypatch, filename, mutate, message
):
    mutate_export(monkeypatch, filename, mutate)
    with pytest.raises(AssertionError, match=message):
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


def test_core_guidance_names_each_missing_extra(tmp_path, monkeypatch):
    # A None entry in sys.modules makes the import fail the way a missing extra does.
    for module in ("reportlab", "pptx", "cairosvg"):
        monkeypatch.setitem(sys.modules, module, None)
    svg = tmp_path / "input.svg"
    svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="128" height="96"/>', encoding="utf-8"
    )
    assert set(smoke.core_guidance(tmp_path, svg)) == {"pdf", "pptx", "svg"}


def test_core_rejects_installed_extras(tmp_path, monkeypatch):
    # Test the guard, not simulated missing-dependency behavior. The CLI guidance is
    # exercised only in the fresh core wheel environment.
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


FULL_EXTRAS = ("reportlab", "pptx", "cairosvg", "typer")
requires_full = pytest.mark.skipif(
    not all(importlib.util.find_spec(module) for module in FULL_EXTRAS)
    or shutil.which("ffmpeg") is None
    or shutil.which("ffprobe") is None,
    reason="full profile needs the release extras, ffmpeg, and ffprobe",
)

FULL_MUTATIONS = [
    pytest.param(
        "deck.pdf",
        lambda path: path.write_bytes(b"BAD" + path.read_bytes()[3:]),
        "Invalid PDF envelope",
        id="pdf-signature",
    ),
    pytest.param(
        "deck.pdf",
        lambda path: path.write_bytes(path.read_bytes().replace(b"%%EOF", b"")),
        "Invalid PDF envelope",
        id="pdf-eof",
    ),
    pytest.param("deck.pdf", _drop_pdf_page, "PDF page count", id="pdf-pages"),
    pytest.param("deck.pptx", _drop_pptx_slide, "PPTX slide count", id="pptx-slides"),
    pytest.param("deck.pptx", _strip_pptx_shapes, "PPTX lost native geometry", id="pptx-geometry"),
    pytest.param(
        "deck.mp4", lambda path: _trim_video(path, 0.3), "Video duration", id="mp4-duration"
    ),
    pytest.param(
        "deck.webm", lambda path: _trim_video(path, 0.3), "Video duration", id="webm-duration"
    ),
]


@requires_full
def test_full_exports_pass_on_real_outputs(tmp_path):
    results = smoke.check_full(tmp_path)
    assert {"canvas.pdf", "deck.pdf", "deck.pptx", "deck.mp4", "deck.webm"} <= set(results)


@requires_full
@pytest.mark.parametrize(("filename", "mutate", "message"), FULL_MUTATIONS)
def test_full_exports_reject_broken_output(tmp_path, monkeypatch, filename, mutate, message):
    mutate_export(monkeypatch, filename, mutate)
    with pytest.raises(AssertionError, match=message):
        smoke.check_full(tmp_path)


def test_profile_rejects_missing_console_entrypoint(tmp_path, monkeypatch):
    monkeypatch.setattr(smoke.importlib.util, "find_spec", lambda name: object())
    monkeypatch.setattr(smoke.sys, "executable", str(tmp_path / "python"))
    with pytest.raises(AssertionError, match="console entry point is missing"):
        smoke.check_profile("full", tmp_path)


def test_missing_ffmpeg_ignores_inherited_override(tmp_path, monkeypatch):
    # If the child inherited this override, quickthumb would use it and the export
    # would not report ffmpeg as missing, so the isolation check would fail.
    monkeypatch.setenv("QUICKTHUMB_FFMPEG", sys.executable)
    assert smoke.check_missing_ffmpeg(tmp_path)["isolated_process"]


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
