# {{project_title}}

MCP server scaffolded with [`toolschema init`](https://github.com/false200/toolschema).

Tools are defined as plain Python functions. Schemas are generated once with **toolschema** and registered on FastMCP — no double schema generation.

## Quick start

```bash
# If toolschema is not on PyPI yet, install from source:
# uv add --editable /path/to/toolschema[fastmcp]

uv sync
uv run python -m {{package_name}} --check   # local smoke test
uv run python -m {{package_name}}           # start stdio MCP server
```

## Claude Desktop

Add to `%APPDATA%\\Claude\\claude_desktop_config.json` (Windows) or
`~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

```json
{
  "mcpServers": {
    "{{project_name}}": {
      "command": "uv",
      "args": ["run", "python", "-m", "{{package_name}}"],
      "cwd": "ABSOLUTE_PATH_TO_THIS_PROJECT"
    }
  }
}
```

See `claude_desktop_config.example.json` for a copy-paste template.

## Add a tool

1. Define a function in `src/{{package_name}}/tools.py`
2. Register it in `src/{{package_name}}/__main__.py` with `register_tool(mcp, schema(fn), fn)`
3. Run `uv run python -m {{package_name}} --check`

## Inspect schemas

```bash
uv run toolschema inspect {{package_name}}.tools:greet --format mcp
```
