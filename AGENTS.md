# AGENTS.md — Instructions for AI coding agents

This file tells automated agents (Cursor, Claude Code, Copilot, etc.) **how to implement `toolschema`** without breaking design intent.

## Mission

Build **Layer 1 only**: `(Python function + type hints) → canonical JSON Schema → provider-specific adapters`.

Do **not** build agent orchestration, MCP transport, or replace Pydantic validation.

## Read first

1. [README.md](./README.md) — full problem, architecture, build plan
2. [Pre-PEP thread](https://discuss.python.org/t/pre-pep-discussion-typing-tool-inspect-tool-schema-close-the-zod-gap-for-python-agent-dev/107431) — target API shape

## Hard rules

| Rule | Reason |
|------|--------|
| Core package MUST NOT import FastMCP, LangChain, OpenAI SDK | Zero framework lock-in |
| All provider output goes through `ToolDefinition` IR | Single source of truth |
| JSON Schema 2020-12 is canonical internal dialect | Pre-PEP alignment |
| MCP adapter defaults `inline_refs=True` | Claude Desktop / Copilot break on `$ref` |
| Every type mapping needs a unit test | Schema bugs break agents silently |
| Golden snapshot tests for each adapter | Prevent regressions |
| Match Pre-PEP API: `schema(fn)`, `@tool` | Future stdlib migration |

## Implementation order

```
Phase 0: pyproject.toml, CI, empty package
Phase 1: _introspect.py, _types.py, _ir.py, @tool, schema()
Phase 2: adapters/openai.py, adapters/mcp.py
Phase 3: cli.py inspect command
Phase 4: integrations/* (optional extras)
Phase 5: PyPI, examples, docs
```

**Do not start Phase 4 before Phase 1–2 tests pass.**

## Key types

```python
# src/toolschema/_ir.py
@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    parameters: dict[str, Any]
    output: dict[str, Any] | None = None

    def to_json_schema(self) -> dict: ...
    def to_openai(self, *, strict: bool = False) -> dict: ...
    def to_mcp(self, *, inline_refs: bool = True) -> dict: ...
    def to_anthropic(self) -> dict: ...
    def to_gemini(self) -> dict: ...
```

## Type → JSON Schema mapping (Phase 1)

| Python | JSON Schema |
|--------|-------------|
| `str` | `{"type": "string"}` |
| `int` | `{"type": "integer"}` |
| `float` | `{"type": "number"}` |
| `bool` | `{"type": "boolean"}` |
| `T \| None` | `{"anyOf": [schema(T), {"type": "null"}]}` |
| `list[T]` | `{"type": "array", "items": schema(T)}` |
| `dict[str, T]` | `{"type": "object", "additionalProperties": schema(T)}` |
| `Literal["a"]` | `{"enum": ["a"]}` |
| default value | `"default"` key; omit from `"required"` |

## Annotated / Field

```python
Annotated[str, Field(description="...", min_length=1)]
# → {"type": "string", "description": "...", "minLength": 1}
```

Support plain string in Annotated as shorthand (Pre-PEP + Claude SDK pattern):

```python
Annotated[str, "City name"]  # → description only
```

## OpenAI strict adapter

When `strict=True`:

- Set `"additionalProperties": false` on parameters object
- Every property key must appear in `"required"`

## MCP adapter

Output shape:

```json
{
  "name": "...",
  "description": "...",
  "inputSchema": { "type": "object", ... },
  "outputSchema": { ... }
}
```

Run `$ref` inlining before return if `inline_refs=True`.

## Test fixtures

Create `tests/fixtures.py`:

```python
def add(a: int, b: int = 1) -> int:
    """Add two numbers."""
    return a + b

def search_github(repo: str, query: str, limit: int = 10) -> list[dict]:
    """Search issues in a GitHub repository."""
    ...
```

Use these in all snapshot tests.

## Commands

```bash
uv sync
uv run pytest -v
uv run ruff check src tests
uv run ruff format src tests
```

## What NOT to do

- ❌ Add LangChain import to `src/toolschema/_types.py`
- ❌ Generate schema separately in each adapter (use IR only)
- ❌ Full Pydantic validation in core (thin `validate()` optional in Phase 2+)
- ❌ Support every Python type in MVP (defer ParamSpec, generics)
- ❌ Change golden snapshots without explaining in PR

## Success definition

An agent can run:

```python
from toolschema import tool, schema

@tool
def greet(name: str) -> str:
    """Say hello."""
    return f"Hello, {name}"

assert schema(greet).to_mcp()["name"] == "greet"
assert "name" in schema(greet).to_openai()["function"]["parameters"]["properties"]
```

And:

```bash
uv run pytest  # all green
```

## Questions?

Open a GitHub issue with label `design` before large architectural changes.
