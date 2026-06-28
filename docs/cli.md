# CLI

The `toolschema` command-line tool inspects, compares, and exports schemas.

```bash
pip install toolschema
toolschema --help
```

## `inspect`

Print tool JSON for a single function.

```bash
toolschema inspect myapp.tools:search_github
toolschema inspect myapp.tools:search_github --format mcp
toolschema inspect myapp.tools:search_github --format openai,mcp,anthropic
```

### Target syntax

| Format | Example |
|--------|---------|
| Module function | `mypackage.tools:add` |
| Nested attribute | `mypackage.registry:TOOLS.search` |

### Formats

| `--format` value | Output |
|------------------|--------|
| `canonical` | `ToolDefinition.to_json_schema()` (default) |
| `openai` | OpenAI function tool |
| `openai-strict` | OpenAI with `strict=True` |
| `anthropic` | Anthropic tool |
| `mcp` | MCP tools/list entry |
| `gemini` | Gemini FunctionDeclaration |

Multiple formats: comma-separated, no spaces (or spaces trimmed).

## `diff`

Compare adapter outputs for the same function.

```bash
toolschema diff myapp.tools:add --targets openai,mcp
toolschema diff myapp.tools:add --targets openai,openai-strict,mcp,anthropic
```

Prints JSON with `equal` flags and key paths for each pair.

## `export`

Export schemas for all callables in a module.

```bash
toolschema export myapp.tools
toolschema export myapp.tools --output tools.json
```

Skips objects where `schema()` raises `TypeError` or `ValueError`.

Output shape:

```json
{
  "module": "myapp.tools",
  "tools": [
    { "name": "...", "description": "...", "parameters": {...}, "_source": "myapp.tools:add" }
  ]
}
```

## `init`

Scaffold a new MCP server project.

```bash
toolschema init my-mcp-server
toolschema init my-mcp-server --path /tmp
```

Creates:

```
my-mcp-server/
├── pyproject.toml
├── README.md
├── claude_desktop_config.example.json
└── src/my_mcp_server/
    ├── tools.py
    └── __main__.py
```

Next steps printed by CLI:

```bash
cd my-mcp-server
uv sync
uv run python -m my_mcp_server --check
uv run python -m my_mcp_server
```

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Runtime error (import failure, bad target, etc.) |
| `2` | Argument error |

## Run as module

```bash
python -m toolschema inspect myapp.tools:add --format mcp
```
