# Validation

`ToolDefinition.validate()` performs **thin argument checking** against the generated parameters schema.

This is **not** full Pydantic validation — use Pydantic for domain models.

## Basic usage

```python
from toolschema import schema, ValidationSuccess, ValidationFailure

definition = schema(my_tool)

result = definition.validate({"name": "Ada", "limit": 5})

if isinstance(result, ValidationSuccess):
    my_tool(**result.value)  # defaults applied
else:
    for issue in result.issues:
        print(issue.kind, issue.path, issue.message)
```

## What gets validated

| Check | Example |
|-------|---------|
| Required fields | Missing `name` when required |
| JSON types | `"abc"` for `integer` param |
| `enum` / `Literal` | Value not in allowed set |
| `minLength` / `maxLength` | String too short |
| `pattern` | Regex mismatch |
| `minimum` / `maximum` | Number out of range |
| `additionalProperties: false` | Extra keys rejected |
| Nested objects / arrays | Recursive validation |
| `anyOf` / optional types | At least one branch matches |
| Defaults | Missing optional fields filled from schema |

## ValidationSuccess

```python
ValidationSuccess(
    value={"name": "Ada", "limit": 10},  # defaults merged in
    issues=None,
)
```

Use `result.value` as kwargs for your function.

## ValidationFailure

```python
ValidationFailure(
    value=None,
    issues=(
        ValidationIssue(
            message="Missing required property 'name'",
            path=("name",),
            kind=ValidationIssueKind.REQUIRED,
        ),
    ),
)
```

### Issue kinds

| Kind | Meaning |
|------|---------|
| `REQUIRED` | Missing required property |
| `TYPE` | Wrong JSON type |
| `ENUM` | Not in enum |
| `CONSTRAINT` | minLength, pattern, min/max, etc. |
| `ADDITIONAL_PROPERTY` | Extra key when not allowed |

## Standard Schema integration

`validate` is also exposed via the Standard Schema protocol:

```python
standard = definition.standard["~standard"]
result = standard["validate"]({"name": "Ada"})
```

## Limitations (v1.0)

- No `$ref` resolution at validate time (schemas are usually inline)
- No `format` keyword (email, uri, etc.)
- No `oneOf` discrimination beyond trying each branch
- Not a replacement for Pydantic `model_validate`

For production argument parsing, consider: `validate()` → `my_fn(**result.value)` or Pydantic models as parameter types.
