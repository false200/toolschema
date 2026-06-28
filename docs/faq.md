# FAQ

## General

### What is toolschema?

A library that converts typed Python functions into JSON Schema for AI agent tools, then exports provider-specific formats (OpenAI, Anthropic, Gemini, MCP) and integrates with FastMCP, LangChain, OpenAI Agents, and Pydantic AI.

### How is this different from Pydantic?

Pydantic validates and models **data**. toolschema introspects **functions** and produces **tool definitions** for LLMs. You can use both — Pydantic models work as parameter types.

### How is this different from FastMCP `@mcp.tool()`?

FastMCP generates MCP schemas inside the MCP framework. toolschema generates schema once and can target MCP **and** OpenAI **and** LangChain from the same function.

### Is this on PyPI?

Yes: `pip install toolschema` — https://pypi.org/project/toolschema/

---

## Usage

### Do I need `@tool`?

No. `schema(any_typed_function)` works if you have type hints and a docstring.

### Can I use plain functions without a framework?

Yes:

```python
definition = schema(my_fn)
requests.post(api_url, json=definition.to_openai())
```

### Why do I need integration glue (`register_tool`, etc.)?

Each framework has its own registration API. toolschema eliminates **schema** duplication, not the one-line registration call.

### Does `validate()` call my function?

No. It only checks arguments against the schema. Call your function separately:

```python
result = definition.validate(args)
if isinstance(result, ValidationSuccess):
    my_fn(**result.value)
```

---

## Providers

### Why does Anthropic schema look different?

Constraints like `minLength` move into `description` text. See [Provider quirks](provider-quirks.md).

### Why inline `$ref` for MCP?

Claude Desktop and VS Code Copilot don't resolve `$ref`. Default `to_mcp(inline_refs=True)` flattens schemas.

### Does Gemini get output schemas?

Not in v1.0 — parameters only.

---

## Errors

### `TypeError: Unsupported type annotation`

Your type hint uses something not yet mapped. See [Type mapping](type-mapping.md). Common fix: use concrete types instead of generics.

### `ImportError: fastmcp is required`

Install the extra: `pip install toolschema[fastmcp]`

### Schema missing parameter descriptions

Use `Annotated[T, Field(description="...")]` or `Annotated[T, "description"]`. Docstring param parsing is not implemented yet.

---

## Development

### How do I run tests?

```bash
uv sync --extra all
uv run pytest -v
```

### How do I update golden snapshots?

```bash
uv run pytest tests/test_adapters.py --snapshot-update  # if using pytest-snapshot
# or manually edit tests/snapshots/*.json with justification
```

### Where is the Pre-PEP alignment doc?

[pre-pep-alignment.md](pre-pep-alignment.md)

---

## Roadmap / limitations

| Feature | Status |
|---------|--------|
| Core types + adapters | ✅ v1.0 |
| FastMCP / LangChain / Agents / Pydantic AI | ✅ v1.0 |
| `validate()` | ✅ v1.0 |
| Standard Schema protocol | ✅ v1.0 |
| `toolschema init` | ✅ v1.0 |
| Docstring param descriptions | ❌ deferred |
| Generics / ParamSpec | ❌ deferred |
| Gemini output schema | ❌ deferred |
| PyPI | ✅ published |
