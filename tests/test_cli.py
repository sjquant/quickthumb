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
