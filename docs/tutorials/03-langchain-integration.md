# Tutorial 3: LangChain integration

**Time:** 10 minutes  
**Prerequisites:** [Tutorial 1](01-getting-started.md), `toolschema[langchain]`

Use toolschema as the single source of truth for tool schemas, then register them in LangChain without regenerating JSON Schema.

## Define and export

```python
from toolschema import schema, tool
from toolschema.integrations.langchain import from_toolschema


@tool
def multiply(a: int, b: int) -> int:
    """Multiply two integers."""
    return a * b


definition = schema(multiply)
structured_tool = from_toolschema(definition, multiply)
```

`from_toolschema()` passes the canonical JSON Schema directly to LangChain as `args_schema` — `infer_schema=False`, so LangChain does not re-introspect the function.

## Invoke the tool

```python
result = structured_tool.invoke({"a": 6, "b": 7})
print(result)  # 42
```

## Simulated agent loop

```python
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

messages = [HumanMessage(content="What is 6 times 7?")]

tool_call = {"name": "multiply", "args": {"a": 6, "b": 7}, "id": "call_1"}
messages.append(AIMessage(content="", tool_calls=[tool_call]))

result = structured_tool.invoke(tool_call["args"])
messages.append(ToolMessage(content=str(result), tool_call_id=tool_call["id"]))
```

No LLM API key required for this pattern — it demonstrates wiring toolschema schemas into a LangChain agent loop.

## Schema parity

The integrated tool uses the same schema as OpenAI export:

```python
assert structured_tool.args_schema == definition.to_openai()["function"]["parameters"]
```

## Run the example

```bash
uv sync --extra langchain
uv run python examples/03_langchain.py
```

## Next steps

- [Tutorial 4: Multi-provider export](04-multi-provider-export.md)
- [Provider quirks](../provider-quirks.md)
