"""Publish the JSON Schemas next to the docs so their `$id` URLs resolve.

`canvas_json_schema()` declares `$id: https://quickthumb.solaqua.dev/schema.json`
and `document_json_schema()` the matching `document-schema.json`. Writing them
into the built site on every build keeps the hosted copies in step with the
code, in the same format as `quickthumb schema`.
"""

import json
from pathlib import Path

from quickthumb.schema import canvas_json_schema, document_json_schema


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def on_post_build(config, **kwargs) -> None:
    site = Path(config["site_dir"])
    _write(site / "schema.json", canvas_json_schema())
    _write(site / "document-schema.json", document_json_schema())
