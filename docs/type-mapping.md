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
| `list[T]` / `Sequence[T]` | `{"type": "array", "items": schema(T)}` |
| `list` (bare) | `{"type": "array"}` |
| `set[T]` / `frozenset[T]` | `{"type": "array", "items": schema(T), "uniqueItems": true}` |
| `dict[str, T]` / `Mapping[str, T]` | `{"type": "object", "additionalProperties": schema(T)}` |
| `dict` (bare) | `{"type": "object"}` |
| `tuple[A, B, C]` | `{"type": "array", "prefixItems": [...], "minItems": 3, "maxItems": 3}` |
| `tuple[()]` | `{"type": "array", "maxItems": 0}` |
| `tuple[T, ...]` | `{"type": "array", "items": schema(T)}` |
| `bytes` | `{"type": "string", "contentEncoding": "base64"}` |

## Unions and optionals

| Python | JSON Schema |
|--------|-------------|
| `A \| B` | `{"anyOf": [schema(A), schema(B)]}` |
| `T \| None` | `{"anyOf": [schema(T), {"type": "null"}]}` |
| `Optional[T]` with `= None` | same + `"default": null` |

`Annotated[str | None, Field(min_length=1)]` keeps `minLength` beside `anyOf`. On Python 3.10, postponed annotations make `get_type_hints` wrap that form in another `Optional`. The extra null branch is removed so the schema matches Python 3.11+. `Annotated[str, Field(min_length=1)] | None` is different: `minLength` stays on the string branch.

## Literals and enums

| Python | JSON Schema |
|--------|-------------|
| `Literal["a", "b"]` | `{"enum": ["a", "b"]}` |
| `Literal[1, 2]` | `{"enum": [1, 2]}` |
| `Literal[Color.RED]` | `{"enum": ["red"]}` (the member value) |
| `class Color(str, Enum)` | `{"enum": ["red", "green", ...]}` |
| `NewType("UserId", str)` | schema of `str` |
| `Final[int]` | schema of `int` |

## Structured types

| Python | JSON Schema |
|--------|-------------|
| `TypedDict` | `object` with `properties`; `required` follows TypedDict rules |
| `@dataclass` | `object` with fields, defaults, required |
| `NamedTuple` | `object` with fields, defaults, required |
| Pydantic `BaseModel` | `model_json_schema()`, with nested models inlined. Circular models keep `$ref` and `$defs` on the enclosing document so `#/$defs/` resolves. |

A dataclass, TypedDict, or NamedTuple that refers to itself (or cycles through another structured type) is emitted the same way: `$ref` plus `$defs` on the enclosing document. Nested structured types that are not part of a cycle stay inlined.

`TypedDict.__total__` is only that class's own flag. A `total=False` subclass still keeps required keys inherited from a parent. `Required` and `NotRequired` are honored, including under `from __future__ import annotations`. `Annotated` and `Field` metadata on TypedDict and dataclass fields is kept (`description`, `minLength`, and the other `Field` constraints).

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

Function parameter defaults become schema `"default"` keys. Parameters with defaults are **not** in `required`. Enum defaults are written as the member value (`Color.RED` → `"red"`), the same values listed in `enum`. Tuple and set defaults are written as arrays. Dataclass and `NamedTuple` instances are written as objects, including when they are nested inside another default. A Pydantic model instance is written as an object whose keys are the validation aliases from `model_json_schema()` (`Field(alias="fullName")`, not `serialization_alias`). A Pydantic root model is written as that root value. Datetime, date, time, UUID, path, decimal, and bytes defaults are written as JSON strings or numbers. List and dict defaults are copied, so mutating a filled value does not change the function default or the next `validate()` result. Nested object defaults are filled too. A cyclic default raises `ValueError`.

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
