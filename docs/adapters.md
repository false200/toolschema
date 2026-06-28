# Provider adapters

Adapters convert `ToolDefinition` into each LLM provider's expected JSON shape.

**Always use `ToolDefinition` methods** in application code — adapters are the implementation.

```python
definition = schema(my_fn)

definition.to_openai()
definition.to_openai(strict=True)
definition.to_anthropic()
definition.to_mcp()
definition.to_mcp(inline_refs=False)
definition.to_gemini()
```

## Canonical (internal)

`definition.parameters` is JSON Schema **2020-12** with:

- `"$schema": "https://json-schema.org/draft/2020-12/schema"`
- `"type": "object"`
- `"additionalProperties": false`
- `"properties"` / `"required"`

`definition.to_json_schema()` wraps this as `{name, description, parameters, output?}`.

## OpenAI

```python
payload = definition.to_openai()
# {
#   "type": "function",
#   "function": {
#     "name": "add",
#     "description": "Add two integers.",
#     "parameters": { "type": "object", "properties": {...}, "required": [...] }
#   }
# }
```

### Strict mode

```python
strict = definition.to_openai(strict=True)
```

- Sets `additionalProperties: false`
- Every property key added to `required` (including those with defaults)

Use when OpenAI structured tool calling requires all fields present.

## Anthropic

```python
payload = definition.to_anthropic()
# {
#   "name": "add",
#   "description": "...",
#   "input_schema": { "type": "object", "properties": {...} }
# }
```

**Quirk:** `minLength`, `pattern`, `minimum`, etc. are appended to the property `description` text and removed as JSON Schema keywords. See [Provider quirks](provider-quirks.md).

## MCP

```python
payload = definition.to_mcp()
# {
#   "name": "add",
#   "description": "...",
#   "inputSchema": { ... },
#   "outputSchema": { ... }   # if return type annotated
# }
```

### `$ref` inlining (default `inline_refs=True`)

Claude Desktop and VS Code Copilot do not resolve `$ref`. Default MCP export flattens `$defs` into inline schemas.

```python
# Keep $ref if your client supports it
definition.to_mcp(inline_refs=False)
```

## Gemini

```python
payload = definition.to_gemini()
# {
#   "name": "add",
#   "description": "...",
#   "parameters": { "type": "OBJECT", "properties": { "a": {"type": "INTEGER"}, ... } }
# }
```

**Quirk:** Types are uppercased. Output schema not included in v1.0.

## Comparison table

| Adapter | Key names | Strict extras | Output schema |
|---------|-----------|---------------|---------------|
| Canonical | `parameters`, `output` | — | yes |
| OpenAI | `function.parameters` | `strict=True` | no (params only) |
| Anthropic | `input_schema` | constraints → description | no |
| MCP | `inputSchema`, `outputSchema` | `inline_refs` | yes |
| Gemini | `parameters` | uppercased types | no |

## Diff two formats

```bash
toolschema diff myapp.tools:add --targets openai,mcp
```

Or in Python:

```python
import json
print(json.dumps(definition.to_openai(), indent=2))
print(json.dumps(definition.to_mcp(), indent=2))
```
