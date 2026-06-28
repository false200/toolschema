from __future__ import annotations

from typing import Any

from toolschema._ir import ToolDefinition
from toolschema._schema_utils import strip_canonical_meta
from toolschema.adapters._inline_refs import inline_refs as resolve_inline_refs


def to_mcp(tool: ToolDefinition, *, inline_refs: bool = True) -> dict[str, Any]:
    """Convert ToolDefinition to MCP tools/list format."""
    input_schema = strip_canonical_meta(tool.parameters)
    if inline_refs:
        input_schema = resolve_inline_refs(input_schema)

    result: dict[str, Any] = {
        "name": tool.name,
        "description": tool.description,
        "inputSchema": input_schema,
    }

    if tool.output is not None:
        output_schema = strip_canonical_meta(tool.output)
        if inline_refs:
            output_schema = resolve_inline_refs(output_schema)
        result["outputSchema"] = output_schema

    return result
