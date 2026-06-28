# GitHub repository About section

Copy these values into **GitHub → false200/toolschema → ⚙️ (gear next to About) → Edit**.

## Description

```
Canonical Python layer for AI agent tools — function to JSON Schema, once, everywhere. OpenAI, Anthropic, MCP, LangChain, FastMCP.
```

## Website

```
https://toolschema.readthedocs.io/en/latest/
```

## Topics (add all)

```
python
ai-agents
json-schema
tool-calling
function-calling
mcp
openai
anthropic
langchain
fastmcp
pydantic-ai
llm
```

## First GitHub Release

After pushing tag `v1.0.0`:

1. Go to **Releases** → **Draft a new release**
2. Choose tag: `v1.0.0`
3. Title: `v1.0.0`
4. Paste notes from [CHANGELOG.md](../CHANGELOG.md)
5. Publish release

PyPI is already live: https://pypi.org/project/toolschema/

Automated PyPI deploy: see [PYPI_PUBLISH.md](PYPI_PUBLISH.md) — configure trusted publishing once, then every `v*` tag publishes automatically.
