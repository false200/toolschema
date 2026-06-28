# API reference

Complete reference for the public **toolschema** API (v1.0.0).

## Package exports (`toolschema`)

| Name | Kind | Description |
|------|------|-------------|
| `tool` | decorator | Mark a function as a tool |
| `schema` | function | Build `ToolDefinition` from a callable |
| `Field` | class | JSON Schema metadata for `Annotated` |
| `ToolDefinition` | class | Canonical tool IR |
| `ValidationSuccess` | class | Successful validation result |
| `ValidationFailure` | class | Failed validation result |
| `ValidationIssue` | class | Single validation error |
| `ValidationResult` | type alias | `ValidationSuccess \| ValidationFailure` |
| `JSONSchemaOptions` | class | Standard JSON Schema export options |
| `StandardSchemaHost` | class | Standard Schema protocol host |
| `__version__` | str | Package version |

---

## `tool`

```python
@tool
def fn(...): ...

@tool(name="custom", description="Override")
def fn(...): ...

decorator = tool(name="custom")
@decorator
def fn(...): ...
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `fn` | `Callable` | — | Function when used as `@tool` without parens |
| `name` | `str \| None` | `None` | Override tool name |
| `description` | `str \| None` | `None` | Override docstring description |

**Returns:** the original function (wrapped), still callable.

---

## `schema(fn) -> ToolDefinition`

```python
definition = schema(my_function)
definition = schema(decorated_function)  # respects @tool metadata
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `fn` | `Callable` | Typed function or `@tool`-decorated callable |

**Raises:** `TypeError` for unsupported type annotations.

---

## `Field`

```python
Field(
    description: str | None = None,
    min_length: int | None = None,
    max_length: int | None = None,
    ge: int | float | None = None,
    le: int | float | None = None,
    gt: int | float | None = None,
    lt: int | float | None = None,
    pattern: str | None = None,
)
```

Frozen dataclass. Use inside `Annotated[T, Field(...)]`.

---

## `ToolDefinition`

Frozen dataclass:

```python
ToolDefinition(
    name: str,
    description: str,
    parameters: dict[str, Any],      # JSON Schema 2020-12 object
    output: dict[str, Any] | None,   # return type schema
)
```

### `to_json_schema() -> dict`

Canonical tool record:

```json
{"name": "...", "description": "...", "parameters": {...}, "output": {...}}
```

### `to_openai(*, strict=False) -> dict`

OpenAI Chat Completions / Responses function tool:

```json
{"type": "function", "function": {"name": "...", "description": "...", "parameters": {...}}}
```

| Parameter | Type | Default | Effect |
|-----------|------|---------|--------|
| `strict` | `bool` | `False` | All properties required; `additionalProperties: false` |

### `to_anthropic() -> dict`

```json
{"name": "...", "description": "...", "input_schema": {...}}
```

Constraints moved into property descriptions (see [Provider quirks](provider-quirks.md)).

### `to_mcp(*, inline_refs=True) -> dict`

```json
{"name": "...", "description": "...", "inputSchema": {...}, "outputSchema": {...}}
```

| Parameter | Type | Default | Effect |
|-----------|------|---------|--------|
| `inline_refs` | `bool` | `True` | Flatten `$ref` / `$defs` for Claude Desktop |

### `to_gemini() -> dict`

```json
{"name": "...", "description": "...", "parameters": {...}}
```

Types uppercased (`STRING`, `INTEGER`, …). Parameters only.

### `validate(args) -> ValidationResult`

Validate a `dict` of arguments against `parameters`.

```python
result = definition.validate({"name": "Ada"})
```

Returns `ValidationSuccess(value=...)` with defaults filled in, or `ValidationFailure(issues=...)`.

### `standard` (property) -> `StandardSchemaHost`

Standard Schema protocol. Access via `definition.standard["~standard"]`.

---

## Validation types

### `ValidationSuccess`

| Field | Type |
|-------|------|
| `value` | `dict[str, Any]` — normalized args with defaults applied |
| `issues` | `None` |

### `ValidationFailure`

| Field | Type |
|-------|------|
| `value` | `None` |
| `issues` | `tuple[ValidationIssue, ...]` |

### `ValidationIssue`

| Field | Type |
|-------|------|
| `message` | `str` |
| `path` | `tuple[str \| int, ...]` — e.g. `("tags", 0)` |
| `kind` | `ValidationIssueKind` |

### `ValidationIssueKind`

`REQUIRED` · `TYPE` · `ENUM` · `CONSTRAINT` · `ADDITIONAL_PROPERTY`

---

## Standard Schema

### `JSONSchemaOptions`

```python
JSONSchemaOptions(
    target: Literal["draft-2020-12", "draft-07", "openapi-3.0"] = "draft-2020-12",
    library_options: dict[str, Any] | None = None,
)
```

### `StandardSchemaHost`

Mapping with single key `"~standard"` containing:

- `version` — `1`
- `vendor` — `"toolschema"`
- `validate` — callable
- `jsonSchema.input` / `jsonSchema.output` — callables

```python
host = definition.standard
standard = host["~standard"]
input_schema = standard["jsonSchema"]["input"]()
```

---

## Integrations — FastMCP

`toolschema.integrations.fastmcp`

### `register_tool(mcp, tool, fn) -> Any`

Register a pre-built schema on a FastMCP server.

| Parameter | Type | Description |
|-----------|------|-------------|
| `mcp` | `FastMCP` | Server instance |
| `tool` | `ToolDefinition` | Pre-built schema |
| `fn` | `Callable` | Function to execute |

**Requires:** `pip install toolschema[fastmcp]`

### `mcp_tool_payload(tool) -> dict`

Same as `tool.to_mcp()` without importing FastMCP.

---

## Integrations — LangChain

`toolschema.integrations.langchain`

### `from_toolschema(tool, fn) -> StructuredTool`

| Parameter | Type | Description |
|-----------|------|-------------|
| `tool` | `ToolDefinition` | Pre-built schema |
| `fn` | `Callable` | Function to invoke |

Uses `infer_schema=False` and passes `tool.parameters` as `args_schema`.

**Requires:** `pip install toolschema[langchain]`

---

## Integrations — OpenAI Agents

`toolschema.integrations.openai_agents`

### `function_tool_kwargs(tool, *, strict=False) -> dict`

Kwargs for `FunctionTool`: `name`, `description`, `params_json_schema`, `strict_json_schema`.

### `to_agents_function_tool(tool, fn, *, strict=False) -> FunctionTool`

Full OpenAI Agents SDK tool with `on_invoke_tool` wired to `fn`.

### `to_openai_agent_tool(tool, fn) -> dict`

Payload with `type`, `function`, `callable`, and `agents_tool`.

### `invoke_agents_tool(tool, fn, arguments) -> Any` (async)

### `invoke_agents_tool_sync(tool, fn, arguments) -> Any`

Direct invoke without running a full agent.

**Requires:** `pip install toolschema[openai-agents]`

---

## Integrations — Pydantic AI

`toolschema.integrations.pydantic_ai`

### `from_toolschema(tool, fn) -> Tool`

Pydantic AI `Tool.from_schema` with pre-built JSON Schema.

### `to_pydantic_ai_tool(tool, fn) -> dict`

Descriptor: `name`, `description`, `parameters_json_schema`, `function`.

### `prepare_toolset(tools) -> list[dict]`

Batch convert `list[tuple[ToolDefinition, Callable]]`.

**Requires:** `pip install toolschema[pydantic-ai]`

---

## CLI

Entry point: `toolschema` (module `toolschema.cli:main`)

### `toolschema inspect TARGET [--format FORMAT]`

| Argument | Description |
|----------|-------------|
| `TARGET` | `module.path:function` or `module:obj.attr` |
| `--format` | `canonical`, `openai`, `openai-strict`, `anthropic`, `mcp`, `gemini` (comma-separated) |

### `toolschema diff TARGET [--targets A,B]`

Compare adapter outputs. Default targets: `openai,mcp`.

### `toolschema export MODULE [--output FILE]`

Export all callables in a module that `schema()` accepts.

### `toolschema init NAME [--path DIR]`

Scaffold MCP server project from packaged template.

---

## Scaffolding (internal API)

`toolschema._init_scaffold` (used by CLI)

### `scaffold_mcp_server(target_dir, project_name) -> ScaffoldResult`

### `slugify_package_name(name) -> str`

### `ScaffoldResult`

| Field | Type |
|-------|------|
| `root` | `Path` |
| `package_name` | `str` |
| `project_name` | `str` |

---

## Adapter modules (advanced)

Low-level adapters — prefer `ToolDefinition` methods:

| Module | Function |
|--------|----------|
| `toolschema.adapters.openai` | `to_openai(tool, *, strict=False)` |
| `toolschema.adapters.anthropic` | `to_anthropic(tool)` |
| `toolschema.adapters.mcp` | `to_mcp(tool, *, inline_refs=True)` |
| `toolschema.adapters.gemini` | `to_gemini(tool)` |
| `toolschema.adapters._inline_refs` | `inline_refs(schema)` |

---

## Internal (not public API)

These exist for maintainers — do not import in application code:

| Module | Purpose |
|--------|---------|
| `_introspect` | `schema()`, `ToolMeta` |
| `_types` | `type_to_schema()` |
| `_validate` | `validate_arguments()` |
| `_schema_utils` | `strip_canonical_meta()` |
| `_decorator` | `@tool` implementation |
