"""End-to-end tests proving toolschema works on complex real-world tools."""

from __future__ import annotations

import json
from pathlib import Path

import complex_fixtures
import pytest

from toolschema import schema

SNAPSHOT = Path(__file__).parent / "snapshots" / "search_products_mcp.json"


def test_complex_tool_is_callable() -> None:
    result = complex_fixtures.search_products(
        query="wireless headphones",
        category="electronics",
        tags=["audio", "bluetooth"],
        price_min=29.99,
        price_max=199.99,
        sort=complex_fixtures.SortOrder.DESC,
        limit=5,
        include_metadata=True,
        filters={"brand": "acme"},
        mode="exact",
    )
    assert len(result) == 1
    assert result[0]["mode"] == "exact"
    assert result[0]["tags"] == ["audio", "bluetooth"]


def test_complex_tool_schema_metadata() -> None:
    tool = schema(complex_fixtures.search_products)

    assert tool.name == "search_products"
    assert tool.description == "Search the product catalog with filters and sorting."

    props = tool.parameters["properties"]
    assert props["query"] == {
        "type": "string",
        "description": "Search query",
        "minLength": 1,
    }
    assert props["category"] == {
        "type": "string",
        "description": "Product category slug",
    }
    assert props["tags"] == {
        "anyOf": [{"type": "array", "items": {"type": "string"}}, {"type": "null"}],
        "default": None,
    }
    assert props["sort"] == {"enum": ["asc", "desc"], "default": "asc"}
    assert props["limit"] == {
        "type": "integer",
        "description": "Max results",
        "minimum": 1,
        "maximum": 100,
        "default": 20,
    }
    assert props["mode"] == {"enum": ["fuzzy", "exact"], "default": "fuzzy"}
    assert props["filters"] == {
        "anyOf": [
            {"type": "object", "additionalProperties": {"type": "string"}},
            {"type": "null"},
        ],
        "default": None,
    }

    required = set(tool.parameters["required"])
    assert required == {"query", "category"}
    assert "limit" not in required
    assert "tags" not in required


def test_complex_tool_output_schema() -> None:
    tool = schema(complex_fixtures.search_products)
    assert tool.output == {"type": "array", "items": {"type": "object"}}


def test_complex_tool_all_adapters() -> None:
    tool = schema(complex_fixtures.search_products)

    openai = tool.to_openai()
    assert openai["type"] == "function"
    assert openai["function"]["name"] == "search_products"
    assert "query" in openai["function"]["parameters"]["properties"]

    strict = tool.to_openai(strict=True)
    strict_params = strict["function"]["parameters"]
    assert strict_params["additionalProperties"] is False
    assert set(strict_params["required"]) == set(strict_params["properties"])

    mcp = tool.to_mcp()
    assert mcp["name"] == "search_products"
    assert "inputSchema" in mcp
    assert "outputSchema" in mcp
    assert "$ref" not in json.dumps(mcp)

    anthropic = tool.to_anthropic()
    query_desc = anthropic["input_schema"]["properties"]["query"]["description"]
    assert "Search query" in query_desc
    assert "min length 1" in query_desc
    assert "minLength" not in anthropic["input_schema"]["properties"]["query"]

    gemini = tool.to_gemini()
    assert gemini["parameters"]["properties"]["query"]["type"] == "STRING"


def test_complex_tool_mcp_snapshot() -> None:
    tool = schema(complex_fixtures.search_products)
    actual = tool.to_mcp()
    expected = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    assert actual == expected


def test_book_flight_pattern_and_literal() -> None:
    tool = schema(complex_fixtures.book_flight)
    props = tool.parameters["properties"]

    assert props["origin"]["pattern"] == r"^[A-Z]{3}$"
    assert props["cabin"] == {"enum": ["economy", "business", "first"], "default": "economy"}
    assert tool.parameters["required"] == ["origin", "destination"]

    result = complex_fixtures.book_flight("JFK", "LHR", passengers=2, cabin="business")
    assert result["confirmation"] == "TS-12345"


def test_complex_tool_integrations_when_extras_installed() -> None:
    pytest.importorskip("fastmcp")
    pytest.importorskip("langchain_core")

    from toolschema.integrations.fastmcp import register_tool
    from toolschema.integrations.langchain import from_toolschema

    definition = schema(complex_fixtures.search_products)

    structured = from_toolschema(definition, complex_fixtures.search_products)
    lc_result = structured.invoke(
        {
            "query": "laptop",
            "category": "computers",
            "sort": "asc",
            "limit": 3,
            "include_metadata": False,
            "mode": "fuzzy",
        }
    )
    assert lc_result[0]["name"] == "laptop in computers"

    import asyncio

    from fastmcp import FastMCP

    async def run_fastmcp() -> dict:
        mcp = FastMCP("complex-e2e")
        register_tool(mcp, definition, complex_fixtures.search_products)
        registered = await mcp.get_tool("search_products")
        result = await registered.run(
            {
                "query": "laptop",
                "category": "computers",
            }
        )
        return result.structured_content  # type: ignore[return-value]

    mcp_result = asyncio.run(run_fastmcp())
    assert mcp_result["result"][0]["name"] == "laptop in computers"
