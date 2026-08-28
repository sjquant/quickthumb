"""Deterministic named plugin registrations for the canonical layer contract."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from copy import deepcopy
from typing import Any, cast

from pydantic import ConfigDict, field_validator

from quickthumb.errors import ValidationError
from quickthumb.models.common import quickthumbModel
from quickthumb.models.layers import PluginLayer

_PLUGIN_NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]*$")


class PluginDefinition(quickthumbModel):
    """Immutable metadata describing one renderer/version pair."""

    renderer: str
    version: str
    params_schema: dict[str, Any] | None = None

    model_config = ConfigDict(extra="forbid", frozen=True)

    @field_validator("renderer", "version")
    @classmethod
    def validate_identity(cls, value: str, info) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"plugin {info.field_name} must be a non-empty string")
        if value != value.strip():
            raise ValueError(f"plugin {info.field_name} must not contain surrounding whitespace")
        if info.field_name == "renderer" and not _PLUGIN_NAME_PATTERN.fullmatch(value):
            raise ValueError(
                "plugin renderer must start with a letter and contain only letters, "
                "numbers, '.', '_', ':', or '-'"
            )
        return value

    @field_validator("params_schema")
    @classmethod
    def validate_schema(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return None
        _validate_schema_document(value)
        return deepcopy(value)

    @property
    def schema(self) -> dict[str, Any] | None:
        """Return a defensive copy under the concise registry terminology."""
        return None if self.params_schema is None else deepcopy(self.params_schema)


class PluginRegistry:
    """An exact, version-aware registry of named plugin definitions.

    The registry stores metadata only.  Renderer execution and native exporter
    hooks intentionally remain D2/D3 work.  All outward collections are sorted
    by ``(renderer, version)`` so schema and inspection output is reproducible.
    """

    def __init__(self) -> None:
        self._definitions: dict[tuple[str, str], PluginDefinition] = {}

    def register(
        self,
        renderer: str | PluginDefinition,
        version: str | None = None,
        params_schema: Mapping[str, Any] | None = None,
        *,
        schema: Mapping[str, Any] | None = None,
        replace: bool = False,
    ) -> PluginDefinition:
        """Register one renderer/version pair and return its immutable definition."""
        definition = self._definition_from_arguments(
            renderer,
            version,
            params_schema,
            schema=schema,
        )
        key = (definition.renderer, definition.version)
        if key in self._definitions and not replace:
            raise ValidationError(
                f"Plugin '{definition.renderer}' version '{definition.version}' "
                "is already registered."
            )
        self._definitions[key] = definition
        return definition

    def unregister(self, renderer: str, version: str | None = None) -> None:
        """Remove one version, or the sole version when no version is supplied."""
        if version is not None:
            self._definitions.pop((renderer, version), None)
            return
        matches = [key for key in self._definitions if key[0] == renderer]
        for key in matches:
            self._definitions.pop(key, None)

    def clear(self) -> None:
        """Remove all definitions, primarily for isolated application lifecycles."""
        self._definitions.clear()

    def validate(self, layer: PluginLayer | Mapping[str, Any]) -> PluginLayer:
        """Validate a plugin layer against registration and its params schema."""
        if isinstance(layer, PluginLayer):
            parsed = layer
        else:
            try:
                parsed = PluginLayer.model_validate(layer)
            except Exception as error:
                raise ValidationError(f"Invalid plugin layer: {error}") from error
        definition = self.require(parsed.renderer, parsed.version)
        if definition.params_schema is not None:
            _validate_schema_value(parsed.params, definition.params_schema, "/params")
        return parsed

    def require(self, renderer: str, version: str | None = None) -> PluginDefinition:
        """Return a registered definition or raise an actionable validation error."""
        definition = self.lookup(renderer, version)
        if definition is None:
            suffix = "" if version is None else f" version '{version}'"
            raise ValidationError(f"Plugin renderer '{renderer}'{suffix} is not registered.")
        return definition

    def lookup(self, renderer: str, version: str | None = None) -> PluginDefinition | None:
        """Look up an exact version, or the sole version for a renderer."""
        if version is not None:
            return self._definitions.get((renderer, version))
        matches = [
            definition for definition in self.definitions() if definition.renderer == renderer
        ]
        if len(matches) > 1:
            raise ValidationError(
                f"Plugin renderer '{renderer}' has multiple registered versions; specify version."
            )
        return matches[0] if matches else None

    def definitions(self) -> tuple[PluginDefinition, ...]:
        """Return all definitions in deterministic renderer/version order."""
        return tuple(self._definitions[key] for key in sorted(self._definitions))

    def renderers(self) -> tuple[str, ...]:
        """Return registered renderer names without duplicates, in sorted order."""
        return tuple(sorted({definition.renderer for definition in self._definitions.values()}))

    def json_schema(self) -> dict[str, Any]:
        """Return the plugin layer schema with registered parameter extensions."""
        base = PluginLayer.model_json_schema(mode="validation")
        base_properties = base.get("properties")
        if isinstance(base_properties, dict):
            renderer_schema = base_properties.get("renderer")
            if isinstance(renderer_schema, dict):
                renderer_schema.update({"minLength": 1, "pattern": _PLUGIN_NAME_PATTERN.pattern})
            version_schema = base_properties.get("version")
            if isinstance(version_schema, dict):
                version_schema["minLength"] = 1
        definitions = self.definitions()
        if not definitions:
            return base

        properties = base.get("properties", {})
        variants = [self._definition_schema(definition, properties) for definition in definitions]
        return {
            "title": "quickthumb Plugin Layer JSON Spec",
            "oneOf": variants,
            "discriminator": {
                "propertyName": "renderer",
                "mapping": {
                    definition.renderer: f"#/oneOf/{index}"
                    for index, definition in enumerate(definitions)
                },
            },
        }

    def schema(self) -> dict[str, Any]:
        """Alias for :meth:`json_schema` used by schema consumers."""
        return self.json_schema()

    def __contains__(self, key: object) -> bool:
        if isinstance(key, tuple) and len(key) == 2:
            return key in self._definitions
        return False

    def _definition_from_arguments(
        self,
        renderer: str | PluginDefinition,
        version: str | None,
        params_schema: Mapping[str, Any] | None,
        *,
        schema: Mapping[str, Any] | None,
    ) -> PluginDefinition:
        if isinstance(renderer, PluginDefinition):
            if version is not None or params_schema is not None or schema is not None:
                raise ValidationError(
                    "PluginDefinition cannot be combined with registration overrides."
                )
            return renderer
        if version is None:
            raise ValidationError("Plugin registration requires an explicit version.")
        if params_schema is not None and schema is not None:
            raise ValidationError("Provide only one of params_schema or schema.")
        selected_schema = params_schema if params_schema is not None else schema
        if selected_schema is not None and not isinstance(selected_schema, Mapping):
            raise ValidationError("Plugin params schema must be a JSON object.")
        return PluginDefinition(
            renderer=renderer,
            version=version,
            params_schema=None if selected_schema is None else dict(deepcopy(selected_schema)),
        )

    @staticmethod
    def _definition_schema(
        definition: PluginDefinition,
        base_properties: Mapping[str, Any],
    ) -> dict[str, Any]:
        properties = {
            key: deepcopy(base_properties[key])
            for key in ("id", "motion_key")
            if key in base_properties
        }
        properties.update(
            {
                "type": {"const": "plugin", "type": "string"},
                "renderer": {"const": definition.renderer, "type": "string"},
                "version": {"const": definition.version, "type": "string"},
                "params": deepcopy(definition.params_schema or {"type": "object"}),
            }
        )
        required = ["type", "renderer", "version", "params"]
        return {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,
        }


plugin_registry = PluginRegistry()


def register_plugin(
    renderer: str | PluginDefinition,
    version: str | None = None,
    params_schema: Mapping[str, Any] | None = None,
    *,
    schema: Mapping[str, Any] | None = None,
    replace: bool = False,
) -> PluginDefinition:
    """Register a plugin in the process-global registry."""
    return plugin_registry.register(
        renderer,
        version,
        params_schema,
        schema=schema,
        replace=replace,
    )


def unregister_plugin(renderer: str, version: str | None = None) -> None:
    """Remove a plugin from the process-global registry."""
    plugin_registry.unregister(renderer, version)


def lookup_plugin(renderer: str, version: str | None = None) -> PluginDefinition | None:
    """Look up a plugin in the process-global registry."""
    return plugin_registry.lookup(renderer, version)


def validate_plugin(layer: PluginLayer | Mapping[str, Any]) -> PluginLayer:
    """Validate a layer against the process-global registry."""
    return plugin_registry.validate(layer)


def plugin_json_schema() -> dict[str, Any]:
    """Return the process-global plugin layer JSON Schema."""
    return plugin_registry.json_schema()


def _validate_schema_document(schema: Mapping[str, Any]) -> None:
    """Check that a params schema is itself a JSON-compatible object."""
    if not isinstance(schema, Mapping):
        raise ValueError("plugin params schema must be a JSON object")
    _validate_json_value(dict(schema), "/params_schema")


def _validate_schema_value(value: object, schema: object, path: str) -> None:
    """Validate the JSON Schema subset needed for deterministic plugin params."""
    if schema is True or schema is None:
        return
    if schema is False:
        raise ValidationError(f"Plugin params value at {path} is not allowed.")
    if not isinstance(schema, Mapping):
        raise ValidationError(f"Plugin params schema at {path} must be an object.")
    schema_map = cast(dict[str, Any], schema)

    if "const" in schema_map and value != schema_map["const"]:
        raise ValidationError(f"Plugin params value at {path} must equal {schema_map['const']!r}.")
    if "enum" in schema_map and value not in schema_map["enum"]:
        raise ValidationError(f"Plugin params value at {path} must be one of enum values.")

    alternatives = schema_map.get("oneOf") or schema_map.get("anyOf")
    if alternatives is not None:
        if not isinstance(alternatives, list):
            raise ValidationError(f"Plugin params schema at {path} has invalid alternatives.")
        matches = []
        for alternative in alternatives:
            try:
                _validate_schema_value(value, alternative, path)
            except ValidationError:
                continue
            matches.append(alternative)
        if (schema_map.get("oneOf") and len(matches) != 1) or (
            schema_map.get("anyOf") and not matches
        ):
            raise ValidationError(f"Plugin params value at {path} does not match its schema.")
        return

    schema_type = schema_map.get("type")
    if schema_type is not None and not _matches_json_type(value, schema_type):
        raise ValidationError(f"Plugin params value at {path} must be of type {schema_type!r}.")

    if isinstance(value, dict):
        required = schema_map.get("required", [])
        if not isinstance(required, list) or any(not isinstance(item, str) for item in required):
            raise ValidationError(f"Plugin params schema at {path} has invalid required fields.")
        missing = [key for key in required if key not in value]
        if missing:
            raise ValidationError(
                f"Plugin params missing required field(s) at {path}: {', '.join(missing)}"
            )
        properties = schema_map.get("properties", {})
        if not isinstance(properties, Mapping):
            raise ValidationError(f"Plugin params schema at {path} has invalid properties.")
        additional = schema_map.get("additionalProperties", True)
        for key, item in value.items():
            if key in properties:
                _validate_schema_value(item, properties[key], f"{path}/{key}")
            elif additional is False:
                raise ValidationError(f"Plugin params contains unknown field at {path}/{key}.")
            elif isinstance(additional, Mapping):
                _validate_schema_value(item, additional, f"{path}/{key}")
        _validate_size(value, schema_map, path, "properties")
    elif isinstance(value, list):
        items = schema_map.get("items")
        if items is not None:
            for index, item in enumerate(value):
                _validate_schema_value(item, items, f"{path}/{index}")
        _validate_size(value, schema_map, path, "items")
    elif isinstance(value, str):
        pattern = schema_map.get("pattern")
        if pattern is not None and (
            not isinstance(pattern, str) or re.search(pattern, value) is None
        ):
            raise ValidationError(f"Plugin params value at {path} does not match its pattern.")
        _validate_size(value, schema_map, path, "characters")
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        _validate_number(value, schema_map, path)


def _validate_json_value(value: object, path: str) -> None:
    """Reject non-JSON values used in a registered parameter schema."""
    if value is None or isinstance(value, (bool, int, str)):
        return
    if isinstance(value, float):
        if math.isfinite(value):
            return
        raise ValueError(f"value at {path} must be finite")
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_json_value(item, f"{path}/{index}")
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(f"object keys at {path} must be strings")
            _validate_json_value(item, f"{path}/{key}")
        return
    raise ValueError(f"value at {path} must be JSON-serializable")


def _matches_json_type(value: object, schema_type: object) -> bool:
    """Return whether a value matches a JSON Schema primitive type."""
    if isinstance(schema_type, list):
        return any(_matches_json_type(value, item) for item in schema_type)
    return {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "null": value is None,
    }.get(schema_type, True)


def _validate_size(value: object, schema: Mapping[str, Any], path: str, subject: str) -> None:
    """Apply common size constraints to arrays, objects, and strings."""
    if "minItems" in schema and isinstance(value, list) and len(value) < schema["minItems"]:
        raise ValidationError(
            f"Plugin params at {path} must contain at least {schema['minItems']} {subject}."
        )
    if "maxItems" in schema and isinstance(value, list) and len(value) > schema["maxItems"]:
        raise ValidationError(
            f"Plugin params at {path} must contain at most {schema['maxItems']} {subject}."
        )
    if (
        "minProperties" in schema
        and isinstance(value, dict)
        and len(value) < schema["minProperties"]
    ):
        raise ValidationError(
            f"Plugin params at {path} must contain at least {schema['minProperties']} {subject}."
        )
    if (
        "maxProperties" in schema
        and isinstance(value, dict)
        and len(value) > schema["maxProperties"]
    ):
        raise ValidationError(
            f"Plugin params at {path} must contain at most {schema['maxProperties']} {subject}."
        )
    if "minLength" in schema and isinstance(value, str) and len(value) < schema["minLength"]:
        raise ValidationError(
            f"Plugin params at {path} must contain at least {schema['minLength']} {subject}."
        )
    if "maxLength" in schema and isinstance(value, str) and len(value) > schema["maxLength"]:
        raise ValidationError(
            f"Plugin params at {path} must contain at most {schema['maxLength']} {subject}."
        )


def _validate_number(value: int | float, schema: Mapping[str, Any], path: str) -> None:
    """Apply common numeric constraints to a JSON number."""
    if "minimum" in schema and value < schema["minimum"]:
        raise ValidationError(f"Plugin params value at {path} is below the minimum.")
    if "maximum" in schema and value > schema["maximum"]:
        raise ValidationError(f"Plugin params value at {path} exceeds the maximum.")
    if "exclusiveMinimum" in schema and value <= schema["exclusiveMinimum"]:
        raise ValidationError(f"Plugin params value at {path} is not above the exclusive minimum.")
    if "exclusiveMaximum" in schema and value >= schema["exclusiveMaximum"]:
        raise ValidationError(f"Plugin params value at {path} is not below the exclusive maximum.")
