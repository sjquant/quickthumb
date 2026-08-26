from __future__ import annotations

from copy import deepcopy
from typing import Any, cast

from pydantic import TypeAdapter

from quickthumb._diagnostic_rules import PLATFORM_SAFE_MARGIN_PRESETS
from quickthumb.models import (
    CanvasSpecModel,
    ExportDiagnostic,
    ExportPolicy,
    MotionCapabilityInspection,
    MotionEventInspection,
    MotionInspection,
    MotionKeyframeInspection,
    MotionLayerInspection,
    MotionMatchInspection,
    MotionProfile,
    MotionSlideInspection,
    MotionTargetInspection,
    MotionTrackInspection,
    ReducedMotionInspection,
)
from quickthumb.transitions import Transition

JSON_SCHEMA_DRAFT = "https://json-schema.org/draft/2020-12/schema"
QUICKTHUMB_SCHEMA_ID = "https://sjquant.github.io/quickthumb/schema.json"


def canvas_json_schema() -> dict[str, Any]:
    """Return the JSON Schema for quickthumb canvas specs."""
    schema = CanvasSpecModel.model_json_schema(mode="validation")
    platform_name_schema = {"enum": sorted(PLATFORM_SAFE_MARGIN_PRESETS), "type": "string"}
    platform_schema = {
        "anyOf": [
            platform_name_schema,
            {"type": "null"},
        ],
        "default": None,
        "title": "Platform",
    }
    sized_dimension_schema = {"exclusiveMinimum": 0, "type": "integer"}
    schema["$schema"] = JSON_SCHEMA_DRAFT
    schema["$id"] = QUICKTHUMB_SCHEMA_ID
    schema["title"] = "quickthumb Canvas JSON Spec"
    schema["description"] = (
        "A quickthumb canvas spec accepted by the quickthumb CLI. Canvas.from_json() also "
        "requires the top-level kind discriminator to be 'canvas'."
    )
    schema["properties"]["kind"] = {"const": "canvas", "type": "string"}
    schema["properties"]["platform"] = platform_schema
    schema["required"] = ["kind", *schema.get("required", [])]
    schema["additionalProperties"] = False
    animation_schema = schema.get("$defs", {}).get("AnimationSpec")
    if animation_schema is not None:
        # Pydantic's generated schema describes the two optional branches, but
        # model-level validators are not represented there. Keep the published
        # contract equally strict for constrained JSON generation and clients.
        animation_schema["oneOf"] = [
            {
                "required": ["effect"],
                "properties": {
                    "effect": {"$ref": "#/$defs/AnimationEffect"},
                    "tracks": {"type": "null"},
                },
            },
            {
                "required": ["tracks"],
                "properties": {
                    "effect": {"type": "null"},
                    "tracks": {"type": "array", "minItems": 1},
                },
            },
        ]
    for definition_name in (
        "AnimationEffect",
        "AnimationSpec",
        "KeyframeSpec",
        "PositionTrack",
        "ScaleTrack",
        "RotationTrack",
        "OpacityTrack",
        "ClipProgressTrack",
        "BlurTrack",
        "ColorTrack",
    ):
        definition = schema.get("$defs", {}).get(definition_name)
        if definition is not None:
            definition["required"] = [
                "type",
                *[field for field in definition.get("required", []) if field != "type"],
            ]
    for model in (
        MotionProfile,
        ExportPolicy,
        ExportDiagnostic,
        MotionInspection,
        MotionSlideInspection,
        MotionLayerInspection,
        MotionEventInspection,
        MotionTrackInspection,
        MotionKeyframeInspection,
        MotionTargetInspection,
        MotionCapabilityInspection,
        MotionMatchInspection,
        ReducedMotionInspection,
    ):
        schema.setdefault("$defs", {})[model.__name__] = model.model_json_schema()
    schema["anyOf"] = [
        {
            "properties": {
                "width": sized_dimension_schema,
                "height": sized_dimension_schema,
            },
            "required": ["width", "height"],
        },
        {
            "properties": {"platform": platform_name_schema},
            "required": ["platform"],
            "not": {"anyOf": [{"required": ["width"]}, {"required": ["height"]}]},
        },
    ]
    _close_model_object_schemas(schema)
    return schema


def _close_model_object_schemas(value: object) -> None:
    """Mark generated model objects strict without closing arbitrary mappings."""
    if isinstance(value, list):
        for item in value:
            _close_model_object_schemas(item)
        return
    if not isinstance(value, dict):
        return
    schema = cast(dict[str, Any], value)
    if schema.get("type") == "object" and "properties" in schema:
        schema.setdefault("additionalProperties", False)
    for item in schema.values():
        _close_model_object_schemas(item)


def document_json_schema() -> dict[str, Any]:
    """Return a discriminated JSON Schema for Canvas and Deck documents."""
    canvas = canvas_json_schema()
    canvas_defs = canvas.pop("$defs", {})
    canvas_document = {key: value for key, value in canvas.items() if key not in {"$schema", "$id"}}
    sized_deck_slide_document = deepcopy(canvas_document)
    sized_deck_slide_document["title"] = "quickthumb Sized Deck Slide JSON Spec"
    slide_metadata = {
        "transition": {"$ref": "#/$defs/TransitionDocument"},
        "audio": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "volume": {"type": "number", "minimum": 0},
                "loop": {"type": "boolean"},
                "fade_out": {"type": "number", "minimum": 0},
            },
            "required": ["path"],
            "additionalProperties": False,
        },
        "duration": {"exclusiveMinimum": 0, "type": "number"},
        "notes": {"type": "string"},
    }
    sized_deck_slide_document["properties"].update(slide_metadata)

    deck_slide_document = deepcopy(sized_deck_slide_document)
    deck_slide_document["title"] = "quickthumb Deck Slide JSON Spec"
    deck_slide_document.pop("anyOf", None)
    deck_slide_document["allOf"] = [
        {
            "if": {"required": ["width"]},
            "then": {"required": ["height"]},
        },
        {
            "if": {"required": ["height"]},
            "then": {"required": ["width"]},
        },
    ]

    transition_schema = TypeAdapter(Transition).json_schema(
        ref_template="#/$defs/Transition_{model}"
    )
    transition_defs = transition_schema.pop("$defs", {})
    transition_defs = {
        f"Transition_{name}": definition for name, definition in transition_defs.items()
    }
    for definition in transition_defs.values():
        if "properties" in definition and "effect" in definition["properties"]:
            definition["required"] = [
                "effect",
                *[field for field in definition.get("required", []) if field != "effect"],
            ]
    transition_document = {
        key: value for key, value in transition_schema.items() if key != "$schema"
    }

    deck_slide_document["properties"].update(
        {
            "transition": transition_document,
        }
    )
    deck_document = {
        "type": "object",
        "title": "quickthumb Deck JSON Spec",
        "properties": {
            "kind": {"const": "deck", "type": "string"},
            "width": {"exclusiveMinimum": 0, "type": "integer"},
            "height": {"exclusiveMinimum": 0, "type": "integer"},
            "theme": {"type": "object"},
            "transition": transition_document,
            "slides": {
                "type": "array",
                "items": {"$ref": "#/$defs/DeckSlideDocument"},
            },
        },
        "required": ["kind", "slides"],
        "additionalProperties": False,
        "allOf": [
            {
                "if": {"required": ["width"]},
                "then": {"required": ["height"]},
            },
            {
                "if": {"required": ["height"]},
                "then": {"required": ["width"]},
            },
            {
                "if": {"not": {"anyOf": [{"required": ["width"]}, {"required": ["height"]}]}},
                "then": {
                    "properties": {"slides": {"items": {"$ref": "#/$defs/SizedDeckSlideDocument"}}}
                },
            },
        ],
    }
    return {
        "$schema": JSON_SCHEMA_DRAFT,
        "$id": f"{QUICKTHUMB_SCHEMA_ID.rsplit('/', 1)[0]}/document-schema.json",
        "title": "quickthumb JSON Document Spec",
        "description": "A discriminated quickthumb Canvas or Deck JSON document.",
        "oneOf": [
            {"$ref": "#/$defs/CanvasDocument"},
            {"$ref": "#/$defs/DeckDocument"},
        ],
        "discriminator": {
            "propertyName": "kind",
            "mapping": {
                "canvas": "#/$defs/CanvasDocument",
                "deck": "#/$defs/DeckDocument",
            },
        },
        "$defs": {
            **canvas_defs,
            **transition_defs,
            "CanvasDocument": canvas_document,
            "DeckSlideDocument": deck_slide_document,
            "SizedDeckSlideDocument": sized_deck_slide_document,
            "TransitionDocument": transition_document,
            "DeckDocument": deck_document,
        },
    }
