# toolschema

[![PyPI version](https://img.shields.io/pypi/v/toolschema.svg)](https://pypi.org/project/toolschema/)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://pypi.org/project/toolschema/)
[![CI](https://github.com/false200/toolschema/actions/workflows/ci.yml/badge.svg)](https://github.com/false200/toolschema/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

Canonical Python layer for AI agent tools — `(function + type hints) → JSON Schema`, once, for every provider. One `ToolDefinition`, adapters at the edge.

FastMCP generates MCP-only schemas. LangChain re-infers per `StructuredTool`. OpenAI strict mode wants every key in `required`. Claude Desktop breaks on `$ref`. **toolschema** introspects the function once and exports OpenAI, Anthropic, Gemini, and MCP shapes from the same IR — with thin hooks for FastMCP, LangChain, OpenAI Agents, and Pydantic AI.

## Install

```sh
pip install toolschema
```

Extras:

```sh
pip install toolschema[fastmcp]        # FastMCP
pip install toolschema[langchain]      # LangChain StructuredTool
pip install toolschema[openai-agents]  # OpenAI Agents SDK
pip install toolschema[pydantic-ai]    # Pydantic AI Tool.from_schema
pip install toolschema[all]            # all integrations
```

Requires **Python 3.10+**. Core depends on stdlib only (`typing_extensions` on 3.10).

**Documentation:** https://toolschema.readthedocs.io

## Usage

### Core

```python
from typing import Annotated
from toolschema import tool, schema, Field

@tool
def get_weather(
    city: Annotated[str, Field(description="City name")],
    units: str = "celsius",
) -> dict:
    """Get current weather for a city."""
    return {"city": city, "temp": 22, "units": units}

t = schema(get_weather)
t.to_openai()
t.to_mcp()
t.to_anthropic()
```

Works without `@tool` on any typed function with a docstring:

```python
def add(a: int, b: int = 1) -> int:
    """Add two integers."""
    return a + b

t = schema(add)
```

### FastMCP

```python
from fastmcp import FastMCP
from toolschema import schema
from toolschema.integrations.fastmcp import register_tool
from myapp.tools import greet, add

mcp = FastMCP("my-server")
register_tool(mcp, schema(greet), greet)
register_tool(mcp, schema(add), add)

mcp.run()
```

### LangChain

```python
from toolschema import schema
from toolschema.integrations.langchain import from_toolschema
from myapp.tools import search

definition = schema(search)
tool = from_toolschema(definition, search)
result = tool.invoke({"query": "laptop", "limit": 5})
```

### OpenAI Agents

```python
from toolschema import schema
from toolschema.integrations.openai_agents import to_agents_function_tool
from myapp.tools import add

definition = schema(add)
agents_tool = to_agents_function_tool(definition, add)
```

### Pydantic AI

```python
from pydantic_ai import Agent
from toolschema import schema
from toolschema.integrations.pydantic_ai import from_toolschema
from myapp.tools import add

definition = schema(add)
tool = from_toolschema(definition, add)
agent = Agent("openai:gpt-4o", tools=[tool])
```

### CLI

```sh
toolschema inspect myapp.tools:search --format mcp
toolschema inspect myapp.tools:search --format openai,mcp,anthropic
toolschema diff myapp.tools:search --targets openai,mcp
toolschema export myapp.tools
toolschema init my-mcp-server
```

## API

### `schema(fn) -> ToolDefinition`

Build the canonical tool IR from a function signature, type hints, defaults, and docstring.

#### fn

*Required*  
Type: `Callable`

Any typed callable, or `@tool`-decorated function.

```python
from toolschema import schema

t = schema(my_function)
t.name
t.description
t.parameters   # JSON Schema 2020-12 object
t.output       # return type schema, or None
```

---

### `@tool`

Optional decorator. Overrides name or description; does not change call semantics.

```python
@tool(name="web_search", description="Search the web.")
def search(query: str) -> list[dict]: ...
```

---

### `Field(...)`

Metadata for `Annotated` parameters. Maps to JSON Schema constraints.

```python
from typing import Annotated
from toolschema import Field

city: Annotated[str, Field(description="City name", min_length=1)]
```

Plain string in `Annotated` sets description only: `Annotated[str, "City name"]`.

---

### `ToolDefinition.to_openai(*, strict=False)`

OpenAI function-calling payload: `{"type": "function", "function": {...}}`.

#### strict

Type: `boolean`  
Default: `false`

When `true`, sets `additionalProperties: false` and lists every property in `required`.

---

### `ToolDefinition.to_anthropic()`

Anthropic Messages API shape: `{"name", "description", "input_schema"}`.

Numeric and string constraints (`minLength`, `pattern`, etc.) are folded into property `description` text.

---

### `ToolDefinition.to_mcp(*, inline_refs=True)`

MCP `tools/list` shape: `name`, `description`, `inputSchema`, optional `outputSchema`.

#### inline_refs

Type: `boolean`  
Default: `true`

When `true`, flatten `$ref` / `$defs` before return. Required for Claude Desktop and VS Code Copilot.

---

### `ToolDefinition.to_gemini()`

Google Gemini `FunctionDeclaration` shape. JSON Schema `type` values are uppercased (`STRING`, `INTEGER`, …). Parameters only; no output schema in v1.0.

---

### `ToolDefinition.validate(args) -> ValidationResult`

Thin argument check against `parameters`. Returns `ValidationSuccess` with defaults applied, or `ValidationFailure` with `ValidationIssue` list.

```python
from toolschema import ValidationSuccess

result = t.validate({"city": "London"})
if isinstance(result, ValidationSuccess):
    get_weather(**result.value)
```

---

### `register_tool(mcp, tool, fn)` (FastMCP)

Register a pre-built `ToolDefinition` on a FastMCP server without regenerating schema inside FastMCP.

#### mcp

*Required*  
Type: `fastmcp.FastMCP`

#### tool

*Required*  
Type: `ToolDefinition`

#### fn

*Required*  
Type: `Callable`

---

### `from_toolschema(tool, fn)` (LangChain)

Build a `StructuredTool` with `infer_schema=False` and `args_schema=tool.parameters`.

---

### `to_agents_function_tool(tool, fn, *, strict=False)` (OpenAI Agents)

Build an OpenAI Agents SDK `FunctionTool` with `on_invoke_tool` wired to `fn`.

Also: `function_tool_kwargs()`, `to_openai_agent_tool()`, `invoke_agents_tool()`, `invoke_agents_tool_sync()`.

---

### `from_toolschema(tool, fn)` (Pydantic AI)

Build a Pydantic AI `Tool` via `Tool.from_schema()` and the pre-built JSON Schema.

Also: `to_pydantic_ai_tool()`, `prepare_toolset()`.

---

### `toolschema init NAME [--path DIR]`

Scaffold an MCP server project from the packaged template. Runs `slugify_package_name()` on the directory name for the Python package.

## Canonical schema

Internal dialect: JSON Schema 2020-12. Parameters object always has `additionalProperties: false`.

```json
{
  "name": "add",
  "description": "Add two integers.",
  "parameters": {
    "type": "object",
    "properties": {
      "a": { "type": "integer" },
      "b": { "type": "integer", "default": 1 }
    },
    "required": ["a"],
    "additionalProperties": false
  }
}
```

| Python | JSON Schema |
|--------|-------------|
| `str`, `int`, `float`, `bool` | `string`, `integer`, `number`, `boolean` |
| `T \| None` | `anyOf: [schema(T), {"type": "null"}]` |
| `list[T]`, `dict[str, T]` | `array`, `object` + `additionalProperties` |
| `Literal`, `Enum` | `enum` |
| `Annotated[T, Field(...)]` | constraints on property |
| `TypedDict`, `@dataclass`, `Union`, `tuple` | `object`, `anyOf`, `prefixItems` |
| default value | `"default"` key; omitted from `required` |
| return annotation | `output` / MCP `outputSchema` |

All adapters read from `ToolDefinition` only. Schema is not generated twice inside an adapter.

## Why not framework `@tool` alone?

```
Function              FastMCP           LangChain          OpenAI
--------              -------           ---------          ------
@mcp.tool()     →     MCP JSON          rewrite            rewrite
LC @tool        →     rewrite           LC schema          rewrite
hand-written    →     drift             drift              drift
```

- [Pre-PEP `inspect.tool_schema`](https://discuss.python.org/t/pre-pep-discussion-typing-tool-inspect-tool-schema-close-the-zod-gap-for-python-agent-dev/107431): proposed stdlib fix, not shipped
- FastMCP `@mcp.tool()`: MCP transport + inference, not portable
- LangChain `StructuredTool.from_function`: infers schema per call site
- Pydantic `model_json_schema()`: domain models, not function-tool IR

## Comparison

| Solution | OpenAI | Anthropic | MCP | LangChain | FastMCP | Lock-in free |
|----------|--------|-----------|-----|-----------|---------|--------------|
| Framework `@tool` | partial | partial | partial | partial | partial | no |
| Hand-written JSON Schema | manual | manual | manual | manual | manual | yes |
| **toolschema** | yes | yes | yes | yes | yes | yes |

## Security

`toolschema export` and `toolschema inspect` import user-specified modules. Only point them at code you trust.

`validate()` checks arguments against generated schema; it does not sandbox tool execution. Your agent framework still runs the callable.

## Examples

| Path | Description |
|------|-------------|
| [`examples/01_basic.py`](examples/01_basic.py) | `@tool`, `schema()`, adapter output |
| [`examples/02_mcp_server.py`](examples/02_mcp_server.py) | FastMCP stdio server + `--check` smoke test |
| [`examples/03_langchain.py`](examples/03_langchain.py) | LangChain `from_toolschema` + invoke |
| [`examples/04_multi_provider.py`](examples/04_multi_provider.py) | One function, all provider formats |
| [`examples/demo_tools.py`](examples/demo_tools.py) | Reusable tools module |
| [`examples/verify_package.py`](examples/verify_package.py) | PyPI install verification |
| [`examples/deep_agents_demo.py`](examples/deep_agents_demo.py) | Cross-framework integration smoke test |

## Related

- [Pre-PEP: `inspect.tool_schema`](https://discuss.python.org/t/pre-pep-discussion-typing-tool-inspect-tool-schema-close-the-zod-gap-for-python-agent-dev/107431): target API shape
- [Standard Schema](https://standardschema.dev/): `tool.standard["~standard"]` protocol
- [FastMCP tools](https://gofastmcp.com/servers/tools): MCP `$ref` client limits
- [MCP specification](https://modelcontextprotocol.io/): `inputSchema` / `outputSchema`

## License

MIT. See [LICENSE](LICENSE).

## Community

* [Contributing](CONTRIBUTING.md)
* [Code of Conduct](CODE_OF_CONDUCT.md)
* [Security policy](SECURITY.md)
* [Documentation](https://toolschema.readthedocs.io)
