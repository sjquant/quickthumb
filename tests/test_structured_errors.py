"""Behavioral specifications for the structured document error contract."""

import json
from pathlib import Path

import pytest
from quickthumb import (
    AnimationSpec,
    Canvas,
    Deck,
    ExportPolicy,
    MissingAssetError,
    RenderingError,
    ValidationError,
)
from quickthumb.cli import app
from typer.testing import CliRunner

INVALID_NESTED_FIELD = {
    "kind": "canvas",
    "width": 100,
    "height": 100,
    "layers": [
        {"type": "background", "color": "#FFFFFF"},
        {
            "type": "group",
            "id": "card",
            "children": [{"type": "text", "id": "title", "content": "Hi", "size": -4}],
        },
    ],
}

MISSING_SLIDE_ASSET = {
    "kind": "deck",
    "slides": [
        {"kind": "canvas", "width": 40, "height": 40, "layers": []},
        {
            "kind": "canvas",
            "width": 40,
            "height": 40,
            "layers": [{"type": "image", "id": "hero", "path": "missing.png", "position": [0, 0]}],
        },
    ],
}

VALID_CANVAS = {
    "kind": "canvas",
    "width": 40,
    "height": 40,
    "layers": [{"type": "background", "color": "#112233"}],
}

DETAIL_FIELDS = {"code", "category", "message", "path", "layer_id", "suggestion"}


def test_nested_layer_field_error_points_at_the_input_location():
    """An invalid field inside a grouped layer reports its full JSON Pointer and layer id."""
    # Given: a Canvas document whose grouped text layer has a negative size
    document = json.dumps(INVALID_NESTED_FIELD)

    # When: the document is parsed
    with pytest.raises(ValidationError) as caught:
        Canvas.from_json(document)

    # Then: the detail locates the field and the innermost layer, and the text says so too
    detail = caught.value.details[0]
    assert detail.code == "invalid_field"
    assert detail.category == "validation"
    assert detail.path == "/layers/1/children/0/size"
    assert detail.layer_id == "title"
    assert str(caught.value).startswith("/layers/1/children/0/size (layer 'title'): ")


def test_tagged_branch_sharing_a_field_name_reports_each_field_path():
    """A grouped shape whose type tag equals its 'shape' field reports the failing fields."""
    # Given: a grouped shape layer with an invalid width and no color
    document = {
        "kind": "canvas",
        "width": 100,
        "height": 100,
        "layers": [
            {
                "type": "group",
                "children": [
                    {
                        "type": "shape",
                        "shape": "rectangle",
                        "position": [0, 0],
                        "width": -5,
                        "height": 10,
                    }
                ],
            }
        ],
    }

    # When: the document is parsed
    with pytest.raises(ValidationError) as caught:
        Canvas.from_json(json.dumps(document))

    # Then: each failure points at its own field instead of the 'shape' value
    assert {(detail.code, detail.path) for detail in caught.value.details} == {
        ("invalid_field", "/layers/0/children/0/width"),
        ("missing_field", "/layers/0/children/0/color"),
    }


def test_slide_audio_field_error_points_inside_the_audio_object():
    """An invalid narration field on a Deck slide is located under that slide's audio."""
    # Given: a Deck slide whose audio path is not a string
    document = {
        "kind": "deck",
        "slides": [
            {"kind": "canvas", "width": 40, "height": 40, "layers": [], "audio": {"path": 1}}
        ],
    }

    # When: the document is parsed
    with pytest.raises(ValidationError) as caught:
        Deck.from_json(json.dumps(document))

    # Then: the pointer includes the audio object
    assert caught.value.details[0].path == "/slides/0/audio/path"


def test_missing_slide_asset_is_reported_identically_by_validate_and_render(tmp_path: Path):
    """A missing image on a later slide yields one asset detail from validate() and render()."""
    # Given: a Deck whose second slide references an image that does not exist
    deck = Deck.from_json(json.dumps(MISSING_SLIDE_ASSET))

    # When: the deck is validated and then rendered
    report = deck.validate()
    with pytest.raises(MissingAssetError) as caught:
        deck.render(str(tmp_path / "slides.png"))

    # Then: both surfaces carry the same actionable detail and nothing is written
    expected = {
        "code": "asset_missing",
        "category": "asset",
        "path": "/slides/1/layers/0/path",
        "layer_id": "hero",
    }
    assert report.errors[0].model_dump(include=set(expected)) == expected
    assert caught.value.details[0].model_dump(include=set(expected)) == expected
    assert caught.value.details[0].suggestion
    assert list(tmp_path.iterdir()) == []


def test_unsupported_export_capability_names_layer_and_remedy(tmp_path: Path):
    """Motion a target cannot represent fails under an 'error' policy with a located remedy."""
    # Given: a shaking layer and a PPTX export policy that refuses motion fallbacks
    canvas = Canvas(40, 40).shape(
        "rectangle",
        position=(0, 0),
        width=10,
        height=10,
        color="#FF0000",
        id="badge",
        animation=AnimationSpec.shake(),
    )

    # When: the canvas is exported to PPTX
    with pytest.raises(RenderingError) as caught:
        canvas.export(str(tmp_path / "deck.pptx"), ExportPolicy(unsupported_motion="error"))

    # Then: the export detail points at the layer's animation and suggests a policy change
    detail = caught.value.details[0]
    assert detail.code == "unsupported_capability"
    assert detail.category == "export"
    assert detail.path == "/layers/0/animation"
    assert detail.layer_id == "badge"
    assert "unsupported_motion" in (detail.suggestion or "")


@pytest.mark.parametrize(
    ("spec", "output", "extra_args", "expected", "exit_code"),
    [
        pytest.param(
            INVALID_NESTED_FIELD,
            "out.png",
            [],
            {
                "code": "invalid_field",
                "category": "validation",
                "path": "/layers/1/children/0/size",
                "layer_id": "title",
            },
            1,
            id="validation",
        ),
        pytest.param(
            MISSING_SLIDE_ASSET,
            "out.png",
            [],
            {
                "code": "asset_missing",
                "category": "asset",
                "path": "/slides/1/layers/0/path",
                "layer_id": "hero",
            },
            1,
            id="asset",
        ),
        pytest.param(
            VALID_CANVAS,
            "out.bmp",
            [],
            {"code": "unsupported_format", "category": "export", "path": None, "layer_id": None},
            2,
            id="export",
        ),
        pytest.param(
            VALID_CANVAS,
            "missing-dir/out.png",
            [],
            {"code": "export_failed", "category": "export", "path": None, "layer_id": None},
            2,
            id="unwritable-output",
        ),
        pytest.param(
            VALID_CANVAS,
            "out.png",
            ["--quality", "0"],
            {"code": "invalid_option", "category": "input", "path": None, "layer_id": None},
            1,
            id="input",
        ),
    ],
)
def test_cli_reports_each_failure_category_as_structured_json(
    tmp_path: Path, spec, output, extra_args, expected, exit_code
):
    """render --error-format json emits every failure with the documented detail fields."""
    # Given: a spec file that fails in one failure category
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(spec))

    # When: rendering it with JSON error reporting
    result = CliRunner().invoke(
        app,
        ["render", str(spec_path), "-o", str(tmp_path / output), "--error-format", "json"]
        + extra_args,
    )

    # Then: stdout is one parseable envelope whose detail carries code, location, and message
    assert result.exit_code == exit_code
    detail = json.loads(result.stdout)["errors"][0]
    assert set(detail) == DETAIL_FIELDS
    assert {key: detail[key] for key in expected} == expected
    assert detail["message"]


@pytest.mark.parametrize(
    ("spec", "output", "expected_line"),
    [
        pytest.param(
            INVALID_NESTED_FIELD,
            "out.png",
            "error[invalid_field] /layers/1/children/0/size (layer 'title'): "
            "Input should be greater than 0",
            id="validation",
        ),
        pytest.param(
            MISSING_SLIDE_ASSET,
            "out.png",
            "error[asset_missing] /slides/1/layers/0/path (layer 'hero'): "
            "Asset not found: 'missing.png'. Suggestion: ",
            id="asset",
        ),
        pytest.param(
            VALID_CANVAS,
            "out.bmp",
            "error[unsupported_format] Unsupported file format: .bmp. Suggestion: use one of .png",
            id="export",
        ),
    ],
)
def test_cli_text_errors_name_code_location_and_remedy(tmp_path: Path, spec, output, expected_line):
    """render prints each failure as one readable line with its code, location, and remedy."""
    # Given: a spec file that fails in one failure category
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(spec))

    # When: rendering it with the default text error reporting
    result = CliRunner().invoke(app, ["render", str(spec_path), "-o", str(tmp_path / output)])

    # Then: stderr leads with the stable code followed by the location and message
    assert result.exit_code != 0
    assert result.stderr.startswith(expected_line)
    assert "Traceback" not in result.output


def test_lint_reports_missing_slide_asset_at_its_deck_location(tmp_path: Path):
    """lint --format json locates a missing image on a later Deck slide by slide and layer."""
    # Given: a Deck spec whose second slide references a missing image
    spec_path = tmp_path / "deck.json"
    spec_path.write_text(json.dumps(MISSING_SLIDE_ASSET))

    # When: linting it with JSON output
    result = CliRunner().invoke(app, ["lint", str(spec_path), "--format", "json"])

    # Then: the asset detail carries the full Deck pointer and exits as invalid input
    assert result.exit_code == 1
    detail = json.loads(result.stdout)["errors"][0]
    assert detail["code"] == "asset_missing"
    assert detail["path"] == "/slides/1/layers/0/path"
    assert detail["layer_id"] == "hero"
