# Contributing to toolschema

Thanks for helping improve toolschema. PRs and issues are welcome.

## Before you start

1. Read [README.md](README.md) for scope and API overview.
2. Read [AGENTS.md](AGENTS.md) if you use an AI coding agent — it defines hard design rules.
3. Search [existing issues](https://github.com/false200/toolschema/issues) to avoid duplicate work.

## Development setup

```sh
git clone https://github.com/false200/toolschema.git
cd toolschema
uv sync --extra dev --extra fastmcp --extra langchain --extra openai-agents --extra pydantic-ai
```

## Making changes

1. Fork the repo and create a branch from `main`.
2. Make focused changes — one feature or fix per PR.
3. Add or update tests for behavior you change.
4. Run checks before opening a PR:

```sh
uv run pytest -v
uv run ruff check src tests
uv run ruff format src tests
```

5. If adapter output changes intentionally, update golden snapshots in `tests/snapshots/` and explain why in the PR.

## Design rules (summary)

- **Layer 1 only** — schema generation, not agent orchestration.
- **No framework imports in core** — FastMCP, LangChain, OpenAI SDK belong in `integrations/` only.
- **Single IR** — all adapters read from `ToolDefinition`; never regenerate schema in an adapter.
- **MCP defaults** — `inline_refs=True` for Claude Desktop / Copilot compatibility.

## Pull requests

Use the [pull request template](.github/pull_request_template.md). Keep PRs small and describe:

- What changed
- Why it changed
- How you tested it

## Issues

Use the [issue template](.github/ISSUE_TEMPLATE/issue.yml). A clear title and short description is enough to get started.

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
