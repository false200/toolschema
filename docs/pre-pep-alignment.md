# Pre-PEP alignment

`toolschema` intentionally mirrors the [May 2026 Pre-PEP proposal](https://discuss.python.org/t/pre-pep-discussion-typing-tool-inspect-tool-schema-close-the-zod-gap-for-python-agent-dev/107431) for `inspect.tool_schema()` and `@typing.tool`.

| Proposed stdlib | toolschema equivalent |
|-----------------|----------------------|
| `inspect.tool_schema(fn) -> dict` | `schema(fn).to_json_schema()` |
| `@typing.tool` | `@tool` |
| `tool.validate(args)` | `schema(fn).validate(args)` |
| JSON Schema 2020-12 canonical | `ToolDefinition.parameters` uses draft 2020-12 |
| Annotated metadata | `Field(...)` and plain-string `Annotated` descriptions |

## Standard Schema interop (v1.0+)

`toolschema` also implements the [Standard Schema](https://standardschema.dev/schema) and [Standard JSON Schema](https://standardschema.dev/json-schema) protocols so ecosystem tools can consume tool schemas without custom adapters:

```python
from toolschema import schema, JSONSchemaOptions
import fixtures

tool = schema(fixtures.add)
standard = tool.standard["~standard"]

assert standard["version"] == 1
assert standard["vendor"] == "toolschema"

input_schema = standard["jsonSchema"]["input"](JSONSchemaOptions(target="draft-2020-12"))
result = standard["validate"]({"a": 2})
assert result.value == {"a": 2, "b": 1}
```

When/if CPython ships `inspect.tool_schema`, this package can become a thin compatibility wrapper or serve as the reference test suite.
