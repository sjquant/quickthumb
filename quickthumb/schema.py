from __future__ import annotations

from typing import Any

from quickthumb.models import CanvasSpecModel

JSON_SCHEMA_DRAFT = "https://json-schema.org/draft/2020-12/schema"
QUICKTHUMB_SCHEMA_ID = "https://sjquant.github.io/quickthumb/schema.json"


def canvas_json_schema() -> dict[str, Any]:
    """Return the JSON Schema for quickthumb canvas specs."""
    schema = CanvasSpecModel.model_json_schema(mode="validation")
    schema["$schema"] = JSON_SCHEMA_DRAFT
    schema["$id"] = QUICKTHUMB_SCHEMA_ID
    schema["title"] = "quickthumb Canvas JSON Spec"
    schema["description"] = (
        "A quickthumb canvas spec accepted by Canvas.from_json() and the quickthumb CLI."
    )
    schema["anyOf"] = [
        {"required": ["width", "height"]},
        {
            "required": ["platform"],
            "not": {"anyOf": [{"required": ["width"]}, {"required": ["height"]}]},
        },
    ]
    return schema
