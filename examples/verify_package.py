"""Verify toolschema works end-to-end by importing a real tools module.

Usage:
    uv run python examples/verify_package.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

# Allow `import demo_tools` when run as `uv run python examples/verify_package.py`
sys.path.insert(0, str(Path(__file__).resolve().parent))

from toolschema import ValidationFailure, ValidationSuccess, __version__

# Import our demo tools module like a real consumer would.
from demo_tools import add, get_tool_definitions, greet, search_items


def check(label: str, condition: bool, detail: str = "") -> None:
    status = "PASS" if condition else "FAIL"
    line = f"  [{status}] {label}"
    if detail and not condition:
        line += f" — {detail}"
    print(line)
    if not condition:
        raise AssertionError(label)


def assert_no_ref(payload: dict[str, Any]) -> None:
    if "$ref" in json.dumps(payload):
        raise AssertionError("schema contains $ref (bad for Claude Desktop)")


def main() -> int:
    print(f"toolschema {__version__} — package verification\n")

    # 1. Import + version
    print("1. Import")
    check("toolschema imported", True)
    check("demo_tools imported", greet.__name__ == "greet")

    # 2. Functions still callable
    print("\n2. Call decorated functions")
    check("greet()", greet(name="world") == "Hello, world!")
    check("add() default", add(a=5) == 6)
    check("add() both args", add(a=10, b=32) == 42)
    check("search_items()", len(search_items(query="test")) == 1)

    # 3. Schema generation
    print("\n3. Schema generation")
    tools = get_tool_definitions()
    check("three tools defined", len(tools) == 3)

    greet_def = tools["greet"]
    check("greet name", greet_def.name == "greet")
    check("greet description", "hello" in greet_def.description.lower())
    props = greet_def.parameters["properties"]
    check("greet has name param", "name" in props and props["name"]["type"] == "string")
    check("greet required", greet_def.parameters["required"] == ["name"])

    add_def = tools["add"]
    check("add default omitted from required", "b" not in add_def.parameters["required"])
    check("add default in schema", add_def.parameters["properties"]["b"]["default"] == 1)

    search_def = tools["search_items"]
    check("search literal enum", search_def.parameters["properties"]["sort"]["enum"] == [
        "relevance",
        "date",
    ])

    # 4. Adapters
    print("\n4. Provider adapters")
    mcp = greet_def.to_mcp()
    check("MCP name", mcp["name"] == "greet")
    check("MCP inputSchema", mcp["inputSchema"]["type"] == "object")
    assert_no_ref(mcp)
    check("MCP no $ref", True)

    openai = add_def.to_openai()
    check("OpenAI function name", openai["function"]["name"] == "add")
    check("OpenAI parameters object", openai["function"]["parameters"]["type"] == "object")

    strict = add_def.to_openai(strict=True)
    strict_params = strict["function"]["parameters"]
    check("OpenAI strict additionalProperties", strict_params["additionalProperties"] is False)
    check("OpenAI strict all required", set(strict_params["required"]) == {"a", "b"})

    anthropic = search_def.to_anthropic()
    check("Anthropic name", anthropic["name"] == "search_items")

    gemini = greet_def.to_gemini()
    check("Gemini name", gemini["name"] == "greet")

    # 5. validate()
    print("\n5. validate()")
    ok = greet_def.validate({"name": "Ada"})
    check("validate success", isinstance(ok, ValidationSuccess))
    bad = greet_def.validate({})
    check("validate missing field", isinstance(bad, ValidationFailure))

    # 6. Optional FastMCP integration
    print("\n6. FastMCP integration (optional)")
    try:
        import asyncio

        from fastmcp import FastMCP
        from toolschema.integrations.fastmcp import register_tool

        mcp_server = FastMCP("verify-demo")
        register_tool(mcp_server, greet_def, greet)

        async def run_fastmcp() -> None:
            tool_obj = await mcp_server.get_tool("greet")
            result = await tool_obj.run({"name": "MCP"})
            assert "MCP" in str(result.structured_content)

        asyncio.run(run_fastmcp())
        check("FastMCP register + run", True)
    except ImportError:
        print("  [SKIP] install fastmcp extra: uv sync --extra fastmcp")

    print("\nAll checks passed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"\nVerification failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
