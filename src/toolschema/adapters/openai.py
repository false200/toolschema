from __future__ import annotations

import copy
from typing import Any

from toolschema._ir import ToolDefinition
from toolschema._schema_utils import strip_canonical_meta


def _strict_schema(node: Any) -> None:
    """Mark every object schema closed and list each of its properties as required.

    A map stays a map: ``additionalProperties`` is left alone when the node has
    no ``properties``. Only ``type: object`` is closed, so the ``properties``
    map itself is not treated as another object.
    """
    if isinstance(node, list):
        for item in node:
            _strict_schema(item)
        return
    if not isinstance(node, dict):
        return
    properties = node.get("properties")
    if node.get("type") == "object" and isinstance(properties, dict):
        node["additionalProperties"] = False
        if properties:
            node["required"] = list(properties)
    for value in node.values():
        if isinstance(value, (dict, list)):
            _strict_schema(value)


def _apply_strict(parameters: dict[str, Any]) -> dict[str, Any]:
    params = copy.deepcopy(parameters)
    _strict_schema(params)
    return params


def to_openai(tool: ToolDefinition, *, strict: bool = False) -> dict[str, Any]:
    """Convert ToolDefinition to OpenAI function-calling tool format."""
    parameters = strip_canonical_meta(tool.parameters)
    if strict:
        parameters = _apply_strict(parameters)

    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": parameters,
        },
    }
