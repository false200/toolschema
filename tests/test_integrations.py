from __future__ import annotations

import asyncio

import fixtures
import pytest

from toolschema import schema
from toolschema.integrations.openai_agents import (
    function_tool_kwargs,
    invoke_agents_tool_sync,
    to_agents_function_tool,
    to_openai_agent_tool,
)

pytest.importorskip("fastmcp")
pytest.importorskip("langchain_core")
pytest.importorskip("agents")


def test_fastmcp_register_tool_on_server() -> None:
    from fastmcp import FastMCP

    from toolschema.integrations.fastmcp import register_tool

    definition = schema(fixtures.add)
    mcp = FastMCP("integration")
    registered = register_tool(mcp, definition, fixtures.add)
    assert registered.name == "add"

    async def check() -> None:
        tool = await mcp.get_tool("add")
        payload = tool.to_mcp_tool().model_dump()
        assert payload["inputSchema"]["properties"]["a"]["type"] == "integer"
        result = await tool.run({"a": 2, "b": 3})
        assert result.structured_content == {"result": 5}

    asyncio.run(check())


def test_langchain_from_toolschema_invoke() -> None:
    from toolschema.integrations.langchain import from_toolschema

    definition = schema(fixtures.add)
    structured = from_toolschema(definition, fixtures.add)
    assert structured.name == "add"
    assert structured.invoke({"a": 2, "b": 3}) == 5
    assert structured.args_schema["properties"]["a"]["type"] == "integer"


def test_openai_agents_function_tool_kwargs() -> None:
    definition = schema(fixtures.add)
    kwargs = function_tool_kwargs(definition)
    assert kwargs["name"] == "add"
    assert kwargs["params_json_schema"]["properties"]["a"]["type"] == "integer"


def test_openai_agents_tool_invoke() -> None:
    definition = schema(fixtures.add)
    agents_tool = to_agents_function_tool(definition, fixtures.add, strict=False)
    assert agents_tool.name == "add"
    assert invoke_agents_tool_sync(definition, fixtures.add, {"a": 2, "b": 3}) == 5


def test_openai_agents_tool_payload() -> None:
    definition = schema(fixtures.add)
    payload = to_openai_agent_tool(definition, fixtures.add)
    assert payload["type"] == "function"
    assert payload["callable"] is fixtures.add
    assert payload["agents_tool"].name == "add"


def test_pydantic_ai_tool_descriptor() -> None:
    from toolschema.integrations.pydantic_ai import from_toolschema, to_pydantic_ai_tool

    definition = schema(fixtures.add)
    descriptor = to_pydantic_ai_tool(definition, fixtures.add)
    assert descriptor["name"] == "add"
    assert "parameters_json_schema" in descriptor

    tool = from_toolschema(definition, fixtures.add)
    assert tool.tool_def.name == "add"
    assert tool.function(a=2, b=3) == 5
