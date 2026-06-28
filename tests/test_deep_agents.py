"""Deep cross-agent integration tests.

Requires all integration extras:
    uv sync --extra dev --extra fastmcp --extra langchain --extra openai-agents --extra pydantic-ai
"""

from __future__ import annotations

import asyncio

import complex_fixtures
import fixtures
import pytest
from deep_harness import (
    BOOK_ARGS,
    SEARCH_ARGS,
    assert_provider_adapters,
    assert_schema_parity_across_frameworks,
    assert_validate,
    mcp_stdio_deep,
    run_fastmcp_add,
    run_fastmcp_search,
    run_langchain_add,
    run_langchain_search,
    run_openai_agents_add,
    run_openai_agents_search,
    run_pydantic_ai_agent,
    run_pydantic_ai_search,
)

from toolschema import schema

pytest.importorskip("fastmcp")
pytest.importorskip("langchain_core")
pytest.importorskip("agents")
pytest.importorskip("pydantic_ai")
pytest.importorskip("mcp")


@pytest.mark.parametrize(
    "fn",
    [
        fixtures.add,
        fixtures.search_github,
        complex_fixtures.search_products,
        complex_fixtures.book_flight,
    ],
)
def test_all_provider_adapters(fn) -> None:
    assert_provider_adapters(schema(fn))


def test_validate_complex_tools() -> None:
    search = schema(complex_fixtures.search_products)
    assert_validate(search, SEARCH_ARGS, {"query": ""})

    book = schema(complex_fixtures.book_flight)
    assert_validate(book, BOOK_ARGS, {"origin": "invalid"})


@pytest.mark.parametrize("fn", [fixtures.add, complex_fixtures.search_products])
def test_schema_parity_across_all_frameworks(fn) -> None:
    assert_schema_parity_across_frameworks(fn)


def test_langchain_executes_complex_search() -> None:
    assert run_langchain_search() == "laptop in computers"


def test_fastmcp_executes_complex_search() -> None:
    assert asyncio.run(run_fastmcp_search()) == "laptop in computers"


def test_openai_agents_executes_complex_search() -> None:
    assert run_openai_agents_search() == "laptop in computers"


def test_pydantic_ai_executes_complex_search() -> None:
    assert run_pydantic_ai_search() == "laptop in computers"


def test_all_frameworks_add_same_result() -> None:
    expected = 42
    assert run_langchain_add() == expected
    assert asyncio.run(run_fastmcp_add()) == expected
    assert run_openai_agents_add() == expected


def test_pydantic_ai_agent_registers_all_tools() -> None:
    names = run_pydantic_ai_agent()
    assert set(names) == {"add", "search_products", "book_flight"}


def test_book_flight_via_langchain() -> None:
    from toolschema.integrations.langchain import from_toolschema

    definition = schema(complex_fixtures.book_flight)
    tool = from_toolschema(definition, complex_fixtures.book_flight)
    result = tool.invoke(BOOK_ARGS)
    assert result["confirmation"] == "TS-12345"
    assert result["cabin"] == "business"


def test_mcp_stdio_all_tools() -> None:
    asyncio.run(mcp_stdio_deep())
