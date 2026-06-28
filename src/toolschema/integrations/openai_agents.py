from __future__ import annotations

import asyncio
import inspect
import json
from collections.abc import Callable
from typing import Any

from toolschema._ir import ToolDefinition


def function_tool_kwargs(tool: ToolDefinition, *, strict: bool = False) -> dict[str, Any]:
    """Return kwargs suitable for OpenAI Agents FunctionTool constructors."""
    openai_tool = tool.to_openai(strict=strict)
    function = openai_tool["function"]
    return {
        "name": function["name"],
        "description": function["description"],
        "params_json_schema": function["parameters"],
        "strict_json_schema": strict,
    }


def to_agents_function_tool(
    tool: ToolDefinition,
    fn: Callable[..., Any],
    *,
    strict: bool = False,
) -> Any:
    """Create an OpenAI Agents SDK FunctionTool from a ToolDefinition."""
    try:
        from agents.tool import FunctionTool
    except ImportError as exc:
        raise ImportError(
            "openai-agents is required for to_agents_function_tool. "
            "Install with: pip install toolschema[openai-agents]"
        ) from exc

    kwargs = function_tool_kwargs(tool, strict=strict)

    async def on_invoke_tool(_ctx: Any, input_json: str) -> Any:
        payload = json.loads(input_json) if input_json else {}
        result = fn(**payload)
        if inspect.isawaitable(result):
            return await result
        return result

    return FunctionTool(
        name=kwargs["name"],
        description=kwargs["description"],
        params_json_schema=kwargs["params_json_schema"],
        on_invoke_tool=on_invoke_tool,
        strict_json_schema=kwargs["strict_json_schema"],
    )


def to_openai_agent_tool(tool: ToolDefinition, fn: Callable[..., Any]) -> dict[str, Any]:
    """Return an OpenAI Agents SDK-compatible registration payload."""
    payload = tool.to_openai()
    return {
        **payload,
        "callable": fn,
        "agents_tool": to_agents_function_tool(tool, fn, strict=False),
    }


async def invoke_agents_tool(
    tool: ToolDefinition, fn: Callable[..., Any], arguments: dict[str, Any]
) -> Any:
    """Invoke a toolschema-backed OpenAI Agents FunctionTool."""
    agents_tool = to_agents_function_tool(tool, fn, strict=False)
    return await agents_tool.on_invoke_tool(None, json.dumps(arguments))


def invoke_agents_tool_sync(
    tool: ToolDefinition, fn: Callable[..., Any], arguments: dict[str, Any]
) -> Any:
    """Synchronous wrapper around :func:`invoke_agents_tool`."""
    return asyncio.run(invoke_agents_tool(tool, fn, arguments))
