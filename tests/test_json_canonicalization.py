"""Black-box specifications for the canonical document JSON boundary."""

import json

import pytest
from jsonschema import ValidationError as JsonSchemaValidationError
from jsonschema import validate
from quickthumb import (
    Canvas,
    Deck,
    PluginLayer,
    PluginRegistry,
    canvas_json_schema,
    lookup_plugin,
    plugin_registry,
    register_plugin,
)
from quickthumb._document import load_document
from quickthumb.errors import ValidationError
from quickthumb.schema import document_json_schema, plugin_layer_json_schema


@pytest.fixture(autouse=True)
def isolated_global_plugin_registry():
    """Restore process-global plugin registrations after each behavioral spec."""
    definitions = plugin_registry.definitions()
    plugin_registry.clear()
    try:
        yield
    finally:
        plugin_registry.clear()
        for definition in definitions:
            plugin_registry.register(definition)


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
    # Given: equivalent JSON inputs with different insertion order
    first_canvas = Canvas.from_json('{"kind":"canvas","width":16,"height":12,"layers":[]}')
    second_canvas = Canvas.from_json('{"layers":[],"height":12,"kind":"canvas","width":16}')
    assert first_canvas.to_json() == second_canvas.to_json()

    # And: a document with nested values whose input order is intentionally varied
    deck = Deck(16, 12).slide(Canvas().background(color="#123456"), notes="stable")

    # When: canonical serialization is repeated and checked against the published schema
    first = deck.to_json()
    second = deck.to_json()

    validate(json.loads(first), document_json_schema())

    # Then: the wire representation is byte-for-byte stable and compact
    assert first == second
    assert first.startswith('{"height":12,"kind":"deck","slides":')
    assert "\n" not in first
    assert ": " not in first


def test_document_schema_matches_sparse_decks_and_strict_nested_metadata():
    """Given parser-supported deck shapes, the published schema accepts only valid ones."""
    schema = document_json_schema()
    sparse_deck = {
        "kind": "deck",
        "width": 32,
        "height": 24,
        "transition": {"effect": "fade"},
        "slides": [{"kind": "canvas", "layers": [], "transition": {"effect": "cut"}}],
    }
    validate(sparse_deck, schema)

    invalid_documents = [
        {
            "kind": "canvas",
            "width": 10,
            "height": 10,
            "layers": [{"type": "background", "color": "#FFFFFF", "bogus": 1}],
        },
        {"kind": "deck", "slides": [], "transition": {}},
        {
            "kind": "deck",
            "width": 32,
            "height": 24,
            "slides": [{"kind": "canvas", "layers": [], "transition": {}}],
        },
        {"kind": "deck", "slides": [{"kind": "canvas", "layers": []}]},
    ]
    for document in invalid_documents:
        with pytest.raises(JsonSchemaValidationError):
            validate(document, schema)


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
    payload = {
        "kind": "canvas",
        "width": 10,
        "height": 10,
        "layers": [
            {
                "type": "background",
                "color": "#FFFFFF",
                "effects": [{"type": "grain", "intensity": 0.2, "oops": True}],
            }
        ],
    }
    with pytest.raises(ValidationError, match="oops"):
        Canvas.from_json(json.dumps(payload))

    payload = {
        "kind": "canvas",
        "width": 10,
        "height": 10,
        "layers": [
            {
                "type": "text",
                "content": [{"text": "hello", "colour": "#FFFFFF"}],
                "position": [0, 0],
                "size": 12,
            }
        ],
    }
    with pytest.raises(ValidationError, match="colour"):
        Canvas.from_json(json.dumps(payload))


@pytest.mark.parametrize(
    ("layer", "field"),
    [
        (
            {
                "type": "background",
                "gradient": {
                    "type": "linear",
                    "angle": 0,
                    "stops": [["#FFFFFF", 0]],
                    "bogus": True,
                },
            },
            "bogus",
        ),
        (
            {
                "type": "shape",
                "shape": "rectangle",
                "position": [0, 0],
                "width": 2,
                "height": 2,
                "color": "#FFFFFF",
                "fill": {
                    "type": "linear",
                    "angle": 0,
                    "stops": [["#FFFFFF", 0]],
                    "bogus": True,
                },
            },
            "bogus",
        ),
        (
            {
                "type": "shape",
                "shape": "rectangle",
                "position": [0, 0],
                "width": 2,
                "height": 2,
                "color": "#FFFFFF",
                "clip": {
                    "type": "rect",
                    "position": [0, 0],
                    "width": 2,
                    "height": 2,
                    "bogus": True,
                },
            },
            "bogus",
        ),
        (
            {
                "type": "text",
                "content": "hello",
                "position": [0, 0],
                "size": 12,
                "animation": {"effect": "fade", "bogus": True},
            },
            "bogus",
        ),
    ],
)
def test_unknown_fields_inside_union_wrappers_are_rejected(layer, field):
    """Given a union-wrapped nested object, unknown fields fail before normalization."""
    payload = {"kind": "canvas", "width": 10, "height": 10, "layers": [layer]}

    with pytest.raises(ValidationError, match=field):
        Canvas.from_json(json.dumps(payload))


def test_custom_layer_unknown_fields_are_rejected_at_the_json_boundary():
    """Given a custom layer payload, extra fields are not silently discarded."""
    payload = {
        "kind": "canvas",
        "width": 10,
        "height": 10,
        "layers": [{"type": "custom", "name": "noop", "kwargs": {}, "bogus": True}],
    }

    with pytest.raises(ValidationError, match="bogus"):
        Canvas.from_json(json.dumps(payload))


@pytest.mark.parametrize(
    ("slide", "message"),
    [
        ({"width": 10, "height": 10, "layers": []}, "kind"),
        ({"kind": "deck", "width": 10, "height": 10, "layers": []}, "kind"),
        (
            {"kind": "canvas", "width": 10, "height": 10, "layers": [], "transition": {}},
            "Invalid transition",
        ),
        (
            {
                "kind": "canvas",
                "width": 10,
                "height": 10,
                "layers": [],
                "audio": {"path": "voice.wav", "bogus": True},
            },
            "bogus",
        ),
        (
            {"kind": "canvas", "width": 10, "height": 10, "layers": [], "duration": 0},
            "duration",
        ),
        (
            {"kind": "canvas", "width": 10, "height": 10, "layers": [], "notes": 1},
            "notes",
        ),
        (
            {"kind": "canvas", "width": 10, "height": 10, "layers": [], "bogus": True},
            "bogus",
        ),
    ],
)
def test_invalid_deck_slide_shapes_have_stable_boundary_errors(slide, message):
    """Given malformed slide input, Deck.from_json reports a stable boundary error."""
    payload = {"kind": "deck", "slides": [slide]}

    with pytest.raises(ValidationError, match=message):
        Deck.from_json(json.dumps(payload))


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_non_standard_json_constants_are_rejected_at_the_boundary(constant):
    """Given a non-standard JSON numeric constant, parsing fails before model creation."""
    payload = (
        '{"kind":"canvas","width":10,"height":10,"layers":['
        '{"type":"shape","shape":"rectangle","position":[0,0],'
        f'"width":2,"height":2,"color":"#FFFFFF","rotation":{constant}'
        "}]}"
    )

    with pytest.raises(ValidationError, match="non-standard JSON constant"):
        Canvas.from_json(payload)


def test_named_plugin_layer_round_trips_through_canonical_json_and_schema():
    """Given a registered plugin, canonical JSON preserves its versioned params."""
    # Given: a deterministic renderer registration and equivalent JSON payload
    register_plugin(
        "brand_badge",
        "1.0",
        schema={
            "type": "object",
            "required": ["label", "accent"],
            "properties": {
                "label": {"type": "string"},
                "accent": {"type": "string", "pattern": r"^#[0-9A-Fa-f]{6}$"},
            },
            "additionalProperties": False,
        },
    )
    payload = {
        "kind": "canvas",
        "width": 120,
        "height": 80,
        "layers": [
            {
                "type": "plugin",
                "renderer": "brand_badge",
                "version": "1.0",
                "params": {"accent": "#FF4D00", "label": "BETA"},
            }
        ],
    }

    # When: the payload crosses the public JSON boundary
    parsed = Canvas.from_json(json.dumps(payload, indent=2))

    # Then: canonical JSON is stable and the published schema accepts it
    assert parsed.to_json() == (
        '{"height":80,"kind":"canvas","layers":[{"params":{"accent":"#FF4D00",'
        '"label":"BETA"},"renderer":"brand_badge","type":"plugin","version":"1.0"}],'
        '"width":120}'
    )
    validate(json.loads(parsed.to_json()), canvas_json_schema())
    definition = lookup_plugin("brand_badge", "1.0")
    assert definition is not None
    assert definition.renderer == "brand_badge"


def test_plugin_registry_lookup_and_schema_order_are_deterministic():
    """Given registrations in arbitrary order, lookup and schema use stable ordering."""
    # Given: registrations added in an intentionally unstable order
    registry = PluginRegistry()
    registry.register("zeta", "2.0")
    registry.register("alpha", "1.0")
    registry.register("zeta", "1.0")

    # When: definitions and lookups are requested
    assert [(item.renderer, item.version) for item in registry.definitions()] == [
        ("alpha", "1.0"),
        ("zeta", "1.0"),
        ("zeta", "2.0"),
    ]
    with pytest.raises(ValidationError, match="multiple registered versions"):
        registry.lookup("zeta")
    definition = registry.lookup("zeta", "2.0")
    assert definition is not None
    assert definition.version == "2.0"
    # Then: ordering and ambiguity behavior are deterministic
    assert [
        variant["properties"]["renderer"]["const"] for variant in registry.json_schema()["oneOf"]
    ] == ["alpha", "zeta", "zeta"]


def test_registered_plugin_schema_preserves_json_schema_defaults():
    """Given an open params schema, runtime validation and exposed schema agree."""
    # Given: a registration whose JSON Schema leaves additional properties open
    registry = PluginRegistry()
    registry.register(
        "open_plugin",
        "1.0",
        schema={"type": "object", "properties": {"label": {"type": "string"}}},
    )

    # When: a layer uses both the declared and an extra parameter
    layer = registry.validate(
        {
            "type": "plugin",
            "renderer": "open_plugin",
            "version": "1.0",
            "params": {"label": "ok", "extra": True},
        }
    )

    # Then: runtime and exposed schema preserve the same default semantics
    assert layer.params["extra"] is True
    params_schema = registry.json_schema()["oneOf"][0]["properties"]["params"]
    assert "additionalProperties" not in params_schema


def test_plugin_registry_lifecycle_rejects_duplicates_and_supports_replacement():
    """Given a named registration, lifecycle operations remain explicit and deterministic."""
    # Given: one registered renderer/version pair
    registry = PluginRegistry()
    registry.register("badge", "1.0", schema={"type": "object"})

    # When: a duplicate is registered without an explicit replacement
    with pytest.raises(ValidationError, match="already registered"):
        registry.register("badge", "1.0", schema={"type": "object", "required": ["label"]})

    # Then: replacement changes only the exact version and unregister is scoped
    replacement = registry.register(
        "badge", "1.0", schema={"type": "object", "required": ["label"]}, replace=True
    )
    assert replacement.params_schema == {"type": "object", "required": ["label"]}
    registry.register("badge", "2.0")
    registry.unregister("badge", "1.0")
    assert registry.lookup("badge", "1.0") is None
    assert registry.lookup("badge", "2.0") is not None
    registry.unregister("badge")
    assert registry.definitions() == ()


@pytest.mark.parametrize(
    ("layer", "message"),
    [
        (
            {
                "type": "plugin",
                "renderer": "missing_renderer",
                "version": "1.0",
                "params": {},
            },
            "not registered",
        ),
        (
            {"type": "plugin", "renderer": "brand_badge", "params": {}},
            "version",
        ),
        (
            {
                "type": "plugin",
                "renderer": "brand_badge",
                "version": "1.0",
                "params": {"label": "BETA"},
            },
            "accent",
        ),
        (
            {
                "type": "plugin",
                "renderer": "brand_badge",
                "version": "1.0",
                "params": {"label": "BETA", "accent": "#FF4D00", "extra": True},
            },
            "unknown field",
        ),
    ],
)
def test_plugin_layer_invalid_inputs_fail_at_the_json_boundary(layer, message):
    """Given an unresolved or schema-invalid plugin, parsing reports the contract failure."""
    # Given: one valid registration and an unresolved or invalid layer payload
    register_plugin(
        "brand_badge",
        "1.0",
        schema={
            "type": "object",
            "required": ["label", "accent"],
            "properties": {
                "label": {"type": "string"},
                "accent": {"type": "string"},
            },
            "additionalProperties": False,
        },
    )
    # When / Then: parsing rejects the payload at the public boundary
    payload = {"kind": "canvas", "width": 120, "height": 80, "layers": [layer]}
    with pytest.raises(ValidationError, match=message):
        Canvas.from_json(json.dumps(payload))


def test_nested_plugin_layer_is_validated_at_the_json_boundary():
    """Given a group child, registry validation reaches nested plugin layers."""
    # Given: a group containing a renderer that is not registered
    payload = {
        "kind": "canvas",
        "width": 120,
        "height": 80,
        "layers": [
            {
                "type": "group",
                "children": [
                    {
                        "type": "plugin",
                        "renderer": "missing_renderer",
                        "version": "1.0",
                        "params": {},
                    }
                ],
            }
        ],
    }

    # When / Then: the nested layer is rejected just like a top-level one
    with pytest.raises(ValidationError, match="not registered"):
        Canvas.from_json(json.dumps(payload))


def test_plugin_layer_rejects_non_json_parameters_before_model_coercion():
    """Given a Python-only parameter, the layer model rejects it instead of coercing it."""
    # Given / When / Then: Python-only objects cannot cross the JSON layer contract
    with pytest.raises(ValidationError, match="JSON-serializable"):
        PluginLayer(
            type="plugin",
            renderer="brand_badge",
            version="1.0",
            params={"callback": object()},
        )


def test_empty_registry_schema_rejects_unregistered_plugin_layers():
    """Given no registrations, the published schema matches the parser's rejection."""
    # Given: a syntactically valid plugin with no registered renderer
    payload = {
        "kind": "canvas",
        "width": 20,
        "height": 20,
        "layers": [{"type": "plugin", "renderer": "missing", "version": "1", "params": {}}],
    }

    # When / Then: both public boundaries reject the unresolved plugin
    with pytest.raises(JsonSchemaValidationError):
        validate(payload, canvas_json_schema())
    with pytest.raises(ValidationError, match="not registered"):
        Canvas.from_json(json.dumps(payload))


def test_explicit_registry_is_used_by_canvas_deck_and_document_parsers():
    """Given an isolated registry, all document parsers resolve its plugins."""
    # Given: a registry that is intentionally different from the process-global one
    registry = PluginRegistry()
    registry.register("isolated", "1.0", schema={"type": "object"})
    canvas_payload = {
        "kind": "canvas",
        "width": 20,
        "height": 20,
        "layers": [{"type": "plugin", "renderer": "isolated", "version": "1.0", "params": {}}],
    }

    # When: each public parser receives the isolated registry
    canvas = Canvas.from_json(json.dumps(canvas_payload), registry=registry)
    deck = Deck.from_json(
        json.dumps({"kind": "deck", "slides": [canvas_payload]}), registry=registry
    )
    loaded_canvas = load_document(json.dumps(canvas_payload), registry=registry)
    loaded_deck = load_document(
        json.dumps({"kind": "deck", "slides": [canvas_payload]}), registry=registry
    )

    # Then: the parsed documents retain the registry for later structural validation
    assert canvas.validate().valid
    assert deck.validate().valid
    assert isinstance(loaded_canvas, Canvas)
    assert isinstance(loaded_deck, Deck)

    # The same registry can drive the schemas used to validate those documents.
    validate(canvas_payload, canvas_json_schema(registry=registry))
    validate(
        {"kind": "deck", "slides": [canvas_payload]},
        document_json_schema(registry=registry),
    )
    assert (
        plugin_layer_json_schema(registry=registry)["oneOf"][0]["properties"]["renderer"]["const"]
        == "isolated"
    )


@pytest.mark.parametrize(
    ("schema", "message"),
    [
        ({"type": "object", "allOf": []}, "unsupported"),
        ({"type": "object", "not": {}}, "unsupported"),
        ({"type": "object", "$ref": "#/$defs/Params"}, "unsupported"),
        ({"type": "object", "properties": {"value": {"pattern": "["}}}, "invalid pattern"),
        ({"type": "object", "minimum": "bad"}, "invalid minimum"),
        ({"type": "object", "required": "value"}, "invalid required"),
        ({"type": "object", "properties": []}, "invalid properties"),
        ({"type": "string"}, "must allow a JSON object"),
        ({"enum": ["not-an-object"]}, "must allow a JSON object"),
        ({"oneOf": [{"type": "string"}, {"type": "integer"}]}, "must allow a JSON object"),
    ],
)
def test_plugin_registration_rejects_unsupported_or_malformed_schemas(schema, message):
    """Given an invalid schema document, registration fails with a stable error."""
    with pytest.raises(ValidationError, match=message):
        PluginRegistry().register("invalid", "1.0", schema=schema)


@pytest.mark.parametrize(
    ("schema", "params"),
    [
        (
            {"type": "object", "properties": {"value": {"const": "yes"}}},
            {"value": "no"},
        ),
        (
            {"type": "object", "properties": {"value": {"enum": ["yes", "ok"]}}},
            {"value": "no"},
        ),
        (
            {
                "type": "object",
                "properties": {"value": {"oneOf": [{"type": "string"}, {"type": "integer"}]}},
            },
            {"value": True},
        ),
        (
            {
                "type": "object",
                "properties": {
                    "value": {
                        "anyOf": [
                            {"type": "string", "minLength": 3},
                            {"type": "integer", "minimum": 2},
                        ]
                    }
                },
            },
            {"value": 1},
        ),
        ({"type": "object", "required": ["value"]}, {}),
        ({"type": "object", "properties": {"value": {"type": "integer"}}}, {"value": "1"}),
        ({"type": "object", "additionalProperties": False}, {"extra": True}),
        ({"type": "object", "additionalProperties": {"type": "string"}}, {"extra": 1}),
        (
            {
                "type": "object",
                "properties": {"values": {"type": "array", "items": {"type": "integer"}}},
            },
            {"values": ["1"]},
        ),
        (
            {"type": "object", "properties": {"value": {"type": "string", "pattern": "^ok$"}}},
            {"value": "no"},
        ),
        ({"type": "object", "minProperties": 2}, {"value": 1}),
        ({"type": "object", "maxProperties": 1}, {"one": 1, "two": 2}),
        (
            {"type": "object", "properties": {"values": {"type": "array", "minItems": 2}}},
            {"values": [1]},
        ),
        (
            {"type": "object", "properties": {"value": {"type": "string", "minLength": 2}}},
            {"value": "a"},
        ),
        (
            {"type": "object", "properties": {"value": {"type": "number", "minimum": 2}}},
            {"value": 1},
        ),
        (
            {"type": "object", "properties": {"value": {"type": "number", "maximum": 2}}},
            {"value": 3},
        ),
        (
            {
                "type": "object",
                "properties": {"value": {"type": "number", "exclusiveMinimum": 2}},
            },
            {"value": 2},
        ),
        (
            {
                "type": "object",
                "properties": {"value": {"type": "number", "exclusiveMaximum": 2}},
            },
            {"value": 2},
        ),
    ],
)
def test_plugin_runtime_rejects_supported_schema_constraint_violations(schema, params):
    """Given a supported parameter constraint, invalid values fail validation."""
    registry = PluginRegistry()
    registry.register("constrained", "1.0", schema=schema)

    with pytest.raises(ValidationError, match="Plugin params"):
        registry.validate(
            {"type": "plugin", "renderer": "constrained", "version": "1.0", "params": params}
        )


def test_plugin_definition_snapshots_are_detached_from_registry_state():
    """Given a returned definition, nested mutation cannot change registry behavior."""
    registry = PluginRegistry()
    definition = registry.register(
        "stable",
        "1.0",
        schema={"type": "object", "properties": {"value": {"type": "string"}}},
    )

    # When: callers mutate both public definition views
    assert definition.params_schema is not None
    definition.params_schema["properties"]["value"]["type"] = "integer"
    listed = registry.definitions()[0]
    assert listed.params_schema is not None
    listed.params_schema["properties"]["value"]["type"] = "boolean"

    # Then: lookup and schema still reflect the registered snapshot
    stored = registry.lookup("stable", "1.0")
    assert stored is not None
    assert stored.params_schema is not None
    assert stored.params_schema["properties"]["value"]["type"] == "string"


def test_duplicate_renderer_versions_omit_ambiguous_discriminator_mapping():
    """Given multiple versions, the schema does not map one renderer to one version."""
    registry = PluginRegistry()
    registry.register("versioned", "1.0")
    registry.register("versioned", "2.0")

    assert "mapping" not in registry.json_schema()["discriminator"]


def test_registry_unregistration_requires_a_version_when_renderer_is_ambiguous():
    """Given multiple versions, omission of version cannot delete them all accidentally."""
    registry = PluginRegistry()
    registry.register("badge", "1.0")
    registry.register("badge", "2.0")

    with pytest.raises(ValidationError, match="specify version"):
        registry.unregister("badge")
    assert registry.lookup("badge", "1.0") is not None
    assert registry.lookup("badge", "2.0") is not None
    registry.unregister("badge", "1.0")
    registry.unregister("badge")
    assert registry.definitions() == ()


def test_registry_validation_requires_the_plugin_discriminator():
    """Given mapping input without type, registry validation rejects the contract violation."""
    registry = PluginRegistry()
    registry.register("typed", "1.0")

    with pytest.raises(ValidationError, match="type 'plugin'"):
        registry.validate({"renderer": "typed", "version": "1.0", "params": {}})


def test_python_authored_canvas_validation_resolves_plugin_registry_entries():
    """Given an unresolved Python-authored plugin, Canvas.validate reports the error."""
    canvas = Canvas(
        20,
        20,
        layers=[PluginLayer(type="plugin", renderer="missing", version="1.0", params={})],
    )

    report = canvas.validate()

    assert not report.valid
    assert report.errors[0].code == "invalid_document"
    assert "not registered" in report.errors[0].message


@pytest.mark.parametrize(
    "params",
    [
        {"value": float("nan")},
        {"value": float("inf")},
        {1: "non-string key"},
        {"value": object()},
    ],
)
def test_plugin_layer_rejects_non_finite_or_non_json_nested_values(params):
    """Given nested Python-only values, PluginLayer enforces the shared JSON grammar."""
    with pytest.raises(ValidationError):
        PluginLayer(type="plugin", renderer="values", version="1.0", params=params)
