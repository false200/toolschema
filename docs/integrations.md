# Framework integrations

Integrations connect `ToolDefinition` to agent frameworks **without regenerating schema**.

Pattern for every integration:

```python
definition = schema(your_function)
# one line of framework-specific glue
```

## FastMCP

**Install:** `pip install toolschema[fastmcp]`

```python
from fastmcp import FastMCP
from toolschema import schema
from toolschema.integrations.fastmcp import register_tool
from myapp.tools import greet, add

mcp = FastMCP("my-server")

register_tool(mcp, schema(greet), greet)
register_tool(mcp, schema(add), add)

if __name__ == "__main__":
    mcp.run()  # stdio transport
```

### How it works

1. `FunctionTool.from_function(fn)` for execution semantics
2. `model_copy(update={"parameters": tool.parameters})` replaces inferred schema
3. Schema is generated **once** by toolschema

### Smoke test

```bash
python examples/02_mcp_server.py --check
```

---

## LangChain

**Install:** `pip install toolschema[langchain]`

```python
from toolschema import schema
from toolschema.integrations.langchain import from_toolschema
from myapp.tools import search

definition = schema(search)
tool = from_toolschema(definition, search)

result = tool.invoke({"query": "laptop", "limit": 5})
```

### How it works

`StructuredTool.from_function(fn, args_schema=parameters, infer_schema=False)`

The `args_schema` is toolschema's dict — LangChain does not re-infer from signatures.

### Agent example

```python
from langchain_core.messages import HumanMessage
from langchain_core.tools import StructuredTool

tools = [from_toolschema(schema(search), search)]
# pass tools= to your agent / graph
```

See `examples/03_langchain.py`.

---

## OpenAI Agents SDK

**Install:** `pip install toolschema[openai-agents]`

```python
from toolschema import schema
from toolschema.integrations.openai_agents import (
    to_agents_function_tool,
    invoke_agents_tool_sync,
)
from myapp.tools import add

definition = schema(add)
agents_tool = to_agents_function_tool(definition, add)

# Direct invoke (no agent loop)
result = invoke_agents_tool_sync(definition, add, {"a": 10, "b": 32})
```

### Functions

| Function | Use when |
|----------|----------|
| `function_tool_kwargs(tool)` | Building `FunctionTool` yourself |
| `to_agents_function_tool(tool, fn)` | Ready-made `FunctionTool` |
| `to_openai_agent_tool(tool, fn)` | Dict with `callable` + `agents_tool` |
| `invoke_agents_tool` / `_sync` | Test invoke without agent |

---

## Pydantic AI

**Install:** `pip install toolschema[pydantic-ai]`

```python
from pydantic_ai import Agent, Tool
from toolschema import schema
from toolschema.integrations.pydantic_ai import from_toolschema
from myapp.tools import add

definition = schema(add)
tool = from_toolschema(definition, add)

agent = Agent("openai:gpt-4o", tools=[tool])
```

### Descriptor (manual registration)

```python
from toolschema.integrations.pydantic_ai import to_pydantic_ai_tool, prepare_toolset

descriptor = to_pydantic_ai_tool(definition, add)
# descriptor["parameters_json_schema"], descriptor["function"]

tools = prepare_toolset([(schema(add), add), (schema(greet), greet)])
```

Uses `Tool.from_schema()` — Pydantic AI does not re-infer from signatures.

---

## Cross-framework parity

The same function should produce equivalent schemas everywhere:

```bash
uv run python examples/deep_agents_demo.py
```

Tests in `tests/test_parity.py` and `tests/test_deep_agents.py` verify semantic equivalence.

## Import cheat sheet

```python
from toolschema.integrations.fastmcp import register_tool, mcp_tool_payload
from toolschema.integrations.langchain import from_toolschema
from toolschema.integrations.openai_agents import (
    function_tool_kwargs,
    to_agents_function_tool,
    to_openai_agent_tool,
    invoke_agents_tool,
    invoke_agents_tool_sync,
)
from toolschema.integrations.pydantic_ai import (
    from_toolschema,  # note: same name as langchain — import from submodule
    to_pydantic_ai_tool,
    prepare_toolset,
)
```
