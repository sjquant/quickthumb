"""Deterministic named plugin registrations for the canonical layer contract."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from copy import deepcopy
from typing import Any, cast

from pydantic import ConfigDict, field_validator
from pydantic import ValidationError as PydanticValidationError

from quickthumb._json_values import validate_json_value
from quickthumb._plugin_contract import PLUGIN_NAME_PATTERN, PLUGIN_VERSION_PATTERN
from quickthumb.errors import ValidationError
from quickthumb.models.common import quickthumbModel
from quickthumb.models.layers import PluginLayer


class PluginDefinition(quickthumbModel):
    """Metadata describing one renderer/version pair."""

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
        if info.field_name == "renderer" and not PLUGIN_NAME_PATTERN.fullmatch(value):
            raise ValueError(
                "plugin renderer must start with a letter and contain only letters, "
                "numbers, '.', '_', ':', or '-'"
            )
        if info.field_name == "version" and not PLUGIN_VERSION_PATTERN.fullmatch(value):
            raise ValueError(f"plugin {info.field_name} must not contain surrounding whitespace")
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
        """Register one renderer/version pair and return a detached definition."""
        try:
            definition = self._definition_from_arguments(
                renderer,
                version,
                params_schema,
                schema=schema,
            )
        except PydanticValidationError as error:
            raise ValidationError(
                f"Invalid plugin registration: {error}", original_error=error
            ) from error
        definition = self._copy_definition(definition)
        key = (definition.renderer, definition.version)
        if key in self._definitions and not replace:
            raise ValidationError(
                f"Plugin '{definition.renderer}' version '{definition.version}' "
                "is already registered."
            )
        self._definitions[key] = definition
        return self._copy_definition(definition)

    def unregister(self, renderer: str, version: str | None = None) -> None:
        """Remove one version, or the sole version when no version is supplied."""
        if version is not None:
            self._definitions.pop((renderer, version), None)
            return
        matches = [key for key in self._definitions if key[0] == renderer]
        if len(matches) > 1:
            raise ValidationError(
                f"Plugin renderer '{renderer}' has multiple registered versions; specify version."
            )
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
            if not isinstance(layer, Mapping) or layer.get("type") != "plugin":
                raise ValidationError("Plugin layer must contain type 'plugin'.")
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
            definition = self._definitions.get((renderer, version))
            return None if definition is None else self._copy_definition(definition)
        matches = [
            definition for definition in self.definitions() if definition.renderer == renderer
        ]
        if len(matches) > 1:
            raise ValidationError(
                f"Plugin renderer '{renderer}' has multiple registered versions; specify version."
            )
        return None if not matches else self._copy_definition(matches[0])

    def definitions(self) -> tuple[PluginDefinition, ...]:
        """Return all definitions in deterministic renderer/version order."""
        return tuple(
            self._copy_definition(self._definitions[key]) for key in sorted(self._definitions)
        )

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
                renderer_schema.update({"minLength": 1, "pattern": PLUGIN_NAME_PATTERN.pattern})
            version_schema = base_properties.get("version")
            if isinstance(version_schema, dict):
                version_schema.update({"minLength": 1, "pattern": PLUGIN_VERSION_PATTERN.pattern})
        definitions = self.definitions()
        if not definitions:
            base["title"] = "quickthumb Plugin Layer JSON Spec"
            base["not"] = {}
            return base

        properties = base.get("properties", {})
        variants = [self._definition_schema(definition, properties) for definition in definitions]
        mapping = {
            renderer: f"#/oneOf/{index}"
            for index, definition in enumerate(definitions)
            for renderer in [definition.renderer]
            if sum(item.renderer == renderer for item in definitions) == 1
        }
        discriminator: dict[str, Any] = {"propertyName": "renderer"}
        if mapping:
            discriminator["mapping"] = mapping
        return {
            "title": "quickthumb Plugin Layer JSON Spec",
            "oneOf": variants,
            "discriminator": discriminator,
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
        if selected_schema is not None:
            if not _schema_allows_object(selected_schema):
                raise ValidationError("Plugin params schema must allow a JSON object.")
            normalized_schema = dict(deepcopy(selected_schema))
            normalized_schema["type"] = "object"
        else:
            normalized_schema = None
        return PluginDefinition(
            renderer=renderer,
            version=version,
            params_schema=normalized_schema,
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

    @staticmethod
    def _copy_definition(definition: PluginDefinition) -> PluginDefinition:
        """Return a detached definition so callers cannot mutate registry state."""
        return PluginDefinition(
            renderer=definition.renderer,
            version=definition.version,
            params_schema=definition.params_schema,
        )


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
    """Check that a params schema uses the supported JSON Schema subset."""
    if not isinstance(schema, Mapping):
        raise ValueError("plugin params schema must be a JSON object")
    _validate_schema_node(schema, "/params_schema", root=True)


_SCHEMA_TYPES = frozenset({"object", "array", "string", "number", "integer", "boolean", "null"})
_SCHEMA_KEYWORDS = frozenset(
    {
        "additionalProperties",
        "anyOf",
        "const",
        "description",
        "default",
        "enum",
        "exclusiveMaximum",
        "exclusiveMinimum",
        "items",
        "maxItems",
        "maxLength",
        "maxProperties",
        "maximum",
        "minItems",
        "minLength",
        "minProperties",
        "minimum",
        "oneOf",
        "pattern",
        "properties",
        "required",
        "title",
        "type",
        "$comment",
        "$id",
        "$schema",
    }
)
_NON_NEGATIVE_INTEGER_KEYWORDS = frozenset(
    {"maxItems", "maxLength", "maxProperties", "minItems", "minLength", "minProperties"}
)
_NUMBER_KEYWORDS = frozenset({"exclusiveMaximum", "exclusiveMinimum", "maximum", "minimum"})


def _validate_schema_node(schema: object, path: str, *, root: bool = False) -> None:
    """Validate one schema node before it is stored in the registry."""
    if isinstance(schema, bool):
        return
    if not isinstance(schema, Mapping):
        raise ValueError(f"plugin params schema at {path} must be an object or boolean")
    validate_json_value(schema, path, context="plugin params schema")
    schema_map = dict(schema)
    unsupported = sorted(set(schema_map) - _SCHEMA_KEYWORDS)
    if unsupported:
        raise ValueError(
            f"unsupported plugin params schema keyword(s) at {path}: {', '.join(unsupported)}"
        )

    schema_type = schema_map.get("type")
    if schema_type is not None:
        types = schema_type if isinstance(schema_type, list) else [schema_type]
        if not types or any(
            not isinstance(item, str) or item not in _SCHEMA_TYPES for item in types
        ):
            raise ValueError(f"plugin params schema at {path} has invalid type")
        if root and "object" not in types:
            raise ValueError("plugin params schema must allow a JSON object")

    enum = schema_map.get("enum")
    if enum is not None and not isinstance(enum, list):
        raise ValueError(f"plugin params schema at {path} has invalid enum")

    for keyword in ("oneOf", "anyOf"):
        alternatives = schema_map.get(keyword)
        if alternatives is not None:
            if not isinstance(alternatives, list):
                raise ValueError(f"plugin params schema at {path} has invalid {keyword}")
            for index, alternative in enumerate(alternatives):
                _validate_schema_node(alternative, f"{path}/{keyword}/{index}")

    required = schema_map.get("required")
    if required is not None and (
        not isinstance(required, list) or any(not isinstance(item, str) for item in required)
    ):
        raise ValueError(f"plugin params schema at {path} has invalid required fields")

    properties = schema_map.get("properties")
    if properties is not None:
        if not isinstance(properties, Mapping):
            raise ValueError(f"plugin params schema at {path} has invalid properties")
        for key, child in properties.items():
            if not isinstance(key, str):
                raise ValueError(f"plugin params schema property names at {path} must be strings")
            _validate_schema_node(child, f"{path}/properties/{key}")

    additional = schema_map.get("additionalProperties")
    if additional is not None and not isinstance(additional, bool):
        _validate_schema_node(additional, f"{path}/additionalProperties")

    items = schema_map.get("items")
    if items is not None:
        _validate_schema_node(items, f"{path}/items")

    pattern = schema_map.get("pattern")
    if pattern is not None:
        if not isinstance(pattern, str):
            raise ValueError(f"plugin params schema at {path} has an invalid pattern")
        try:
            re.compile(pattern)
        except re.error as error:
            raise ValueError(
                f"plugin params schema at {path} has an invalid pattern: {error}"
            ) from error

    for keyword in _NON_NEGATIVE_INTEGER_KEYWORDS:
        value = schema_map.get(keyword)
        if value is not None and (
            not isinstance(value, int) or isinstance(value, bool) or value < 0
        ):
            raise ValueError(f"plugin params schema at {path} has invalid {keyword}")
    for keyword in _NUMBER_KEYWORDS:
        value = schema_map.get(keyword)
        if value is not None and (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(value)
        ):
            raise ValueError(f"plugin params schema at {path} has invalid {keyword}")


def _schema_type_allows_object(schema_type: object) -> bool:
    """Return whether a schema type declaration can validate an object."""
    if isinstance(schema_type, list):
        return "object" in schema_type
    return schema_type == "object"


def _schema_allows_object(schema: object) -> bool:
    """Return whether a schema can accept the object-valued params contract."""
    if schema is True:
        return True
    if schema is False or not isinstance(schema, Mapping):
        return False
    schema_map = cast(Mapping[str, Any], schema)
    schema_type = schema_map.get("type")
    if schema_type is not None and not _schema_type_allows_object(schema_type):
        return False
    if "const" in schema_map and not isinstance(schema_map["const"], dict):
        return False
    enum = schema_map.get("enum")
    if enum is not None and (
        not isinstance(enum, list) or not any(isinstance(item, dict) for item in enum)
    ):
        return False
    for keyword in ("oneOf", "anyOf"):
        alternatives = schema_map.get(keyword)
        if alternatives is not None and (
            not isinstance(alternatives, list)
            or not any(_schema_allows_object(alternative) for alternative in alternatives)
        ):
            return False
    return True


def _validate_schema_value(value: object, schema: object, path: str) -> None:
    """Validate the JSON Schema subset needed for deterministic plugin params."""
    if schema is True or schema is None:
        return
    if schema is False:
        raise ValidationError(f"Plugin params value at {path} is not allowed.")
    if not isinstance(schema, Mapping):
        raise ValidationError(f"Plugin params schema at {path} must be an object.")
    schema_map = cast(dict[str, Any], schema)

    if "const" in schema_map and not _json_equal(value, schema_map["const"]):
        raise ValidationError(f"Plugin params value at {path} must equal {schema_map['const']!r}.")
    if "enum" in schema_map and not any(_json_equal(value, item) for item in schema_map["enum"]):
        raise ValidationError(f"Plugin params value at {path} must be one of enum values.")

    for keyword in ("oneOf", "anyOf"):
        alternatives = schema_map.get(keyword)
        if alternatives is None:
            continue
        if not isinstance(alternatives, list):
            raise ValidationError(f"Plugin params schema at {path} has invalid {keyword}.")
        matches = 0
        for alternative in alternatives:
            try:
                _validate_schema_value(value, alternative, path)
            except ValidationError:
                continue
            matches += 1
        if (keyword == "oneOf" and matches != 1) or (keyword == "anyOf" and matches == 0):
            raise ValidationError(f"Plugin params value at {path} does not match its schema.")

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
    }.get(schema_type, False)


def _json_equal(left: object, right: object) -> bool:
    """Compare JSON values with JSON Schema's boolean/number distinction."""
    if (
        isinstance(left, (int, float))
        and not isinstance(left, bool)
        and isinstance(right, (int, float))
        and not isinstance(right, bool)
    ):
        return left == right
    if type(left) is not type(right):
        return False
    if isinstance(left, list):
        if not isinstance(right, list):
            return False
        return len(left) == len(right) and all(
            _json_equal(a, b) for a, b in zip(left, right, strict=True)
        )
    if isinstance(left, dict):
        if not isinstance(right, dict):
            return False
        left_map = cast(dict[str, object], left)
        right_map = cast(dict[str, object], right)
        return left_map.keys() == right_map.keys() and all(
            _json_equal(left_map[key], right_map[key]) for key in left_map
        )
    return left == right


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
