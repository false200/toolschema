"""Runnable FastMCP server backed by toolschema schemas.

Usage:
    uv run python examples/02_mcp_server.py          # start stdio MCP server
    uv run python examples/02_mcp_server.py --check  # smoke test (no server)
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from fastmcp import FastMCP
from toolschema import schema, tool
from toolschema.integrations.fastmcp import register_tool


@tool
def greet(name: str) -> str:
    """Say hello to someone."""
    return f"Hello, {name}!"


@tool
def add(a: int, b: int = 1) -> int:
    """Add two integers."""
    return a + b


def build_server() -> FastMCP:
    mcp = FastMCP("toolschema-demo")
    register_tool(mcp, schema(greet), greet)
    register_tool(mcp, schema(add), add)
    return mcp


async def smoke_check() -> None:
    mcp = build_server()
    greet_tool = await mcp.get_tool("greet")
    add_tool = await mcp.get_tool("add")
    greet_result = await greet_tool.run({"name": "toolschema"})
    add_result = await add_tool.run({"a": 40, "b": 2})
    print(greet_result.structured_content)
    print(add_result.structured_content)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Run a local smoke test instead of starting the MCP server",
    )
    args = parser.parse_args()

    if args.check:
        asyncio.run(smoke_check())
        return 0

    build_server().run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
