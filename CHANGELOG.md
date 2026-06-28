# Changelog

All notable changes to this project are documented in this file.

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
