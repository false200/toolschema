# MCP scaffolding

`toolschema init` creates a ready-to-run MCP server project.

## Create a project

```bash
toolschema init my-mcp-server
cd my-mcp-server
uv sync
uv run python -m my_mcp_server --check
```

Package name is derived from project name:

| Project name | Python package |
|--------------|----------------|
| `my-mcp-server` | `my_mcp_server` |
| `Demo` | `demo` |
| `123demo` | `mcp_123demo` |

## Generated layout

```
my-mcp-server/
├── pyproject.toml              # depends on toolschema[fastmcp]
├── README.md
├── claude_desktop_config.example.json
└── src/my_mcp_server/
    ├── __init__.py
    ├── tools.py                # define @tool functions here
    └── __main__.py             # FastMCP server + --check smoke test
```

## Add a tool

**1.** Define in `src/my_mcp_server/tools.py`:

```python
from toolschema import tool

@tool
def weather(city: str) -> dict:
    """Get weather for a city."""
    return {"city": city, "temp": 22}
```

**2.** Register in `src/my_mcp_server/__main__.py`:

```python
from toolschema.integrations.fastmcp import register_tool
from my_mcp_server.tools import weather

register_tool(mcp, schema(weather), weather)
```

**3.** Smoke test:

```bash
uv run python -m my_mcp_server --check
```

## Claude Desktop

Copy from `claude_desktop_config.example.json`:

```json
{
  "mcpServers": {
    "my-mcp-server": {
      "command": "uv",
      "args": ["run", "python", "-m", "my_mcp_server"],
      "cwd": "ABSOLUTE_PATH_TO_PROJECT"
    }
  }
}
```

See [Claude Desktop guide](claude-desktop.md).

## Programmatic API

```python
from pathlib import Path
from toolschema._init_scaffold import scaffold_mcp_server, slugify_package_name

result = scaffold_mcp_server(Path("."), "my-mcp-server")
print(result.root, result.package_name)
```

## Template location

Packaged at `toolschema/templates/mcp_server/` inside the wheel.
