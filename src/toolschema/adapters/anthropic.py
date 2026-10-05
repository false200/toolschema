from __future__ import annotations

import copy
from typing import Any

from toolschema._ir import ToolDefinition
from toolschema._schema_utils import strip_canonical_meta

_CONSTRAINT_KEYS = frozenset(
    {
        "minLength",
        "maxLength",
        "minimum",
        "maximum",
        "exclusiveMinimum",
        "exclusiveMaximum",
        "pattern",
    }
)


def _constraint_to_description(prop: dict[str, Any]) -> str | None:
    parts: list[str] = []
    if "minLength" in prop:
        parts.append(f"min length {prop['minLength']}")
    if "maxLength" in prop:
        parts.append(f"max length {prop['maxLength']}")
    if "minimum" in prop:
        parts.append(f"minimum {prop['minimum']}")
    if "maximum" in prop:
        parts.append(f"maximum {prop['maximum']}")
    if "exclusiveMinimum" in prop:
        parts.append(f"exclusive minimum {prop['exclusiveMinimum']}")
    if "exclusiveMaximum" in prop:
        parts.append(f"exclusive maximum {prop['exclusiveMaximum']}")
    if "pattern" in prop:
        parts.append(f"pattern {prop['pattern']!r}")
    return "; ".join(parts) if parts else None


def _adapt_property(prop: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(prop)
    constraint_desc = _constraint_to_description(result)
    if constraint_desc:
        existing = result.get("description", "")
        suffix = f" ({constraint_desc})"
        result["description"] = f"{existing}{suffix}" if existing else constraint_desc
        for key in _CONSTRAINT_KEYS:
            result.pop(key, None)
    return result


def _adapt_schema(schema: Any) -> Any:
    if isinstance(schema, list):
        return [_adapt_schema(item) for item in schema]
    if not isinstance(schema, dict):
        return schema
    result = _adapt_property(schema)
    for key, value in list(result.items()):
        if key in {"properties", "$defs"} and isinstance(value, dict):
            result[key] = {name: _adapt_schema(child) for name, child in value.items()}
        elif key in {"items", "additionalProperties"} and isinstance(value, dict):
            result[key] = _adapt_schema(value)
        elif key in {"anyOf", "oneOf", "allOf", "prefixItems"} and isinstance(value, list):
            result[key] = [_adapt_schema(item) for item in value]
    return result


def _adapt_input_schema(schema: dict[str, Any]) -> dict[str, Any]:
    return _adapt_schema(strip_canonical_meta(schema))


def to_anthropic(tool: ToolDefinition) -> dict[str, Any]:
    """Convert ToolDefinition to Anthropic tool format."""
    return {
        "name": tool.name,
        "description": tool.description,
        "input_schema": _adapt_input_schema(tool.parameters),
    }
