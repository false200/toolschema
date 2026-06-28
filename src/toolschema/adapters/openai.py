from __future__ import annotations

import copy
from typing import Any

from toolschema._ir import ToolDefinition
from toolschema._schema_utils import strip_canonical_meta


def _apply_strict(parameters: dict[str, Any]) -> dict[str, Any]:
    params = copy.deepcopy(parameters)
    params["additionalProperties"] = False
    properties = params.get("properties", {})
    if properties:
        params["required"] = list(properties.keys())
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
