# Tutorial 2: Build an MCP server with `toolschema init`

**Time:** 15 minutes  
**Prerequisites:** [Tutorial 1](01-getting-started.md), uv, FastMCP (via `toolschema[fastmcp]`)

This tutorial scaffolds a production-ready MCP server where schemas are generated once by toolschema and registered on FastMCP — no double generation.

## Scaffold a project

```bash
uv run toolschema init my-mcp-server
cd my-mcp-server
uv sync
```

This creates:

```
my-mcp-server/
├── pyproject.toml
├── README.md
├── claude_desktop_config.example.json
└── src/my_mcp_server/
    ├── tools.py       # define tools here
    └── __main__.py    # FastMCP server entrypoint
```

## Smoke test locally

```bash
uv run python -m my_mcp_server --check
```

Expected output:

```json
{"result": "Hello, toolschema!"}
{"result": 42}
```

## Start the stdio MCP server

```bash
uv run python -m my_mcp_server
```

The server speaks MCP over stdin/stdout — ready for Claude Desktop, Cursor, or any MCP client.

## Add a custom tool

Edit `src/my_mcp_server/tools.py`:

```python
@tool
def search(query: str, limit: int = 10) -> list[dict]:
    """Search documents."""
    return [{"id": "1", "title": query}]
```

Register in `src/my_mcp_server/__main__.py`:

```python
from my_mcp_server.tools import add, greet, search

register_tool(mcp, schema(search), search)
```

Verify:

```bash
uv run python -m my_mcp_server --check
uv run toolschema inspect my_mcp_server.tools:search --format mcp
```

## Claude Desktop

See [Claude Desktop setup guide](../claude-desktop.md) for full instructions.

Quick config snippet (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "my-mcp-server": {
      "command": "uv",
      "args": ["run", "python", "-m", "my_mcp_server"],
      "cwd": "C:\\path\\to\\my-mcp-server"
    }
  }
}
```

Restart Claude Desktop after saving.

## Why toolschema + FastMCP?

| Approach | Schema source |
|----------|---------------|
| `@mcp.tool()` only | FastMCP generates schema internally |
| **toolschema + `register_tool()`** | toolschema generates once; FastMCP executes |

Same function can also export OpenAI / LangChain formats without rewriting.

## Next steps

- [Claude Desktop smoke test guide](../claude-desktop.md)
- [Tutorial 3: LangChain integration](03-langchain-integration.md)
