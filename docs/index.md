# toolschema documentation

**toolschema** turns typed Python functions into JSON Schema for AI agent tools — once, for every provider.

```
Your function  →  schema(fn)  →  ToolDefinition  →  OpenAI / MCP / LangChain / …
```

## Who is this for?

| You are… | Start here |
|----------|------------|
| New to toolschema | [Installation](installation.md) → [Quick start](quickstart.md) |
| Building an MCP server | [MCP tutorial](tutorials/02-mcp-server.md) → [Scaffolding](scaffolding.md) |
| Using LangChain / Agents SDK | [Integrations](integrations.md) |
| Looking up a function | [API reference](api-reference.md) |
| Understanding design | [Architecture](architecture.md) |

## What toolschema does

1. **Reads** your function's type hints, defaults, and docstring
2. **Builds** a canonical JSON Schema 2020-12 (`ToolDefinition`)
3. **Exports** provider-specific JSON (OpenAI, Anthropic, Gemini, MCP)
4. **Integrates** with FastMCP, LangChain, OpenAI Agents, Pydantic AI via thin adapters

## What toolschema does *not* do

- Run agents or orchestrate LLM calls
- Replace Pydantic for domain modeling
- Handle MCP transport (use FastMCP for that)

## Install

```bash
pip install toolschema
pip install toolschema[fastmcp]   # MCP servers
pip install toolschema[all]       # everything
```

See [Installation](installation.md) for all extras.

## Minimal example

```python
from toolschema import tool, schema

@tool
def greet(name: str) -> str:
    """Say hello."""
    return f"Hello, {name}!"

definition = schema(greet)
print(definition.to_openai())
print(definition.to_mcp())
```

## Package layout

```
toolschema/
├── tool, schema, Field          # public API
├── ToolDefinition               # IR (intermediate representation)
├── adapters/                    # OpenAI, Anthropic, Gemini, MCP
├── integrations/                # FastMCP, LangChain, Agents, Pydantic AI
├── cli.py                       # inspect, diff, export, init
└── templates/                   # MCP server scaffold
```

## Version

Current release: **1.0.0** (see [PyPI](https://pypi.org/project/toolschema/)).
