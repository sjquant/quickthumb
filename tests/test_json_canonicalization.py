"""Black-box specifications for the canonical document JSON boundary."""

import json

import pytest
from quickthumb import Canvas, Deck
from quickthumb.errors import ValidationError
from quickthumb.schema import document_json_schema


def test_python_and_json_canvas_specs_normalize_to_one_rendered_document():
    """Given equivalent authoring inputs, normalization and pixels are identical."""
    # Given: a Python-authored canvas and the same spec authored as sparse JSON
    python_canvas = (
        Canvas(64, 48)
        .background(color="#102030")
        .shape(
            "rectangle",
            position=(8, 6),
            width=24,
            height=18,
            color="#E0F2FE",
            opacity=0.8,
        )
        .text("Canonical", position=(4, 28), size=12, color="#FFFFFF")
    )
    json_spec = {
        "kind": "canvas",
        "height": 48,
        "layers": [
            {"type": "background", "color": "#102030"},
            {
                "type": "shape",
                "shape": "rectangle",
                "position": [8, 6],
                "width": 24,
                "height": 18,
                "color": "#E0F2FE",
                "opacity": 0.8,
            },
            {
                "type": "text",
                "content": "Canonical",
                "position": [4, 28],
                "size": 12,
                "color": "#FFFFFF",
            },
        ],
        "width": 64,
    }

    # When: both inputs are normalized at the public document boundary
    json_canvas = Canvas.from_json(json.dumps(json_spec, indent=2))

    # Then: canonical JSON and public rendering behavior converge
    assert json_canvas.to_json() == python_canvas.to_json()
    assert json_canvas.sample().to_bytes() == python_canvas.sample().to_bytes()


def test_python_and_json_deck_specs_normalize_metadata_and_samples():
    """Given equivalent deck inputs, slide metadata and canonical frames survive."""
    # Given: a Python-authored deck and an equivalent JSON-authored deck
    python_deck = (
        Deck(32, 24)
        .transition("fade")
        .slide(
            Canvas().background(color="#FFFFFF"),
            audio={"path": "voice.wav", "volume": 0.5, "loop": True},
            duration=1.5,
            notes="Opening",
        )
        .slide(Canvas().background(color="#000000"), notes="Closing")
    )
    json_spec = {
        "kind": "deck",
        "height": 24,
        "transition": {"effect": "fade"},
        "slides": [
            {
                "kind": "canvas",
                "width": 32,
                "height": 24,
                "layers": [{"type": "background", "color": "#FFFFFF"}],
                "notes": "Opening",
                "duration": 1.5,
                "audio": {"path": "voice.wav", "volume": 0.5, "loop": True},
            },
            {
                "kind": "canvas",
                "width": 32,
                "height": 24,
                "layers": [{"type": "background", "color": "#000000"}],
                "notes": "Closing",
            },
        ],
        "width": 32,
    }

    # When: the JSON deck is normalized and round-tripped
    json_deck = Deck.from_json(json.dumps(json_spec, indent=4))
    round_tripped = Deck.from_json(json_deck.to_json())

    # Then: metadata, canonical JSON, and sampled frame bytes remain equivalent
    assert json_deck.to_json() == python_deck.to_json()
    assert round_tripped.to_json() == json_deck.to_json()
    assert [frame.to_bytes() for frame in json_deck.sample().frames] == [
        frame.to_bytes() for frame in python_deck.sample().frames
    ]


def test_canonical_serialization_is_deterministic_and_schema_valid():
    """Given a deck with metadata, serialization is stable and accepted by its schema."""
    # Given: a document with nested values whose input order is intentionally varied
    deck = Deck(16, 12).slide(Canvas().background(color="#123456"), notes="stable")

    # When: canonical serialization is repeated and checked against the published schema
    first = deck.to_json()
    second = deck.to_json()
    from jsonschema import validate

    validate(json.loads(first), document_json_schema())

    # Then: the wire representation is byte-for-byte stable and compact
    assert first == second
    assert "\n" not in first
    assert ": " not in first


@pytest.mark.parametrize(
    ("factory", "payload", "message"),
    [
        (Canvas.from_json, '{"width": 10, "height": 10, "layers": []}', "kind"),
        (Deck.from_json, '{"slides": []}', "kind"),
        (
            Canvas.from_json,
            '{"kind":"deck","width":10,"height":10,"layers":[]}',
            "kind",
        ),
        (
            Deck.from_json,
            '{"kind":"canvas","slides":[]}',
            "kind",
        ),
        (
            Deck.from_json,
            '{"kind":"deck","slides":[],"zeta":1,"alpha":2}',
            "alpha, zeta",
        ),
        (
            Canvas.from_json,
            '{"kind":"canvas","width":10,"height":10,"layers":[],"zeta":1,"alpha":2}',
            "alpha, zeta",
        ),
        (Canvas.from_json, '{"kind":"canvas","width":10,"height":10,"layers":', "Invalid JSON"),
        (Canvas.from_json, "[]", "object"),
    ],
)
def test_invalid_document_shapes_have_stable_boundary_errors(factory, payload, message):
    """Given malformed or mismatched JSON, the public parser reports a stable error."""
    # When / Then: parsing fails with the expected stable discriminator/shape detail
    with pytest.raises(ValidationError, match=message):
        factory(payload)


def test_unknown_layer_fields_are_rejected_at_the_json_boundary():
    """Given an unknown layer field, validation fails instead of silently dropping it."""
    # Given: a valid canvas shape with one misspelled/unknown field
    payload = {
        "kind": "canvas",
        "width": 10,
        "height": 10,
        "layers": [{"type": "background", "color": "#FFFFFF", "colour": "#000000"}],
    }

    # When / Then: the unknown field is surfaced as a validation error
    with pytest.raises(ValidationError, match="colour"):
        Canvas.from_json(json.dumps(payload))

    # Nested discriminated models use the same strict boundary.
    payload["layers"][0] = {
        "type": "background",
        "color": "#FFFFFF",
        "effects": [{"type": "grain", "intensity": 0.2, "oops": True}],
    }
    with pytest.raises(ValidationError, match="oops"):
        Canvas.from_json(json.dumps(payload))

    payload["layers"][0] = {
        "type": "text",
        "content": [{"text": "hello", "colour": "#FFFFFF"}],
        "position": [0, 0],
        "size": 12,
    }
    with pytest.raises(ValidationError, match="colour"):
        Canvas.from_json(json.dumps(payload))
