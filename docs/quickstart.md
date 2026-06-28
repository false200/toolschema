# Quick start

This guide takes you from zero to a working tool schema in five minutes.

## Step 1 — Define a function

```python
from toolschema import tool, schema

@tool
def add(a: int, b: int = 1) -> int:
    """Add two integers."""
    return a + b
```

Rules:

- Every parameter needs a **type hint**
- The **docstring** becomes the tool description for the LLM
- **`@tool`** is optional but lets you override name/description

## Step 2 — Generate the schema

```python
definition = schema(add)

print(definition.name)         # "add"
print(definition.description)  # "Add two integers."
print(definition.parameters)   # JSON Schema dict
```

## Step 3 — Export for a provider

```python
openai_tool = definition.to_openai()
mcp_tool = definition.to_mcp()
anthropic_tool = definition.to_anthropic()
```

Each method returns a `dict` ready to pass to that provider's API or SDK.

## Step 4 — Validate arguments (optional)

```python
from toolschema import ValidationSuccess, ValidationFailure

result = definition.validate({"a": 5})
if isinstance(result, ValidationSuccess):
    print(add(**result.value))  # uses defaults for missing optional fields
```

## Step 5 — Use with a framework

Pick one integration — same `definition`, same function:

=== "FastMCP"

    ```python
    from fastmcp import FastMCP
    from toolschema.integrations.fastmcp import register_tool

    mcp = FastMCP("demo")
    register_tool(mcp, definition, add)
    mcp.run()
    ```

=== "LangChain"

    ```python
    from toolschema.integrations.langchain import from_toolschema

    lc_tool = from_toolschema(definition, add)
    lc_tool.invoke({"a": 10, "b": 32})  # 42
    ```

=== "OpenAI Agents"

    ```python
    from toolschema.integrations.openai_agents import to_agents_function_tool

    agents_tool = to_agents_function_tool(definition, add)
    ```

## CLI one-liner

```bash
toolschema inspect myapp.tools:add --format openai,mcp
```

## Next steps

- [Defining tools](defining-tools.md) — `Field`, `Literal`, optional types, complex params
- [Integrations](integrations.md) — full framework examples
- [API reference](api-reference.md) — every function documented
