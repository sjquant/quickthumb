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
import quickthumb
from PIL import Image, ImageSequence, UnidentifiedImageError
from quickthumb import Canvas, Deck

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "release_smoke.py"
_SPEC = importlib.util.spec_from_file_location("release_smoke", _SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
smoke = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(smoke)

FULL_EXTRAS = ("reportlab", "pptx", "cairosvg", "typer")
requires_full = pytest.mark.skipif(
    not all(importlib.util.find_spec(module) for module in FULL_EXTRAS)
    or shutil.which("ffmpeg") is None
    or shutil.which("ffprobe") is None,
    reason="full profile needs the release extras, ffmpeg, and ffprobe",
)


def test_canonical_exports_write_every_format(tmp_path):
    """Canonical document exports write every format and the per-slide SVG guidance.

    Given the canvas and deck fixtures
    When the canonical document checks run
    Then the GIF is written, deck SVG points to per-slide export, and samples are saved
    """
    details = smoke.check_documents(tmp_path)
    assert "deck.gif" in details
    assert "Render slides individually" in details["deck.svg"]["unsupported_guidance"]
    assert (tmp_path / "canvas-sample.json").is_file()
    assert (tmp_path / "deck-slide-1.svg").is_file()


@pytest.mark.parametrize(
    ("replace_page", "error", "message"),
    [
        pytest.param(
            lambda path: path.write_bytes(b"not a PNG"),
            UnidentifiedImageError,
            None,
            id="not-an-image",
        ),
        pytest.param(
            lambda path: path.write_bytes(path.with_name("deck_01.png").read_bytes()),
            AssertionError,
            "Wrong pixels",
            id="repeats-page-one",
        ),
    ],
)
def test_deck_png_page_two_that_is_corrupt_fails_export(
    tmp_path, monkeypatch, replace_page, error, message
):
    """A deck PNG export fails when its second page is not a distinct valid image.

    Given the second deck PNG page is replaced after the real export writes it
    When the canonical document checks run
    Then the check fails on that page
    """
    mutate_export(monkeypatch, "deck_02.png", replace_page)
    with pytest.raises(error, match=message):
        smoke.check_documents(tmp_path)


@pytest.mark.parametrize(
    ("corrupt", "error", "message"),
    [
        pytest.param(
            lambda path: path.unlink(), AssertionError, "Missing SVG output", id="missing"
        ),
        pytest.param(
            lambda path: path.write_text("not SVG", encoding="utf-8"),
            ET.ParseError,
            None,
            id="invalid-xml",
        ),
        pytest.param(
            lambda path: _set_svg_height(path, "1"),
            AssertionError,
            "SVG height",
            id="wrong-size",
        ),
        pytest.param(
            lambda path: path.write_text(
                '<notsvg width="128" height="96"><x/></notsvg>', encoding="utf-8"
            ),
            AssertionError,
            "Invalid SVG root",
            id="wrong-root",
        ),
    ],
)
def test_deck_svg_slide_that_is_corrupt_fails_export(
    tmp_path, monkeypatch, corrupt, error, message
):
    """A per-slide deck SVG export fails when the slide file is missing or malformed.

    Given the second slide's SVG is removed or rewritten after the real export
    When the canonical document checks run
    Then the check fails on that slide file
    """
    mutate_export(monkeypatch, "deck-slide-1.svg", corrupt)
    with pytest.raises(error, match=message):
        smoke.check_documents(tmp_path)


@pytest.mark.parametrize(
    ("filename", "mutate", "message"),
    [
        pytest.param(
            "canvas.html",
            lambda path: _edit_text(path, lambda text: text + "{{ title }}"),
            "Unexpanded HTML template",
            id="html-template",
        ),
        pytest.param(
            "canvas.html",
            lambda path: _edit_text(
                path, lambda text: text.replace('class="qt-stage"', 'class="qt-other"')
            ),
            "HTML stage count",
            id="html-stage-count",
        ),
        pytest.param(
            "canvas.html",
            lambda path: _edit_text(
                path, lambda text: text.replace(_resource("base.css").strip(), "")
            ),
            "Missing embedded base.css",
            id="html-base-css",
        ),
        pytest.param(
            "canvas.html",
            lambda path: _edit_text(
                path, lambda text: text.replace(_runtime("canvas_runtime.js"), "")
            ),
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
            lambda path: _touch_unsampled_pixel(path),
            "PNG differs from canonical settled sample",
            id="png-bytes",
        ),
    ],
)
def test_canonical_document_output_mutations_fail_export(
    tmp_path, monkeypatch, filename, mutate, message
):
    """A canonical document export fails when its HTML, GIF, or PNG output is wrong.

    Given one exported document is altered after the real export writes it
    When the canonical document checks run
    Then the check fails with the message for that alteration
    """
    mutate_export(monkeypatch, filename, mutate)
    with pytest.raises(AssertionError, match=message):
        smoke.check_documents(tmp_path)


def test_blank_frame_fails_pixel_check():
    """The pixel check rejects a blank frame that lacks the expected colours.

    Given an all-white image at the output size
    When the pixel check runs
    Then it fails reporting wrong pixels
    """
    with pytest.raises(AssertionError, match="Wrong pixels"):
        smoke.assert_pixels(Image.new("RGB", smoke.SIZE, "white"))


def test_guidance_check_rejects_unhelpful_or_missing_errors():
    """The guidance check fails both when an error lacks the hint and when no error occurs.

    Given an action that raises an error without the install hint
    And an action that raises no error
    When each is checked for the hint
    Then each fails with its own message
    """

    def broken():
        raise RuntimeError("module missing")

    with pytest.raises(AssertionError, match="Unhelpful error"):
        smoke.expect_guidance(broken, "quickthumb[pdf]")
    with pytest.raises(AssertionError, match="Expected failure"):
        smoke.expect_guidance(lambda: None, "quickthumb[pdf]")


def test_core_profile_reports_install_hints_without_extras(tmp_path, monkeypatch):
    """The core profile passes when the optional extras and the typer CLI are absent.

    Given the optional modules cannot be imported and the console script cannot import typer
    When the core profile runs
    Then each optional export and the CLI report their install hint
    """
    # A None entry in sys.modules makes an import fail the same way a missing extra does.
    for module in FULL_EXTRAS:
        monkeypatch.setitem(sys.modules, module, None)
    # The console script runs in a child process, so it only sees a file on PYTHONPATH.
    blocked = tmp_path / "blocked"
    blocked.mkdir()
    (blocked / "typer.py").write_text(
        'raise ImportError("typer is blocked for this test")\n', encoding="utf-8"
    )
    monkeypatch.setenv("PYTHONPATH", str(blocked))

    result = smoke.check_profile("core", tmp_path)

    assert set(result["guidance"]) == {"pdf", "pptx", "svg", "cli"}


def test_core_profile_rejects_installed_extras(tmp_path, monkeypatch):
    """The core profile refuses to run when any optional extra is installed.

    Given every optional module reports as installed
    When the core profile runs
    Then it fails before exporting, naming the absent-extras requirement
    """
    monkeypatch.setattr(smoke.importlib.util, "find_spec", lambda name: object())
    with pytest.raises(AssertionError, match="core needs absent extras"):
        smoke.check_profile("core", tmp_path)


def test_full_profile_rejects_missing_extras(tmp_path, monkeypatch):
    """The full profile refuses to run when an optional extra is missing.

    Given no optional module reports as installed
    When the full profile runs
    Then it fails before exporting, naming the present-extras requirement
    """
    monkeypatch.setattr(smoke.importlib.util, "find_spec", lambda name: None)
    with pytest.raises(AssertionError, match="full needs present extras"):
        smoke.check_profile("full", tmp_path)


def test_full_profile_rejects_missing_ffmpeg(tmp_path, monkeypatch):
    """The full profile stops before exporting when ffmpeg or ffprobe is not on PATH.

    Given no executable can be found on PATH
    When the full export checks run
    Then they fail naming ffmpeg and ffprobe
    """
    monkeypatch.setattr(smoke.shutil, "which", lambda name: None)
    with pytest.raises(AssertionError, match="requires ffmpeg and ffprobe"):
        smoke.check_full(tmp_path)


@requires_full
def test_full_profile_passes_on_real_outputs(tmp_path):
    """Every full-profile export passes its format checks on real output.

    Given the release extras and ffmpeg are installed
    When the full export checks run
    Then the PDF, PPTX, MP4, and WebM outputs are all reported
    """
    results = smoke.check_full(tmp_path)
    assert {"canvas.pdf", "deck.pdf", "deck.pptx", "deck.mp4", "deck.webm"} <= set(results)


@requires_full
@pytest.mark.parametrize(
    ("filename", "mutate", "message"),
    [
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
        pytest.param(
            "deck.pdf",
            lambda path: _drop_pdf_page(path),
            "PDF page count",
            id="pdf-pages",
        ),
        pytest.param(
            "deck.pptx",
            lambda path: _drop_pptx_slide(path),
            "PPTX slide count",
            id="pptx-slides",
        ),
        pytest.param(
            "deck.pptx",
            lambda path: _strip_pptx_shapes(path),
            "PPTX lost native geometry",
            id="pptx-geometry",
        ),
        pytest.param(
            "deck.mp4",
            lambda path: _reencode(path, "-t", "0.3", "-c", "copy"),
            "Video duration",
            id="mp4-duration",
        ),
        pytest.param(
            "deck.webm",
            lambda path: _reencode(path, "-t", "0.3", "-c", "copy"),
            "Video duration",
            id="webm-duration",
        ),
        pytest.param(
            "deck.mp4",
            lambda path: _reencode(path, "-vf", "scale=64:48", "-c:v", "libx264"),
            "Video dimensions",
            id="mp4-dimensions",
        ),
        pytest.param(
            "deck.mp4",
            lambda path: _reencode(path, "-c:v", "mpeg4"),
            "Video codec",
            id="mp4-codec",
        ),
        pytest.param(
            "deck.mp4",
            lambda path: _reencode(path, "-r", "20", "-c:v", "libx264"),
            "Video frame count",
            id="mp4-frame-count",
        ),
        pytest.param(
            "deck.mp4",
            lambda path: _reencode(
                path,
                "-vf",
                "drawbox=w=iw:h=ih:color=black:t=fill:enable='eq(n,0)'",
                "-c:v",
                "libx264",
            ),
            "Wrong pixels",
            id="mp4-first-frame-pixels",
        ),
    ],
)
def test_full_output_mutations_fail_export(tmp_path, monkeypatch, filename, mutate, message):
    """A full-profile export fails when its PDF, PPTX, or video output is malformed.

    Given one exported file is altered after the real export writes it
    When the full export checks run
    Then the check fails with the message for that alteration
    """
    mutate_export(monkeypatch, filename, mutate)
    with pytest.raises(AssertionError, match=message):
        smoke.check_full(tmp_path)


def test_profile_rejects_missing_console_entrypoint(tmp_path, monkeypatch):
    """The full profile fails when the installed quickthumb console script is absent.

    Given every optional module reports as installed
    And the interpreter's directory has no quickthumb script
    When the full profile runs
    Then it fails naming the missing console entry point
    """
    monkeypatch.setattr(smoke.importlib.util, "find_spec", lambda name: object())
    monkeypatch.setattr(smoke.sys, "executable", str(tmp_path / "python"))
    with pytest.raises(AssertionError, match="console entry point is missing"):
        smoke.check_profile("full", tmp_path)


def test_missing_ffmpeg_ignores_inherited_override(tmp_path, monkeypatch):
    """The missing-ffmpeg check reports ffmpeg as missing even when a parent override exists.

    Given the parent environment points QUICKTHUMB_FFMPEG at another executable
    When the isolated missing-ffmpeg check runs
    Then the child process still reports ffmpeg as missing with install guidance
    """
    # If the child inherited the override, quickthumb would run it and the export would
    # not fail with install guidance, so the isolation check would fail.
    monkeypatch.setenv("QUICKTHUMB_FFMPEG", sys.executable)
    assert smoke.check_missing_ffmpeg(tmp_path)["isolated_process"]


def test_main_reports_passed_when_every_check_passes(tmp_path, monkeypatch):
    """main exits 0 and marks the run passed when every check completes.

    Given each check returns without raising
    When main runs the core profile
    Then it returns 0 and the report marks every check and the run as passed
    """
    for check in ("check_profile", "check_documents", "check_missing_ffmpeg"):
        monkeypatch.setattr(smoke, check, lambda *args: {"ran": True})

    assert smoke.main(["--profile", "core", "--output", str(tmp_path)]) == 0
    report = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert report["status"] == "passed"
    assert [check["status"] for check in report["checks"]] == ["passed", "passed", "passed"]


def test_main_reports_failure_when_a_check_raises(tmp_path, monkeypatch):
    """main exits 1 and records the error when one check raises.

    Given check_profile raises an error
    When main runs the core profile
    Then it returns 1, records the error, and still records the checks that passed
    """

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
    assert Path(report["package_path"]) == Path(quickthumb.__file__).resolve()


def mutate_export(monkeypatch, filename, mutate):
    """Run `mutate(path)` on each written output named `filename` right after its export."""
    for owner in (Canvas, Deck):
        original = owner.export

        def export(self, output, *args, _original=original, **kwargs):
            result = _original(self, output, *args, **kwargs)
            for written in result.written_paths:
                if Path(written).name == filename:
                    mutate(Path(written))
            return result

        monkeypatch.setattr(owner, "export", export)


def _edit_text(path, edit):
    path.write_text(edit(path.read_text(encoding="utf-8")), encoding="utf-8")


def _resource(name):
    return importlib.resources.files("quickthumb.html").joinpath(name).read_text(encoding="utf-8")


def _runtime(name):
    # Mirrors how the smoke check embeds the runtime script into the HTML.
    return _resource(name).replace("{{ responsive }}", "true").strip()


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


def _set_svg_height(path, height):
    root = ET.fromstring(path.read_text(encoding="utf-8"))
    root.set("height", height)
    path.write_text(ET.tostring(root, encoding="unicode"), encoding="utf-8")


def _reencode(path, *options):
    reencoded = path.with_name(f"reencoded-{path.name}")
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(path), *options, str(reencoded)],
        check=True,
        capture_output=True,
        timeout=60,
    )
    reencoded.replace(path)


def _drop_pdf_page(path):
    path.write_bytes(re.sub(rb"/Type\s*/Page\b", b"/Type /Pagx", path.read_bytes(), count=1))


def _drop_pptx_slide(path):
    _rewrite_zip(path, lambda name, data: None if name == "ppt/slides/slide2.xml" else data)


EMPTY_SLIDE = (
    b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    b'<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
    b"<p:cSld><p:spTree/></p:cSld></p:sld>"
)


def _strip_pptx_shapes(path):
    _rewrite_zip(
        path,
        lambda name, data: (
            EMPTY_SLIDE if name.startswith("ppt/slides/slide") and name.endswith(".xml") else data
        ),
    )


def _rewrite_zip(path, edit):
    with zipfile.ZipFile(path) as archive:
        entries = [(info.filename, archive.read(info.filename)) for info in archive.infolist()]
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in entries:
            edited = edit(name, data)
            if edited is not None:
                archive.writestr(name, edited)
