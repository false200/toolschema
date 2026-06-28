from __future__ import annotations

from collections.abc import Callable
from typing import Any

from toolschema._ir import ToolDefinition
from toolschema._schema_utils import strip_canonical_meta


def register_tool(mcp: Any, tool: ToolDefinition, fn: Callable[..., Any]) -> Any:
    """Register a pre-built ToolDefinition on a FastMCP server.

    Uses ``FunctionTool.from_function`` for execution semantics, then replaces
    the generated input schema with the canonical toolschema parameters so schema
    is not generated twice.
    """
    try:
        from fastmcp.tools.function_tool import FunctionTool
    except ImportError as exc:
        raise ImportError(
            "fastmcp is required for register_tool. Install with: pip install toolschema[fastmcp]"
        ) from exc

    function_tool = FunctionTool.from_function(
        fn,
        name=tool.name,
        description=tool.description or None,
    )
    function_tool = function_tool.model_copy(
        update={"parameters": strip_canonical_meta(tool.parameters)}
    )
    return mcp.add_tool(function_tool)


def mcp_tool_payload(tool: ToolDefinition) -> dict[str, Any]:
    """Return MCP tool registration payload without requiring FastMCP."""
    return tool.to_mcp()
