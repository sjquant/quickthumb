"""Behavioral specifications for the structured document error contract."""

import json
from pathlib import Path

import pytest
from quickthumb import (
    AnimationSpec,
    Canvas,
    Deck,
    ExportPolicy,
    RenderingError,
    ValidationError,
)
from quickthumb.cli import app
from typer.testing import CliRunner

# A text layer with a negative size nested inside the group "card" (layer 1).
NEGATIVE_TEXT_SIZE_IN_GROUP = {
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

# A Deck whose second slide has an image layer "hero" pointing at a missing file.
MISSING_IMAGE_ON_SECOND_SLIDE = {
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
    # given: a Canvas document whose grouped text layer has a negative size
    document = json.dumps(NEGATIVE_TEXT_SIZE_IN_GROUP)

    # when: the document is parsed
    with pytest.raises(ValidationError) as caught:
        Canvas.from_json(document)

    # then: the detail locates the field and the innermost layer, and the text says so too
    detail = caught.value.details[0]
    assert (detail.code, detail.category) == ("invalid_field", "validation")
    assert detail.path == "/layers/1/children/0/size"
    assert detail.layer_id == "title"
    assert str(caught.value).startswith("/layers/1/children/0/size (layer 'title'): ")


def test_tagged_branch_sharing_a_field_name_reports_each_field_path():
    """A grouped shape whose type tag equals its 'shape' field reports the failing fields."""
    # given: a grouped shape layer with an invalid width and no color
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

    # when: the document is parsed
    with pytest.raises(ValidationError) as caught:
        Canvas.from_json(json.dumps(document))

    # then: each failure points at its own field instead of the 'shape' value
    assert {(detail.code, detail.path) for detail in caught.value.details} == {
        ("invalid_field", "/layers/0/children/0/width"),
        ("missing_field", "/layers/0/children/0/color"),
    }


@pytest.mark.parametrize(
    ("factory", "document", "code", "path"),
    [
        pytest.param(
            Canvas.from_json,
            {"kind": "poster", "layers": []},
            "invalid_field",
            "/kind",
            id="unknown-kind",
        ),
        pytest.param(
            Canvas.from_json,
            {"kind": "canvas", "width": 100, "layers": []},
            "missing_field",
            "/height",
            id="canvas-width-without-height",
        ),
        pytest.param(
            Deck.from_json,
            {"kind": "deck", "slides": [], "layers": []},
            "unknown_field",
            "/layers",
            id="deck-with-layers",
        ),
        pytest.param(
            Deck.from_json,
            {"kind": "deck", "slides": "intro"},
            "invalid_field",
            "/slides",
            id="slides-not-a-list",
        ),
        pytest.param(
            Deck.from_json,
            {"kind": "deck", "slides": [], "theme": 1},
            "invalid_field",
            "/theme",
            id="theme-not-an-object",
        ),
        pytest.param(
            Deck.from_json,
            {"kind": "deck", "slides": [], "transition": 1},
            "invalid_field",
            "/transition",
            id="transition-not-an-object",
        ),
        pytest.param(
            Deck.from_json,
            {"kind": "deck", "slides": [1]},
            "invalid_field",
            "/slides/0",
            id="slide-not-an-object",
        ),
        pytest.param(
            Deck.from_json,
            {
                "kind": "deck",
                "slides": [
                    {
                        "kind": "canvas",
                        "width": 40,
                        "height": 40,
                        "layers": [],
                        "audio": {"path": 1},
                    }
                ],
            },
            "invalid_field",
            "/slides/0/audio/path",
            id="slide-audio-path-not-a-string",
        ),
    ],
)
def test_malformed_document_envelope_reports_the_failing_field(factory, document, code, path):
    """A malformed top-level or slide-level document field is reported at its JSON Pointer."""
    # given: a document with one malformed envelope field
    text = json.dumps(document)

    # when: the document is parsed
    with pytest.raises(ValidationError) as caught:
        factory(text)

    # then: the first detail names the field's code and location
    detail = caught.value.details[0]
    assert (detail.code, detail.path) == (code, path)


def test_validate_reports_missing_slide_asset_without_rendering():
    """validate() reports a missing image on a later Deck slide with its location and remedy."""
    # given: a Deck whose second slide references an image that does not exist
    deck = Deck.from_json(json.dumps(MISSING_IMAGE_ON_SECOND_SLIDE))

    # when: the deck is validated
    report = deck.validate()

    # then: the report carries one actionable asset detail
    assert not report.valid
    detail = report.errors[0]
    assert (detail.code, detail.category) == ("asset_missing", "asset")
    assert (detail.path, detail.layer_id) == ("/slides/1/layers/0/path", "hero")
    assert "missing.png" in detail.message
    assert "working directory" in (detail.suggestion or "")


def test_unsupported_export_capability_names_layer_and_remedy(tmp_path: Path):
    """Motion a target cannot represent fails under an 'error' policy with a located remedy."""
    # given: a shaking layer and a PPTX export policy that refuses motion fallbacks
    canvas = Canvas(40, 40).shape(
        "rectangle",
        position=(0, 0),
        width=10,
        height=10,
        color="#FF0000",
        id="badge",
        animation=AnimationSpec.shake(),
    )

    # when: the canvas is exported to PPTX
    with pytest.raises(RenderingError) as caught:
        canvas.export(str(tmp_path / "deck.pptx"), ExportPolicy(unsupported_motion="error"))

    # then: the export detail points at the layer's animation and suggests a policy change
    detail = caught.value.details[0]
    assert (detail.code, detail.category) == ("unsupported_capability", "export")
    assert (detail.path, detail.layer_id) == ("/layers/0/animation", "badge")
    assert "unsupported_motion" in (detail.suggestion or "")


@pytest.mark.parametrize(
    ("spec", "output", "extra_args", "expected", "message_fragment", "exit_code"),
    [
        pytest.param(
            NEGATIVE_TEXT_SIZE_IN_GROUP,
            "out.png",
            [],
            {
                "code": "invalid_field",
                "category": "validation",
                "path": "/layers/1/children/0/size",
                "layer_id": "title",
            },
            None,  # the message text comes from pydantic
            1,
            id="validation",
        ),
        pytest.param(
            MISSING_IMAGE_ON_SECOND_SLIDE,
            "out.png",
            [],
            {
                "code": "asset_missing",
                "category": "asset",
                "path": "/slides/1/layers/0/path",
                "layer_id": "hero",
            },
            "missing.png",
            1,
            id="asset",
        ),
        pytest.param(
            VALID_CANVAS,
            "out.bmp",
            [],
            {"code": "unsupported_format", "category": "export", "path": None, "layer_id": None},
            ".bmp",
            2,
            id="export",
        ),
        pytest.param(
            VALID_CANVAS,
            "missing-dir/out.png",
            [],
            {"code": "export_failed", "category": "export", "path": None, "layer_id": None},
            "missing-dir",
            2,
            id="unwritable-output",
        ),
        pytest.param(
            VALID_CANVAS,
            "out.png",
            ["--quality", "0"],
            {"code": "invalid_option", "category": "input", "path": None, "layer_id": None},
            "quality",
            1,
            id="input",
        ),
        pytest.param(
            MISSING_IMAGE_ON_SECOND_SLIDE,
            "out.png",
            ["--debug"],
            {"code": "invalid_option", "category": "input", "path": None, "layer_id": None},
            "--debug",
            1,
            id="deck-debug",
        ),
        pytest.param(
            {**VALID_CANVAS, "layers": [{"type": "background", "color": "$accent"}]},
            "out.png",
            ["--var", "title=Launch"],
            {
                "code": "unresolved_variable",
                "category": "input",
                "path": None,
                "layer_id": None,
            },
            "accent",
            1,
            id="unresolved-variable",
        ),
    ],
)
def test_failed_render_emits_structured_json_error(
    tmp_path: Path, spec, output, extra_args, expected, message_fragment, exit_code
):
    """render --error-format json reports a failure with every documented detail field."""
    # given: a spec file that fails in one failure category
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(spec))

    # when: rendering it with JSON error reporting
    result = CliRunner().invoke(
        app,
        ["render", str(spec_path), "-o", str(tmp_path / output), "--error-format", "json"]
        + extra_args,
    )

    # then: stdout is one envelope whose detail carries the code, location, and message
    assert result.exit_code == exit_code
    detail = json.loads(result.stdout)["errors"][0]
    assert set(detail) == DETAIL_FIELDS
    assert {key: detail[key] for key in expected} == expected
    if message_fragment is not None:
        assert message_fragment in detail["message"]


@pytest.mark.parametrize(
    ("spec", "output", "expected_prefix", "exit_code"),
    [
        pytest.param(
            NEGATIVE_TEXT_SIZE_IN_GROUP,
            "out.png",
            "error[invalid_field] /layers/1/children/0/size (layer 'title'): ",
            1,
            id="path-and-layer",
        ),
        pytest.param(
            MISSING_IMAGE_ON_SECOND_SLIDE,
            "out.png",
            "error[asset_missing] /slides/1/layers/0/path (layer 'hero'): "
            "Asset not found: 'missing.png'. Suggestion: ",
            1,
            id="suggestion",
        ),
        pytest.param(
            VALID_CANVAS,
            "out.bmp",
            "error[unsupported_format] Unsupported file format: .bmp. Suggestion: use one of .png",
            2,
            id="no-document-path",
        ),
    ],
)
def test_failed_render_prints_code_location_and_remedy(
    tmp_path: Path, spec, output, expected_prefix, exit_code
):
    """render prints a failure as one readable stderr line with its code, location, and remedy."""
    # given: a spec file that fails to render
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(spec))

    # when: rendering it with the default text error reporting
    result = CliRunner().invoke(app, ["render", str(spec_path), "-o", str(tmp_path / output)])

    # then: stderr leads with the stable code followed by the location and message
    assert result.exit_code == exit_code
    assert result.stderr.startswith(expected_prefix)
    assert "Traceback" not in result.output


def test_lint_reports_missing_slide_asset_at_its_deck_location(tmp_path: Path):
    """lint --format json locates a missing image on a later Deck slide by slide and layer."""
    # given: a Deck spec whose second slide references a missing image
    spec_path = tmp_path / "deck.json"
    spec_path.write_text(json.dumps(MISSING_IMAGE_ON_SECOND_SLIDE))

    # when: linting it with JSON output
    result = CliRunner().invoke(app, ["lint", str(spec_path), "--format", "json"])

    # then: the asset detail carries the full Deck pointer and exits as invalid input
    assert result.exit_code == 1
    detail = json.loads(result.stdout)["errors"][0]
    assert (detail["code"], detail["path"], detail["layer_id"]) == (
        "asset_missing",
        "/slides/1/layers/0/path",
        "hero",
    )
