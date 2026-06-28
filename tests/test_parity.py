from __future__ import annotations

import asyncio
import copy
from collections.abc import Callable
from typing import Any

import fixtures
import pytest

from toolschema import schema

pytest.importorskip("fastmcp")
pytest.importorskip("langchain_core")


def normalize_input_schema(payload: dict[str, Any] | type) -> dict[str, Any]:
    """Normalize provider input schemas for semantic comparison."""
    if isinstance(payload, type):
        from pydantic import BaseModel

        if issubclass(payload, BaseModel):
            payload = payload.model_json_schema()
        else:
            raise TypeError(f"Unsupported schema type: {payload!r}")

    result = copy.deepcopy(payload)
    result.pop("$schema", None)
    result.pop("title", None)
    result.pop("description", None)
    if "required" in result:
        result["required"] = sorted(result["required"])
    properties = result.get("properties")
    if isinstance(properties, dict):
        for prop in properties.values():
            if isinstance(prop, dict):
                prop.pop("title", None)
    return result


def semantic_input_schema(payload: dict[str, Any] | type) -> dict[str, Any]:
    """Extract comparable parameter semantics from an input schema."""
    normalized = normalize_input_schema(payload)
    properties: dict[str, Any] = {}
    for name, prop in normalized.get("properties", {}).items():
        if isinstance(prop, dict):
            properties[name] = {
                key: prop[key]
                for key in ("type", "default", "enum", "description", "anyOf")
                if key in prop
            }
    return {
        "properties": properties,
        "required": sorted(normalized.get("required", [])),
    }


def assert_input_schemas_equivalent(
    left: dict[str, Any] | type, right: dict[str, Any] | type
) -> None:
    assert normalize_input_schema(left) == normalize_input_schema(right)


def assert_input_schemas_semantically_equivalent(
    left: dict[str, Any] | type, right: dict[str, Any] | type
) -> None:
    assert semantic_input_schema(left) == semantic_input_schema(right)


async def fastmcp_input_schema(fn: Callable[..., Any]) -> dict[str, Any]:
    from fastmcp import FastMCP
    from fastmcp.tools.function_tool import FunctionTool

    mcp = FastMCP("parity")
    tool = FunctionTool.from_function(fn)
    mcp.add_tool(tool)
    registered = await mcp.get_tool(tool.name)
    return registered.to_mcp_tool().model_dump()["inputSchema"]


async def toolschema_fastmcp_input_schema(fn: Callable[..., Any]) -> dict[str, Any]:
    from fastmcp import FastMCP

    from toolschema.integrations.fastmcp import register_tool

    mcp = FastMCP("parity")
    definition = schema(fn)
    register_tool(mcp, definition, fn)
    registered = await mcp.get_tool(definition.name)
    return registered.to_mcp_tool().model_dump()["inputSchema"]


@pytest.mark.parametrize("fn", [fixtures.add, fixtures.search_github])
def test_fastmcp_native_matches_toolschema_mcp_input(fn: Callable[..., Any]) -> None:
    definition = schema(fn)
    native = asyncio.run(fastmcp_input_schema(fn))
    toolschema_mcp = definition.to_mcp()["inputSchema"]
    assert_input_schemas_equivalent(native, toolschema_mcp)


@pytest.mark.parametrize("fn", [fixtures.add, fixtures.search_github])
def test_register_tool_matches_toolschema_mcp_input(fn: Callable[..., Any]) -> None:
    definition = schema(fn)
    registered = asyncio.run(toolschema_fastmcp_input_schema(fn))
    toolschema_mcp = definition.to_mcp()["inputSchema"]
    assert_input_schemas_equivalent(registered, toolschema_mcp)


@pytest.mark.parametrize("fn", [fixtures.add, fixtures.search_github])
def test_langchain_integrated_matches_toolschema_openai(fn: Callable[..., Any]) -> None:
    from toolschema.integrations.langchain import from_toolschema

    definition = schema(fn)
    integrated = from_toolschema(definition, fn)
    toolschema_openai = definition.to_openai()["function"]["parameters"]
    assert_input_schemas_equivalent(integrated.args_schema, toolschema_openai)


@pytest.mark.parametrize("fn", [fixtures.add, fixtures.search_github])
def test_langchain_native_semantically_matches_toolschema(fn: Callable[..., Any]) -> None:
    from langchain_core.tools import StructuredTool

    definition = schema(fn)
    native = StructuredTool.from_function(fn)
    toolschema_openai = definition.to_openai()["function"]["parameters"]
    assert_input_schemas_semantically_equivalent(native.args_schema, toolschema_openai)


@pytest.mark.parametrize("fn", [fixtures.add, fixtures.search_github])
def test_openai_agents_schema_matches_toolschema_openai(fn: Callable[..., Any]) -> None:
    pytest.importorskip("agents")
    from toolschema.integrations.openai_agents import to_agents_function_tool

    definition = schema(fn)
    agents_tool = to_agents_function_tool(definition, fn, strict=False)
    toolschema_openai = definition.to_openai()["function"]["parameters"]
    assert_input_schemas_equivalent(agents_tool.params_json_schema, toolschema_openai)


def test_integration_roundtrip_execution() -> None:
    from toolschema.integrations.fastmcp import register_tool
    from toolschema.integrations.langchain import from_toolschema
    from toolschema.integrations.openai_agents import invoke_agents_tool_sync

    definition = schema(fixtures.add)

    async def run_fastmcp() -> Any:
        from fastmcp import FastMCP

        mcp = FastMCP("roundtrip")
        register_tool(mcp, definition, fixtures.add)
        tool = await mcp.get_tool("add")
        result = await tool.run({"a": 4, "b": 5})
        return result.structured_content

    langchain_tool = from_toolschema(definition, fixtures.add)
    assert langchain_tool.invoke({"a": 4, "b": 5}) == 9
    assert asyncio.run(run_fastmcp()) == {"result": 9}
    assert invoke_agents_tool_sync(definition, fixtures.add, {"a": 4, "b": 5}) == 9
