from __future__ import annotations

from collections.abc import Callable
from typing import Any

from toolschema._ir import ToolDefinition
from toolschema._schema_utils import strip_canonical_meta


def to_pydantic_ai_tool(tool: ToolDefinition, fn: Callable[..., Any]) -> dict[str, Any]:
    """Return a pydantic-ai compatible tool descriptor using pre-built schema."""
    openai_tool = tool.to_openai()
    function = openai_tool["function"]
    return {
        "name": function["name"],
        "description": function["description"],
        "parameters_json_schema": strip_canonical_meta(tool.parameters),
        "function": fn,
    }


def from_toolschema(tool: ToolDefinition, fn: Callable[..., Any]) -> Any:
    """Create a pydantic-ai Tool from a ToolDefinition."""
    try:
        from pydantic_ai import Tool
    except ImportError as exc:
        raise ImportError(
            "pydantic-ai is required for from_toolschema. "
            "Install with: pip install toolschema[pydantic-ai]"
        ) from exc

    openai_tool = tool.to_openai()
    function = openai_tool["function"]
    return Tool.from_schema(
        function=fn,
        name=function["name"],
        description=function["description"],
        json_schema=strip_canonical_meta(tool.parameters),
    )


def prepare_toolset(tools: list[tuple[ToolDefinition, Callable[..., Any]]]) -> list[dict[str, Any]]:
    """Convert multiple ToolDefinition/callable pairs for pydantic-ai registration."""
    return [to_pydantic_ai_tool(tool, fn) for tool, fn in tools]
