# Tutorial 1: Getting started with toolschema

**Time:** 10 minutes  
**Prerequisites:** Python 3.10+, [uv](https://docs.astral.sh/uv/)

toolschema turns a typed Python function into JSON Schema for any AI agent provider — once, without framework lock-in.

## Install

```bash
uv add toolschema
# or with integrations:
uv add "toolschema[fastmcp,langchain]"
```

## Define a tool

```python
from typing import Annotated
from toolschema import Field, schema, tool


@tool
def get_weather(
    city: Annotated[str, Field(description="City name", min_length=1)],
    units: str = "celsius",
) -> dict:
    """Get current weather for a city."""
    return {"city": city, "temp": 22, "units": units}
```

## Export schemas

```python
definition = schema(get_weather)

definition.parameters                    # canonical JSON Schema 2020-12
definition.to_openai()                   # OpenAI function-calling
definition.to_openai(strict=True)        # OpenAI strict mode
definition.to_mcp()                      # MCP inputSchema (+ outputSchema)
definition.to_anthropic()                # Anthropic input_schema
definition.to_gemini()                   # Gemini FunctionDeclaration
```

## Validate arguments (Pre-PEP aligned)

```python
result = definition.validate({"city": "Paris"})
if result.issues:
    for issue in result.issues:
        print(issue.message)
else:
    print(result.value)  # defaults filled in
```

## Standard Schema interop

Ecosystem tools that support [Standard Schema](https://standardschema.dev/schema) can consume toolschema without custom adapters:

```python
from toolschema import JSONSchemaOptions

standard = definition.standard["~standard"]
input_schema = standard["jsonSchema"]["input"](JSONSchemaOptions(target="draft-2020-12"))
validated = standard["validate"]({"city": "Tokyo"})
```

## CLI inspect

```bash
uv run toolschema inspect myapp.tools:get_weather --format mcp
uv run toolschema diff myapp.tools:get_weather --targets openai,mcp
```

## Next steps

- [Tutorial 2: Build an MCP server](02-mcp-server.md)
- [Tutorial 3: LangChain integration](03-langchain-integration.md)
- [Tutorial 4: Multi-provider export](04-multi-provider-export.md)
