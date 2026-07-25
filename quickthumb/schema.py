from __future__ import annotations

from typing import Any

from quickthumb._diagnostic_rules import PLATFORM_SAFE_MARGIN_PRESETS
from quickthumb.models import CanvasSpecModel

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
        "accepts legacy documents without the top-level kind."
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
    return schema


def document_json_schema() -> dict[str, Any]:
    """Return a discriminated JSON Schema for Canvas and Deck documents."""
    canvas = canvas_json_schema()
    canvas_defs = canvas.pop("$defs", {})
    canvas_document = {key: value for key, value in canvas.items() if key not in {"$schema", "$id"}}
    deck_document = {
        "type": "object",
        "title": "quickthumb Deck JSON Spec",
        "properties": {
            "kind": {"const": "deck", "type": "string"},
            "width": {"exclusiveMinimum": 0, "type": "integer"},
            "height": {"exclusiveMinimum": 0, "type": "integer"},
            "theme": {"type": "object"},
            "transition": {"type": "object"},
            "slides": {
                "type": "array",
                "items": {"$ref": "#/$defs/CanvasDocument"},
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
            "CanvasDocument": canvas_document,
            "DeckDocument": deck_document,
        },
    }
