# Architecture

## Layer model

```
Layer 1: SCHEMA GENERATION   ← toolschema (this project)
Layer 2: VALIDATION          ← toolschema.validate() (thin) or Pydantic
Layer 3: ORCHESTRATION       ← LangChain, Pydantic AI, OpenAI Agents, etc.
Layer 4: TRANSPORT           ← FastMCP, HTTP APIs, stdio MCP
```

toolschema owns **Layer 1** only.

## Data flow

```
┌─────────────────────────────────────┐
│  Python function                    │
│  - type hints                       │
│  - defaults                         │
│  - docstring / @tool metadata       │
└──────────────┬──────────────────────┘
               │ schema(fn)
               ▼
┌─────────────────────────────────────┐
│  ToolDefinition (IR)                │
│  - name, description                │
│  - parameters (JSON Schema 2020-12)   │
│  - output (optional)                │
└──────────────┬──────────────────────┘
               │
     ┌─────────┼─────────┬─────────────┐
     ▼         ▼         ▼             ▼
 to_openai  to_mcp  to_anthropic  to_gemini
     │         │         │             │
     ▼         ▼         ▼             ▼
 integrations/ (optional glue to frameworks)
```

## Core modules

| Module | Role |
|--------|------|
| `_decorator.py` | `@tool` decorator, `ToolMeta` |
| `_introspect.py` | `schema()` — signature → `ToolDefinition` |
| `_types.py` | `type_to_schema()` type mapping |
| `_fields.py` | `Field`, Annotated metadata extraction |
| `_ir.py` | `ToolDefinition` dataclass + adapter methods |
| `_validate.py` | `validate_arguments()` |
| `_standard.py` | Standard Schema protocol |
| `_schema_utils.py` | Strip `$schema` for provider export |

## Adapter modules

| Module | Output |
|--------|--------|
| `adapters/openai.py` | OpenAI function tool |
| `adapters/anthropic.py` | Anthropic input_schema |
| `adapters/mcp.py` | MCP inputSchema / outputSchema |
| `adapters/gemini.py` | Gemini parameters |
| `adapters/_inline_refs.py` | `$ref` flattening |

**Rule:** Adapters read `ToolDefinition` only. Never call `type_to_schema()` inside an adapter.

## Integration modules

| Module | Framework |
|--------|-----------|
| `integrations/fastmcp.py` | FastMCP `register_tool` |
| `integrations/langchain.py` | LangChain `StructuredTool` |
| `integrations/openai_agents.py` | OpenAI Agents `FunctionTool` |
| `integrations/pydantic_ai.py` | Pydantic AI `Tool.from_schema` |

Integrations are **optional extras** — not imported by core.

## Design principles

1. **Function-first** — plain Python, Pydantic optional
2. **Zero framework lock-in** in core package
3. **Single IR** — one `ToolDefinition`, many adapters
4. **Pre-PEP aligned** — `schema(fn)`, `@tool` match proposed stdlib
5. **MCP-safe defaults** — inline `$ref` by default
6. **Testable** — golden snapshots per adapter

## JSON Schema dialect

Internal canonical dialect: **JSON Schema 2020-12**

```python
JSON_SCHEMA_2020_12 = "https://json-schema.org/draft/2020-12/schema"
```

Provider exports strip `$schema` where providers reject unknown keys.

## Testing strategy

| Layer | Tests |
|-------|-------|
| Type mapping | `test_core.py`, `test_types_extended.py` |
| Adapters | `test_adapters.py` + `tests/snapshots/` |
| Integrations | `test_integrations.py`, `test_parity.py` |
| End-to-end | `test_complex_e2e.py`, `test_deep_agents.py` |
| MCP stdio | `test_mcp_smoke.py` |
| CLI | `test_cli.py` |
| Scaffold | `test_init.py` |

## What we deliberately don't build

- Agent memory / planning
- MCP wire protocol (use FastMCP)
- LLM API clients
- Full JSON Schema validation engine (use Pydantic or jsonschema for that)
