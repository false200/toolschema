# Claude Desktop MCP smoke test

This guide validates that a toolschema-backed MCP server works with clients that have strict JSON Schema requirements (Claude Desktop, VS Code Copilot).

## Automated smoke test (recommended first)

From the toolschema repo:

```bash
uv sync --extra dev --extra fastmcp
uv run pytest -v tests/test_mcp_smoke.py
```

This spawns a real stdio MCP server and verifies:

1. `tools/list` succeeds
2. Tool `inputSchema` contains **no `$ref`**
3. `tools/call` returns expected results
4. Schemas are valid JSON Schema objects

## Scaffold + smoke test a new server

```bash
uv run toolschema init my-smoke-test
cd my-smoke-test
uv add --editable /path/to/toolschema[fastmcp]   # until PyPI publish
uv sync
uv run python -m my_smoke_test --check
```

## Manual Claude Desktop setup

### 1. Build or scaffold a server

Use `toolschema init` or `examples/02_mcp_server.py` from this repo.

### 2. Find your config file

| OS | Path |
|----|------|
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Linux | `~/.config/Claude/claude_desktop_config.json` |

### 3. Add the server entry

For a scaffolded project at `C:\projects\my-mcp-server`:

```json
{
  "mcpServers": {
    "my-mcp-server": {
      "command": "uv",
      "args": ["run", "python", "-m", "my_mcp_server"],
      "cwd": "C:\\projects\\my-mcp-server"
    }
  }
}
```

For the toolschema repo example server:

```json
{
  "mcpServers": {
    "toolschema-demo": {
      "command": "uv",
      "args": ["run", "python", "examples/02_mcp_server.py"],
      "cwd": "C:\\path\\to\\toolschema"
    }
  }
}
```

**Important:** Use absolute paths for `cwd`. On Windows, escape backslashes (`\\`) in JSON.

### 4. Restart Claude Desktop

Fully quit and reopen Claude Desktop (tray icon → Quit, not just close the window).

### 5. Verify in Claude

1. Open a new conversation
2. Click the **tools** icon (hammer) — you should see `greet` and `add`
3. Ask: *"Use the greet tool to say hello to Claude"*
4. Ask: *"Use add with a=10 and b=32"*

### 6. Check logs if tools don't appear

| OS | Log path |
|----|----------|
| Windows | `%APPDATA%\Claude\logs\mcp*.log` |
| macOS | `~/Library/Logs/Claude/mcp*.log` |

Common issues:

| Symptom | Fix |
|---------|-----|
| No tools listed | Check `cwd` is absolute; run `uv run python -m ... --check` manually |
| Server crashes on start | Run `uv sync` in project directory first |
| Schema errors in logs | Ensure `to_mcp(inline_refs=True)` — toolschema default |
| `$ref` errors | Regenerate with toolschema ≥ 1.0; MCP adapter inlines `$ref` by default |

## Why toolschema is Claude-safe

Claude Desktop and VS Code Copilot do not fully resolve JSON Schema `$ref`. toolschema's MCP adapter defaults to `inline_refs=True`, flattening `$defs` before registration.

```python
definition.to_mcp()                    # no $ref
definition.to_mcp(inline_refs=False)   # may break some clients
```

## CI coverage

The integration CI job runs MCP smoke tests on every push. See `.github/workflows/ci.yml`.
