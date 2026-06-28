# toolschema

[![PyPI version](https://img.shields.io/pypi/v/toolschema.svg)](https://pypi.org/project/toolschema/)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://pypi.org/project/toolschema/)
[![Documentation](https://img.shields.io/badge/docs-readthedocs-blue.svg)](https://toolschema.readthedocs.io/en/latest/)
[![CI](https://github.com/false200/toolschema/actions/workflows/ci.yml/badge.svg)](https://github.com/false200/toolschema/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

**Write a Python function once. Get the JSON Schema every AI framework needs.**

LLMs can't read your Python code. They need JSON that describes your tool — name, description, parameters. Today every framework (OpenAI, LangChain, FastMCP, MCP…) wants that JSON in a slightly different shape. **toolschema** builds it from your function **one time**, then exports it anywhere.

📖 **Full docs:** https://toolschema.readthedocs.io/en/latest/

---

## 30-second example

```python
from toolschema import schema, tool

@tool
def greet(name: str) -> str:
    """Say hello to someone."""
    return f"Hello, {name}!"

t = schema(greet)

t.to_openai()      # for ChatGPT / OpenAI Agents
t.to_mcp()         # for Claude Desktop / Cursor MCP
t.to_anthropic()   # for Claude API
```

That's it. Your function still runs normally: `greet("world")` → `"Hello, world!"`

---

## The problem (in plain English)

You write this:

```python
def add(a: int, b: int = 1) -> int:
    """Add two numbers."""
    return a + b
```

The LLM needs this (JSON):

```json
{
  "name": "add",
  "description": "Add two numbers.",
  "parameters": {
    "type": "object",
    "properties": {
      "a": { "type": "integer" },
      "b": { "type": "integer", "default": 1 }
    },
    "required": ["a"]
  }
}
```

**Without toolschema:** you hand-write JSON, or let each framework generate its own (and hope they match).

**With toolschema:** `schema(add)` → done. Export to any provider with one line.

---

## Install

```bash
pip install toolschema
```

Need a specific framework? Install an extra:

```bash
pip install toolschema[fastmcp]       # MCP servers
pip install toolschema[langchain]     # LangChain
pip install toolschema[openai-agents]
pip install toolschema[pydantic-ai]
pip install toolschema[all]           # everything
```

Requires **Python 3.10+**.

---

## Beginner guide (5 minutes)

### 1. Write a typed function

Type hints on every parameter. Docstring = what the LLM sees.

```python
from toolschema import tool, schema

@tool
def search(query: str, limit: int = 10) -> list[dict]:
    """Search the product catalog."""
    return [{"query": query, "limit": limit}]
```

> `@tool` is optional. `schema(search)` works on any typed function with a docstring.

### 2. Generate the schema

```python
definition = schema(search)

print(definition.name)         # "search"
print(definition.description)  # "Search the product catalog."
print(definition.parameters)   # JSON Schema dict
```

### 3. Export for your provider

```python
openai_payload = definition.to_openai()
mcp_payload = definition.to_mcp()
```

Or use the CLI:

```bash
toolschema inspect myapp.tools:search --format mcp
```

### 4. Plug into a framework (one extra line)

Same function, same `definition` — pick your stack:

| You use… | Do this |
|----------|---------|
| **FastMCP** | `register_tool(mcp, definition, search)` |
| **LangChain** | `from_toolschema(definition, search)` |
| **OpenAI Agents** | `to_agents_function_tool(definition, search)` |
| **Pydantic AI** | `from_toolschema(definition, search)` |

Details: [Integrations guide](https://toolschema.readthedocs.io/en/latest/integrations/)

---

## Common patterns

### Add parameter descriptions

```python
from typing import Annotated
from toolschema import Field

def weather(
    city: Annotated[str, Field(description="City name", min_length=1)],
) -> dict:
    """Get current weather."""
    ...
```

Or the short form: `Annotated[str, "City name"]`

### Validate arguments before calling

```python
from toolschema import ValidationSuccess

result = definition.validate({"query": "laptop"})
if isinstance(result, ValidationSuccess):
    search(**result.value)
```

### Start a new MCP server project

```bash
toolschema init my-mcp-server
cd my-mcp-server
uv sync
uv run python -m my_mcp_server --check
```

---

## Framework examples

### FastMCP (MCP / Claude Desktop)

```python
from fastmcp import FastMCP
from toolschema import schema
from toolschema.integrations.fastmcp import register_tool

mcp = FastMCP("my-server")
register_tool(mcp, schema(greet), greet)
mcp.run()
```

### LangChain

```python
from toolschema.integrations.langchain import from_toolschema

lc_tool = from_toolschema(schema(search), search)
lc_tool.invoke({"query": "laptop", "limit": 5})
```

More examples in [`examples/`](examples/) and the [docs](https://toolschema.readthedocs.io/en/latest/examples/).

---

## What toolschema supports

| Python types | ✅ |
|--------------|----|
| `str`, `int`, `float`, `bool` | ✅ |
| `list`, `dict`, optional (`T \| None`) | ✅ |
| `Literal`, `Enum`, defaults | ✅ |
| `TypedDict`, `@dataclass`, `Union` | ✅ |
| Pydantic models as params | ✅ |

| Export targets | ✅ |
|----------------|----|
| OpenAI (+ strict mode) | ✅ |
| Anthropic, Gemini, MCP | ✅ |
| FastMCP, LangChain, OpenAI Agents, Pydantic AI | ✅ |

Full type table: [docs](https://toolschema.readthedocs.io/en/latest/type-mapping/)

---

## Why toolschema?

| Approach | Problem |
|----------|---------|
| Hand-written JSON | Drifts from your code, no single source of truth |
| `@mcp.tool()` only | MCP-only, not portable to LangChain/OpenAI |
| `@tool` per framework | Rewrite the same function 3× |
| **toolschema** | One function → one schema → every provider |

---

## Learn more

| Topic | Link |
|-------|------|
| **Full documentation** | https://toolschema.readthedocs.io/en/latest/ |
| Quick start tutorial | [docs/quickstart.md](docs/quickstart.md) |
| Complete API reference | [docs/api-reference.md](docs/api-reference.md) |
| MCP server tutorial | [docs/tutorials/02-mcp-server.md](docs/tutorials/02-mcp-server.md) |
| Provider differences | [docs/provider-quirks.md](docs/provider-quirks.md) |
| FAQ | [docs/faq.md](docs/faq.md) |

---

## Development

```bash
git clone https://github.com/false200/toolschema.git
cd toolschema
uv sync --extra all
uv run pytest -v
```

Contributing: [CONTRIBUTING.md](CONTRIBUTING.md) · PyPI releases: [.github/PYPI_PUBLISH.md](.github/PYPI_PUBLISH.md)

## License

MIT — see [LICENSE](LICENSE).
