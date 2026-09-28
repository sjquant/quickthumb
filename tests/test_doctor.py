"""Tests for the environment readiness check, using a faked machine"""

import json

import pytest
from typer.testing import CliRunner


def _env(*, modules=(), tools=(), fonts=(), plugins=(), environ=None):
    from quickthumb._doctor import Environment

    return Environment(
        environ=environ or {},
        which=lambda name: f"/usr/bin/{name}" if name in tools else None,
        has_module=lambda name: name in modules,
        find_font=lambda family: f"/fonts/{family}.ttf" if family in fonts else None,
        registered_plugins=lambda: plugins,
    )


def _by_check(report):
    return {finding.check: finding for finding in report.findings}


class TestCheckEnvironment:
    """Test suite for check_environment findings"""

    def test_should_report_healthy_environment_without_findings_to_fix(self, tmp_path):
        """a fully provisioned environment yields only ok findings"""
        # given: every module, tool, font, and plugin the workflow needs, plus a writable cache
        from quickthumb._doctor import Requirements, check_environment

        env = _env(
            modules={"reportlab", "fontTools", "cairosvg"},
            tools={"ffmpeg", "ffprobe"},
            fonts={"Inter"},
            plugins=("chart",),
            environ={"QUICKTHUMB_ASSET_CACHE_DIR": str(tmp_path / "cache")},
        )
        requirements = Requirements(
            plugins=frozenset({"chart"}),
            fonts=frozenset({"Inter"}),
            svg_layers=True,
            remote_assets=True,
        )

        # when: a PDF export is checked
        report = check_environment(
            "pdf", requirements, output=tmp_path / "out" / "thumb.pdf", env=env
        )

        # then: nothing needs fixing
        assert report.ok
        assert report.errors == ()
        assert report.warnings == ()
        assert {finding.status for finding in report.findings} == {"ok"}

    def test_should_separate_required_failures_from_optional_limitations(self, tmp_path):
        """missing packages, plugins, and output are errors; a missing font is a warning"""
        # given: an empty machine and an output path below a regular file
        from quickthumb._doctor import Requirements, check_environment

        (tmp_path / "blocked").write_text("a file, not a directory")
        requirements = Requirements(
            plugins=frozenset({"chart"}), fonts=frozenset({"Missing Sans"}), svg_layers=True
        )

        # when: a PDF export is checked
        report = check_environment(
            "pdf", requirements, output=tmp_path / "blocked" / "thumb.pdf", env=_env()
        )

        # then: required failures are errors and every non-ok finding has a remedy
        findings = _by_check(report)
        assert not report.ok
        assert findings["python:reportlab"].status == "error"
        assert findings["python:fonttools"].status == "error"
        assert findings["python:cairosvg"].status == "error"
        assert findings["plugin:chart"].status == "error"
        assert findings["output"].status == "error"
        assert findings["font:Missing Sans"].status == "warning"
        assert all(finding.remedy for finding in report.findings if finding.status != "ok")
        assert findings["python:reportlab"].remedy == "pip install 'quickthumb[pdf]'"

    def test_should_require_ffprobe_only_for_video_layers(self):
        """canvas MP4 needs ffmpeg; ffprobe is required once video layers are present"""
        # given: a machine without FFmpeg, then one with only ffmpeg
        from quickthumb._doctor import Requirements, check_environment

        # when: MP4 is checked without tools and with video layers but no ffprobe
        without_tools = _by_check(check_environment("mp4", env=_env()))
        with_layers = _by_check(
            check_environment("mp4", Requirements(video_layers=True), env=_env(tools={"ffmpeg"}))
        )

        # then: ffprobe is optional without video layers and required with them
        assert without_tools["tool:ffmpeg"].status == "error"
        assert without_tools["tool:ffprobe"].status == "warning"
        assert with_layers["tool:ffmpeg"].status == "ok"
        assert with_layers["tool:ffprobe"].status == "error"

    def test_should_honour_configured_tool_path(self):
        """QUICKTHUMB_FFMPEG overrides PATH and a broken override is named in the finding"""
        # given: a working override and a broken one
        from quickthumb._doctor import check_environment

        working = _env(tools={"/opt/ff/ffmpeg"}, environ={"QUICKTHUMB_FFMPEG": "/opt/ff/ffmpeg"})
        broken = _env(environ={"QUICKTHUMB_FFMPEG": "/nope/ffmpeg"})

        # when: WebM is checked with each
        ok = _by_check(check_environment("webm", env=working))["tool:ffmpeg"]
        failed = _by_check(check_environment("webm", env=broken))["tool:ffmpeg"]

        # then: the working one is ok and the broken one names the setting
        assert ok.status == "ok"
        assert failed.status == "error"
        assert "QUICKTHUMB_FFMPEG='/nope/ffmpeg'" in failed.message

    def test_should_treat_missing_ffmpeg_as_optional_for_gif(self):
        """GIF export works without ffmpeg, so its absence is only a warning"""
        # given: a machine without FFmpeg
        from quickthumb._doctor import check_environment

        # when: GIF is checked
        report = check_environment("gif", env=_env())

        # then: the environment is ready with an optional limitation
        assert report.ok
        assert _by_check(report)["tool:ffmpeg"].status == "warning"

    def test_should_need_nothing_optional_for_raster_output(self):
        """PNG export has no optional requirements"""
        # given: an empty machine
        from quickthumb._doctor import check_environment

        # when: PNG is checked
        report = check_environment("png", env=_env())

        # then: there is nothing to report
        assert report.ok
        assert report.findings == ()

    def test_should_warn_when_asset_cache_is_unusable(self, tmp_path):
        """an unwritable asset cache is an optional limitation with a remedy"""
        # given: a cache directory below a regular file
        from quickthumb._doctor import Requirements, check_environment

        (tmp_path / "file").write_text("x")
        env = _env(environ={"QUICKTHUMB_ASSET_CACHE_DIR": str(tmp_path / "file" / "cache")})

        # when: remote assets are checked
        finding = _by_check(check_environment("png", Requirements(remote_assets=True), env=env))[
            "asset-cache"
        ]

        # then: it warns and points at the cache setting
        assert finding.status == "warning"
        assert "QUICKTHUMB_ASSET_CACHE_DIR" in (finding.remedy or "")

    def test_should_mention_offline_mode_for_healthy_cache(self, tmp_path):
        """offline mode is reported alongside a writable cache"""
        # given: a writable cache with offline mode enabled
        from quickthumb._doctor import Requirements, check_environment

        env = _env(
            environ={
                "QUICKTHUMB_ASSET_CACHE_DIR": str(tmp_path),
                "QUICKTHUMB_ASSET_OFFLINE": "1",
            }
        )

        # when: remote assets are checked
        finding = _by_check(check_environment("png", Requirements(remote_assets=True), env=env))[
            "asset-cache"
        ]

        # then: the finding is ok and mentions offline mode
        assert finding.status == "ok"
        assert "offline" in finding.message

    def test_should_report_invalid_offline_setting(self, tmp_path):
        """an invalid QUICKTHUMB_ASSET_OFFLINE is surfaced instead of ignored"""
        # given: a writable cache with an invalid offline value
        from quickthumb._doctor import Requirements, check_environment

        env = _env(
            environ={
                "QUICKTHUMB_ASSET_CACHE_DIR": str(tmp_path),
                "QUICKTHUMB_ASSET_OFFLINE": "maybe",
            }
        )

        # when: remote assets are checked
        finding = _by_check(check_environment("png", Requirements(remote_assets=True), env=env))[
            "asset-cache"
        ]

        # then: the finding is a warning that names the setting
        assert finding.status == "warning"
        assert "QUICKTHUMB_ASSET_OFFLINE" in finding.message

    def test_should_reject_directory_as_output(self, tmp_path):
        """the output path must be a file, not a directory"""
        # given: an existing directory as the output path
        from quickthumb._doctor import check_environment

        # when: the output is checked
        finding = _by_check(check_environment("png", output=tmp_path, env=_env()))["output"]

        # then: it is a required failure
        assert finding.status == "error"

    def test_should_not_create_output_directory(self, tmp_path):
        """the check has no side effects on the filesystem"""
        # given: an output path in a directory that does not exist
        from quickthumb._doctor import check_environment

        # when: the output is checked
        check_environment("png", output=tmp_path / "new" / "a.png", env=_env())

        # then: the directory was not created
        assert not (tmp_path / "new").exists()

    def test_should_reject_unknown_workflow(self):
        """an unsupported workflow raises a ValueError listing the valid ones"""
        # given: a workflow name that is not supported
        from quickthumb._doctor import check_environment

        # when / then: checking it raises
        with pytest.raises(ValueError, match="Unknown workflow 'tiff'"):
            check_environment("tiff", env=_env())

    def test_should_accept_workflow_case_insensitively(self):
        """workflow names are normalised to lower case"""
        # given: an upper-case workflow name
        from quickthumb._doctor import check_environment

        # when: it is checked
        report = check_environment("PNG", env=_env())

        # then: the report uses the normalised name
        assert report.workflow == "png"

    def test_should_check_every_supported_workflow(self):
        """every advertised workflow can be checked"""
        # given: the supported workflow names
        from quickthumb._doctor import WORKFLOWS, check_environment

        # when / then: each one produces a report
        for workflow in WORKFLOWS:
            assert check_environment(workflow, env=_env()).workflow == workflow


class TestRequirementsFromDocument:
    """Test suite for deriving requirements from document JSON"""

    def test_should_collect_requirements_from_nested_layers(self):
        """plugins, fonts, layer kinds, and remote assets are found at any depth"""
        # given: a deck using each requirement-bearing layer
        from quickthumb._doctor import Requirements, requirements_from_document

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

        # when: requirements are derived
        found = requirements_from_document(payload)

        # then: file-path fonts are ignored and everything else is reported
        assert found == Requirements(
            plugins=frozenset({"chart"}),
            fonts=frozenset({"Inter"}),
            svg_layers=True,
            video_layers=True,
            background_removal=True,
            remote_assets=True,
        )


class TestEnvironmentReport:
    """Test suite for report serialisation"""

    def test_should_serialise_to_json_and_text(self):
        """a report renders as a dict and as human-readable text with remedies"""
        # given: a PPTX check on a machine without python-pptx
        from quickthumb._doctor import check_environment

        report = check_environment("pptx", env=_env())

        # when: it is serialised
        payload = report.to_dict()
        text = report.format()

        # then: both forms carry the failure and its remedy
        assert payload["ok"] is False
        assert payload["findings"][0]["remedy"] == "pip install 'quickthumb[pptx]'"
        assert "NOT ready: 1 required failure(s)" in text
        assert "fix: pip install 'quickthumb[pptx]'" in text


class TestDoctorCLI:
    """Test suite for the quickthumb doctor subcommand"""

    def test_should_exit_one_and_print_json_for_required_failure(self, tmp_path, monkeypatch):
        """doctor --format json reports failures and exits 1"""
        # given: a PATH without ffmpeg
        from quickthumb.cli import app

        monkeypatch.setenv("PATH", str(tmp_path))
        monkeypatch.delenv("QUICKTHUMB_FFMPEG", raising=False)

        # when: MP4 is checked
        result = CliRunner().invoke(app, ["doctor", "mp4", "--format", "json"])

        # then: the JSON payload names the failed tool and the exit code is 1
        assert result.exit_code == 1
        payload = json.loads(result.output)
        assert payload["ok"] is False
        assert any(
            finding["check"] == "tool:ffmpeg" and finding["status"] == "error"
            for finding in payload["findings"]
        )

    def test_should_exit_zero_for_ready_workflow(self, tmp_path):
        """doctor exits 0 when no required check fails"""
        # given: a writable output path for a raster workflow
        from quickthumb.cli import app

        # when: PNG is checked
        result = CliRunner().invoke(app, ["doctor", "png", "-o", str(tmp_path / "a.png")])

        # then: the environment is ready
        assert result.exit_code == 0, result.output
        assert "ready: 0 required failure(s)" in result.output

    def test_should_read_requirements_from_spec(self, tmp_path):
        """--spec adds the spec's plugin renderers to the checks"""
        # given: a spec that uses an unregistered plugin
        from quickthumb.cli import app

        spec = tmp_path / "spec.json"
        spec.write_text(json.dumps({"layers": [{"type": "plugin", "renderer": "unregistered-x"}]}))

        # when: doctor is run with the spec
        result = CliRunner().invoke(app, ["doctor", "png", "--spec", str(spec)])

        # then: the missing plugin is a required failure
        assert result.exit_code == 1
        assert "plugin renderer 'unregistered-x' is not registered" in result.output

    def test_should_reject_unknown_workflow_and_unreadable_spec(self, tmp_path):
        """invalid input exits 1 with an explanation"""
        # given: the CLI runner
        from quickthumb.cli import app

        runner = CliRunner()

        # when: an unknown workflow and a missing spec are given
        bad_workflow = runner.invoke(app, ["doctor", "tiff"])
        missing_spec = runner.invoke(app, ["doctor", "png", "--spec", str(tmp_path / "none.json")])

        # then: both fail with exit code 1
        assert bad_workflow.exit_code == 1
        assert "Unknown workflow" in bad_workflow.output
        assert missing_spec.exit_code == 1
