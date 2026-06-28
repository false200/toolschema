# Defining tools

## The `@tool` decorator

```python
from toolschema import tool

@tool
def search(query: str, limit: int = 10) -> list[dict]:
    """Search the catalog."""
    ...
```

`@tool` does **not** change how the function runs. It only attaches metadata for `schema()`.

### Override name or description

```python
@tool(name="web_search", description="Search the public web for current information.")
def search(query: str) -> list[dict]:
    ...
```

### Without decorator

```python
from toolschema import schema

def search(query: str) -> list[dict]:
    """Search the catalog."""
    ...

definition = schema(search)  # works fine
```

## Docstrings

The **first paragraph** of the docstring becomes `ToolDefinition.description`:

```python
def foo(x: str) -> str:
    """Short summary shown to the LLM.

    Longer notes for humans are ignored by schema().
    """
```

Parameter descriptions from Google/NumPy docstrings are **not** parsed yet (planned).

## `Field` and `Annotated`

Use `Annotated` to add descriptions and JSON Schema constraints:

```python
from typing import Annotated
from toolschema import Field

def book(
    origin: Annotated[str, Field(description="IATA code", pattern=r"^[A-Z]{3}$")],
    passengers: Annotated[int, Field(ge=1, le=9)] = 1,
) -> dict:
    """Book a flight."""
    ...
```

### `Field` parameters

| Parameter | JSON Schema key |
|-----------|-----------------|
| `description` | `description` |
| `min_length` | `minLength` |
| `max_length` | `maxLength` |
| `ge` | `minimum` |
| `le` | `maximum` |
| `gt` | `exclusiveMinimum` |
| `lt` | `exclusiveMaximum` |
| `pattern` | `pattern` |

### String shorthand

Pre-PEP style — description only:

```python
city: Annotated[str, "City name"]
```

## Defaults and required fields

```python
def add(a: int, b: int = 1) -> int: ...
```

- `a` → required
- `b` → optional, `"default": 1` in schema, omitted from `required`

## Optional / nullable types

```python
def search(query: str, tags: list[str] | None = None) -> list[dict]: ...
```

`tags` becomes `anyOf: [array, null]` with `"default": null`.

## Literals and enums

```python
from typing import Literal
from enum import Enum

class Sort(str, Enum):
    ASC = "asc"
    DESC = "desc"

def list_items(sort: Sort = Sort.ASC, mode: Literal["fast", "safe"] = "fast") -> list: ...
```

Both become `"enum": [...]` in the schema.

## Complex parameter types

| Python type | Supported |
|-------------|-----------|
| `list[T]` | yes |
| `dict[str, T]` | yes |
| bare `dict` | yes (`type: object`) |
| `tuple[A, B]` | yes (`prefixItems`) |
| `tuple[T, ...]` | yes (`items`) |
| `TypedDict` | yes |
| `@dataclass` | yes |
| `Union[A, B]` | yes (`anyOf`) |
| Pydantic `BaseModel` | yes (duck-typed via `model_json_schema()`) |

See [Type mapping](type-mapping.md) for full table.

## Return types (output schema)

Return annotations become `ToolDefinition.output` and MCP `outputSchema`:

```python
def greet(name: str) -> str: ...        # output: {"type": "string"}
def search() -> list[dict]: ...         # output: {"type": "array", "items": {...}}
def noop() -> None: ...                 # no output schema
```

Gemini adapter does not emit output schemas yet.

## Common mistakes

| Mistake | Fix |
|---------|-----|
| Missing type hints | Add hints to every parameter |
| `*args` / `**kwargs` | Not supported — use explicit params |
| Untyped `def foo(x)` | Use `x: str` |
| Expecting Pydantic validation | Use `validate()` or Pydantic separately |
