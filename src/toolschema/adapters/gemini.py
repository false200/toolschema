from __future__ import annotations

import copy
from typing import Any

from toolschema._ir import ToolDefinition

_TYPE_MAP = {
    "string": "STRING",
    "integer": "INTEGER",
    "number": "NUMBER",
    "boolean": "BOOLEAN",
    "array": "ARRAY",
    "object": "OBJECT",
    "null": "NULL",
}


def _strip_canonical_meta(schema: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(schema)
    result.pop("$schema", None)
    return result


def _convert_type(schema: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in schema.items():
        if key == "type" and isinstance(value, str):
            result["type"] = _TYPE_MAP.get(value, value.upper())
        elif key == "properties" and isinstance(value, dict):
            result["properties"] = {k: _convert_schema(v) for k, v in value.items()}
        elif key == "items" and isinstance(value, dict):
            result["items"] = _convert_schema(value)
        elif key == "prefixItems" and isinstance(value, list):
            result["prefixItems"] = [
                _convert_schema(item) if isinstance(item, dict) else item for item in value
            ]
        elif key == "additionalProperties" and isinstance(value, dict):
            result["additionalProperties"] = _convert_schema(value)
        elif key in {"anyOf", "oneOf", "allOf"} and isinstance(value, list):
            result[key] = [
                _convert_schema(item) if isinstance(item, dict) else item for item in value
            ]
        elif key == "$defs" and isinstance(value, dict):
            result["$defs"] = {
                name: _convert_schema(item) if isinstance(item, dict) else item
                for name, item in value.items()
            }
        else:
            result[key] = value
    enum_values = result.get("enum")
    if "type" not in result and isinstance(enum_values, list):
        inferred = _enum_type(enum_values)
        if inferred is not None:
            result["type"] = inferred
    return _use_items(_fold_nullable(result))


def _is_null_branch(branch: dict[str, Any]) -> bool:
    """Return whether this branch is only null.

    A null schema is converted to ``{"nullable": true}`` before the parent
    union sees it, so both shapes count.
    """
    if branch.get("type") == "NULL":
        return True
    if branch.get("nullable") is not True:
        return False
    return not any(
        key in branch
        for key in (
            "type",
            "enum",
            "const",
            "properties",
            "items",
            "anyOf",
            "oneOf",
            "allOf",
            "prefixItems",
            "$ref",
            "additionalProperties",
            "format",
        )
    )


def _fold_nullable(result: dict[str, Any]) -> dict[str, Any]:
    """Replace a null union arm with ``nullable: true``.

    Gemini's function-calling type enum has no ``NULL``.
    """
    for key in ("anyOf", "oneOf"):
        branches = result.get(key)
        if not isinstance(branches, list):
            continue
        kept = [
            branch
            for branch in branches
            if not (isinstance(branch, dict) and _is_null_branch(branch))
        ]
        if len(kept) == len(branches):
            continue
        result["nullable"] = True
        if len(kept) == 1 and isinstance(kept[0], dict):
            result.pop(key)
            for branch_key, branch_value in kept[0].items():
                result.setdefault(branch_key, branch_value)
            continue
        if kept:
            result[key] = kept
        else:
            result.pop(key, None)
    if result.get("type") == "NULL":
        result.pop("type")
        result["nullable"] = True
    return result


def _use_items(result: dict[str, Any]) -> dict[str, Any]:
    """Turn ``prefixItems`` into one ``items`` schema.

    shortcut: tuple positions are not kept, use prefixItems if Gemini accepts it.
    """
    prefix = result.pop("prefixItems", None)
    if "items" in result or not isinstance(prefix, list):
        return result
    schemas = [item for item in prefix if isinstance(item, dict)]
    if not schemas:
        return result
    if all(item == schemas[0] for item in schemas):
        result["items"] = schemas[0]
    else:
        result["items"] = {"anyOf": schemas}
    return result


def _enum_type(values: list[Any]) -> str | None:
    if not values:
        return None
    if all(isinstance(value, str) for value in values):
        return "STRING"
    if all(isinstance(value, bool) for value in values):
        return "BOOLEAN"
    if all(isinstance(value, int) and not isinstance(value, bool) for value in values):
        return "INTEGER"
    if all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in values):
        return "NUMBER"
    return None


def _convert_schema(schema: dict[str, Any]) -> dict[str, Any]:
    return _convert_type(copy.deepcopy(schema))


def to_gemini(tool: ToolDefinition) -> dict[str, Any]:
    """Convert ToolDefinition to Gemini FunctionDeclaration format."""
    parameters = _convert_schema(_strip_canonical_meta(tool.parameters))
    if "type" not in parameters:
        parameters["type"] = "OBJECT"

    result: dict[str, Any] = {
        "name": tool.name,
        "description": tool.description,
        "parameters": parameters,
    }
    return result
