"""Structured error vocabulary shared by the Python API and the CLI.

Every quickthumb exception carries one or more :class:`ErrorDetail` records.
A detail is the machine-readable contract: a stable ``code``, the failure
``category``, a human-readable ``message``, an RFC 6901 JSON Pointer ``path``
into the input document, the affected ``layer_id``, and a ``suggestion`` when
a concrete remedy is known. ``str(error)`` renders the same details for people.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any, ClassVar, Literal, cast

from pydantic import BaseModel, ConfigDict
from pydantic import ValidationError as PydanticValidationError

ErrorCategory = Literal["validation", "asset", "export", "input"]


class ErrorDetail(BaseModel):
    """One machine-readable failure attached to a quickthumb error or report."""

    model_config = ConfigDict(extra="forbid")

    code: str
    category: ErrorCategory
    message: str
    path: str | None = None
    layer_id: str | None = None
    suggestion: str | None = None

    def format(self) -> str:
        """Render this detail as one human-readable line."""
        location = self.path or ""
        if self.layer_id:
            location = f"{location} (layer '{self.layer_id}')".lstrip()
        text = f"{location}: {self.message}" if location else self.message
        if self.suggestion and self.suggestion not in self.message:
            text = f"{text.rstrip('.')}. Suggestion: {self.suggestion}."
        return text


class QuickthumbError(Exception):
    category: ClassVar[ErrorCategory] = "export"
    default_code: ClassVar[str] = "export_failed"

    def __init__(
        self,
        message: str = "",
        *,
        code: str | None = None,
        path: str | None = None,
        layer_id: str | None = None,
        suggestion: str | None = None,
        details: Sequence[ErrorDetail] | None = None,
    ):
        super().__init__(message)
        if details is None:
            details = [
                ErrorDetail(
                    code=code or self.default_code,
                    category=self.category,
                    message=message,
                    path=path,
                    layer_id=layer_id,
                    suggestion=suggestion,
                )
            ]
        self._details = list(details)

    def __str__(self) -> str:
        return " | ".join(detail.format() for detail in self._details)

    @property
    def details(self) -> tuple[ErrorDetail, ...]:
        """The structured failures described by this error."""
        return tuple(self._details)

    @property
    def code(self) -> str:
        """The stable code of the primary failure."""
        return self._details[0].code

    def at(self, prefix: str, value: object = None) -> QuickthumbError:
        """Re-anchor detail paths under ``prefix`` in an enclosing document.

        ``value`` is the input found at ``prefix``; when given, details without
        a layer id adopt the id of the innermost layer object on their path.
        """
        self._details = [
            detail.model_copy(
                update={
                    "path": prefix + (detail.path or ""),
                    "layer_id": detail.layer_id or _layer_id_on_path(value, detail.path),
                }
            )
            for detail in self._details
        ]
        return self


class ValidationError(QuickthumbError):
    category = "validation"
    default_code = "invalid_document"

    def __init__(
        self,
        message: str = "",
        original_error: PydanticValidationError | None = None,
        **kwargs: Any,
    ):
        super().__init__(message, **kwargs)
        self._original_error = original_error

    @property
    def original_error(self) -> PydanticValidationError | None:
        return self._original_error

    @classmethod
    def unknown_fields(
        cls, names: Iterable[str], *, owner: str = "JSON object", base: str = ""
    ) -> ValidationError:
        """Report each unexpected key at its own JSON Pointer."""
        details = [
            ErrorDetail(
                code="unknown_field",
                category="validation",
                message=f"{owner} contains unknown field '{name}'",
                path=base + json_pointer(name),
            )
            for name in names
        ]
        return cls(details[0].message, details=details)

    @classmethod
    def from_pydantic(cls, error: PydanticValidationError, data: object) -> ValidationError:
        """Translate pydantic failures into details anchored at ``data``."""
        details = _dedupe(_pydantic_detail(item, data) for item in error.errors())
        return cls(details[0].message, original_error=error, details=details)


class RenderingError(QuickthumbError):
    category = "export"
    default_code = "export_failed"


class MissingAssetError(QuickthumbError, FileNotFoundError):
    """A local asset referenced by a document does not exist."""

    category = "asset"
    default_code = "asset_missing"

    def __init__(self, source: str, *, label: str = "Asset", **kwargs: Any):
        kwargs.setdefault(
            "suggestion",
            "check the path relative to the working directory or use an http(s) URL",
        )
        super().__init__(f"{label} not found: {source!r}", **kwargs)
        self.source = source


class InputError(QuickthumbError):
    """A command-line option or input file cannot be used."""

    category = "input"
    default_code = "invalid_option"


def json_pointer(*parts: str | int) -> str:
    """Build an RFC 6901 JSON Pointer from object keys and array indexes."""
    return "".join("/" + str(part).replace("~", "~0").replace("/", "~1") for part in parts)


_PYDANTIC_CODES = {"missing": "missing_field", "extra_forbidden": "unknown_field"}


def _pydantic_detail(item: Any, data: object) -> ErrorDetail:
    parts = _input_path(data, item["loc"])
    discriminator = item.get("ctx", {}).get("discriminator")
    if item["type"].startswith("union_tag_") and isinstance(discriminator, str):
        parts.append(discriminator.strip("'"))
    message = str(item["msg"]).removeprefix("Value error, ")
    return ErrorDetail(
        code=_PYDANTIC_CODES.get(item["type"], "invalid_field"),
        category="validation",
        message=message,
        path=json_pointer(*parts) if parts else None,
    )


def _input_path(data: object, loc: Sequence[str | int]) -> list[str | int]:
    """Follow a pydantic location through the input, skipping union branch tags."""
    parts: list[str | int] = []
    current = data
    for position, segment in enumerate(loc):
        last = position == len(loc) - 1
        if not last and _is_discriminator_tag(current, segment):
            # A tagged-union branch such as ``shape`` can share its name with a
            # real field; the tag precedes the fields of the selected branch.
            continue
        if _has_child(current, segment):
            current = cast(Any, current)[segment]
        elif (
            last
            and isinstance(current, dict)
            and isinstance(segment, str)
            and not _is_branch_tag(segment)
        ):
            # A missing required key still names a real input location.
            pass
        else:
            continue
        parts.append(segment)
    return parts


def _is_discriminator_tag(value: object, segment: str | int) -> bool:
    if not isinstance(value, dict) or not isinstance(segment, str):
        return False
    mapping = cast(dict[str, Any], value)
    # A same-named scalar field cannot have children, so the location must
    # continue inside the tagged branch rather than inside that field.
    return mapping.get("type") == segment and not isinstance(mapping.get(segment), (dict, list))


def _has_child(value: object, key: str | int) -> bool:
    if isinstance(value, dict):
        return key in value
    return isinstance(value, list) and isinstance(key, int) and 0 <= key < len(value)


def _is_branch_tag(segment: str) -> bool:
    return any(marker in segment for marker in ("[", "(")) or segment[:1].isupper()


def _layer_id_on_path(value: object, path: str | None) -> str | None:
    layer_id = _layer_id(value)
    current = value
    for token in (path or "").split("/")[1:]:
        key: str | int = token.replace("~1", "/").replace("~0", "~")
        if isinstance(current, list) and str(key).isdigit():
            key = int(key)
        if not _has_child(current, key):
            break
        current = cast(Any, current)[key]
        layer_id = _layer_id(current) or layer_id
    return layer_id


def _layer_id(value: object) -> str | None:
    if not isinstance(value, dict):
        return None
    layer = cast(dict[str, Any], value)
    layer_id = layer.get("id")
    return layer_id if "type" in layer and isinstance(layer_id, str) else None


def _dedupe(details: Iterable[ErrorDetail]) -> list[ErrorDetail]:
    unique: dict[tuple[str | None, str], ErrorDetail] = {}
    for detail in details:
        unique.setdefault((detail.path, detail.message), detail)
    return list(unique.values())
