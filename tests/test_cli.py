"""Tests for the quickthumb CLI"""

import json
import os
import tempfile

import pytest
from typer.testing import CliRunner

SIMPLE_SPEC = json.dumps(
    {
        "width": 100,
        "height": 100,
        "layers": [{"type": "background", "color": "#FF0000"}],
    }
)


@pytest.fixture
def spec_file():
    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
        f.write(SIMPLE_SPEC)
        f.flush()
    yield f.name
    os.unlink(f.name)


class TestCLIRender:
    def test_should_render_to_default_output(self, spec_file):
        """Test that render writes output.png in the current directory by default"""
        # Given: A valid spec file and no -o flag
        from quickthumb.cli import app

        runner = CliRunner()

        # When: User runs `quickthumb render spec.json`
        with runner.isolated_filesystem():
            result = runner.invoke(app, ["render", spec_file])

            # Then: output.png is created and the command exits successfully
            assert result.exit_code == 0
            assert os.path.exists("output.png")

    def test_should_render_to_custom_output_path(self, spec_file):
        """Test that -o flag writes to the specified output path"""
        # Given: A valid spec file and a custom output path
        from quickthumb.cli import app

        runner = CliRunner()

        # When: User runs `quickthumb render spec.json -o thumb.png`
        with runner.isolated_filesystem():
            result = runner.invoke(app, ["render", spec_file, "-o", "thumb.png"])

            # Then: thumb.png is created and the command exits successfully
            assert result.exit_code == 0
            assert os.path.exists("thumb.png")

    def test_should_infer_format_from_output_extension(self, spec_file):
        """Test that output format is inferred from the file extension when --format is omitted"""
        # Given: A valid spec file and a .webp output path
        from PIL import Image
        from quickthumb.cli import app

        runner = CliRunner()

        # When: User runs `quickthumb render spec.json -o thumb.webp`
        with runner.isolated_filesystem():
            result = runner.invoke(app, ["render", spec_file, "-o", "thumb.webp"])

            # Then: The output file is a WEBP image
            assert result.exit_code == 0
            img = Image.open("thumb.webp")
            assert img.format == "WEBP"

    def test_should_use_explicit_format_flag(self, spec_file):
        """Test that --format overrides the format inferred from the output extension"""
        # Given: A valid spec file and a .png output path with --format JPEG
        from PIL import Image
        from quickthumb.cli import app

        runner = CliRunner()

        # When: User runs `quickthumb render spec.json -o thumb.png --format JPEG`
        with runner.isolated_filesystem():
            result = runner.invoke(
                app, ["render", spec_file, "-o", "thumb.png", "--format", "JPEG"]
            )

            # Then: The output file is a JPEG image despite the .png extension
            assert result.exit_code == 0
            img = Image.open("thumb.png")
            assert img.format == "JPEG"

    def test_should_accept_quality_flag(self, spec_file):
        """Test that --quality flag is accepted and the output file is created"""
        # Given: A valid spec file and --quality 80
        from quickthumb.cli import app

        runner = CliRunner()

        # When: User runs `quickthumb render spec.json -o thumb.jpg --quality 80`
        with runner.isolated_filesystem():
            result = runner.invoke(app, ["render", spec_file, "-o", "thumb.jpg", "--quality", "80"])

            # Then: thumb.jpg is created and the command exits successfully
            assert result.exit_code == 0
            assert os.path.exists("thumb.jpg")

    def test_should_print_output_path_on_success(self, spec_file):
        """Test that the output file path is printed to stdout on success"""
        # Given: A valid spec file and a custom output path
        from quickthumb.cli import app

        runner = CliRunner()

        # When: User runs `quickthumb render spec.json -o thumb.png`
        with runner.isolated_filesystem():
            result = runner.invoke(app, ["render", spec_file, "-o", "thumb.png"])

            # Then: The output path is printed to stdout
            assert "thumb.png" in result.output

    def test_should_exit_1_on_validation_error(self):
        """Test that exit code 1 is returned when the spec JSON is invalid"""
        # Given: A spec file with an invalid layers value
        from quickthumb.cli import app

        runner = CliRunner()
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            f.write('{"width": 100, "height": 100, "layers": "INVALID"}')
            bad_spec = f.name

        # When: User runs `quickthumb render` with the invalid spec
        try:
            with runner.isolated_filesystem():
                result = runner.invoke(app, ["render", bad_spec])

            # Then: Exit code is 1 (ValidationError)
            assert result.exit_code == 1
        finally:
            os.unlink(bad_spec)

    def test_should_exit_2_on_rendering_error(self):
        """Test that exit code 2 is returned when rendering fails (e.g. unreachable image URL)"""
        # Given: A spec with a background image at an invalid URL
        from quickthumb.cli import app

        runner = CliRunner()
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            f.write(
                json.dumps(
                    {
                        "width": 100,
                        "height": 100,
                        "layers": [
                            {
                                "type": "background",
                                "image": "https://does-not-exist.invalid/img.png",
                            }
                        ],
                    }
                )
            )
            bad_spec = f.name

        # When: User runs `quickthumb render` with the unreachable image spec
        try:
            with runner.isolated_filesystem():
                result = runner.invoke(app, ["render", bad_spec])

            # Then: Exit code is 2 (RenderingError)
            assert result.exit_code == 2
        finally:
            os.unlink(bad_spec)

    def test_should_substitute_var_placeholders(self):
        """Test that --var KEY=VALUE substitutes $KEY placeholders in the spec before parsing"""
        # Given: A spec template using $bg_color and a --var flag
        from quickthumb.cli import app

        template_spec = json.dumps(
            {
                "width": 100,
                "height": 100,
                "layers": [{"type": "background", "color": "$bg_color"}],
            }
        )
        runner = CliRunner()
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            f.write(template_spec)
            spec_path = f.name

        # When: User runs `quickthumb render template.json --var bg_color=#00FF00`
        try:
            with runner.isolated_filesystem():
                result = runner.invoke(app, ["render", spec_path, "--var", "bg_color=#00FF00"])

                # Then: The placeholder is replaced and the image renders successfully
                assert result.exit_code == 0
                assert os.path.exists("output.png")
        finally:
            os.unlink(spec_path)

    def test_should_exit_1_on_missing_spec_file(self):
        """Test that exit code 1 is returned when the spec file does not exist"""
        # Given: A path to a non-existent spec file
        from quickthumb.cli import app

        runner = CliRunner()

        # When: User runs `quickthumb render` with a missing file
        with runner.isolated_filesystem():
            result = runner.invoke(app, ["render", "does_not_exist.json"])

        # Then: Exit code is 1 with a clear error message
        assert result.exit_code == 1
        assert "does_not_exist.json" in result.output

    def test_should_exit_1_on_malformed_json(self):
        """Test that exit code 1 is returned when the spec file contains malformed JSON"""
        # Given: A spec file with broken JSON
        from quickthumb.cli import app

        runner = CliRunner()
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            f.write("{ not valid json }")
            bad_spec = f.name

        # When: User runs `quickthumb render` with the malformed spec
        try:
            with runner.isolated_filesystem():
                result = runner.invoke(app, ["render", bad_spec])

            # Then: Exit code is 1
            assert result.exit_code == 1
        finally:
            os.unlink(bad_spec)

    def test_should_exit_1_on_unresolved_placeholder(self):
        """Test that exit code 1 is returned when a $VAR placeholder has no matching --var"""
        # Given: A spec template with an unresolved placeholder
        from quickthumb.cli import app

        template_spec = json.dumps(
            {
                "width": 100,
                "height": 100,
                "layers": [{"type": "background", "color": "$missing_var"}],
            }
        )
        runner = CliRunner()
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            f.write(template_spec)
            spec_path = f.name

        # When: User runs render without providing the required variable
        try:
            with runner.isolated_filesystem():
                result = runner.invoke(app, ["render", spec_path])

            # Then: Exit code is 1 with a message about the unresolved placeholder
            assert result.exit_code == 1
            assert "missing_var" in result.output
        finally:
            os.unlink(spec_path)

    def test_should_exit_1_on_var_without_equals(self, spec_file):
        """Test that exit code 1 is returned when --var is passed without an = sign"""
        # Given: A valid spec file and a malformed --var value
        from quickthumb.cli import app

        runner = CliRunner()

        # When: User runs `quickthumb render spec.json --var keyonly`
        with runner.isolated_filesystem():
            result = runner.invoke(app, ["render", spec_file, "--var", "keyonly"])

        # Then: Exit code is 1 with a clear error message
        assert result.exit_code == 1
        assert "keyonly" in result.output

    def test_should_exit_1_on_invalid_format(self, spec_file):
        """Test that exit code 1 is returned when --format is not PNG, JPEG, or WEBP"""
        # Given: A valid spec file and an unsupported format
        from quickthumb.cli import app

        runner = CliRunner()

        # When: User runs `quickthumb render spec.json --format BMP`
        with runner.isolated_filesystem():
            result = runner.invoke(app, ["render", spec_file, "--format", "BMP"])

        # Then: Exit code is 1 with a clear error message
        assert result.exit_code == 1
        assert "BMP" in result.output

    def test_should_exit_1_on_quality_out_of_range(self, spec_file):
        """Test that exit code 1 is returned when --quality is outside 1-95"""
        # Given: A valid spec file and an out-of-range quality value
        from quickthumb.cli import app

        runner = CliRunner()

        # When: User runs `quickthumb render spec.json --quality 200`
        with runner.isolated_filesystem():
            result = runner.invoke(app, ["render", spec_file, "--quality", "200"])

        # Then: Exit code is 1 with a clear error message
        assert result.exit_code == 1

    def test_should_substitute_braced_var_placeholders(self):
        """Test that --var KEY=VALUE substitutes ${KEY} braced placeholders in the spec"""
        # Given: A spec template using ${bg} and a --var flag
        from quickthumb.cli import app

        template_spec = json.dumps(
            {
                "width": 100,
                "height": 100,
                "layers": [{"type": "background", "color": "${bg}"}],
            }
        )
        runner = CliRunner()
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            f.write(template_spec)
            spec_path = f.name

        # When: User runs `quickthumb render template.json --var bg=#FF0000`
        try:
            with runner.isolated_filesystem():
                result = runner.invoke(app, ["render", spec_path, "--var", "bg=#FF0000"])

                # Then: The placeholder is replaced and the image renders successfully
                assert result.exit_code == 0
        finally:
            os.unlink(spec_path)

    def test_should_render_spec_with_theme_tokens(self):
        """Theme token references are left for from_json and do not trip the unresolved-var check"""
        # Given: a themed spec with $theme references and no --var flags
        from quickthumb.cli import app

        themed_spec = json.dumps(
            {
                "width": 100,
                "height": 100,
                "theme": {"colors": {"bg": "#FF0000"}},
                "layers": [{"type": "background", "color": "$theme.colors.bg"}],
            }
        )
        runner = CliRunner()
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            f.write(themed_spec)
            spec_path = f.name

        # When: the user renders the themed spec with an unrelated --var present
        try:
            with runner.isolated_filesystem():
                result = runner.invoke(app, ["render", spec_path, "--var", "unused=1"])

                # Then: the theme resolves and the image renders successfully
                assert result.exit_code == 0
        finally:
            os.unlink(spec_path)


class TestCLILint:
    """Test suite for the quickthumb lint subcommand"""

    def _write_spec(self, spec: dict) -> str:
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            f.write(json.dumps(spec))
        return f.name

    def test_should_exit_0_for_clean_spec(self, spec_file):
        """lint exits 0 and reports no issues for a clean spec"""
        from quickthumb.cli import app

        # given: a valid spec with no diagnostics

        # when: linting a plain background-only spec
        result = CliRunner().invoke(app, ["lint", spec_file])

        # then
        assert result.exit_code == 0
        assert "No issues found" in result.output

    def test_should_emit_json_for_clean_spec(self, spec_file):
        """lint --format json exits 0 and emits an empty diagnostics payload"""
        from quickthumb.cli import app

        # given: a valid spec with no diagnostics

        # when
        result = CliRunner().invoke(app, ["lint", spec_file, "--format", "json"])

        # then
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload == {
            "summary": {
                "diagnostic_count": 0,
                "error_count": 0,
                "warning_count": 0,
            },
            "diagnostics": [],
        }

    def test_should_exit_3_and_list_findings(self):
        """lint exits 3 and prints each finding when diagnostics are reported"""
        from quickthumb.cli import app

        # given: a spec with a shape fully outside the canvas
        spec_path = self._write_spec(
            {
                "width": 100,
                "height": 100,
                "layers": [
                    {"type": "background", "color": "#FFFFFF"},
                    {
                        "type": "shape",
                        "shape": "rectangle",
                        "position": [300, 300],
                        "width": 50,
                        "height": 50,
                        "color": "#FF0000",
                    },
                ],
            }
        )

        # when
        try:
            result = CliRunner().invoke(app, ["lint", spec_path])
        finally:
            os.unlink(spec_path)

        # then: findings are listed with code, severity, and layer index
        assert result.exit_code == 3
        assert "off-canvas" in result.output
        assert "error" in result.output
        assert "layer 1" in result.output

    def test_should_exit_3_and_emit_structured_json_findings(self):
        """lint --format json exits 3 and emits structured diagnostics for findings"""
        from quickthumb.cli import app

        # given: a spec with a shape fully outside the canvas
        spec_path = self._write_spec(
            {
                "width": 100,
                "height": 100,
                "layers": [
                    {"type": "background", "color": "#FFFFFF"},
                    {
                        "type": "shape",
                        "shape": "rectangle",
                        "position": [300, 300],
                        "width": 50,
                        "height": 50,
                        "color": "#FF0000",
                    },
                ],
            }
        )

        # when
        try:
            result = CliRunner().invoke(app, ["lint", spec_path, "--format", "json"])
        finally:
            os.unlink(spec_path)

        # then
        assert result.exit_code == 3
        payload = json.loads(result.output)
        assert payload["summary"] == {
            "diagnostic_count": 1,
            "error_count": 1,
            "warning_count": 0,
        }
        finding = payload["diagnostics"][0]
        assert finding["code"] == "off-canvas"
        assert finding["severity"] == "error"
        assert finding["layer_index"] == 1
        assert finding["layer_id"] == "layer:1"
        assert finding["bbox"] == {"x": 300, "y": 300, "width": 50, "height": 50}
        assert finding["related_layers"] == ["layer:1"]
        assert finding["measured"] == {
            "layer_type": "shape",
            "canvas_width": 100,
            "canvas_height": 100,
            "outside": "fully",
        }
        assert finding["suggestion"] == "move layer to x=50, y=50 to fit within the canvas"

    def test_should_emit_structured_json_for_layer_overlap(self):
        """lint --format json includes structured layer-overlap fields"""
        from quickthumb.cli import app

        # given: a spec with two substantially overlapping visible shapes
        spec_path = self._write_spec(
            {
                "width": 240,
                "height": 180,
                "layers": [
                    {"type": "background", "color": "#FFFFFF"},
                    {
                        "type": "shape",
                        "shape": "rectangle",
                        "position": [20, 20],
                        "width": 100,
                        "height": 60,
                        "color": "#FF0000",
                    },
                    {
                        "type": "shape",
                        "shape": "rectangle",
                        "position": [80, 40],
                        "width": 80,
                        "height": 50,
                        "color": "#00FF00",
                    },
                ],
            }
        )

        # when
        try:
            result = CliRunner().invoke(app, ["lint", spec_path, "--format", "json"])
        finally:
            os.unlink(spec_path)

        # then
        assert result.exit_code == 3
        payload = json.loads(result.output)
        assert payload == {
            "summary": {
                "diagnostic_count": 1,
                "error_count": 0,
                "warning_count": 1,
            },
            "diagnostics": [
                {
                    "code": "layer-overlap",
                    "severity": "warning",
                    "layer_index": 2,
                    "message": (
                        "shape layer layer:2 (order 2) overlaps shape layer layer:1 "
                        "(order 1); bbox_overlap=1600px "
                        "(bbox_overlap_pct=40% of upper, 27% of lower), "
                        "visible_overlap=1600px "
                        "(visible_overlap_pct=40% of upper, 27% of lower); "
                        "move layer 2 to y=88 to clear the overlap"
                    ),
                    "layer_id": "layer:2",
                    "bbox": {"x": 80, "y": 40, "width": 40, "height": 40},
                    "related_layers": ["layer:2", "layer:1"],
                    "measured": {
                        "lower_layer_id": "layer:1",
                        "upper_layer_id": "layer:2",
                        "lower_bbox": {"x": 20, "y": 20, "width": 100, "height": 60},
                        "upper_bbox": {"x": 80, "y": 40, "width": 80, "height": 50},
                        "overlap_bbox": {"x": 80, "y": 40, "width": 40, "height": 40},
                        "bbox_overlap": 1600,
                        "bbox_overlap_pct_lower": 1600 / 6000,
                        "bbox_overlap_pct_upper": 1600 / 4000,
                        "visible_overlap": 1600,
                        "visible_overlap_pct_lower": 1600 / 6000,
                        "visible_overlap_pct_upper": 1600 / 4000,
                    },
                    "suggestion": "move layer 2 to y=88 to clear the overlap",
                }
            ],
        }

    def test_should_emit_structured_json_for_group_child_overlap(self):
        """lint --format json reports grouped child overlap with stable related layer ids"""
        from quickthumb.cli import app

        # given: a grouped text child and a later top-level text layer overlap
        spec_path = self._write_spec(
            {
                "width": 360,
                "height": 220,
                "layers": [
                    {"type": "background", "color": "#FFFFFF"},
                    {
                        "type": "group",
                        "position": [20, 20],
                        "children": [
                            {
                                "type": "text",
                                "content": "Alpha",
                                "size": 48,
                                "color": "#000000",
                            }
                        ],
                    },
                    {
                        "type": "text",
                        "content": "Beta",
                        "size": 48,
                        "color": "#000000",
                        "position": [50, 32],
                    },
                ],
            }
        )

        # when
        try:
            result = CliRunner().invoke(app, ["lint", spec_path, "--format", "json"])
        finally:
            os.unlink(spec_path)

        # then
        assert result.exit_code == 3
        payload = json.loads(result.output)
        assert payload["summary"] == {
            "diagnostic_count": 1,
            "error_count": 0,
            "warning_count": 1,
        }
        finding = payload["diagnostics"][0]
        assert finding["code"] == "layer-overlap"
        assert finding["layer_index"] == 2
        assert finding["layer_id"] == "layer:2"
        assert finding["related_layers"] == ["layer:2", "layer:1:0"]
        assert finding["measured"]["lower_layer_id"] == "layer:1:0"
        assert finding["measured"]["upper_layer_id"] == "layer:2"
        assert "overlaps text layer layer:1:0" in finding["message"]

    def test_should_exit_1_for_invalid_lint_format(self, spec_file):
        """lint exits 1 when --format is neither text nor json"""
        from quickthumb.cli import app

        # given: a valid spec and an unsupported lint output format

        # when
        result = CliRunner().invoke(app, ["lint", spec_file, "--format", "xml"])

        # then
        assert result.exit_code == 1
        assert "Invalid lint format 'xml'. Must be one of: text, json" in result.output

    def test_should_exit_1_for_invalid_spec(self):
        """lint exits 1 for specs that fail validation"""
        from quickthumb.cli import app

        # given: a spec with an invalid layer type
        spec_path = self._write_spec({"width": 100, "height": 100, "layers": [{"type": "nope"}]})

        # when
        try:
            result = CliRunner().invoke(app, ["lint", spec_path])
        finally:
            os.unlink(spec_path)

        # then
        assert result.exit_code == 1
