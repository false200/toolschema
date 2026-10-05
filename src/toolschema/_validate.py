from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any
from uuid import UUID

from toolschema._schema_utils import copy_json_value


class ValidationIssueKind(str, Enum):
    REQUIRED = "required"
    TYPE = "type"
    ENUM = "enum"
    CONST = "const"
    CONSTRAINT = "constraint"
    ADDITIONAL_PROPERTY = "additional_property"


@dataclass(frozen=True)
class ValidationIssue:
    message: str
    path: tuple[str | int, ...] = ()
    kind: ValidationIssueKind = ValidationIssueKind.TYPE


@dataclass(frozen=True)
class ValidationSuccess:
    value: dict[str, Any]
    issues: None = None


@dataclass(frozen=True)
class ValidationFailure:
    value: None = None
    issues: tuple[ValidationIssue, ...] = ()


ValidationResult = ValidationSuccess | ValidationFailure


def _issue(
    message: str,
    *,
    path: tuple[str | int, ...] = (),
    kind: ValidationIssueKind = ValidationIssueKind.TYPE,
) -> ValidationIssue:
    return ValidationIssue(message=message, path=path, kind=kind)


def _type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int) and not isinstance(value, bool):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def _json_equal(left: Any, right: Any) -> bool:
    """Return whether two values are equal in the JSON Schema data model.

    Booleans are their own type, so ``True`` is not ``1``. Numbers match by
    mathematical value, so ``1`` and ``1.0`` are equal. Arrays and objects
    are compared element by element.
    """
    if isinstance(left, bool) or isinstance(right, bool):
        return isinstance(left, bool) and isinstance(right, bool) and left == right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return left == right
    if isinstance(left, str) or isinstance(right, str):
        return isinstance(left, str) and isinstance(right, str) and left == right
    if left is None or right is None:
        return left is None and right is None
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(
            _json_equal(item, other) for item, other in zip(left, right, strict=True)
        )
    if isinstance(left, dict) and isinstance(right, dict):
        if set(left) != set(right):
            return False
        return all(_json_equal(left[key], right[key]) for key in left)
    return False


def _matches_type(value: Any, expected: str) -> bool:
    if expected == "null":
        return value is None
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "string":
        return isinstance(value, str)
    if expected == "array":
        return isinstance(value, list)
    if expected == "object":
        return isinstance(value, dict)
    return True


def _validate_constraints(
    value: Any, schema: dict[str, Any], path: tuple[str | int, ...]
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    if isinstance(value, str):
        min_length = schema.get("minLength")
        max_length = schema.get("maxLength")
        pattern = schema.get("pattern")
        if min_length is not None and len(value) < min_length:
            issues.append(
                _issue(
                    f"String too short (minLength {min_length})",
                    path=path,
                    kind=ValidationIssueKind.CONSTRAINT,
                )
            )
        if max_length is not None and len(value) > max_length:
            issues.append(
                _issue(
                    f"String too long (maxLength {max_length})",
                    path=path,
                    kind=ValidationIssueKind.CONSTRAINT,
                )
            )
        if pattern is not None:
            try:
                matched = re.search(pattern, value) is not None
            except re.error:
                issues.append(
                    _issue(
                        f"Invalid pattern {pattern!r}",
                        path=path,
                        kind=ValidationIssueKind.CONSTRAINT,
                    )
                )
                matched = True
            if not matched:
                issues.append(
                    _issue(
                        f"String does not match pattern {pattern!r}",
                        path=path,
                        kind=ValidationIssueKind.CONSTRAINT,
                    )
                )

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        minimum = schema.get("minimum")
        maximum = schema.get("maximum")
        exclusive_minimum = schema.get("exclusiveMinimum")
        exclusive_maximum = schema.get("exclusiveMaximum")
        if minimum is not None and value < minimum:
            issues.append(
                _issue(
                    f"Value must be >= {minimum}", path=path, kind=ValidationIssueKind.CONSTRAINT
                )
            )
        if maximum is not None and value > maximum:
            issues.append(
                _issue(
                    f"Value must be <= {maximum}", path=path, kind=ValidationIssueKind.CONSTRAINT
                )
            )
        if exclusive_minimum is not None and value <= exclusive_minimum:
            issues.append(
                _issue(
                    f"Value must be > {exclusive_minimum}",
                    path=path,
                    kind=ValidationIssueKind.CONSTRAINT,
                )
            )
        if exclusive_maximum is not None and value >= exclusive_maximum:
            issues.append(
                _issue(
                    f"Value must be < {exclusive_maximum}",
                    path=path,
                    kind=ValidationIssueKind.CONSTRAINT,
                )
            )
        multiple_of = schema.get("multipleOf")
        if multiple_of is not None and not _is_multiple(value, multiple_of):
            issues.append(
                _issue(
                    f"Value must be a multiple of {multiple_of}",
                    path=path,
                    kind=ValidationIssueKind.CONSTRAINT,
                )
            )

    format_name = schema.get("format")
    if (
        isinstance(format_name, str)
        and isinstance(value, str)
        and not _matches_format(value, format_name)
    ):
        issues.append(
            _issue(
                f"String does not match format {format_name!r}",
                path=path,
                kind=ValidationIssueKind.CONSTRAINT,
            )
        )

    return issues


def _is_multiple(value: int | float, multiple: Any) -> bool:
    if isinstance(multiple, bool) or not isinstance(multiple, (int, float)) or multiple == 0:
        return False
    try:
        quotient = Decimal(str(value)) / Decimal(str(multiple))
    except (InvalidOperation, ValueError):
        return False
    return quotient == quotient.to_integral_value()


def _matches_format(value: str, format_name: str) -> bool:
    if format_name == "date-time":
        text = value[:-1] + "+00:00" if value.endswith("Z") else value
        try:
            datetime.fromisoformat(text)
        except ValueError:
            return False
        return True
    if format_name == "date":
        try:
            date.fromisoformat(value)
        except ValueError:
            return False
        return True
    if format_name == "time":
        try:
            time.fromisoformat(value)
        except ValueError:
            return False
        return True
    if format_name == "uuid":
        try:
            UUID(value)
        except ValueError:
            return False
        return True
    return True


def _schema_types(schema: dict[str, Any]) -> list[str]:
    json_type = schema.get("type")
    if isinstance(json_type, str):
        return [json_type]
    if isinstance(json_type, list):
        return [item for item in json_type if isinstance(item, str)]
    return []


def _enum_contains(value: Any, options: list[Any]) -> bool:
    return any(_json_equal(value, option) for option in options)


def _root_defs(schema: dict[str, Any]) -> dict[str, Any]:
    defs = schema.get("$defs")
    return defs if isinstance(defs, dict) else {}


def _with_defaults(
    value: Any,
    schema: dict[str, Any],
    defs: dict[str, Any] | None = None,
    seen: frozenset[tuple[str, int]] = frozenset(),
) -> Any:
    """Copy ``value`` and fill nested defaults from ``schema``."""
    if defs is None:
        defs = _root_defs(schema)
    if "$ref" in schema:
        ref = schema["$ref"]
        if isinstance(ref, str) and ref.startswith("#/$defs/"):
            token = (ref, id(value))
            target = defs.get(ref.removeprefix("#/$defs/"))
            if token not in seen and isinstance(target, dict):
                return _with_defaults(value, target, defs, seen | {token})
        return value
    if "anyOf" in schema and isinstance(schema.get("anyOf"), list):
        for branch in schema["anyOf"]:
            if isinstance(branch, dict) and not _validate_value(value, branch, defs=defs):
                return _with_defaults(value, branch, defs, seen)
        return value
    object_schema = schema.get("type") == "object" or "object" in _schema_types(schema)
    if isinstance(value, dict) and (object_schema or "properties" in schema):
        properties = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
        additional = schema.get("additionalProperties")
        filled: dict[str, Any] = {}
        for key, item in value.items():
            prop = properties.get(key)
            if isinstance(prop, dict):
                filled[key] = _with_defaults(item, prop, defs, seen)
            elif isinstance(additional, dict):
                filled[key] = _with_defaults(item, additional, defs, seen)
            else:
                filled[key] = item
        for key, prop in properties.items():
            if key not in filled and isinstance(prop, dict) and "default" in prop:
                filled[key] = copy_json_value(prop["default"])
        return filled
    if isinstance(value, list) and (
        schema.get("type") == "array"
        or "array" in _schema_types(schema)
        or "items" in schema
        or "prefixItems" in schema
    ):
        prefix = schema.get("prefixItems") if isinstance(schema.get("prefixItems"), list) else []
        items_schema = schema.get("items") if isinstance(schema.get("items"), dict) else None
        filled_items: list[Any] = []
        for index, item in enumerate(value):
            if index < len(prefix) and isinstance(prefix[index], dict):
                child = prefix[index]
            else:
                child = items_schema
            if isinstance(child, dict):
                filled_items.append(_with_defaults(item, child, defs, seen))
            else:
                filled_items.append(item)
        return filled_items
    return value


def _validate_value(
    value: Any,
    schema: dict[str, Any],
    path: tuple[str | int, ...] = (),
    defs: dict[str, Any] | None = None,
    seen: frozenset[tuple[str, int]] = frozenset(),
) -> list[ValidationIssue]:
    if defs is None:
        defs = _root_defs(schema)

    if "$ref" in schema:
        ref = schema["$ref"]
        if not isinstance(ref, str) or not ref.startswith("#/$defs/"):
            return [_issue(f"Unsupported $ref {ref!r}", path=path)]
        token = (ref, id(value))
        if token in seen:
            return []
        target = defs.get(ref.removeprefix("#/$defs/"))
        if not isinstance(target, dict):
            return [_issue(f"Unresolved $ref {ref!r}", path=path)]
        issues = _validate_value(value, target, path, defs, seen | {token})
        rest = {key: item for key, item in schema.items() if key not in {"$ref", "$defs"}}
        if rest:
            issues.extend(_validate_value(value, rest, path, defs, seen))
        return issues

    if "anyOf" in schema:
        # Applicator keywords do not replace the rest of the schema.
        # Annotated[str | None, Field(min_length=1)] is anyOf plus minLength;
        # a string that matches the first branch can still be too short.
        branch_issues = [
            _validate_value(value, branch, path, defs, seen) for branch in schema["anyOf"]
        ]
        if not any(not branch for branch in branch_issues):
            return [
                _issue(
                    f"Value {_type_name(value)!r} does not match anyOf",
                    path=path,
                    kind=ValidationIssueKind.TYPE,
                )
            ]
        rest = {key: item for key, item in schema.items() if key != "anyOf"}
        if not rest:
            return []
        return _validate_value(value, rest, path, defs, seen)

    if "enum" in schema and not _enum_contains(value, schema["enum"]):
        return [
            _issue(
                f"Value {value!r} is not in enum {schema['enum']!r}",
                path=path,
                kind=ValidationIssueKind.ENUM,
            )
        ]

    # ``"const": null`` is a present keyword. ``dict.get`` cannot tell that
    # apart from a missing key, and Python ``==`` treats ``True`` as ``1``.
    if "const" in schema and not _json_equal(value, schema["const"]):
        return [
            _issue(
                f"Value {value!r} is not const {schema['const']!r}",
                path=path,
                kind=ValidationIssueKind.CONST,
            )
        ]

    types = _schema_types(schema)
    if types and not any(_matches_type(value, expected) for expected in types):
        expected = schema.get("type")
        return [
            _issue(
                f"Expected {expected}, got {_type_name(value)}",
                path=path,
                kind=ValidationIssueKind.TYPE,
            )
        ]

    issues = _validate_constraints(value, schema, path)
    array_like = isinstance(value, list) and (
        "array" in types or (not types and ("items" in schema or "prefixItems" in schema))
    )
    if array_like:
        min_items = schema.get("minItems")
        max_items = schema.get("maxItems")
        if min_items is not None and len(value) < min_items:
            issues.append(
                _issue(
                    f"Array too short (minItems {min_items})",
                    path=path,
                    kind=ValidationIssueKind.CONSTRAINT,
                )
            )
        if max_items is not None and len(value) > max_items:
            issues.append(
                _issue(
                    f"Array too long (maxItems {max_items})",
                    path=path,
                    kind=ValidationIssueKind.CONSTRAINT,
                )
            )
        if schema.get("uniqueItems") is True and _has_duplicate(value):
            issues.append(
                _issue(
                    "Array items must be unique",
                    path=path,
                    kind=ValidationIssueKind.CONSTRAINT,
                )
            )

        prefix_items = schema.get("prefixItems")
        if isinstance(prefix_items, list):
            for index, item_schema in enumerate(prefix_items):
                if index < len(value) and isinstance(item_schema, dict):
                    issues.extend(
                        _validate_value(value[index], item_schema, path + (index,), defs, seen)
                    )
            items_schema = schema.get("items")
            if isinstance(items_schema, dict):
                for index, item in enumerate(value[len(prefix_items) :], start=len(prefix_items)):
                    issues.extend(_validate_value(item, items_schema, path + (index,), defs, seen))
        elif isinstance(schema.get("items"), dict):
            for index, item in enumerate(value):
                issues.extend(_validate_value(item, schema["items"], path + (index,), defs, seen))

    object_like = isinstance(value, dict) and (
        "object" in types or (not types and "properties" in schema)
    )
    if object_like:
        properties = schema.get("properties", {})
        required = set(schema.get("required", []))

        if schema.get("additionalProperties") is False:
            extra = set(value) - set(properties)
            for key in sorted(extra):
                issues.append(
                    _issue(
                        f"Additional property {key!r} is not allowed",
                        path=path + (key,),
                        kind=ValidationIssueKind.ADDITIONAL_PROPERTY,
                    )
                )

        for key in sorted(required):
            if key not in value:
                prop_schema = properties.get(key, {})
                if "default" not in prop_schema:
                    issues.append(
                        _issue(
                            f"Missing required property {key!r}",
                            path=path + (key,),
                            kind=ValidationIssueKind.REQUIRED,
                        )
                    )

        for key, prop_schema in properties.items():
            if key in value and isinstance(prop_schema, dict):
                issues.extend(_validate_value(value[key], prop_schema, path + (key,), defs, seen))

        additional = schema.get("additionalProperties")
        if isinstance(additional, dict):
            for key, item in value.items():
                if key not in properties:
                    issues.extend(_validate_value(item, additional, path + (key,), defs, seen))

    return issues


def _has_duplicate(values: list[Any]) -> bool:
    for index, item in enumerate(values):
        for previous in values[:index]:
            if _json_equal(item, previous):
                return True
    return False


def validate_arguments(args: Any, parameters_schema: dict[str, Any]) -> ValidationResult:
    """Validate tool arguments against a JSON Schema parameters object."""
    if not isinstance(args, dict):
        return ValidationFailure(
            issues=(
                _issue(
                    f"Arguments must be an object, got {_type_name(args)}",
                    kind=ValidationIssueKind.TYPE,
                ),
            )
        )

    normalized = _with_defaults(args, parameters_schema)
    issues = _validate_value(normalized, parameters_schema)
    if issues:
        return ValidationFailure(issues=tuple(issues))
    return ValidationSuccess(value=normalized)
