"""Tests for the quickthumb CLI"""

import json
import os
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

SIMPLE_SPEC = json.dumps(
    {
        "kind": "canvas",
        "width": 100,
        "height": 100,
        "layers": [
            {
                "type": "shape",
                "shape": "rectangle",
                "position": [10, 10],
                "width": 30,
                "height": 20,
                "color": "#00FF00",
            },
        ],
    }
)


@pytest.fixture
def spec_file():
    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
        f.write(SIMPLE_SPEC)
        f.flush()
    yield f.name
    os.unlink(f.name)


class TestCLISchema:
    """Test suite for the quickthumb schema subcommand"""

    def test_should_emit_deterministic_json_schema_to_stdout(self):
        """schema emits stable JSON only, suitable for shell pipelines"""
        # given: the quickthumb CLI application
        from quickthumb.cli import app

        runner = CliRunner()

        # when: the user asks for the published schema twice
        first = runner.invoke(app, ["schema"])
        second = runner.invoke(app, ["schema"])

        # then: stdout is deterministic parseable JSON with schema metadata
        assert first.exit_code == 0
        assert second.exit_code == 0
        assert first.output == second.output
        payload = json.loads(first.output)
        assert payload["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert payload["$id"] == "https://sjquant.github.io/quickthumb/schema.json"
        assert payload["title"] == "quickthumb Canvas JSON Spec"

    def test_should_include_canvas_theme_platform_and_layer_contracts(self):
        """schema includes top-level spec fields and every JSON layer discriminator"""
        # given: the quickthumb CLI application
        from quickthumb.cli import app

        # when: the user emits the schema
        result = CliRunner().invoke(app, ["schema"])

        # then: the schema describes canvas fields, theme tokens, and layer types
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert set(payload["properties"]) == {
            "height",
            "kind",
            "layers",
            "platform",
            "theme",
            "width",
        }
        assert payload["properties"]["kind"] == {"const": "canvas", "type": "string"}
        assert "kind" in payload["required"]
        assert payload["anyOf"][0]["properties"] == {
            "width": {"exclusiveMinimum": 0, "type": "integer"},
            "height": {"exclusiveMinimum": 0, "type": "integer"},
        }
        assert payload["anyOf"][0]["required"] == ["width", "height"]
        assert payload["anyOf"][1] == {
            "not": {"anyOf": [{"required": ["width"]}, {"required": ["height"]}]},
            "properties": {
                "platform": {
                    "enum": [
                        "instagram-reel",
                        "instagram-reels",
                        "instagram-square",
                        "tiktok",
                        "youtube",
                        "youtube-shorts",
                        "youtube-thumbnail",
                    ],
                    "type": "string",
                }
            },
            "required": ["platform"],
        }
        assert payload["properties"]["platform"]["anyOf"][0]["enum"] == [
            "instagram-reel",
            "instagram-reels",
            "instagram-square",
            "tiktok",
            "youtube",
            "youtube-shorts",
            "youtube-thumbnail",
        ]
        assert payload["properties"]["theme"]["type"] == "object"
        layer_mapping = payload["properties"]["layers"]["items"]["discriminator"]["mapping"]
        assert set(layer_mapping) == {
            "chart",
            "background",
            "group",
            "image",
            "outline",
            "plugin",
            "qr_code",
            "shape",
            "svg",
            "text",
            "video",
        }

    def test_should_emit_a_discriminated_canvas_and_deck_schema(self):
        """schema --document describes both top-level JSON document kinds."""
        from quickthumb.cli import app

        # given: the quickthumb schema command

        # when: the user requests the combined document schema
        result = CliRunner().invoke(app, ["schema", "--document"])

        # then: the published schema maps both discriminated document roots
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["title"] == "quickthumb JSON Document Spec"
        assert payload["discriminator"] == {
            "propertyName": "kind",
            "mapping": {
                "canvas": "#/$defs/CanvasDocument",
                "deck": "#/$defs/DeckDocument",
            },
        }
        assert payload["$defs"]["DeckDocument"]["properties"]["slides"]["items"] == {
            "$ref": "#/$defs/DeckSlideDocument"
        }

    def test_should_reflect_model_validation_for_common_fields(self):
        """schema preserves generated constraints from the public Pydantic models"""
        # given: the quickthumb CLI application
        from quickthumb.cli import app

        # when: the schema is emitted
        result = CliRunner().invoke(app, ["schema"])

        # then: generated field schemas include color, opacity, position, align, and fit constraints
        assert result.exit_code == 0
        defs = json.loads(result.output)["$defs"]
        text_props = defs["TextLayer"]["properties"]
        image_props = defs["ImageLayer"]["properties"]
        background_props = defs["BackgroundLayer"]["properties"]
        assert text_props["color"]["anyOf"][0]["pattern"] == "^#[0-9A-Fa-f]{6}([0-9A-Fa-f]{2})?$"
        assert text_props["opacity"]["minimum"] == 0.0
        assert text_props["opacity"]["maximum"] == 1.0
        assert text_props["position"]["anyOf"][0]["minItems"] == 2
        assert text_props["position"]["anyOf"][0]["maxItems"] == 2
        position_item_options = text_props["position"]["anyOf"][0]["prefixItems"][0]["anyOf"]
        assert position_item_options == [
            {"type": "integer"},
            {"pattern": "^-?(\\d+(\\.\\d+)?)%$", "type": "string"},
        ]
        max_width_options = text_props["max_width"]["anyOf"]
        assert max_width_options == [
            {"type": "integer"},
            {"pattern": "^(\\d+(\\.\\d+)?)%$", "type": "string"},
            {"type": "null"},
        ]
        text_fill_image_props = defs["TextFillImage"]["properties"]
        assert text_fill_image_props["fit"]["$ref"] == "#/$defs/FitMode"
        for props in (image_props, background_props, text_fill_image_props):
            focal_options = props["focal_point"]["anyOf"]
            assert focal_options[0]["minItems"] == 2
            assert focal_options[0]["maxItems"] == 2
            assert focal_options[0]["prefixItems"][0]["minimum"] == 0.0
            assert focal_options[0]["prefixItems"][0]["maximum"] == 1.0
            assert props["faces"]["items"]["$ref"] == "#/$defs/FaceRegion"
        face_props = defs["FaceRegion"]["properties"]
        assert face_props["x"]["minimum"] == 0.0
        assert face_props["x"]["maximum"] == 1.0
        for property_name in ("width", "height"):
            assert face_props[property_name]["exclusiveMinimum"] == 0
            assert face_props[property_name]["maximum"] == 1.0
        align_options = text_props["align"]["anyOf"]
        assert align_options[0] == {"$ref": "#/$defs/Align"}
        assert align_options[1]["prefixItems"][0]["enum"] == ["left", "center", "right"]
        assert align_options[1]["prefixItems"][1]["enum"] == ["top", "middle", "bottom"]

    def test_should_write_schema_to_output_path(self):
        """schema --output writes the same script-friendly JSON to a file"""
        # given: the quickthumb CLI application and an isolated output directory
        from quickthumb.cli import app

        runner = CliRunner()

        # when: the user writes the schema to a file
        with runner.isolated_filesystem():
            result = runner.invoke(app, ["schema", "--output", "schema.json"])

            # then: the command prints the path and writes parseable schema JSON
            assert result.exit_code == 0
            assert result.output.strip() == "schema.json"
            with open("schema.json") as f:
                payload = json.load(f)
            assert payload["$schema"] == "https://json-schema.org/draft/2020-12/schema"

    def test_should_exit_1_when_schema_output_path_cannot_be_written(self):
        """schema --output exits 1 when the target cannot be written as a file"""
        # given: the quickthumb CLI application and a directory used as the output path
        from quickthumb.cli import app

        runner = CliRunner()

        # when: the user asks schema to write to a directory
        with runner.isolated_filesystem():
            os.mkdir("schema-dir")
            result = runner.invoke(app, ["schema", "--output", "schema-dir"])

            # then: the command exits 1 and surfaces the filesystem error
            assert result.exit_code == 1
            assert "schema-dir" in result.output


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

    def test_should_render_debug_overlay(self, spec_file):
        """render --debug writes annotated raster output"""
        # Given: a valid spec file
        from quickthumb.cli import app

        # When: User runs `quickthumb render spec.json --debug`
        with CliRunner().isolated_filesystem():
            normal = CliRunner().invoke(app, ["render", spec_file, "-o", "normal.png"])
            result = CliRunner().invoke(app, ["render", spec_file, "-o", "debug.png", "--debug"])

            # Then: the debug output is created and differs from the normal render
            assert normal.exit_code == 0
            assert result.exit_code == 0
            assert Path("debug.png").read_bytes() != Path("normal.png").read_bytes()

    def test_should_exit_2_for_debug_document_output(self, spec_file):
        """render --debug rejects document output through the CLI."""
        # Given: a valid spec file and a document output path
        from quickthumb.cli import app

        runner = CliRunner()

        # When: User runs `quickthumb render spec.json -o out.svg --debug`
        result = runner.invoke(app, ["render", spec_file, "-o", "out.svg", "--debug"])

        # Then: the CLI reports the raster-only debug error
        assert result.exit_code == 2
        assert "Debug render is only supported for PNG, JPEG, and WEBP output." in result.output

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
                        "kind": "canvas",
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

    def test_should_report_deck_render_validation_errors_without_traceback(self):
        """render maps invalid Deck audio metadata to a clean input error."""
        from quickthumb.cli import app

        # given: a Deck JSON document referring to an audio file that does not exist
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as spec_file:
            json.dump(
                {
                    "kind": "deck",
                    "slides": [
                        {
                            "kind": "canvas",
                            "width": 100,
                            "height": 100,
                            "layers": [],
                            "audio": "missing-narration.wav",
                        }
                    ],
                },
                spec_file,
            )
            spec_path = spec_file.name

        # when: rendering the Deck to the narrated MP4 path
        try:
            result = CliRunner().invoke(app, ["render", spec_path, "-o", "deck.mp4"])
        finally:
            os.unlink(spec_path)

        # then: the CLI returns an input error without leaking a traceback
        assert result.exit_code == 1
        assert "Audio file not found" in result.output
        assert "Traceback" not in result.output

    def test_should_substitute_var_placeholders(self):
        """Test that --var KEY=VALUE substitutes $KEY placeholders in the spec before parsing"""
        # Given: A spec template using $bg_color and a --var flag
        from quickthumb.cli import app

        template_spec = json.dumps(
            {
                "kind": "canvas",
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
                "kind": "canvas",
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
                "kind": "canvas",
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
                "kind": "canvas",
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


class TestCLIWatch:
    """Test suite for the quickthumb watch subcommand"""

    def test_should_exit_1_when_watchfiles_is_missing(self, spec_file, monkeypatch):
        """watch exits 1 with install guidance when watchfiles cannot be imported"""
        # Given: a valid spec and an environment where watchfiles is unavailable
        import builtins

        from quickthumb.cli import app

        original_import = builtins.__import__

        def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name == "watchfiles":
                raise ImportError("watchfiles missing")
            return original_import(name, globals, locals, fromlist, level)

        monkeypatch.setattr(builtins, "__import__", fake_import)

        # When: the user runs the watch command
        result = CliRunner().invoke(app, ["watch", spec_file])

        # Then: the command fails with the optional dependency hint
        assert result.exit_code == 1
        assert "watchfiles is not installed" in result.output

    def test_should_render_initial_watch_pass_and_stop_on_keyboard_interrupt(
        self, spec_file, monkeypatch
    ):
        """watch --debug renders once immediately and stops cleanly on Ctrl+C"""
        # Given: a valid spec, a fake filesystem watcher, and a fake render target
        import sys
        import types

        import quickthumb.cli as cli

        rendered: list[tuple[str, str | None, int | None, bool]] = []

        class FakeCanvas:
            def render(self, output, format=None, quality=None, debug=False):
                rendered.append((output, format, quality, debug))

        def fake_load_canvas(spec, variables):
            assert str(spec) == spec_file
            assert variables == {"accent": "#00FF00"}
            return FakeCanvas()

        def fake_watch(spec):
            assert str(spec) == spec_file
            raise KeyboardInterrupt
            yield

        monkeypatch.setattr(cli, "_load_canvas", fake_load_canvas)
        monkeypatch.setitem(sys.modules, "watchfiles", types.SimpleNamespace(watch=fake_watch))

        # When: the user runs watch with format, quality, variable, and debug options
        result = CliRunner().invoke(
            cli.app,
            [
                "watch",
                spec_file,
                "-o",
                "thumb.webp",
                "--format",
                "WEBP",
                "--quality",
                "75",
                "--var",
                "accent=#00FF00",
                "--debug",
            ],
        )

        # Then: watch exits cleanly after the simulated interrupt and renders once
        assert result.exit_code == 0
        assert rendered == [("thumb.webp", "WEBP", 75, True)]
        assert "thumb.webp" in result.output

    def test_should_keep_watching_when_initial_render_spec_is_invalid(self, spec_file, monkeypatch):
        """watch keeps running when the initial spec load exits with a validation error"""
        # Given: a watch run where loading the spec fails and the watcher is then interrupted
        import sys
        import types

        import quickthumb.cli as cli
        import typer

        def fake_load_canvas(spec, variables):
            raise typer.Exit(1)

        def fake_watch(spec):
            raise KeyboardInterrupt
            yield

        monkeypatch.setattr(cli, "_load_canvas", fake_load_canvas)
        monkeypatch.setitem(sys.modules, "watchfiles", types.SimpleNamespace(watch=fake_watch))

        # When: the user starts watching the spec
        result = CliRunner().invoke(cli.app, ["watch", spec_file])

        # Then: watch handles the load failure and exits cleanly on interrupt
        assert result.exit_code == 0
        assert "Watching" in result.output

    def test_should_render_again_when_watch_reports_a_change(self, spec_file, monkeypatch):
        """watch renders once at startup and again for filesystem changes"""
        # Given: a valid loaded canvas and a watcher that emits one change event
        import sys
        import types

        import quickthumb.cli as cli

        rendered: list[str] = []

        class FakeCanvas:
            def render(self, output, format=None, quality=None, debug=False):
                rendered.append(output)

        def fake_load_canvas(spec, variables):
            return FakeCanvas()

        def fake_watch(spec):
            yield {("modified", spec)}

        monkeypatch.setattr(cli, "_load_canvas", fake_load_canvas)
        monkeypatch.setitem(sys.modules, "watchfiles", types.SimpleNamespace(watch=fake_watch))

        # When: the watched spec changes once and the watcher exits naturally
        result = CliRunner().invoke(cli.app, ["watch", spec_file, "-o", "thumb.png"])

        # Then: watch renders the initial pass and the changed pass
        assert result.exit_code == 0
        assert rendered == ["thumb.png", "thumb.png"]

    def test_should_report_watch_render_errors_and_continue(self, spec_file, monkeypatch):
        """watch reports render errors without crashing the watch loop"""
        # Given: a valid loaded canvas whose render step fails
        import sys
        import types

        import quickthumb.cli as cli

        class FailingCanvas:
            def render(self, output, format=None, quality=None, debug=False):
                raise OSError("cannot write output")

        def fake_load_canvas(spec, variables):
            return FailingCanvas()

        def fake_watch(spec):
            raise KeyboardInterrupt
            yield

        monkeypatch.setattr(cli, "_load_canvas", fake_load_canvas)
        monkeypatch.setitem(sys.modules, "watchfiles", types.SimpleNamespace(watch=fake_watch))

        # When: the user starts watching the spec
        result = CliRunner().invoke(cli.app, ["watch", spec_file])

        # Then: the render error is printed and watch exits cleanly on interrupt
        assert result.exit_code == 0
        assert "cannot write output" in result.output

    def test_should_keep_watching_after_deck_render_validation_error(self, spec_file, monkeypatch):
        """watch reports Deck validation errors and continues to the next change."""
        import sys
        import types

        import quickthumb.cli as cli
        from quickthumb import Canvas, Deck

        # given: a Deck whose narration path is invalid and a watcher interrupted after startup
        deck = Deck(100, 100).slide(Canvas(), audio="missing-narration.wav")

        def fake_load_canvas(spec, variables):
            return deck

        def fake_watch(spec):
            raise KeyboardInterrupt
            yield

        monkeypatch.setattr(cli, "_load_canvas", fake_load_canvas)
        monkeypatch.setitem(sys.modules, "watchfiles", types.SimpleNamespace(watch=fake_watch))

        # when: the user starts watching a Deck MP4 render
        result = CliRunner().invoke(cli.app, ["watch", spec_file, "-o", "deck.mp4"])

        # then: validation output is reported and the watcher exits normally
        assert result.exit_code == 0
        assert "Audio file not found" in result.output


class TestCLILint:
    """Test suite for the quickthumb lint subcommand"""

    def _write_spec(self, spec: dict) -> str:
        spec = {"kind": "deck" if "slides" in spec else "canvas", **spec}
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

    def test_should_emit_structured_json_for_near_alignment(self):
        """lint --format json serializes measured near-alignment repair data"""
        from quickthumb.cli import app

        # given: two related shapes whose measured x starts differ by three pixels
        spec_path = self._write_spec(
            {
                "width": 160,
                "height": 100,
                "layers": [
                    {
                        "type": "shape",
                        "shape": "rectangle",
                        "position": [80, 20],
                        "width": 2,
                        "height": 30,
                        "color": "#FF0000",
                    },
                    {
                        "type": "shape",
                        "shape": "rectangle",
                        "position": [83, 20],
                        "width": 2,
                        "height": 30,
                        "color": "#00FF00",
                    },
                ],
            }
        )

        # when: the JSON lint command inspects the spec
        try:
            result = CliRunner().invoke(app, ["lint", spec_path, "--format", "json"])
        finally:
            os.unlink(spec_path)

        # then: the command reports one warning with the measured coordinate delta
        assert result.exit_code == 3
        payload = json.loads(result.output)
        assert payload["summary"] == {
            "diagnostic_count": 1,
            "error_count": 0,
            "warning_count": 1,
        }
        finding = payload["diagnostics"][0]
        assert finding == {
            "code": "near-alignment",
            "severity": "warning",
            "layer_index": 1,
            "message": (
                "shape layer layer:1 is nearly aligned with shape layer layer:0 on x "
                "(83 vs 80, delta=3px); move layer 1 x from 83 to 80 to align with layer 0"
            ),
            "layer_id": "layer:1",
            "bbox": {"x": 83, "y": 20, "width": 2, "height": 30},
            "related_layers": ["layer:1", "layer:0"],
            "measured": {
                "axis": "x",
                "reference_layer_id": "layer:0",
                "actual_layer_id": "layer:1",
                "reference_coordinate": 80,
                "actual_coordinate": 83,
                "delta": 3,
                "tolerance": 3,
                "reference_bbox": {"x": 80, "y": 20, "width": 2, "height": 30},
                "actual_bbox": {"x": 83, "y": 20, "width": 2, "height": 30},
            },
            "suggestion": "move layer 1 x from 83 to 80 to align with layer 0",
        }

    def test_should_emit_structured_json_for_text_clipped(self):
        """lint --format json includes structured text-clipped diagnostics"""
        from quickthumb.cli import app

        # given: a spec with wrapped text that runs beyond the canvas
        spec_path = self._write_spec(
            {
                "width": 260,
                "height": 110,
                "layers": [
                    {"type": "background", "color": "#FFFFFF"},
                    {
                        "type": "text",
                        "content": "one two three four five six seven eight nine ten",
                        "size": 30,
                        "color": "#000000",
                        "position": [10, 70],
                        "max_width": 90,
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
        assert payload["summary"]["diagnostic_count"] == 2
        finding = payload["diagnostics"][0]
        bbox = finding["bbox"]
        assert bbox["width"] <= 90
        assert bbox["y"] + bbox["height"] > 110
        assert finding == {
            "code": "text-clipped",
            "severity": "warning",
            "layer_index": 1,
            "message": (
                f"wrapped text block at (10, 70) size {bbox['width']}x{bbox['height']} "
                "exceeds canvas and may be clipped"
            ),
            "layer_id": "layer:1",
            "bbox": {"x": 10, "y": 70, "width": bbox["width"], "height": bbox["height"]},
            "related_layers": ["layer:1"],
            "measured": {
                "text_bbox": {"x": 10, "y": 70, "width": bbox["width"], "height": bbox["height"]},
                "wrapped_line_count": 10,
                "max_width": 90,
                "text_width": bbox["width"],
                "text_height": bbox["height"],
                "canvas_width": 260,
                "canvas_height": 110,
                "clipped_by": "canvas",
                "overflow": {"bottom": bbox["y"] + bbox["height"] - 110},
            },
            "suggestion": (
                "move the text fully inside the canvas, reduce text size, increase max_width, "
                "or enable auto_scale"
            ),
        }

    def test_should_emit_structured_json_for_declared_width_text_clipping(self):
        """lint --format json reports wrapped text that exceeds max_width"""
        from quickthumb.cli import app

        # given: a wrapped block exceeds max_width but stays within the canvas
        spec_path = self._write_spec(
            {
                "width": 400,
                "height": 300,
                "layers": [
                    {"type": "background", "color": "#FFFFFF"},
                    {
                        "type": "text",
                        "content": "overlong ok",
                        "size": 40,
                        "color": "#000000",
                        "position": [10, 10],
                        "max_width": 50,
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
            "diagnostic_count": 2,
            "error_count": 0,
            "warning_count": 2,
        }
        assert [finding["code"] for finding in payload["diagnostics"]] == [
            "text-overflow",
            "text-clipped",
        ]
        finding = payload["diagnostics"][1]
        bbox = finding["bbox"]
        assert bbox["width"] > 50
        assert bbox["x"] + bbox["width"] <= 400
        assert finding == {
            "code": "text-clipped",
            "severity": "warning",
            "layer_index": 1,
            "message": (
                f"wrapped text block at (10, 10) size {bbox['width']}x{bbox['height']} "
                "exceeds max_width and may be clipped"
            ),
            "layer_id": "layer:1",
            "bbox": {"x": 10, "y": 10, "width": bbox["width"], "height": bbox["height"]},
            "related_layers": ["layer:1"],
            "measured": {
                "text_bbox": {"x": 10, "y": 10, "width": bbox["width"], "height": bbox["height"]},
                "wrapped_line_count": 2,
                "max_width": 50,
                "text_width": bbox["width"],
                "text_height": bbox["height"],
                "canvas_width": 400,
                "canvas_height": 300,
                "clipped_by": "max_width",
                "overflow_width": bbox["width"] - 50,
            },
            "suggestion": (
                "move the text fully inside the canvas, reduce text size, increase max_width, "
                "or enable auto_scale"
            ),
        }

    def test_should_emit_structured_json_for_missing_glyph(self, monkeypatch):
        """lint --format json includes structured missing-glyph diagnostics"""
        from quickthumb.cli import app

        # given: the bundled default font and a character it renders as tofu
        monkeypatch.delenv("QUICKTHUMB_DEFAULT_FONT", raising=False)
        spec_path = self._write_spec(
            {
                "width": 200,
                "height": 120,
                "layers": [
                    {"type": "background", "color": "#FFFFFF"},
                    {
                        "type": "text",
                        "content": "\ud55c",
                        "size": 40,
                        "color": "#000000",
                        "position": [10, 10],
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
        bbox = finding["bbox"]
        assert finding == {
            "code": "missing-glyph",
            "severity": "warning",
            "layer_index": 1,
            "message": (
                "text contains glyphs that render as the font replacement glyph: " + repr("\ud55c")
            ),
            "layer_id": "layer:1",
            "bbox": {"x": 10, "y": 10, "width": bbox["width"], "height": bbox["height"]},
            "related_layers": ["layer:1"],
            "measured": {"characters": ["\ud55c"], "character_count": 1},
            "suggestion": "use a font that supports '\ud55c'",
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

    def test_should_emit_structured_json_for_platform_edge_crowding(self):
        """lint --format json includes edge-crowding fields from platform presets"""
        from quickthumb.cli import app

        # given: a YouTube alias spec whose platform sets size and a duration badge overlay
        spec_path = self._write_spec(
            {
                "platform": "youtube",
                "layers": [
                    {"type": "background", "color": "#FFFFFF"},
                    {
                        "type": "shape",
                        "shape": "rectangle",
                        "position": [1100, 620],
                        "width": 90,
                        "height": 20,
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
            "error_count": 0,
            "warning_count": 1,
        }
        finding = payload["diagnostics"][0]
        assert finding["code"] == "edge-crowding"
        assert finding["layer_index"] == 1
        assert finding["layer_id"] == "layer:1"
        assert finding["bbox"] == {"x": 1100, "y": 620, "width": 90, "height": 20}
        assert finding["related_layers"] == ["layer:1"]
        assert finding["measured"] == {
            "layer_type": "shape",
            "platform": "youtube-thumbnail",
            "overlay": "duration-badge",
            "overlay_label": "duration badge",
            "overlay_bbox": {"x": 1075, "y": 619, "width": 179, "height": 72},
            "overlap_bbox": {"x": 1100, "y": 620, "width": 90, "height": 20},
        }

    def test_should_exit_1_when_platform_spec_has_only_one_dimension(self):
        """lint rejects a platform spec with only width or height set explicitly"""
        from quickthumb.cli import app

        # given: a platform spec that provides width but omits height
        spec_path = self._write_spec(
            {
                "platform": "youtube",
                "width": 640,
                "layers": [{"type": "background", "color": "#FFFFFF"}],
            }
        )

        # when
        try:
            result = CliRunner().invoke(app, ["lint", spec_path, "--format", "json"])
        finally:
            os.unlink(spec_path)

        # then
        assert result.exit_code == 1
        assert "'width' and 'height' must be integers" in result.output

    def test_should_emit_worst_tile_contrast_json_for_busy_background(self):
        """lint --format json reports the tile that drives low-contrast text"""
        from PIL import Image
        from quickthumb.cli import app

        # given: a raster background with white text crossing black and white regions
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as image_file:
            image_path = image_file.name
        image = Image.new("RGBA", (240, 120), (0, 0, 0, 255))
        image.paste((255, 255, 255, 255), (116, 0, 240, 120))
        image.save(image_path)
        spec_path = self._write_spec(
            {
                "width": 240,
                "height": 120,
                "layers": [
                    {"type": "background", "image": image_path},
                    {
                        "type": "text",
                        "content": "BUSY TITLE",
                        "size": 36,
                        "color": "#FFFFFF",
                        "position": [20, 30],
                    },
                ],
            }
        )

        # when
        try:
            result = CliRunner().invoke(app, ["lint", spec_path, "--format", "json"])
        finally:
            os.unlink(spec_path)
            os.unlink(image_path)

        # then
        assert result.exit_code == 3
        payload = json.loads(result.output)
        assert payload["summary"] == {
            "diagnostic_count": 1,
            "error_count": 0,
            "warning_count": 1,
        }
        finding = payload["diagnostics"][0]
        assert finding["code"] == "low-contrast"
        assert finding["measured"] == {
            "contrast": 1.0,
            "threshold": 2.0,
            "method": "worst-tile",
            "tile_bbox": {"x": 116, "y": 30, "width": 32, "height": 26},
            "tile_count": 6,
            "tile_size": 32,
            "foreground_rgb": [255.0, 255.0, 255.0],
            "background_rgb": [255.0, 255.0, 255.0],
        }

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

    def test_should_emit_json_error_without_traceback_for_invalid_layer(self):
        """lint --format json emits a parseable error for an invalid layer discriminator"""
        from quickthumb.cli import app

        # given: a spec with an unknown layer type
        spec_path = self._write_spec({"width": 100, "height": 100, "layers": [{"type": "unknown"}]})

        # when
        try:
            result = CliRunner().invoke(app, ["lint", spec_path, "--format", "json"])
        finally:
            os.unlink(spec_path)

        # then: expected input failures are structured and do not expose a traceback
        assert result.exit_code == 1
        assert "Traceback" not in result.output
        payload = json.loads(result.output)
        assert payload["error"]["code"] == "invalid-spec"
        assert "unknown" in payload["error"]["message"]

    def test_should_reject_an_ambiguous_canvas_document(self):
        """lint rejects a Canvas document that also claims to contain Deck slides."""
        from quickthumb.cli import app

        # given: a document explicitly marked as Canvas but carrying a top-level slides field
        spec_path = self._write_spec(
            {
                "kind": "canvas",
                "width": 100,
                "height": 100,
                "layers": [],
                "slides": [],
            }
        )

        # when: linting the ambiguous JSON document
        try:
            result = CliRunner().invoke(app, ["lint", spec_path, "--format", "json"])
        finally:
            os.unlink(spec_path)

        # then: the structured invalid-spec contract is preserved
        assert result.exit_code == 1
        payload = json.loads(result.output)
        assert payload["error"]["code"] == "invalid-spec"
        assert "slides" in payload["error"]["message"]

    def test_should_require_a_top_level_document_kind(self):
        """lint rejects JSON documents without an explicit Canvas or Deck discriminator."""
        from quickthumb.cli import app

        # given: a legacy shape-only JSON document
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as spec_file:
            json.dump({"width": 100, "height": 100, "layers": []}, spec_file)
            spec_path = spec_file.name

        # when: linting the document through the CLI boundary
        try:
            result = CliRunner().invoke(app, ["lint", spec_path, "--format", "json"])
        finally:
            os.unlink(spec_path)

        # then: the missing discriminator is a structured invalid-spec error
        assert result.exit_code == 1
        payload = json.loads(result.output)
        assert payload["error"]["code"] == "invalid-spec"
        assert "kind" in payload["error"]["message"]

    @pytest.mark.parametrize("width", ["100", 100.5, True])
    def test_should_reject_non_integer_deck_dimensions(self, width):
        """lint rejects Deck dimensions that are not positive JSON integers."""
        from quickthumb.cli import app

        # given: a Deck with one malformed root dimension
        spec_path = self._write_spec({"kind": "deck", "width": width, "height": 100, "slides": []})

        # when: linting the malformed Deck
        try:
            result = CliRunner().invoke(app, ["lint", spec_path, "--format", "json"])
        finally:
            os.unlink(spec_path)

        # then: invalid dimensions produce structured JSON and no traceback
        assert result.exit_code == 1
        assert "Traceback" not in result.output
        payload = json.loads(result.output)
        assert payload["error"]["code"] == "invalid-spec"
        assert "integer" in payload["error"]["message"]

    def test_should_reject_non_mapping_deck_slide_theme(self):
        """lint rejects a non-object slide theme instead of leaking a merge TypeError."""
        from quickthumb.cli import app

        # given: a Deck with a shared theme and an invalid per-slide theme value
        spec_path = self._write_spec(
            {
                "kind": "deck",
                "theme": {"brand": "#B8FF00"},
                "slides": [
                    {
                        "kind": "canvas",
                        "width": 100,
                        "height": 100,
                        "theme": "not-an-object",
                        "layers": [],
                    }
                ],
            }
        )

        # when: linting the malformed slide theme
        try:
            result = CliRunner().invoke(app, ["lint", spec_path, "--format", "json"])
        finally:
            os.unlink(spec_path)

        # then: the public invalid-spec response is structured and traceback-free
        assert result.exit_code == 1
        assert "Traceback" not in result.output
        payload = json.loads(result.output)
        assert payload["error"]["code"] == "invalid-spec"
        assert "theme" in payload["error"]["message"]

    @pytest.mark.parametrize(
        ("spec", "message"),
        [
            ({"kind": "canvas", "width": 100, "height": 100}, "layers"),
            (
                {"kind": "canvas", "width": 100, "height": 100, "layerz": []},
                "unknown field",
            ),
            (
                {"kind": "canvas", "width": True, "height": 100, "layers": []},
                "integer",
            ),
        ],
    )
    def test_should_reject_malformed_canvas_envelopes(self, spec, message):
        """lint rejects missing, misspelled, and boolean Canvas envelope fields."""
        from quickthumb.cli import app

        # given: a Canvas document with one malformed top-level field
        spec_path = self._write_spec(spec)

        # when: linting the malformed Canvas document
        try:
            result = CliRunner().invoke(app, ["lint", spec_path, "--format", "json"])
        finally:
            os.unlink(spec_path)

        # then: the CLI emits a structured invalid-spec response
        assert result.exit_code == 1
        payload = json.loads(result.output)
        assert payload["error"]["code"] == "invalid-spec"
        assert message in payload["error"]["message"]

    def test_should_support_deck_specs_and_preserve_slide_diagnostic_fields(self):
        """lint accepts deck JSON and includes slide and layer diagnostic context"""
        from quickthumb.cli import app

        # given: a deck whose first slide has an off-canvas layer
        spec_path = self._write_spec(
            {
                "kind": "deck",
                "slides": [
                    {
                        "kind": "canvas",
                        "width": 100,
                        "height": 100,
                        "layers": [
                            {
                                "type": "shape",
                                "shape": "rectangle",
                                "position": [300, 300],
                                "width": 50,
                                "height": 50,
                                "color": "#FF0000",
                            }
                        ],
                    }
                ],
            }
        )

        # when
        try:
            result = CliRunner().invoke(app, ["lint", spec_path, "--format", "json"])
        finally:
            os.unlink(spec_path)

        # then: the finding carries both slide and original Canvas context
        assert result.exit_code == 3
        finding = json.loads(result.output)["diagnostics"][0]
        assert finding["slide_index"] == 0
        assert finding["layer_index"] == 0
        assert finding["layer_id"] == "layer:0"
        assert finding["bbox"] == {"x": 300, "y": 300, "width": 50, "height": 50}
        assert finding["suggestion"] == "move layer to x=50, y=50 to fit within the canvas"

    def test_should_support_diagnose_alias_and_fail_on_filters(self):
        """diagnose aliases lint and fail-on controls warning-only findings"""
        from quickthumb.cli import app

        # given: a shape that produces only an edge-crowding warning
        spec_path = self._write_spec(
            {
                "width": 100,
                "height": 100,
                "layers": [
                    {
                        "type": "shape",
                        "shape": "rectangle",
                        "position": [0, 10],
                        "width": 20,
                        "height": 20,
                        "color": "#FF0000",
                    }
                ],
            }
        )

        # when: warnings are ignored for exit status and then filtered entirely
        try:
            warning_result = CliRunner().invoke(app, ["diagnose", spec_path, "--fail-on", "error"])
            ignored_result = CliRunner().invoke(
                app,
                ["diagnose", spec_path, "--ignore", "edge-crowding", "--format", "json"],
            )
        finally:
            os.unlink(spec_path)

        # then
        assert warning_result.exit_code == 0
        assert "edge-crowding" in warning_result.output
        assert ignored_result.exit_code == 0
        assert json.loads(ignored_result.output)["diagnostics"] == []

    def test_should_emit_json_error_for_unknown_diagnostic_filter(self, spec_file):
        """lint --format json reports unknown diagnostic filters as structured errors"""
        from quickthumb.cli import app

        # given: a valid canvas and a misspelled diagnostic code

        # when
        result = CliRunner().invoke(
            app,
            ["lint", spec_file, "--format", "json", "--ignore", "not-a-rule"],
        )

        # then
        assert result.exit_code == 1
        assert json.loads(result.output) == {
            "error": {
                "code": "invalid-options",
                "message": "Unknown diagnostic code(s): not-a-rule",
            }
        }

    def test_should_exit_1_when_lint_variable_substitution_leaves_placeholder(self):
        """lint exits 1 when variable substitution leaves unresolved placeholders"""
        from quickthumb.cli import app

        # given: a spec template with one unresolved placeholder after substitution
        spec_path = self._write_spec(
            {
                "width": 100,
                "height": 100,
                "layers": [{"type": "background", "color": "$missing_color"}],
            }
        )

        # when
        try:
            result = CliRunner().invoke(app, ["lint", spec_path, "--var", "other=#FFFFFF"])
        finally:
            os.unlink(spec_path)

        # then
        assert result.exit_code == 1
        assert "missing_color" in result.output

    def test_should_exit_1_when_lint_diagnose_reports_missing_referenced_file(self, monkeypatch):
        """lint exits 1 when diagnostics discover a missing referenced file"""
        # given: a loaded canvas whose diagnose step raises FileNotFoundError
        import quickthumb.cli as cli

        class MissingFileCanvas:
            def diagnose(self):
                raise FileNotFoundError("asset.png")

        monkeypatch.setattr(cli, "_load_canvas", lambda spec, variables: MissingFileCanvas())

        # when
        result = CliRunner().invoke(cli.app, ["lint", "spec.json"])

        # then
        assert result.exit_code == 1
        assert "Referenced file not found" in result.output

    def test_should_exit_2_when_lint_diagnose_reports_rendering_error(self, monkeypatch):
        """lint exits 2 when diagnostics fail during rendering-style analysis"""
        # given: a loaded canvas whose diagnose step raises an OSError
        import quickthumb.cli as cli

        class BrokenCanvas:
            def diagnose(self):
                raise OSError("cannot inspect image")

        monkeypatch.setattr(cli, "_load_canvas", lambda spec, variables: BrokenCanvas())

        # when
        result = CliRunner().invoke(cli.app, ["lint", "spec.json"])

        # then
        assert result.exit_code == 2
        assert "cannot inspect image" in result.output


class TestCLIEntry:
    """Test suite for the installed quickthumb entrypoint"""

    def test_should_call_typer_app_from_cli_main(self, monkeypatch):
        """cli.main invokes the configured Typer application"""
        # Given: a replacement Typer app callable
        import quickthumb.cli as cli

        calls: list[str] = []
        monkeypatch.setattr(cli, "app", lambda: calls.append("called"))

        # When: the CLI module main function runs
        cli.main()

        # Then: it dispatches to the configured app callable
        assert calls == ["called"]

    def test_should_exit_1_when_typer_is_missing(self, monkeypatch, capsys):
        """entrypoint exits 1 with install guidance when typer is unavailable"""
        # Given: an environment where typer cannot be imported
        import builtins

        from quickthumb import _entry

        original_import = builtins.__import__

        def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name == "typer":
                raise ImportError("typer missing")
            return original_import(name, globals, locals, fromlist, level)

        monkeypatch.setattr(builtins, "__import__", fake_import)

        # When: the installed entrypoint starts
        with pytest.raises(SystemExit) as exc_info:
            _entry.main()

        # Then: it exits with a clear optional dependency message
        assert exc_info.value.code == 1
        assert "quickthumb[cli]" in capsys.readouterr().err

    def test_should_dispatch_to_cli_main_when_typer_is_available(self, monkeypatch):
        """entrypoint delegates to quickthumb.cli.main when CLI dependencies are installed"""
        # Given: a fake CLI main function in the import path
        import sys
        import types

        from quickthumb import _entry

        calls: list[str] = []
        fake_cli = types.SimpleNamespace(main=lambda: calls.append("called"))
        monkeypatch.setitem(sys.modules, "quickthumb.cli", fake_cli)

        # When: the installed entrypoint starts
        _entry.main()

        # Then: it delegates to the CLI module main function
        assert calls == ["called"]
