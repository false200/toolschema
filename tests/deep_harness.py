"""Shared harness for deep cross-agent integration tests."""

from __future__ import annotations

import copy
import json
import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import complex_fixtures
import fixtures

from toolschema import ValidationFailure, ValidationSuccess, schema
from toolschema._ir import ToolDefinition

SEARCH_ARGS: dict[str, Any] = {
    "query": "laptop",
    "category": "computers",
    "sort": "asc",
    "limit": 3,
    "include_metadata": False,
    "mode": "fuzzy",
}

BOOK_ARGS: dict[str, Any] = {
    "origin": "JFK",
    "destination": "LHR",
    "passengers": 2,
    "cabin": "business",
    "flexible_dates": True,
}

ADD_ARGS: dict[str, Any] = {"a": 10, "b": 32}


def semantic_input_schema(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = copy.deepcopy(payload)
    normalized.pop("$schema", None)
    normalized.pop("title", None)
    if "required" in normalized:
        normalized["required"] = sorted(normalized["required"])
    properties = normalized.get("properties")
    if isinstance(properties, dict):
        for prop in properties.values():
            if isinstance(prop, dict):
                prop.pop("title", None)
    props: dict[str, Any] = {}
    for name, prop in normalized.get("properties", {}).items():
        if isinstance(prop, dict):
            props[name] = {
                key: prop[key]
                for key in ("type", "default", "enum", "description", "anyOf")
                if key in prop
            }
    return {
        "properties": props,
        "required": sorted(normalized.get("required", [])),
    }


def assert_provider_adapters(tool: ToolDefinition) -> None:
    openai = tool.to_openai()
    assert openai["type"] == "function"
    assert openai["function"]["name"] == tool.name
    assert openai["function"]["parameters"]["type"] == "object"

    strict = tool.to_openai(strict=True)
    strict_params = strict["function"]["parameters"]
    assert strict_params["additionalProperties"] is False
    assert set(strict_params["required"]) == set(strict_params["properties"])

    mcp = tool.to_mcp()
    assert mcp["name"] == tool.name
    assert mcp["inputSchema"]["type"] == "object"
    assert "$ref" not in json.dumps(mcp)

    anthropic = tool.to_anthropic()
    assert anthropic["name"] == tool.name
    assert anthropic["input_schema"]["type"] == "object"

    gemini = tool.to_gemini()
    assert gemini["name"] == tool.name
    assert "parameters" in gemini


def assert_validate(tool: ToolDefinition, good: dict[str, Any], bad: dict[str, Any]) -> None:
    ok = tool.validate(good)
    if not isinstance(ok, ValidationSuccess):
        raise AssertionError(f"expected success for {good!r}, got {ok!r}")
    fail = tool.validate(bad)
    if not isinstance(fail, ValidationFailure):
        raise AssertionError(f"expected failure for {bad!r}, got {fail!r}")


def search_result_name(result: Any) -> str:
    if isinstance(result, list):
        return result[0]["name"]
    if isinstance(result, dict) and "result" in result:
        payload = result["result"]
        if isinstance(payload, list):
            return payload[0]["name"]
    raise AssertionError(f"unexpected search result shape: {result!r}")


def run_langchain_search() -> str:
    from toolschema.integrations.langchain import from_toolschema

    definition = schema(complex_fixtures.search_products)
    structured = from_toolschema(definition, complex_fixtures.search_products)
    result = structured.invoke(SEARCH_ARGS)
    return search_result_name(result)


async def run_fastmcp_search() -> str:
    from fastmcp import FastMCP

    from toolschema.integrations.fastmcp import register_tool

    definition = schema(complex_fixtures.search_products)
    mcp = FastMCP("deep-harness")
    register_tool(mcp, definition, complex_fixtures.search_products)
    tool = await mcp.get_tool("search_products")
    result = await tool.run(SEARCH_ARGS)
    return search_result_name(result.structured_content)


def run_openai_agents_search() -> str:
    from toolschema.integrations.openai_agents import invoke_agents_tool_sync

    definition = schema(complex_fixtures.search_products)
    result = invoke_agents_tool_sync(definition, complex_fixtures.search_products, SEARCH_ARGS)
    return search_result_name(result)


def run_pydantic_ai_search() -> str:
    from toolschema.integrations.pydantic_ai import from_toolschema

    definition = schema(complex_fixtures.search_products)
    tool = from_toolschema(definition, complex_fixtures.search_products)
    result = tool.function(**SEARCH_ARGS)
    return search_result_name(result)


def run_pydantic_ai_agent() -> list[str]:
    from pydantic_ai import Agent
    from pydantic_ai.models.test import TestModel

    from toolschema.integrations.pydantic_ai import from_toolschema

    tools = [
        from_toolschema(schema(fixtures.add), fixtures.add),
        from_toolschema(schema(complex_fixtures.search_products), complex_fixtures.search_products),
        from_toolschema(schema(complex_fixtures.book_flight), complex_fixtures.book_flight),
    ]
    test_model = TestModel(call_tools="all")
    agent = Agent(test_model, tools=tools)
    agent.run_sync("deep integration test")
    registered = test_model.last_model_request_parameters
    assert registered is not None
    return [tool.name for tool in registered.function_tools]


def run_langchain_add() -> int:
    from toolschema.integrations.langchain import from_toolschema

    definition = schema(fixtures.add)
    return from_toolschema(definition, fixtures.add).invoke(ADD_ARGS)


async def run_fastmcp_add() -> int:
    from fastmcp import FastMCP

    from toolschema.integrations.fastmcp import register_tool

    definition = schema(fixtures.add)
    mcp = FastMCP("deep-harness-add")
    register_tool(mcp, definition, fixtures.add)
    tool = await mcp.get_tool("add")
    result = await tool.run(ADD_ARGS)
    payload = result.structured_content
    if isinstance(payload, dict) and "result" in payload:
        return int(payload["result"])
    return int(payload)


def run_openai_agents_add() -> int:
    from toolschema.integrations.openai_agents import invoke_agents_tool_sync

    definition = schema(fixtures.add)
    return int(invoke_agents_tool_sync(definition, fixtures.add, ADD_ARGS))


async def mcp_stdio_deep() -> None:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    tests_dir = Path(__file__).resolve().parent
    project_root = tests_dir.parent
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([str(project_root / "src"), str(tests_dir)])

    params = StdioServerParameters(
        command=sys.executable,
        args=[str(tests_dir / "deep_mcp_server.py")],
        cwd=str(tests_dir),
        env=env,
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            listed = await session.list_tools()
            names = {tool.name for tool in listed.tools}
            assert names == {"add", "search_products", "book_flight"}

            for tool in listed.tools:
                dumped = json.dumps(tool.inputSchema)
                assert "$ref" not in dumped
                assert tool.inputSchema.get("type") == "object"

            search = await session.call_tool("search_products", SEARCH_ARGS)
            assert search.isError is not True
            assert "laptop" in search.content[0].text

            add = await session.call_tool("add", ADD_ARGS)
            assert add.isError is not True
            assert "42" in add.content[0].text

            book = await session.call_tool("book_flight", BOOK_ARGS)
            assert book.isError is not True
            assert "TS-12345" in book.content[0].text


def assert_schema_parity_across_frameworks(fn: Callable[..., Any]) -> None:
    from toolschema.integrations.langchain import from_toolschema as lc_from
    from toolschema.integrations.openai_agents import to_agents_function_tool
    from toolschema.integrations.pydantic_ai import from_toolschema as pai_from

    definition = schema(fn)
    canonical = semantic_input_schema(definition.parameters)
    openai = semantic_input_schema(definition.to_openai()["function"]["parameters"])

    lc_schema = lc_from(definition, fn).args_schema
    if not isinstance(lc_schema, dict):
        lc_schema = lc_schema.model_json_schema()  # type: ignore[union-attr]
    lc = semantic_input_schema(lc_schema)

    agents = semantic_input_schema(
        to_agents_function_tool(definition, fn, strict=False).params_json_schema
    )
    pai = semantic_input_schema(pai_from(definition, fn).tool_def.parameters_json_schema)

    assert canonical == openai == lc == agents == pai
