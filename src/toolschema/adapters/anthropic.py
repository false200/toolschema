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


def _adapt_input_schema(schema: dict[str, Any]) -> dict[str, Any]:
    result = strip_canonical_meta(schema)
    properties = result.get("properties")
    if isinstance(properties, dict):
        result["properties"] = {k: _adapt_property(v) for k, v in properties.items()}
    return result


def to_anthropic(tool: ToolDefinition) -> dict[str, Any]:
    """Convert ToolDefinition to Anthropic tool format."""
    return {
        "name": tool.name,
        "description": tool.description,
        "input_schema": _adapt_input_schema(tool.parameters),
    }
