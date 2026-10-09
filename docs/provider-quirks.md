# Provider quirks

This document captures intentional differences between provider adapters.

## OpenAI

- `to_openai(strict=True)` sets `additionalProperties: false` and marks every property as required, including nested objects. A `dict[str, T]` map keeps its `additionalProperties` schema.
- Canonical `$schema` is stripped from `parameters` in the OpenAI payload.

## Anthropic

- Numeric and string constraints (`minLength`, `pattern`, etc.) are moved into the property `description` text because Anthropic tool schemas are less expressive for some JSON Schema keywords. Nested properties, item schemas, and union branches are included.

## MCP

- `to_mcp(inline_refs=True)` (default) flattens `$ref` / `$defs` for clients that do not resolve references (Claude Desktop, VS Code Copilot). A circular model cannot be fully inlined; its `$ref` stays, and `$defs` sit on that same document.
- MCP uses camelCase keys: `inputSchema`, `outputSchema`.
- Return type annotations become `outputSchema` when present.

## Gemini

- JSON Schema `type` values are uppercased (`STRING`, `INTEGER`, `OBJECT`, ...), including types nested under `prefixItems` and `$defs`.
- `enum` / `Literal` values with no `type` get one inferred from the values (`STRING`, `INTEGER`, `NUMBER`, or `BOOLEAN`).
- Output schemas are not emitted in the Gemini adapter in v0.1; parameters only.

## Canonical IR

All adapters read from `ToolDefinition` only. Never regenerate schema inside an adapter.
