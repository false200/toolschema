"""MCP stdio server used by deep agent integration tests."""

from __future__ import annotations

import complex_fixtures
import fixtures
from fastmcp import FastMCP

from toolschema import schema
from toolschema.integrations.fastmcp import register_tool


def build_server() -> FastMCP:
    mcp = FastMCP("toolschema-deep-test")
    for fn in (fixtures.add, complex_fixtures.search_products, complex_fixtures.book_flight):
        register_tool(mcp, schema(fn), fn)
    return mcp


if __name__ == "__main__":
    build_server().run()
