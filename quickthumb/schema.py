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
        "A quickthumb canvas spec accepted by Canvas.from_json() and the quickthumb CLI."
    )
    schema["properties"]["platform"] = platform_schema
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
