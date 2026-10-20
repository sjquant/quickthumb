"""CLI inspection emits the same generic envelope as the Python API."""

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image
from quickthumb import (
    AnimationSpec,
    BlurTrack,
    Canvas,
    Deck,
    DocumentInspection,
    ExportPolicy,
    KeyframeSpec,
    inspect_document,
)
from quickthumb.cli import app
from typer.testing import CliRunner


def _unstyled(value: str) -> str:
    """Ignore terminal SGR styling without depending on optional CLI libraries."""
    return re.sub(r"\x1b\[[0-9;]*m", "", value)


def _canvas() -> Canvas:
    return Canvas(48, 32).shape(
        shape="rectangle", position=(-4, 5), width=8, height=6, color="#FF0000"
    )


@pytest.mark.parametrize("kind", ["canvas", "deck"])
def test_inspect_json_matches_python_and_does_not_write_exports(kind: str, tmp_path: Path):
    source = _canvas() if kind == "canvas" else Deck(slides=[_canvas(), Canvas(60, 40)])
    spec = tmp_path / "document.json"
    spec.write_text(source.to_json())
    expected = inspect_document(source, target="video", fps=4, max_samples=5)

    result = CliRunner().invoke(
        app,
        [
            "inspect",
            str(spec),
            "--format",
            "json",
            "--target",
            "video",
            "--fps",
            "4",
            "--max-samples",
            "5",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload == expected.model_dump(mode="json")
    assert DocumentInspection.model_validate(payload).kind == kind
    assert list(tmp_path.iterdir()) == [spec]
    assert result.stderr == ""


@pytest.mark.parametrize("kind", ["canvas", "deck"])
def test_inspect_text_includes_layout_motion_assets_and_diagnostics(kind: str, tmp_path: Path):
    source = _canvas() if kind == "canvas" else Deck(slides=[_canvas()])
    spec = tmp_path / "document.json"
    spec.write_text(source.to_json())

    result = CliRunner().invoke(app, ["inspect", str(spec)])

    assert result.exit_code == 0
    assert f"{kind}: 48x32, 1 page(s)" in result.stdout
    assert "Motion:" in result.stdout
    assert "Page 0: 48x32, 1 top-level layer(s)" in result.stdout
    assert "layer:0: shape, visible, (-4, 5) 8x6" in result.stdout
    assert "Capabilities:" in result.stdout
    assert "Assets: 0 observed reference(s)" in result.stdout
    assert "off-canvas" in result.stdout
    assert "Diagnostics:" in result.stdout


def test_inspect_reports_observed_local_assets(tmp_path: Path):
    asset = tmp_path / "image.png"
    Image.new("RGBA", (2, 2), (255, 0, 0, 255)).save(asset)
    source = Canvas(48, 32).image(str(asset), position=(0, 0))
    spec = tmp_path / "document.json"
    spec.write_text(source.to_json())

    result = CliRunner().invoke(app, ["inspect", str(spec)])

    assert result.exit_code == 0
    assert f"image: {asset} [local]" in result.stdout


def test_inspect_motion_capabilities_and_reduced_motion(tmp_path: Path):
    source = Canvas(48, 32).shape(
        shape="rectangle",
        position=(4, 5),
        width=8,
        height=6,
        color="#FF0000",
        animation=AnimationSpec.timeline(
            BlurTrack(keyframes=[KeyframeSpec(time=0, value=0), KeyframeSpec(time=1, value=4)])
        ),
    )
    spec = tmp_path / "motion.json"
    spec.write_text(source.to_json())

    normal = CliRunner().invoke(app, ["inspect", str(spec), "--target", "pptx"])
    reduced = CliRunner().invoke(
        app, ["inspect", str(spec), "--format", "json", "--reduced-motion"]
    )

    assert normal.exit_code == reduced.exit_code == 0
    assert "Motion layer:0: 1s, 1 event(s)" in normal.stdout
    assert "pptx/blur:" in normal.stdout and "fallback=rasterize" in normal.stdout
    assert json.loads(reduced.stdout) == inspect_document(
        source, policy=ExportPolicy(reduced_motion=True)
    ).model_dump(mode="json")


def test_inspect_text_retains_nested_layer_bounds(tmp_path: Path):
    source = Canvas(48, 32).group(
        children=[
            {
                "type": "shape",
                "shape": "rectangle",
                "position": [0, 0],
                "width": 8,
                "height": 6,
                "color": "#FF0000",
            }
        ],
        position=(10, 10),
    )
    spec = tmp_path / "group.json"
    spec.write_text(source.to_json())

    result = CliRunner().invoke(app, ["inspect", str(spec)])

    assert result.exit_code == 0, result.output
    assert "  layer:0: group" in result.stdout
    assert "    layer:0:0: shape" in result.stdout


def test_inspect_supports_variables(tmp_path: Path):
    spec = tmp_path / "document.json"
    spec.write_text(_canvas().to_json().replace("#FF0000", "${color}"))

    result = CliRunner().invoke(
        app, ["inspect", str(spec), "--format", "json", "--var", "color=#00FF00"]
    )

    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["kind"] == "canvas"


@pytest.mark.parametrize(
    "options",
    [
        ["--fps", "0"],
        ["--fps", "nan"],
        ["--max-samples", "1"],
        ["--target", "unknown"],
        ["--var", "invalid"],
    ],
)
def test_inspect_invalid_options_return_json_errors(options: list[str], tmp_path: Path):
    spec = tmp_path / "document.json"
    spec.write_text(_canvas().to_json())

    result = CliRunner().invoke(app, ["inspect", str(spec), "--format", "json", *options])

    assert result.exit_code == 1
    assert json.loads(result.stdout)["errors"]
    assert "Traceback" not in result.output


@pytest.mark.parametrize("contents", ["{broken", "[]", '{"kind":"unknown"}'])
def test_inspect_invalid_specs_return_json_errors(contents: str, tmp_path: Path):
    spec = tmp_path / "document.json"
    spec.write_text(contents)

    result = CliRunner().invoke(app, ["inspect", str(spec), "--format", "json"])

    assert result.exit_code == 1
    assert json.loads(result.stdout)["errors"]


def test_inspect_unreadable_and_missing_asset_errors(tmp_path: Path):
    missing_spec = CliRunner().invoke(app, ["inspect", str(tmp_path / "none"), "--format", "json"])
    assert missing_spec.exit_code == 1
    assert json.loads(missing_spec.stdout)["errors"][0]["code"] == "input_unreadable"
    source = Canvas(48, 32).image(str(tmp_path / "missing.png"), position=(0, 0))
    spec = tmp_path / "document.json"
    spec.write_text(source.to_json())
    missing_asset = CliRunner().invoke(app, ["inspect", str(spec), "--format", "json"])
    assert missing_asset.exit_code == 1
    assert json.loads(missing_asset.stdout)["errors"][0]["code"] == "asset_missing"


def test_inspect_empty_deck_uses_existing_render_error_exit(tmp_path: Path):
    spec = tmp_path / "empty.json"
    spec.write_text(Deck().to_json())

    result = CliRunner().invoke(app, ["inspect", str(spec), "--format", "json"])

    assert result.exit_code == 2
    assert "empty deck" in json.loads(result.stdout)["errors"][0]["message"]


@pytest.mark.parametrize("color", [False, True])
def test_inspect_invalid_format_and_help_are_actionable(tmp_path: Path, color: bool):
    result = CliRunner().invoke(app, ["inspect", str(tmp_path / "none"), "--format", "yaml"])
    assert result.exit_code == 1
    assert "Must be one of: text, json" in result.output
    help_result = CliRunner().invoke(
        app, ["inspect", "--help"], color=color, env={"FORCE_COLOR": "1" if color else "0"}
    )
    assert help_result.exit_code == 0
    assert "--max-samples" in _unstyled(help_result.stdout)


@pytest.mark.parametrize("color", [False, True])
def test_argument_parsing_keeps_standard_cli_errors(tmp_path: Path, color: bool):
    result = CliRunner().invoke(
        app,
        ["inspect", str(tmp_path / "none"), "--format", "json", "--fps", "abc"],
        color=color,
        env={"FORCE_COLOR": "1" if color else "0"},
    )
    assert result.exit_code == 2
    assert result.stdout == ""
    assert "--fps" in _unstyled(result.stderr)


def test_module_entrypoint_exposes_inspect(tmp_path: Path):
    spec = tmp_path / "document.json"
    spec.write_text(_canvas().to_json())

    result = subprocess.run(
        [sys.executable, "-m", "quickthumb.cli", "inspect", str(spec), "--format", "json"],
        capture_output=True,
        text=True,
        check=True,
    )

    assert json.loads(result.stdout)["kind"] == "canvas"
    assert result.stderr == ""
