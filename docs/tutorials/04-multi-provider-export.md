# Tutorial 4: Multi-provider export from one function

**Time:** 10 minutes  
**Prerequisites:** [Tutorial 1](01-getting-started.md)

One Python function. Four provider formats. Zero rewrites.

## The function

```python
from typing import Annotated
from toolschema import Field, schema, tool


@tool
def book_flight(
    origin: Annotated[str, Field(description="IATA code", pattern=r"^[A-Z]{3}$")],
    destination: Annotated[str, Field(description="IATA code", pattern=r"^[A-Z]{3}$")],
    passengers: Annotated[int, Field(ge=1, le=9)] = 1,
) -> dict:
    """Book a one-way flight."""
    return {"confirmation": "TS-12345", "origin": origin, "destination": destination}
```

## Export all formats

```python
definition = schema(book_flight)

openai = definition.to_openai()
openai_strict = definition.to_openai(strict=True)
mcp = definition.to_mcp()              # inline_refs=True by default (no $ref)
anthropic = definition.to_anthropic()  # constraints → description text
gemini = definition.to_gemini()        # STRING, INTEGER, OBJECT types
```

## CLI batch export

```bash
uv run toolschema inspect myapp.tools:book_flight --format openai,mcp,anthropic,gemini
uv run toolschema export myapp.tools --output tools.json
```

## OpenAI Agents SDK

```python
from toolschema.integrations.openai_agents import to_agents_function_tool

agents_tool = to_agents_function_tool(definition, book_flight)
# agents_tool.params_json_schema matches definition.to_openai() parameters
```

## Pydantic AI descriptor

```python
from toolschema.integrations.pydantic_ai import to_pydantic_ai_tool

descriptor = to_pydantic_ai_tool(definition, book_flight)
# descriptor["parameters_json_schema"] ready for pydantic-ai registration
```

## Run the example

```bash
uv run python examples/04_multi_provider.py
```

## Provider differences (intentional)

| Provider | Key difference |
|----------|----------------|
| OpenAI strict | All properties required; `additionalProperties: false` |
| MCP | camelCase `inputSchema`; `$ref` inlined by default |
| Anthropic | `minLength`/`pattern` moved into description text |
| Gemini | Uppercase type names (`STRING`, `INTEGER`) |

See [provider quirks](../provider-quirks.md) for details.

## Next steps

- [Pre-PEP alignment](../pre-pep-alignment.md)
- [Build an MCP server](02-mcp-server.md)
