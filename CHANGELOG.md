# Changelog

All notable changes to this project are documented in this file.

## [Unreleased]

### Fixed

- Bytes defaults are standard base64. `data: bytes = b"hi"` was stored as the text `"hi"`, so `validate({})` rejected the omitted argument. The same text was written for a nested dataclass field.
- `toolschema export` skips a function whose annotation name is undefined. `NameError` used to abort the command, so one unfinished function hid every other tool in the module.
- `validate()` rejects a `bytes` argument whose text is not standard base64. `contentEncoding: base64` used to accept any string, including `"!!!"`.
- `validate()` checks `allOf`. A schema that requires a field only inside `allOf` used to accept `{}`.
- `to_openai(strict=True)` closes nested objects and lists every nested property in `required`. A dataclass field with a default stayed optional. Maps (`dict[str, T]`) keep their value schema.
- `Field(min_length=...)` and `Field(max_length=...)` on a list or set become `minItems` and `maxItems`. They were emitted as `minLength` and `maxLength`, which do not apply to arrays, so `validate()` accepted `[]`. A fixed tuple keeps the length it already has. Strings still use `minLength` and `maxLength`.
- `validate()` checks `date`, `date-time`, `time`, and `uuid` against the JSON Schema grammars (RFC 3339 and the hyphenated RFC 4122 form). `datetime.fromisoformat` accepted a calendar date, a time with no offset, and other ISO 8601 forms as `date-time`, and rejected leap seconds and lowercase `t` / `z`. `UUID()` accepted unhyphenated, URN, and brace forms.
- `@staticmethod` parameters named `self` or `cls` stay in the schema. They were dropped because the qualified name looks like a method. Instance methods and classmethods still omit the receiver. A staticmethod on a class created inside a function still uses that qualified-name rule, because the class object cannot be loaded from the module.
- `Annotated[T | None, Field(...)]` keeps constraints beside `anyOf` on Python 3.10. Postponed annotations made `get_type_hints` add an extra `Optional`, which nested `minLength` inside `anyOf` and duplicated the null branch.
- Dataclass, `NamedTuple`, and Pydantic model instance defaults are written as JSON. A `NamedTuple` default was stored as an array, so `validate({})` rejected an omitted argument. A dataclass or model default was not JSON-serializable. Model object keys follow the validation alias used by `model_json_schema()`. A cyclic default raises `ValueError`.
- Generated schemas stay JSON-serializable and safe to validate more than once. List and dict defaults are copied. Sets, datetimes, dates, times, decimals, UUIDs, paths, bytes, and `Literal` enum members are written as JSON values. `tuple[()]` is an empty array. A plain function can take a parameter named `self`.
- `list`, `set`, `frozenset`, `Sequence`, `Mapping[str, T]`, `bytes`, `NewType`, `Final`, and `NamedTuple` map to JSON Schema instead of raising `TypeError`.
- Circular Pydantic models keep `$ref` and `$defs` on the schema document that contains them, so `#/$defs/Name` resolves for parameters and list items. `validate()` follows those references. `to_mcp()` keeps a circular reference instead of failing.
- `validate()` uses JSON equality for `enum` (`True` is not `1`), checks `multipleOf`, `uniqueItems`, `format` (`date-time`, `date`, `time`, `uuid`), and type arrays. A bad `pattern` is reported instead of raising. Nested defaults, including dataclass fields, are filled with their own copies.
- Gemini enum and `Literal` properties include a type. Anthropic constraint text is applied inside nested properties, items, and unions.
- `validate()` honors JSON Schema `const`. Pydantic emits `const` for a single-value `Literal`, so a discriminated-union arm was accepted when only the tag was wrong. Booleans stay distinct from numbers.
- Enum parameter and dataclass defaults are emitted as the member value. Plain `Enum` defaults were not JSON-serializable, and `validate()` rejected omitted arguments because the member was not in the value `enum`. Tuple defaults are emitted as arrays.
- TypedDict `required` follows inheritance, `Required`, and `NotRequired`, including when annotations are postponed. `Annotated` metadata on TypedDict and dataclass fields is preserved.
- A TypedDict key redeclared without `Required` or `NotRequired` follows that class's totality on Python 3.10. Postponed annotations left the key in `__required_keys__`.
- Nested Pydantic models are inlined into the tool schema. `model_json_schema()` `$ref`s no longer point at `$defs` entries that were removed. Circular models keep both.

## [1.0.1] - 2026-06-28

### Changed

- README intro: Zod + Standard Schema positioning
- PyPI publish via GitHub Actions trusted publishing (`environment: pypi`)

[1.0.1]: https://github.com/false200/toolschema/releases/tag/v1.0.1

## [1.0.0] - 2026-06-28

### Added

- Core API: `@tool`, `schema()`, `Field`, `ToolDefinition`
- Provider adapters: OpenAI, Anthropic, Gemini, MCP (`inline_refs` default)
- Framework integrations: FastMCP, LangChain, OpenAI Agents, Pydantic AI
- `validate()` for thin argument checking
- Standard Schema + Standard JSON Schema protocol
- CLI: `inspect`, `diff`, `export`, `init`
- MCP server scaffolding (`toolschema init`)
- TypedDict, dataclass, Union, tuple type support
- 92 tests including deep cross-agent harness
- MkDocs documentation site
- PyPI publish: `pip install toolschema`

[1.0.0]: https://github.com/false200/toolschema/releases/tag/v1.0.0
