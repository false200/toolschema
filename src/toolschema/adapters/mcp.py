from __future__ import annotations

from typing import Any

from toolschema._ir import ToolDefinition
from toolschema._schema_utils import strip_canonical_meta
from toolschema.adapters._inline_refs import inline_refs as resolve_inline_refs


def _maybe_inline(schema: dict[str, Any], *, enabled: bool) -> dict[str, Any]:
    if not enabled:
        return schema
    try:
        return resolve_inline_refs(schema)
    except ValueError:
        # Circular models cannot be fully inlined. The remaining ``$ref``
        # values point at ``$defs`` on this same document.
        return schema


def to_mcp(tool: ToolDefinition, *, inline_refs: bool = True) -> dict[str, Any]:
    """Convert ToolDefinition to MCP tools/list format."""
    input_schema = _maybe_inline(strip_canonical_meta(tool.parameters), enabled=inline_refs)

    result: dict[str, Any] = {
        "name": tool.name,
        "description": tool.description,
        "inputSchema": input_schema,
    }

    if tool.output is not None:
        output_schema = _maybe_inline(strip_canonical_meta(tool.output), enabled=inline_refs)
        result["outputSchema"] = output_schema

    return result
