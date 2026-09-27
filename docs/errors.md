---
description: Handle quickthumb validation, missing-asset, export, and CLI failures through one structured error contract with stable codes and JSON Pointer locations.
---

# Structured Errors

Every quickthumb failure — an invalid field, a missing asset, an export a
target cannot perform, or a bad command-line option — carries the same
machine-readable detail. Agents can locate the offending input and choose a
remedy without parsing prose; people still get a clear one-line message.

## Error detail fields

| Field | Type | Meaning |
| --- | --- | --- |
| `code` | string | Stable identifier for the kind of failure (see [codes](#error-codes)) |
| `category` | string | `validation`, `asset`, `export`, or `input` |
| `message` | string | Human-readable description of the failure |
| `path` | string or `null` | [RFC 6901 JSON Pointer](https://www.rfc-editor.org/rfc/rfc6901) into the input document, when the failure has a document location |
| `layer_id` | string or `null` | Id of the innermost layer containing `path`, when one is known |
| `suggestion` | string or `null` | Concrete remedy, when one is known |

`path` is relative to the document being parsed or validated. For
`Canvas.from_json`, `Deck.from_json`, `validate()`, and the CLI that is the
document root, so Deck failures start with `/slides/<index>`. For a model built
directly in Python, such as `TextLayer(...)`, it is relative to that model.

## Python API

All quickthumb exceptions derive from `QuickthumbError` and expose the same
details:

```python
from quickthumb import Canvas, QuickthumbError

try:
    Canvas.from_json(spec).render("out.png")
except QuickthumbError as error:
    for detail in error.details:
        print(detail.code, detail.path, detail.layer_id, detail.suggestion)
    print(error)  # "/layers/1/max_width (layer 'title'): max_width must be positive"
```

| Exception | Category | Raised for |
| --- | --- | --- |
| `ValidationError` | `validation` | Invalid JSON, unknown or missing fields, invalid values |
| `MissingAssetError` | `asset` | A local image, SVG, video, text-fill, or audio file does not exist; also a `FileNotFoundError` |
| `RenderingError` | `export` | Unsupported output formats, capabilities a target cannot export, renderer failures |
| `InputError` | `input` | Invalid command-line options or unreadable spec files |

`Canvas.validate()` and `Deck.validate()` return the same `ErrorDetail`
records in `ValidationReport.errors`, so a pre-flight check and a failed render
describe a problem identically.

## CLI

`quickthumb render` accepts `--error-format json`; `quickthumb lint` and
`quickthumb diagnose` use their `--format json` option. Failures are written to
stdout as one envelope with every detail field present:

```bash
quickthumb render spec.json -o out.png --error-format json
```

```json
{
  "errors": [
    {
      "code": "asset_missing",
      "category": "asset",
      "message": "Asset not found: 'hero.png'",
      "path": "/slides/1/layers/0/path",
      "layer_id": "hero",
      "suggestion": "check the path relative to the working directory or use an http(s) URL"
    }
  ]
}
```

Text mode prints one line per detail to stderr, leading with the code:

```text
error[asset_missing] /slides/1/layers/0/path (layer 'hero'): Asset not found: 'hero.png'. Suggestion: check the path relative to the working directory or use an http(s) URL.
```

Exit codes follow the category: `export` failures exit `2`; `validation`,
`asset`, and `input` failures exit `1`.

## Error codes

| Code | Category | Meaning |
| --- | --- | --- |
| `invalid_json` | `validation` | The document is not valid JSON |
| `invalid_document` | `validation` | The document is structurally unusable (for example, a Deck with no slides) |
| `invalid_field` | `validation` | A field value has the wrong type or is out of range |
| `missing_field` | `validation` | A required field is absent |
| `unknown_field` | `validation` | A field is not part of the schema |
| `unknown_plugin` | `validation` | A plugin layer names a renderer that is not registered |
| `asset_missing` | `asset` | A referenced local file does not exist |
| `unsupported_format` | `export` | The output extension is not an export format |
| `unsupported_capability` | `export` | The export policy forbids a fallback the target needs (for example, `ExportPolicy(unsupported_motion="error")`) |
| `missing_dependency` | `export` | An external tool such as FFmpeg is unavailable |
| `export_failed` | `export` | Any other export or rendering failure, including an output path that cannot be written |
| `invalid_option` | `input` | A command-line option value is invalid |
| `input_unreadable` | `input` | The spec file cannot be read |
| `unresolved_variable` | `input` | A `$KEY` placeholder has no matching `--var` |

Codes are stable. Messages may be reworded, so automation should branch on
`code` and `path` rather than on `message`.
