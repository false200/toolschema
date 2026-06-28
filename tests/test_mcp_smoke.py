"""MCP protocol smoke tests — simulates what Claude Desktop / Cursor do over stdio."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

import pytest

pytest.importorskip("fastmcp")
pytest.importorskip("mcp")

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_SERVER = PROJECT_ROOT / "examples" / "02_mcp_server.py"


def _assert_claude_safe_schema(schema: dict) -> None:
    """Claude Desktop / Copilot break on unresolved $ref."""
    dumped = json.dumps(schema)
    assert "$ref" not in dumped
    assert schema.get("type") == "object"
    assert "properties" in schema


async def _run_example_server_smoke() -> None:
    params = StdioServerParameters(
        command=sys.executable,
        args=[str(EXAMPLE_SERVER)],
        cwd=str(PROJECT_ROOT),
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            response = await session.list_tools()
            names = {tool.name for tool in response.tools}
            assert names == {"greet", "add"}

            for tool in response.tools:
                assert tool.description
                _assert_claude_safe_schema(tool.inputSchema)

            greet = await session.call_tool("greet", {"name": "Claude"})
            assert greet.isError is not True
            assert "Claude" in greet.content[0].text

            add = await session.call_tool("add", {"a": 10, "b": 32})
            assert add.isError is not True
            assert "42" in add.content[0].text


def test_mcp_stdio_smoke_like_claude_desktop() -> None:
    asyncio.run(_run_example_server_smoke())


async def _run_scaffolded_server_smoke(root: Path, package_name: str) -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([str(root / "src"), str(PROJECT_ROOT / "src")])
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", package_name],
        cwd=str(root),
        env=env,
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            response = await session.list_tools()
            names = {tool.name for tool in response.tools}
            assert "greet" in names
            assert "add" in names
            for tool in response.tools:
                _assert_claude_safe_schema(tool.inputSchema)


def test_scaffolded_server_mcp_stdio(tmp_path: Path) -> None:
    from toolschema._init_scaffold import scaffold_mcp_server

    result = scaffold_mcp_server(tmp_path, "smoke-server")
    asyncio.run(_run_scaffolded_server_smoke(result.root, result.package_name))
