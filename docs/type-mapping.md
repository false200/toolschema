# Type mapping

How Python type hints become JSON Schema 2020-12 in `ToolDefinition.parameters`.

Implemented in `toolschema._types.type_to_schema()`.

## Primitives

| Python | JSON Schema |
|--------|-------------|
| `str` | `{"type": "string"}` |
| `int` | `{"type": "integer"}` |
| `float` | `{"type": "number"}` |
| `bool` | `{"type": "boolean"}` |
| `Any` | `{}` (unconstrained) |
| `None` / `type(None)` | `{"type": "null"}` |

## Containers

| Python | JSON Schema |
|--------|-------------|
| `list[T]` | `{"type": "array", "items": schema(T)}` |
| `dict[str, T]` | `{"type": "object", "additionalProperties": schema(T)}` |
| `dict` (bare) | `{"type": "object"}` |
| `tuple[A, B, C]` | `{"type": "array", "prefixItems": [...], "minItems": 3, "maxItems": 3}` |
| `tuple[T, ...]` | `{"type": "array", "items": schema(T)}` |

## Unions and optionals

| Python | JSON Schema |
|--------|-------------|
| `A \| B` | `{"anyOf": [schema(A), schema(B)]}` |
| `T \| None` | `{"anyOf": [schema(T), {"type": "null"}]}` |
| `Optional[T]` with `= None` | same + `"default": null` |

## Literals and enums

| Python | JSON Schema |
|--------|-------------|
| `Literal["a", "b"]` | `{"enum": ["a", "b"]}` |
| `Literal[1, 2]` | `{"enum": [1, 2]}` |
| `class Color(str, Enum)` | `{"enum": ["red", "green", ...]}` |

## Structured types

| Python | JSON Schema |
|--------|-------------|
| `TypedDict` | `object` with `properties`, `required` from `__total__` |
| `@dataclass` | `object` with fields, defaults, required |
| Pydantic `BaseModel` | `model_json_schema()` normalized |

## Annotated

```python
Annotated[str, Field(description="City", min_length=1)]
```

→ `{"type": "string", "description": "City", "minLength": 1}`

```python
Annotated[str, "City name"]
```

→ `{"type": "string", "description": "City name"}`

## Defaults

Function parameter defaults become schema `"default"` keys. Parameters with defaults are **not** in `required`.

```python
def f(a: int, b: int = 1): ...
# required: ["a"]
# properties.b.default: 1
```

## Return types

Return annotations map to `ToolDefinition.output` via the same `type_to_schema()`:

```python
def f() -> list[dict[str, str]]: ...
# output: {"type": "array", "items": {"type": "object", ...}}
```

## Unsupported (v1.0)

| Type | Status |
|------|--------|
| `*args`, `**kwargs` | skipped / not supported |
| Generics `list[T]` unbound | use concrete types |
| `ParamSpec`, `TypeVar` | deferred |
| `dict[int, T]` | only `dict[str, T]` |
| Callable types | not supported |

Raises `TypeError: Unsupported type annotation: ...`

## Example — complex function

```python
from typing import Annotated, Literal
from toolschema import Field, schema

def search(
    query: Annotated[str, Field(min_length=1)],
    tags: list[str] | None = None,
    mode: Literal["fuzzy", "exact"] = "fuzzy",
) -> list[dict]:
    """Search products."""
    ...

print(schema(search).parameters)
```

See `tests/complex_fixtures.py` and `tests/test_types_extended.py` for golden examples.
