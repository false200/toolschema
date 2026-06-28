# Standard Schema

toolschema implements the [Standard Schema](https://standardschema.dev/schema) and [Standard JSON Schema](https://standardschema.dev/json-schema) protocols for ecosystem interop.

## Access

```python
definition = schema(my_fn)
host = definition.standard

# Standard Schema protocol
standard = host["~standard"]
```

## Protocol shape

```python
{
    "version": 1,
    "vendor": "toolschema",
    "validate": <callable>,
    "jsonSchema": {
        "input": <callable>,
        "output": <callable>,
    },
}
```

## JSON Schema export

```python
from toolschema import JSONSchemaOptions

standard = definition.standard["~standard"]

input_schema = standard["jsonSchema"]["input"]()
output_schema = standard["jsonSchema"]["output"]()  # raises if no return type

# With options
opts = JSONSchemaOptions(target="draft-2020-12")
input_schema = standard["jsonSchema"]["input"](opts)
```

### `JSONSchemaOptions`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `target` | `"draft-2020-12"` \| `"draft-07"` \| `"openapi-3.0"` | `"draft-2020-12"` | Schema dialect |
| `library_options` | `dict` \| `None` | `None` | Reserved for future use |

## Validate via protocol

```python
result = standard["validate"]({"city": "London"})
```

Same as `definition.validate()`.

## Why this matters

Libraries that support Standard Schema can consume toolschema tools without a custom adapter:

- Unified `validate()` interface
- Unified `jsonSchema.input()` / `jsonSchema.output()` export
- Aligns with Pre-PEP `inspect.tool_schema` direction

## Pre-PEP alignment

See [Pre-PEP alignment](pre-pep-alignment.md) for how `schema()` and `@tool` map to the proposed stdlib API.
