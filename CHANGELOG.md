# Changelog

All notable changes to this project are documented in this file.

## [Unreleased]

### Fixed

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
