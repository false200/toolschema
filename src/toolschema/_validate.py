from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any


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
        if pattern is not None and re.search(pattern, value) is None:
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

    return issues


def _validate_value(
    value: Any, schema: dict[str, Any], path: tuple[str | int, ...] = ()
) -> list[ValidationIssue]:
    if "anyOf" in schema:
        # Applicator keywords do not replace the rest of the schema.
        # Annotated[str | None, Field(min_length=1)] is anyOf plus minLength;
        # a string that matches the first branch can still be too short.
        branch_issues = [_validate_value(value, branch, path) for branch in schema["anyOf"]]
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
        return _validate_value(value, rest, path)

    if "enum" in schema and value not in schema["enum"]:
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

    json_type = schema.get("type")
    if json_type and not _matches_type(value, json_type):
        return [
            _issue(
                f"Expected {json_type}, got {_type_name(value)}",
                path=path,
                kind=ValidationIssueKind.TYPE,
            )
        ]

    issues = _validate_constraints(value, schema, path)

    if json_type == "array" and isinstance(value, list):
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

        prefix_items = schema.get("prefixItems")
        if isinstance(prefix_items, list):
            for index, item_schema in enumerate(prefix_items):
                if index < len(value) and isinstance(item_schema, dict):
                    issues.extend(_validate_value(value[index], item_schema, path + (index,)))
            items_schema = schema.get("items")
            if isinstance(items_schema, dict):
                for index, item in enumerate(value[len(prefix_items) :], start=len(prefix_items)):
                    issues.extend(_validate_value(item, items_schema, path + (index,)))
        elif isinstance(schema.get("items"), dict):
            for index, item in enumerate(value):
                issues.extend(_validate_value(item, schema["items"], path + (index,)))

    if json_type == "object" and isinstance(value, dict):
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
            if key in value:
                issues.extend(_validate_value(value[key], prop_schema, path + (key,)))

        additional = schema.get("additionalProperties")
        if isinstance(additional, dict):
            for key, item in value.items():
                if key not in properties:
                    issues.extend(_validate_value(item, additional, path + (key,)))

    return issues


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

    if parameters_schema.get("type") != "object":
        issues = _validate_value(args, parameters_schema)
        return ValidationFailure(issues=tuple(issues)) if issues else ValidationSuccess(value=args)

    properties = parameters_schema.get("properties", {})
    required = set(parameters_schema.get("required", []))
    issues: list[ValidationIssue] = []

    for key in sorted(required):
        if key not in args:
            prop_schema = properties.get(key, {})
            if "default" not in prop_schema:
                issues.append(
                    _issue(
                        f"Missing required property {key!r}",
                        path=(key,),
                        kind=ValidationIssueKind.REQUIRED,
                    )
                )

    normalized = dict(args)
    for key, prop_schema in properties.items():
        if key not in normalized and isinstance(prop_schema, dict) and "default" in prop_schema:
            normalized[key] = prop_schema["default"]

    if parameters_schema.get("additionalProperties") is False:
        extra = set(normalized) - set(properties)
        for key in sorted(extra):
            issues.append(
                _issue(
                    f"Additional property {key!r} is not allowed",
                    path=(key,),
                    kind=ValidationIssueKind.ADDITIONAL_PROPERTY,
                )
            )

    for key, prop_schema in properties.items():
        if key in normalized:
            issues.extend(_validate_value(normalized[key], prop_schema, (key,)))

    if issues:
        return ValidationFailure(issues=tuple(issues))
    return ValidationSuccess(value=normalized)
