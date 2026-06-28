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
        elif key == "additionalProperties" and isinstance(value, dict):
            result["additionalProperties"] = _convert_schema(value)
        elif key == "anyOf" and isinstance(value, list):
            result["anyOf"] = [_convert_schema(item) for item in value]
        else:
            result[key] = value
    return result


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
