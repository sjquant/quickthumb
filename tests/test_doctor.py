"""Tests for the environment readiness check, using a faked machine."""

import json

import pytest
from quickthumb._doctor import (
    WORKFLOWS,
    Environment,
    Requirements,
    check_environment,
    requirements_from_document,
)
from quickthumb.cli import app
from typer.testing import CliRunner

runner = CliRunner()


def _env(*, modules=(), tools=(), fonts=(), plugins=(), environ=None):
    return Environment(
        environ=environ or {},
        which=lambda name: f"/usr/bin/{name}" if name in tools else None,
        has_module=lambda name: name in modules,
        find_font=lambda family: f"/fonts/{family}.ttf" if family in fonts else None,
        registered_plugins=lambda: plugins,
    )


def _by_check(report):
    return {finding.check: finding for finding in report.findings}


def test_healthy_environment_has_no_findings_to_fix(tmp_path):
    env = _env(
        modules={"reportlab", "fontTools", "cairosvg"},
        tools={"ffmpeg", "ffprobe"},
        fonts={"Inter"},
        plugins=("chart",),
        environ={"QUICKTHUMB_ASSET_CACHE_DIR": str(tmp_path / "cache")},
    )
    report = check_environment(
        "pdf",
        Requirements(
            plugins=frozenset({"chart"}),
            fonts=frozenset({"Inter"}),
            svg_layers=True,
            remote_assets=True,
        ),
        output=tmp_path / "out" / "thumb.pdf",
        env=env,
    )

    assert report.ok
    assert report.errors == () and report.warnings == ()
    assert {f.status for f in report.findings} == {"ok"}


def test_incomplete_environment_separates_required_from_optional(tmp_path):
    (tmp_path / "blocked").write_text("a file, not a directory")
    report = check_environment(
        "pdf",
        Requirements(
            plugins=frozenset({"chart"}), fonts=frozenset({"Missing Sans"}), svg_layers=True
        ),
        output=tmp_path / "blocked" / "thumb.pdf",
        env=_env(),
    )

    findings = _by_check(report)
    assert not report.ok
    assert findings["python:reportlab"].status == "error"
    assert findings["python:fonttools"].status == "error"
    assert findings["python:cairosvg"].status == "error"
    assert findings["plugin:chart"].status == "error"
    assert findings["output"].status == "error"
    assert findings["font:Missing Sans"].status == "warning"
    assert all(f.remedy for f in report.findings if f.status != "ok")
    assert findings["python:reportlab"].remedy == "pip install 'quickthumb[pdf]'"


def test_video_tools_are_required_for_mp4_and_ffprobe_only_for_video_layers():
    without_tools = check_environment("mp4", env=_env())
    assert _by_check(without_tools)["tool:ffmpeg"].status == "error"
    assert _by_check(without_tools)["tool:ffprobe"].status == "warning"

    with_layers = check_environment(
        "mp4", Requirements(video_layers=True), env=_env(tools={"ffmpeg"})
    )
    assert _by_check(with_layers)["tool:ffmpeg"].status == "ok"
    assert _by_check(with_layers)["tool:ffprobe"].status == "error"


def test_configured_tool_path_is_honoured_and_reported_when_broken():
    env = _env(tools={"/opt/ff/ffmpeg"}, environ={"QUICKTHUMB_FFMPEG": "/opt/ff/ffmpeg"})
    assert _by_check(check_environment("webm", env=env))["tool:ffmpeg"].status == "ok"

    broken = _env(environ={"QUICKTHUMB_FFMPEG": "/nope/ffmpeg"})
    finding = _by_check(check_environment("webm", env=broken))["tool:ffmpeg"]
    assert finding.status == "error"
    assert "QUICKTHUMB_FFMPEG='/nope/ffmpeg'" in finding.message


def test_gif_without_ffmpeg_is_only_an_optional_limitation():
    report = check_environment("gif", env=_env())

    assert report.ok
    assert _by_check(report)["tool:ffmpeg"].status == "warning"


def test_raster_workflow_needs_nothing_optional():
    report = check_environment("png", env=_env())

    assert report.ok and report.findings == ()


def test_unusable_asset_cache_is_a_warning(tmp_path):
    (tmp_path / "file").write_text("x")
    env = _env(environ={"QUICKTHUMB_ASSET_CACHE_DIR": str(tmp_path / "file" / "cache")})

    finding = _by_check(check_environment("png", Requirements(remote_assets=True), env=env))[
        "asset-cache"
    ]

    assert finding.status == "warning"
    assert "QUICKTHUMB_ASSET_CACHE_DIR" in (finding.remedy or "")


def test_offline_mode_is_mentioned_for_a_healthy_cache(tmp_path):
    env = _env(
        environ={
            "QUICKTHUMB_ASSET_CACHE_DIR": str(tmp_path),
            "QUICKTHUMB_ASSET_OFFLINE": "1",
        }
    )

    finding = _by_check(check_environment("png", Requirements(remote_assets=True), env=env))[
        "asset-cache"
    ]

    assert finding.status == "ok" and "offline" in finding.message


def test_invalid_offline_setting_is_reported(tmp_path):
    env = _env(
        environ={"QUICKTHUMB_ASSET_CACHE_DIR": str(tmp_path), "QUICKTHUMB_ASSET_OFFLINE": "maybe"}
    )

    finding = _by_check(check_environment("png", Requirements(remote_assets=True), env=env))[
        "asset-cache"
    ]

    assert finding.status == "warning"
    assert "QUICKTHUMB_ASSET_OFFLINE" in finding.message


def test_output_directory_is_rejected(tmp_path):
    finding = _by_check(check_environment("png", output=tmp_path, env=_env()))["output"]

    assert finding.status == "error"


def test_check_does_not_create_the_output_directory(tmp_path):
    check_environment("png", output=tmp_path / "new" / "a.png", env=_env())

    assert not (tmp_path / "new").exists()


def test_unknown_workflow_is_rejected():
    with pytest.raises(ValueError, match="Unknown workflow 'tiff'"):
        check_environment("tiff", env=_env())


def test_workflow_name_is_case_insensitive():
    assert check_environment("PNG", env=_env()).workflow == "png"


def test_requirements_are_read_from_document_json():
    payload = {
        "kind": "deck",
        "slides": [
            {
                "layers": [
                    {"type": "plugin", "renderer": "chart", "version": "1"},
                    {"type": "svg", "font": "Inter"},
                    {"type": "video", "source": "https://example.com/a.mp4"},
                    {"type": "text", "font": "fonts/Local.ttf"},
                    {"type": "image", "remove_background": True},
                ]
            }
        ],
    }

    found = requirements_from_document(payload)

    assert found == Requirements(
        plugins=frozenset({"chart"}),
        fonts=frozenset({"Inter"}),
        svg_layers=True,
        video_layers=True,
        background_removal=True,
        remote_assets=True,
    )


def test_report_serialises_to_json_and_text():
    report = check_environment("pptx", env=_env())

    payload = report.to_dict()
    assert payload["ok"] is False
    assert payload["findings"][0]["remedy"] == "pip install 'quickthumb[pptx]'"
    assert "NOT ready: 1 required failure(s)" in report.format()
    assert "fix: pip install 'quickthumb[pptx]'" in report.format()


def test_every_workflow_can_be_checked():
    for workflow in WORKFLOWS:
        assert check_environment(workflow, env=_env()).workflow == workflow


def test_cli_reports_json_and_exit_code(tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", str(tmp_path))
    monkeypatch.delenv("QUICKTHUMB_FFMPEG", raising=False)

    result = runner.invoke(app, ["doctor", "mp4", "--format", "json"])

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert any(f["check"] == "tool:ffmpeg" and f["status"] == "error" for f in payload["findings"])


def test_cli_healthy_png_check_exits_zero(tmp_path):
    result = runner.invoke(app, ["doctor", "png", "-o", str(tmp_path / "a.png")])

    assert result.exit_code == 0, result.output
    assert "ready: 0 required failure(s)" in result.output


def test_cli_reads_requirements_from_a_spec(tmp_path):
    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps({"layers": [{"type": "plugin", "renderer": "unregistered-x"}]}))

    result = runner.invoke(app, ["doctor", "png", "--spec", str(spec)])

    assert result.exit_code == 1
    assert "plugin renderer 'unregistered-x' is not registered" in result.output


def test_cli_rejects_bad_workflow_and_unreadable_spec(tmp_path):
    bad = runner.invoke(app, ["doctor", "tiff"])
    missing = runner.invoke(app, ["doctor", "png", "--spec", str(tmp_path / "none.json")])

    assert bad.exit_code == 1 and "Unknown workflow" in bad.output
    assert missing.exit_code == 1
