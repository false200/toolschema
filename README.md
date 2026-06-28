# toolschema

[![PyPI version](https://img.shields.io/pypi/v/toolschema.svg)](https://pypi.org/project/toolschema/)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://pypi.org/project/toolschema/)
[![Documentation](https://img.shields.io/badge/docs-readthedocs-blue.svg)](https://toolschema.readthedocs.io/en/latest/)
[![CI](https://github.com/false200/toolschema/actions/workflows/ci.yml/badge.svg)](https://github.com/false200/toolschema/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

**Function → JSON Schema, once, everywhere.**

Python's answer to the gap TypeScript solved with [Zod](https://zod.dev/) + [Standard Schema](https://standardschema.dev/). Write a typed function. Export one schema. Use it in OpenAI, Anthropic, Gemini, MCP, LangChain, FastMCP, and Pydantic AI — without rewriting.

Every agent framework generates tool JSON differently. FastMCP is MCP-only. LangChain infers its own schema. OpenAI strict mode wants every field required. Claude Desktop breaks on `$ref`. **toolschema** is Layer 1 only: introspect a function once, adapt at the edge.

## Install

```sh
pip install toolschema
```

Extras:

```sh
pip install toolschema[fastmcp]        # FastMCP MCP servers
pip install toolschema[langchain]      # LangChain StructuredTool
pip install toolschema[openai-agents]  # OpenAI Agents SDK
pip install toolschema[pydantic-ai]    # Pydantic AI Tool.from_schema
pip install toolschema[all]            # all integrations + dev tools
```

Requires **Python 3.10+**. Core has zero framework dependencies (`typing_extensions` on 3.10 only).

**Full documentation:** https://toolschema.readthedocs.io (or build locally: `pip install mkdocs mkdocs-material && mkdocs serve`)

Docs links: [tutorials](docs/tutorials/) · [API reference](docs/api-reference.md) · [provider quirks](docs/provider-quirks.md)

## Usage

### Define a tool

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

definition = schema(get_weather)
definition.to_openai()
definition.to_mcp()
definition.to_anthropic()
```

Works without `@tool` — any typed function with a docstring:

```python
def add(a: int, b: int = 1) -> int:
    """Add two integers."""
    return a + b

definition = schema(add)
```

### FastMCP (MCP server)

```python
from fastmcp import FastMCP
from toolschema import schema
from toolschema.integrations.fastmcp import register_tool
from myapp.tools import greet, add

mcp = FastMCP("my-server")
register_tool(mcp, schema(greet), greet)
register_tool(mcp, schema(add), add)

mcp.run()  # stdio MCP server
```

`register_tool` uses your pre-built schema — no double generation inside FastMCP.

### LangChain

```python
from toolschema import schema
from toolschema.integrations.langchain import from_toolschema
from myapp.tools import search

tool = from_toolschema(schema(search), search)
result = tool.invoke({"query": "laptop", "limit": 5})
```

### OpenAI Agents SDK

```python
from toolschema import schema
from toolschema.integrations.openai_agents import to_agents_function_tool
from myapp.tools import add

agents_tool = to_agents_function_tool(schema(add), add)
```

### Pydantic AI

```python
from pydantic_ai import Agent
from toolschema import schema
from toolschema.integrations.pydantic_ai import from_toolschema
from myapp.tools import add

tool = from_toolschema(schema(add), add)
agent = Agent("openai:gpt-4o", tools=[tool])
```

### Scaffold an MCP project

```sh
toolschema init my-mcp-server
cd my-mcp-server
uv sync
uv run python -m my_mcp_server --check   # smoke test
uv run python -m my_mcp_server            # start server
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

### `@tool`

Optional decorator. Attaches tool metadata; does not change call semantics.

```python
@tool(name="custom_name", description="Override docstring")
def my_fn(x: str) -> str: ...
```

---

### `schema(fn) -> ToolDefinition`

Introspect a typed callable and return the canonical intermediate representation.

#### fn

*Required*  
Type: `Callable`

Any function or `@tool`-decorated callable with type hints. Docstring becomes the tool description.

```python
from toolschema import schema

definition = schema(my_function)
definition.name          # function name (or @tool override)
definition.description   # docstring (or @tool override)
definition.parameters    # JSON Schema 2020-12 object
definition.output        # return-type schema, or None
```

---

### `Field(...)`

Attach JSON Schema constraints and descriptions via `Annotated`:

```python
from typing import Annotated
from toolschema import Field

city: Annotated[str, Field(description="City name", min_length=1)]
```

Plain string shorthand (Pre-PEP style):

```python
city: Annotated[str, "City name"]
```

---

### `ToolDefinition`

Frozen dataclass — single source of truth for all adapters.

#### `to_json_schema() -> dict`

Canonical record: `name`, `description`, `parameters`, optional `output`.

#### `to_openai(*, strict=False) -> dict`

OpenAI function-calling shape: `{"type": "function", "function": {...}}`.

When `strict=True`, sets `additionalProperties: false` and marks every property required.

#### `to_anthropic() -> dict`

Anthropic Messages API tool shape. Constraints like `minLength` move into `description` text.

#### `to_mcp(*, inline_refs=True) -> dict`

MCP `tools/list` shape with `inputSchema` and optional `outputSchema`.

When `inline_refs=True` (default), flattens `$ref` / `$defs` for Claude Desktop and VS Code Copilot.

#### `to_gemini() -> dict`

Google Gemini `FunctionDeclaration` shape. Parameter types uppercased (`STRING`, `INTEGER`, …).

#### `validate(args) -> ValidationResult`

Thin argument checking against `parameters`. Returns `ValidationSuccess` or `ValidationFailure`.

```python
from toolschema import ValidationSuccess

result = definition.validate({"city": "London"})
if isinstance(result, ValidationSuccess):
    print(result.value)
```

#### `standard` (property)

[Standard Schema](https://standardschema.dev/schema) + [Standard JSON Schema](https://standardschema.dev/json-schema) protocol host (`tool.standard["~standard"]`).

---

### Integrations

| Function | Package extra | Purpose |
|----------|---------------|---------|
| `register_tool(mcp, definition, fn)` | `fastmcp` | Register on FastMCP without `@mcp.tool` schema regen |
| `from_toolschema(definition, fn)` | `langchain` | `StructuredTool` with `infer_schema=False` |
| `to_agents_function_tool(definition, fn)` | `openai-agents` | OpenAI Agents `FunctionTool` |
| `from_toolschema(definition, fn)` | `pydantic-ai` | Pydantic AI `Tool.from_schema` |

Import from submodules:

```python
from toolschema.integrations.fastmcp import register_tool
from toolschema.integrations.langchain import from_toolschema
from toolschema.integrations.openai_agents import to_agents_function_tool
from toolschema.integrations.pydantic_ai import from_toolschema
```

## Type coverage

| Python | JSON Schema |
|--------|-------------|
| `str`, `int`, `float`, `bool` | `string`, `integer`, `number`, `boolean` |
| `T \| None` | `anyOf: [schema(T), {type: null}]` |
| `list[T]`, `dict[str, T]` | `array`, `object` with `additionalProperties` |
| `Literal["a"]`, `Enum` | `enum` |
| `Annotated[T, Field(...)]` | constraints + `description` |
| `TypedDict`, `@dataclass` | `object` with `properties` |
| `Union[A, B]`, `tuple[...]` | `anyOf`, `prefixItems` |
| Default values | `"default"` key; omitted from `required` |
| Return type | `output` / `outputSchema` |

Deferred: generics, `ParamSpec`, docstring parameter parsing (Google/NumPy).

## Architecture

```
Python function + type hints
        │
        ▼
   schema(fn)  ──►  ToolDefinition (IR)
        │                │
        │    ┌───────────┼───────────┬──────────┐
        ▼    ▼           ▼           ▼          ▼
    validate()    to_openai()  to_mcp()  to_anthropic()  to_gemini()
                       │           │
                       ▼           ▼
              integrations/   register_tool()
              langchain       fastmcp
              openai_agents   pydantic_ai
```

**Rule:** adapters read `ToolDefinition` only. Schema is never generated twice.

## Why not framework decorators alone?

```
Your function          FastMCP              LangChain           OpenAI
------------          -------              ---------           ------
@mcp.tool()     →     MCP JSON only        rewrite needed      rewrite needed
@tool (LC)      →     rewrite needed       LC schema only      rewrite needed
raw OpenAI SDK  →     rewrite needed       rewrite needed      OpenAI JSON only
```

- [Pre-PEP `inspect.tool_schema`](https://discuss.python.org/t/pre-pep-discussion-typing-tool-inspect-tool-schema-close-the-zod-gap-for-python-agent-dev/107431): proposed stdlib fix, not shipped yet
- FastMCP `@mcp.tool()`: MCP transport + Pydantic inference, not portable
- Pydantic `model_json_schema()`: domain models, not function-tool IR
- LangChain `StructuredTool.from_function`: infers schema per call site

## Comparison

| Solution | OpenAI | Anthropic | MCP | LangChain | FastMCP | Zero lock-in |
|----------|--------|-----------|-----|-----------|---------|--------------|
| Framework `@tool` | partial | partial | partial | partial | partial | no |
| Pydantic JSON Schema | manual | manual | manual | manual | manual | yes |
| **toolschema** | yes | yes | yes | yes | yes | yes |

## Provider quirks

| Provider | Behavior |
|----------|----------|
| **OpenAI** | `strict=True` → all properties required, `additionalProperties: false` |
| **Anthropic** | `minLength`, `pattern`, etc. folded into `description` |
| **MCP** | `inline_refs=True` default; camelCase `inputSchema` / `outputSchema` |
| **Gemini** | uppercased types; parameters only (no output schema yet) |

Details: [docs/provider-quirks.md](docs/provider-quirks.md)

## Examples

| Path | Description |
|------|-------------|
| [`examples/01_basic.py`](examples/01_basic.py) | `@tool`, `schema()`, adapter output |
| [`examples/02_mcp_server.py`](examples/02_mcp_server.py) | FastMCP stdio server + `--check` smoke test |
| [`examples/03_langchain.py`](examples/03_langchain.py) | LangChain `from_toolschema` + invoke |
| [`examples/04_multi_provider.py`](examples/04_multi_provider.py) | One function → all provider formats |
| [`examples/demo_tools.py`](examples/demo_tools.py) | Sample tools module |
| [`examples/verify_package.py`](examples/verify_package.py) | End-to-end package verification script |
| [`examples/deep_agents_demo.py`](examples/deep_agents_demo.py) | Cross-framework deep integration demo |

## Testing

```sh
uv sync --extra dev --extra fastmcp --extra langchain --extra openai-agents --extra pydantic-ai
uv run pytest -v
uv run python examples/deep_agents_demo.py
```

92 tests: unit, golden snapshots, parity vs native FastMCP/LangChain, MCP stdio smoke, deep cross-agent harness.

## Non-goals

- Replacing Pydantic for domain modeling / validation
- Agent orchestration, memory, or MCP transport
- Live LLM API translation

## Related

- [Pre-PEP: `inspect.tool_schema`](https://discuss.python.org/t/pre-pep-discussion-typing-tool-inspect-tool-schema-close-the-zod-gap-for-python-agent-dev/107431) — API shape we align with
- [Standard Schema](https://standardschema.dev/) — interop protocol
- [FastMCP tools](https://gofastmcp.com/servers/tools) — MCP `$ref` client limitations
- [MCP specification](https://modelcontextprotocol.io/) — `inputSchema` / `outputSchema`

## License

MIT. See [LICENSE](LICENSE).

## Contributing

PRs welcome. See [CONTRIBUTING.md](CONTRIBUTING.md). Run `uv run pytest && uv run ruff check src tests` before submitting.

## Publishing

See [.github/PYPI_PUBLISH.md](.github/PYPI_PUBLISH.md) for automated PyPI releases via GitHub Actions.

## Community

- [Documentation](https://toolschema.readthedocs.io)
- [Contributing](CONTRIBUTING.md)
- [Code of Conduct](CODE_OF_CONDUCT.md)
- [Security policy](SECURITY.md)
