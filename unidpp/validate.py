"""Minimal JSON Schema (draft 2020-12 subset) validator.

Hand-rolled to keep the SDK dependency-free — a faithful port of
``@unidpp/model`` ``validate.ts``. Supports exactly the keywords the
``@unidpp`` schemas use: ``$ref`` (local ``$defs``), ``type``, ``enum``,
``const``, ``required``, ``properties``, ``additionalProperties``,
``items``, ``pattern``, ``format`` (``date-time``, ``date``, ``uri``),
string/array length bounds, numeric bounds, ``allOf``/``anyOf``/``oneOf``,
``$defs``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

__all__ = ["JsonSchema", "ValidationIssue", "ValidationResult", "validate"]


JsonSchema = dict[str, Any]

_DATETIME_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(\.\d+)?([Zz]|[+-]\d{2}:\d{2})$"
)
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_URI_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:[^\s]*$")

_TYPE_MAP = {
    "object": dict,
    "array": list,
    "string": str,
    "boolean": bool,
    "null": type(None),
}


@dataclass
class ValidationIssue:
    path: str
    keyword: str
    message: str


@dataclass
class ValidationResult:
    valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)


def _resolve_ref(ref: str, root: JsonSchema) -> JsonSchema | None:
    if ref == "#":
        return root
    if not ref.startswith("#/"):
        return None
    node: Any = root
    for part in ref[2:].split("/"):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def _type_matches(instance: Any, expected: str) -> bool:
    if expected == "integer":
        return isinstance(instance, int) and not isinstance(instance, bool)
    if expected == "number":
        return isinstance(instance, (int, float)) and not isinstance(instance, bool)
    py = _TYPE_MAP.get(expected)
    if py is None:
        return True
    if py is bool:
        return isinstance(instance, bool)
    if py is str:
        return isinstance(instance, str)
    if py is dict:
        return isinstance(instance, dict)
    if py is list:
        return isinstance(instance, list)
    return instance is None


def _check_format(instance: str, fmt: str) -> bool:
    if fmt == "date-time":
        return bool(_DATETIME_RE.match(instance))
    if fmt == "date":
        return bool(_DATE_RE.match(instance))
    if fmt == "uri":
        return bool(_URI_RE.match(instance))
    return True


def _check(
    instance: Any,
    schema: JsonSchema,
    root: JsonSchema,
    path: str,
    issues: list[ValidationIssue],
) -> None:
    if schema.get("$ref") is not None:
        resolved = _resolve_ref(schema["$ref"], root)
        if resolved is None:
            issues.append(
                ValidationIssue(path, "$ref", f"unresolvable $ref: {schema['$ref']}")
            )
            return
        _check(instance, resolved, root, path, issues)
        return

    if "allOf" in schema:
        for sub in schema["allOf"]:
            _check(instance, sub, root, path, issues)
    if "anyOf" in schema and not any(
        not _validate_nested(instance, sub, root) for sub in schema["anyOf"]
    ):
        issues.append(
            ValidationIssue(path, "anyOf", "value matches no schemas")
        )
    if "oneOf" in schema:
        matches = sum(
            1 for sub in schema["oneOf"] if not _validate_nested(instance, sub, root)
        )
        if matches != 1:
            issues.append(
                ValidationIssue(
                    path, "oneOf", f"value matches {matches} schemas, expected exactly 1"
                )
            )
            return

    if "type" in schema:
        expected = schema["type"]
        options = expected if isinstance(expected, list) else [expected]
        if not any(_type_matches(instance, opt) for opt in options):
            issues.append(
                ValidationIssue(
                    path,
                    "type",
                    f"expected {expected}, got {type(instance).__name__}",
                )
            )
            return

    if "enum" in schema and instance not in schema["enum"]:
        issues.append(
            ValidationIssue(
                path, "enum", f"value {instance!r} not in enum {schema['enum']}"
            )
        )
    if "const" in schema and instance != schema["const"]:
        issues.append(
            ValidationIssue(path, "const", f"value {instance!r} != const {schema['const']!r}")
        )

    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < schema["minLength"]:
            issues.append(
                ValidationIssue(path, "minLength", f"shorter than {schema['minLength']}")
            )
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            issues.append(
                ValidationIssue(path, "maxLength", f"longer than {schema['maxLength']}")
            )
        if "pattern" in schema and re.search(schema["pattern"], instance) is None:
            issues.append(
                ValidationIssue(
                    path, "pattern", f"does not match {schema['pattern']}"
                )
            )
        if "format" in schema and not _check_format(instance, schema["format"]):
            issues.append(
                ValidationIssue(
                    path, "format", f"not a valid {schema['format']}: {instance!r}"
                )
            )

    if isinstance(instance, bool):
        pass
    elif isinstance(instance, (int, float)):
        if "minimum" in schema and instance < schema["minimum"]:
            issues.append(
                ValidationIssue(path, "minimum", f"below minimum {schema['minimum']}")
            )
        if "maximum" in schema and instance > schema["maximum"]:
            issues.append(
                ValidationIssue(path, "maximum", f"above maximum {schema['maximum']}")
            )

    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            issues.append(
                ValidationIssue(path, "minItems", f"fewer than {schema['minItems']} items")
            )
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            issues.append(
                ValidationIssue(path, "maxItems", f"more than {schema['maxItems']} items")
            )
        if "items" in schema:
            for i, item in enumerate(instance):
                _check(item, schema["items"], root, f"{path}[{i}]", issues)

    if isinstance(instance, dict):
        props = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in instance:
                issues.append(
                    ValidationIssue(path, "required", f"missing required property {key!r}")
                )
        for key, value in instance.items():
            if key in props:
                _check(value, props[key], root, f"{path}.{key}", issues)
            else:
                ap = schema.get("additionalProperties", True)
                if ap is False:
                    issues.append(
                        ValidationIssue(
                            path,
                            "additionalProperties",
                            f"additional property {key!r} not allowed",
                        )
                    )
                elif isinstance(ap, dict):
                    _check(value, ap, root, f"{path}.{key}", issues)


def _validate_nested(instance: Any, schema: JsonSchema, root: JsonSchema) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    _check(instance, schema, root, "$", issues)
    return issues


def validate(instance: Any, schema: JsonSchema, root: JsonSchema | None = None) -> ValidationResult:
    """Validate ``instance`` against ``schema`` (subset of draft 2020-12)."""
    if root is None:
        root = schema
    issues = _validate_nested(instance, schema, root)
    return ValidationResult(valid=len(issues) == 0, issues=issues)
