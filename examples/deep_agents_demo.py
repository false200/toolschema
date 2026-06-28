"""Deep cross-agent demo — run every integration path and print results.

Usage:
    uv sync --extra fastmcp --extra langchain --extra openai-agents --extra pydantic-ai
    uv run python examples/deep_agents_demo.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# tests/ helpers live next to fixtures
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))

import complex_fixtures  # noqa: E402
import fixtures  # noqa: E402
from deep_harness import (  # noqa: E402
    ADD_ARGS,
    SEARCH_ARGS,
    assert_provider_adapters,
    assert_schema_parity_across_frameworks,
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

from toolschema import schema  # noqa: E402


def section(title: str) -> None:
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


def main() -> int:
    section("1. Provider adapters (OpenAI, MCP, Anthropic, Gemini)")
    for name, fn in {
        "add": fixtures.add,
        "search_products": complex_fixtures.search_products,
        "book_flight": complex_fixtures.book_flight,
    }.items():
        tool = schema(fn)
        assert_provider_adapters(tool)
        print(f"  OK  {name}")

    section("2. Schema parity (toolschema IR == LangChain == Agents == Pydantic AI)")
    for fn in (fixtures.add, complex_fixtures.search_products):
        assert_schema_parity_across_frameworks(fn)
        print(f"  OK  {fn.__name__}")

    section("3. Execute complex search_products everywhere")
    print(f"  args: {SEARCH_ARGS}")
    print(f"  LangChain:      {run_langchain_search()}")
    print(f"  FastMCP:        {asyncio.run(run_fastmcp_search())}")
    print(f"  OpenAI Agents:  {run_openai_agents_search()}")
    print(f"  Pydantic AI:    {run_pydantic_ai_search()}")

    section("4. Execute add (expect 42)")
    print(f"  args: {ADD_ARGS}")
    print(f"  LangChain:      {run_langchain_add()}")
    print(f"  FastMCP:        {asyncio.run(run_fastmcp_add())}")
    print(f"  OpenAI Agents:  {run_openai_agents_add()}")

    section("5. Pydantic AI Agent (TestModel registers all tools)")
    registered = run_pydantic_ai_agent()
    print(f"  tools seen by model: {registered}")

    section("6. MCP stdio client (spawn deep_mcp_server.py)")
    asyncio.run(mcp_stdio_deep())
    print("  OK  list_tools + call add/search/book over stdio")

    print("\nDeep cross-agent verification complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
