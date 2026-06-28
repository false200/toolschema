# toolschema

**The canonical Python layer for AI agent tools — function → JSON Schema, once, everywhere.**

> Python's answer to the gap TypeScript solved with Zod + [Standard Schema](https://standardschema.dev/).
> Write a typed function. Export one schema. Use it in OpenAI, Anthropic, MCP, LangChain, FastMCP, and Pydantic AI — without rewriting.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Status: v1.0 — beta](https://img.shields.io/badge/status-v1.0%20beta-green.svg)](#roadmap)

---

## Table of contents

- [The problem](#the-problem)
- [Why this is still unsolved (2026)](#why-this-is-still-unsolved-2026)
- [Our solution](#our-solution)
- [Goals and non-goals](#goals-and-non-goals)
- [Quick start (target API)](#quick-start-target-api)
- [Architecture](#architecture)
- [Provider adapters](#provider-adapters)
- [Type coverage](#type-coverage)
- [Comparison to existing tools](#comparison-to-existing-tools)
- [Alignment with Python stdlib (Pre-PEP)](#alignment-with-python-stdlib-pre-pep)
- [Build plan for contributors & AI agents](#build-plan-for-contributors--ai-agents)
- [Repository structure](#repository-structure)
- [Testing strategy](#testing-strategy)
- [Release criteria](#release-criteria)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [References](#references)

---

## The problem

AI agents call **tools** (functions). Before a model can call your tool, it needs a **JSON Schema** describing:

- Tool name
- Description (what it does)
- Parameters (names, types, descriptions, defaults, required fields)

In Python you write:

```python
def search_github(repo: str, query: str, limit: int = 10) -> list[dict]:
    """Search issues in a GitHub repository."""
    ...
```

The LLM cannot read Python. It needs:

```json
{
  "name": "search_github",
  "description": "Search issues in a GitHub repository.",
  "parameters": {
    "type": "object",
    "properties": {
      "repo": { "type": "string" },
      "query": { "type": "string" },
      "limit": { "type": "integer", "default": 10 }
    },
    "required": ["repo", "query"]
  }
}
```

**Something must convert Python functions → JSON Schema.** Today, every agent framework implements this differently.

### Who feels this pain

| Person | Pain |
|--------|------|
| MCP server author | Wrote tools in FastMCP; can't reuse in LangChain without rewrite |
| Agent builder | Same `@tool` logic copy-pasted across 3 SDKs |
| Library author | Ships a PyPI package of tools; each consumer needs a different wrapper |
| Tutorial writer | No single pattern to teach ("use Zod" exists in TS; Python has 11 answers) |
| Cursor / Claude Code user | Wants portable tool modules, gets framework lock-in |

### TypeScript already solved this

| Layer | TypeScript | Python (today) |
|-------|------------|----------------|
| Schema definition | **Zod** (cultural default) | Pydantic / raw types / framework decorators |
| Interop interface | **[Standard Schema](https://standardschema.dev/schema)** | ❌ None |
| JSON Schema export | **[Standard JSON Schema](https://standardschema.dev/json-schema)** | ❌ Per-framework, inconsistent |
| MCP SDK support | Native `~standard.jsonSchema` | ❌ None |

Python developers pick a **framework** partly based on which `@tool` decorator they prefer. That is the bug.

---

## Why this is still unsolved (2026)

Deep analysis (June 2026) shows **partial fixes, no canonical standard**:

| Attempt | Status | Gap |
|---------|--------|-----|
| **`inspect.tool_schema()` in stdlib** | [Pre-PEP parked May 2026](https://discuss.python.org/t/pre-pep-discussion-typing-tool-inspect-tool-schema-close-the-zod-gap-for-python-agent-dev/107431) | CPython core: "wait 10 years" |
| **FastMCP `@mcp.tool()`** | ~70% of MCP servers | MCP-only; Pydantic-coupled |
| **Pydantic v2 JSON Schema** | Used internally by many libs | Not interchangeable across providers |
| **[ToolRegistry](https://github.com/Oaklight/ToolRegistry)** | ~59 stars, multi-provider | Full registry, not a lightweight primitive; low adoption |
| **[llm-rosetta](https://github.com/Oaklight/llm-rosetta)** | API wire translation | Does not introspect Python functions |
| **MIF / PAM / AgentSchema** | Memory & agent manifests | Wrong layer (not tool schema from functions) |

**Verdict:** The gap is **real, documented, and open**. This project exists to ship the fix the stdlib won't ship yet.

---

## Our solution

**`toolschema`** is a **Layer 1 only** library:

```
Layer 1: SCHEMA GENERATION   ← toolschema owns this
Layer 2: VALIDATION          ← Pydantic / msgspec (optional adapters)
Layer 3: ORCHESTRATION       ← LangGraph, Pydantic AI, FastMCP (adapters)
```

### One function, many outputs

```python
from toolschema import tool, schema

@tool
def search_github(
    repo: Annotated[str, "Repository as owner/name"],
    query: str,
    limit: int = 10,
) -> list[dict]:
    """Search issues in a GitHub repository."""
    ...

t = schema(search_github)

t.parameters          # JSON Schema 2020-12 (canonical)
t.to_openai()         # OpenAI function / strict mode
t.to_anthropic()      # Anthropic tool format
t.to_mcp()            # MCP tools/list inputSchema (+ outputSchema)
t.to_gemini()         # Google FunctionDeclaration shape
```

### Design principles

1. **Function-first** — plain Python functions with type hints; Pydantic optional
2. **Zero framework lock-in** — no LangChain/FastMCP import required for core
3. **Provider adapters at the edge** — canonical schema inside; dialect-specific outside
4. **Pre-PEP aligned** — API matches proposed `inspect.tool_schema()` for future stdlib migration
5. **MCP-safe by default** — inline `$ref`, compatible with Claude Desktop / VS Code Copilot
6. **Lightweight** — core works with stdlib + `typing_extensions` only

---

## Goals and non-goals

### Goals

- [x] `@tool` decorator + `schema(fn)` introspection API
- [x] JSON Schema 2020-12 as canonical output dialect
- [x] Adapters: OpenAI, Anthropic, Gemini, MCP (minimum viable set)
- [x] Support `Annotated[T, Field(...)]` and docstring tool descriptions
- [ ] Docstring **parameter** descriptions (Google/NumPy) — deferred
- [x] Output schemas from return type annotations (MCP 2025+)
- [x] `$ref` inlining option for broken MCP clients
- [x] Snapshot tests: same function → stable schema across releases
- [x] CLI: `toolschema inspect module.path:function`
- [x] Thin adapters for FastMCP, LangChain, OpenAI Agents SDK, Pydantic AI
- [x] Document alignment with [Pre-PEP inspect.tool_schema](https://discuss.python.org/t/pre-pep-discussion-typing-tool-inspect-tool-schema-close-the-zod-gap-for-python-agent-dev/107431)
- [x] `validate(args)` thin argument checking (Pre-PEP aligned)
- [x] [Standard Schema](https://standardschema.dev/schema) + [Standard JSON Schema](https://standardschema.dev/json-schema) protocol (`tool.standard["~standard"]`)
- [x] TypedDict, dataclass, Union, tuple types

### Non-goals (v1)

- ❌ Replacing Pydantic for domain modeling / validation
- ❌ Agent orchestration, memory, or MCP transport
- ❌ LLM provider API translation (see llm-rosetta)
- ❌ Stdlib PEP process (we implement what stdlib may adopt later)
- ❌ Supporting every Python type on day one (generics, ParamSpec deferred)

---

## Quick start

```bash
uv sync --extra dev
uv run python examples/01_basic.py
```

### Scaffold an MCP server

```bash
uv run toolschema init my-mcp-server
cd my-mcp-server
uv add --editable /path/to/toolschema[fastmcp]   # until PyPI publish
uv sync
uv run python -m my_mcp_server --check            # smoke test
uv run python -m my_mcp_server                    # stdio MCP server
```

See [docs/tutorials/02-mcp-server.md](./docs/tutorials/02-mcp-server.md) and [docs/claude-desktop.md](./docs/claude-desktop.md).

### Install (future PyPI)

```bash
pip install toolschema
# or
uv add toolschema
```

### Define a tool

```python
from typing import Annotated
from toolschema import tool, schema, Field

@tool
def get_weather(
    city: Annotated[str, Field(description="City name")],
    units: Annotated[str, Field(description="celsius or fahrenheit")] = "celsius",
) -> dict:
    """Get current weather for a city."""
    return {"city": city, "temp": 22, "units": units}
```

### Export for any provider

```python
t = schema(get_weather)

print(t.to_openai())
# {"type": "function", "function": {"name": "get_weather", ...}}

print(t.to_mcp())
# {"name": "get_weather", "description": "...", "inputSchema": {...}, "outputSchema": {...}}
```

### Use without decorator

```python
def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b

t = schema(add)  # works on any typed function
```

### CLI

```bash
uv run toolschema init my-mcp-server
uv run toolschema inspect mypackage.tools:search_github
uv run toolschema inspect mypackage.tools:search_github --format openai,mcp,anthropic
uv run toolschema diff mypackage.tools:search_github --targets openai,mcp
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Python function                      │
│              (@tool decorator + type hints + docstring)          │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     toolschema.core.introspect                   │
│  • inspect.signature + annotationlib (3.14+) / get_type_hints    │
│  • Parse Annotated metadata + Field                              │
│  • Parse Google/NumPy docstring param descriptions (fallback)      │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   toolschema.core.types → json_schema            │
│  • Python type → JSON Schema 2020-12 (canonical IR)              │
│  • Optional Pydantic BaseModel delegation (duck-typed)             │
│  • Return type → outputSchema                                    │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      ToolDefinition (IR)                         │
│  name, description, parameters, output, metadata                   │
└───────────────────────────────┬─────────────────────────────────┘
                                │
          ┌─────────────────────┼─────────────────────┐
          ▼                     ▼                     ▼
   ┌────────────┐        ┌────────────┐        ┌────────────┐
   │  openai    │        │ anthropic  │        │    mcp     │
   │  adapter   │        │  adapter   │        │  adapter   │
   └────────────┘        └────────────┘        └────────────┘
          │                     │                     │
          ▼                     ▼                     ▼
   OpenAI SDK           Anthropic SDK          FastMCP / MCP SDK
   LangChain            Pydantic AI            Cursor / Claude Code
```

### Internal intermediate representation (IR)

```python
@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    parameters: dict[str, Any]      # JSON Schema object
    output: dict[str, Any] | None   # JSON Schema object (optional)
    source: SourceLocation | None   # module, qualname (debug)

    def to_json_schema(self) -> dict: ...
    def to_openai(self, *, strict: bool = False) -> dict: ...
    def to_anthropic(self) -> dict: ...
    def to_mcp(self, *, inline_refs: bool = True) -> dict: ...
    def to_gemini(self) -> dict: ...
```

**Rule:** All adapters read from `ToolDefinition` only. Never generate schema twice.

---

## Provider adapters

Each LLM API wants a slightly different shape. Adapters translate canonical IR → provider dialect.

| Provider | Key differences | Adapter responsibility |
|----------|-----------------|------------------------|
| **Canonical** | JSON Schema 2020-12 | Maximal expressiveness |
| **OpenAI** | `strict: true` → all props required, `additionalProperties: false` | `to_openai(strict=True)` |
| **Anthropic** | `input_schema` key; some constraints → description text | Map keys + constraint fallback |
| **MCP** | `inputSchema` / `outputSchema` camelCase; no `$ref` on some clients | `inline_refs=True` default |
| **Gemini** | `FunctionDeclaration` protobuf-like JSON | Type name mapping |
| **OpenAI Responses** | New tool format (2025+) | Separate adapter when stable |

### MCP `$ref` inlining (critical)

[FastMCP documents](https://gofastmcp.com/servers/tools) that Claude Desktop and VS Code Copilot don't fully support JSON Schema `$ref`. **Default `to_mcp(inline_refs=True)`** — flatten `$defs` into properties.

### OpenAI strict mode

```python
t.to_openai(strict=True)
# Ensures: additionalProperties: false, all properties in required[]
```

---

## Type coverage

### Phase 1 (MVP)

| Python | JSON Schema |
|--------|-------------|
| `str`, `int`, `float`, `bool` | string, integer, number, boolean |
| `None` / optional | `anyOf` or nullable (provider-specific) |
| `list[T]`, `dict[str, T]` | array, object |
| `Literal["a", "b"]` | enum |
| `Enum` subclasses | enum |
| `TypedDict` | object with properties |
| `@dataclass` | object with properties |
| Default values | `default` in schema |
| `Annotated[T, Field(...)]` | descriptions, min/max, pattern |

### Phase 2

| Python | Notes |
|--------|-------|
| `pydantic.BaseModel` | Duck-type delegate to `model_json_schema()` then normalize |
| `Union` / `\|` types | anyOf |
| `NamedTuple` | object |
| Return type → `outputSchema` | MCP output schemas |

### Phase 3 (deferred)

- PEP 695 generics, `ParamSpec`, recursive types
- Full OpenAPI 3.1 compatibility mode

---

## Comparison to existing tools

| Project | What it does | Why toolschema is different |
|---------|--------------|----------------------------|
| **Pydantic** | Validation + models | Heavy; not function-first; no provider adapters |
| **FastMCP** | MCP server framework | Lock-in to FastMCP; not cross-framework |
| **ToolRegistry** | Full registry + execution | 59 stars; registry not primitive; pydantic dep |
| **LangChain `@tool`** | LangChain only | Framework lock-in |
| **Instructor** | Structured LLM *responses* | Different problem |
| **jsonschema** | Validate JSON | Does not generate from functions |
| **toolschema (this)** | Function → canonical schema → any provider | **The missing Layer 1** |

---

## Alignment with Python stdlib (Pre-PEP)

We intentionally mirror the [May 2026 Pre-PEP proposal](https://discuss.python.org/t/pre-pep-discussion-typing-tool-inspect-tool-schema-close-the-zod-gap-for-python-agent-dev/107431):

| Proposed stdlib | toolschema equivalent |
|-----------------|----------------------|
| `inspect.tool_schema(fn) -> dict` | `schema(fn).to_json_schema()` |
| `@typing.tool` | `@tool` |
| `tool.validate(args)` | `schema(fn).validate(args)` (thin check, optional) |
| Uses `annotationlib` (PEP 749) | Use on 3.14+; fallback `get_type_hints` on 3.10–3.13 |
| JSON Schema 2020-12 canonical | Same |
| Does NOT replace Pydantic | Same — dataclasses/attrs precedent |

**Migration path:** When/if stdlib ships `inspect.tool_schema`, we deprecate to a thin wrapper or become the reference test suite.

---

## Build plan for contributors & AI agents

> **Instructions for AI coding agents:** Read this section fully before writing code. Implement phases in order. Do not skip tests. Match Pre-PEP API shapes. Keep core free of framework imports.

### Phase 0 — Repository bootstrap (Day 1)

**Deliverables:**

- [ ] `pyproject.toml` with uv, ruff, pytest, hatchling
- [ ] Package layout (see [Repository structure](#repository-structure))
- [ ] CI: lint + test on push
- [ ] `LICENSE` (MIT)
- [ ] This README + `AGENTS.md` (condensed agent instructions)

**Acceptance criteria:**

```bash
uv sync
uv run pytest  # passes (even if minimal)
uv run ruff check .
```

---

### Phase 1 — Core introspection (Week 1)

**Files to create:**

```
src/toolschema/
  __init__.py          # export tool, schema, Field, ToolDefinition
  _decorator.py        # @tool implementation
  _introspect.py       # signature + annotations + docstring
  _types.py            # Python type → JSON Schema
  _ir.py               # ToolDefinition dataclass
  _fields.py           # Field() helper (Annotated metadata)
```

**Tasks:**

1. Implement `@tool` — attaches metadata, non-invasive wrapper
2. Implement `schema(fn) -> ToolDefinition`
3. Map primitives: str, int, float, bool
4. Map `Optional`, defaults, `Literal`, `Enum`
5. Map `list[T]`, `dict[str, T]`
6. Parse `Annotated[T, Field(description=...)]`
7. Parse function docstring → tool description
8. Emit JSON Schema 2020-12 for `parameters`

**Tests (required):**

```python
# tests/test_core.py
def test_primitive_params(): ...
def test_defaults_and_required(): ...
def test_literal_enum(): ...
def test_annotated_field_descriptions(): ...
def test_docstring_description(): ...
def test_snapshot_search_github_schema(): ...  # golden file
```

**Acceptance criteria:**

```python
from toolschema import tool, schema

@tool
def add(a: int, b: int = 1) -> int:
    """Add two numbers."""
    return a + b

t = schema(add)
assert t.name == "add"
assert t.parameters["properties"]["a"]["type"] == "integer"
assert "b" not in t.parameters["required"]  # has default
```

---

### Phase 2 — Provider adapters (Week 2)

**Files:**

```
src/toolschema/adapters/
  __init__.py
  openai.py
  anthropic.py
  mcp.py
  gemini.py
  _inline_refs.py      # JSON Schema $ref flattener
```

**Tasks:**

1. `ToolDefinition.to_openai(strict=False|True)`
2. `ToolDefinition.to_anthropic()`
3. `ToolDefinition.to_mcp(inline_refs=True)`
4. `ToolDefinition.to_gemini()`
5. Snapshot tests per provider (golden JSON files in `tests/snapshots/`)

**Acceptance criteria:**

- Same `add` function produces valid OpenAI + MCP shapes
- MCP output has no `$ref` when `inline_refs=True`
- OpenAI strict mode passes OpenAI validator rules

---

### Phase 3 — CLI + DX (Week 3)

**Files:**

```
src/toolschema/cli.py
src/toolschema/__main__.py   # python -m toolschema
```

**Commands:**

```bash
toolschema inspect MODULE:FUNCTION [--format canonical,openai,mcp,...]
toolschema diff MODULE:FUNCTION --targets openai,mcp
toolschema export MODULE [--output tools.json]
```

**Acceptance criteria:**

```bash
uv run toolschema inspect toolschema.tests.fixtures:sample_tool --format mcp
```

---

### Phase 4 — Framework adapters (Week 4)

**Optional extras in pyproject.toml:**

```toml
[project.optional-dependencies]
fastmcp = ["fastmcp>=2.0"]
langchain = ["langchain-core>=0.3"]
openai-agents = ["openai-agents>=0.1"]
pydantic = ["pydantic>=2.0"]
all = ["toolschema[fastmcp,langchain,openai-agents,pydantic]"]
```

**Files:**

```
src/toolschema/integrations/
  fastmcp.py      # register ToolDefinition as MCP tool without @mcp.tool
  langchain.py    # StructuredTool.from_toolschema(t)
  openai_agents.py
  pydantic_ai.py
```

**Pattern:**

```python
# integrations/fastmcp.py
def register_tool(mcp, t: ToolDefinition, fn: Callable):
    """Register pre-built schema — no double generation."""
    ...
```

---

### Phase 5 — Polish for launch (Week 5–6)

- [ ] PyPI publish (`toolschema` name — verify availability)
- [ ] README GIF: function → 4 provider formats
- [ ] Blog post: "Python's Zod gap, solved"
- [ ] Compare output vs FastMCP/LangChain for 5 fixture functions (table in docs)
- [ ] Submit discussion comment on [Pre-PEP thread](https://discuss.python.org/t/pre-pep-discussion-typing-tool-inspect-tool-schema-close-the-zod-gap-for-python-agent-dev/107431) linking repo
- [x] MCP server template: `toolschema init my-mcp-server` (see [docs/tutorials](./docs/tutorials/))

---

## Repository structure

```
toolschema/
├── README.md                 ← you are here
├── AGENTS.md                 ← condensed instructions for AI agents
├── LICENSE
├── pyproject.toml
├── src/
│   └── toolschema/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py
│       ├── _decorator.py
│       ├── _introspect.py
│       ├── _types.py
│       ├── _ir.py
│       ├── _fields.py
│       ├── adapters/
│       │   ├── openai.py
│       │   ├── anthropic.py
│       │   ├── mcp.py
│       │   └── gemini.py
│       └── integrations/
│           ├── fastmcp.py
│           ├── langchain.py
│           └── ...
├── tests/
│   ├── fixtures.py           # sample functions for tests
│   ├── test_core.py
│   ├── test_adapters.py
│   └── snapshots/            # golden JSON outputs
│       ├── add_openai.json
│       ├── add_mcp.json
│       └── ...
├── examples/
│   ├── 01_basic.py
│   ├── 02_mcp_server.py
│   ├── 03_langchain.py
│   └── 04_multi_provider.py
└── docs/
    ├── tutorials/            # step-by-step guides (4 tutorials)
    ├── claude-desktop.md     # MCP smoke test + manual Claude Desktop setup
    ├── pre-pep-alignment.md
    └── provider-quirks.md
```

---

## Testing strategy

### 1. Unit tests

Every type mapping, every adapter edge case.

### 2. Snapshot / golden tests

Store expected JSON in `tests/snapshots/`. CI fails on unintended schema changes.

```python
def test_add_openai_snapshot(snapshot):
    t = schema(fixtures.add)
    assert t.to_openai() == snapshot
```

### 3. Cross-framework parity tests

Same fixture function; assert semantic equivalence across OpenAI/MCP/Anthropic (required fields match, types match).

### 4. Compatibility fixtures

Copy 5 real-world tool signatures from:

- FastMCP docs examples
- OpenAI Agents SDK examples
- Pre-PEP proposal examples

Ensure `toolschema` output matches or documents intentional differences.

### 5. MCP client smoke tests

Automated in `tests/test_mcp_smoke.py` (stdio MCP client, `$ref`-free schemas, `tools/call`).

Manual checklist: [docs/claude-desktop.md](./docs/claude-desktop.md).

---

## Release criteria

### v0.1.0 — MVP

- [x] `@tool` + `schema(fn)`
- [x] Types: primitives, Optional, Literal, Enum, list, dict, defaults
- [x] Adapters: canonical, OpenAI, MCP
- [x] 50+ unit tests, 10+ snapshots
- [ ] Published to PyPI

### v0.2.0 — Providers

- [x] Anthropic + Gemini adapters
- [x] Output schemas from return types
- [x] CLI `inspect`

### v0.3.0 — Ecosystem

- [x] FastMCP + LangChain integration extras
- [x] Pydantic BaseModel as parameter type
- [x] `$ref` inlining tested (unit + parity + MCP stdio smoke tests)

### v0.4.0 — DX

- [x] `toolschema init` MCP server template
- [x] Tutorials: [docs/tutorials/](./docs/tutorials/) (4 guides)
- [x] Claude Desktop smoke test guide + automated MCP client tests

### v1.0.0 — Stable

- [x] API aligned with Pre-PEP shapes (`schema`, `@tool`, `validate`)
- [x] Standard Schema + Standard JSON Schema protocol
- [x] Parity tests vs FastMCP / LangChain / OpenAI Agents
- [x] TypedDict, dataclass, Union, tuple support
- [x] First-party tutorials: [docs/tutorials/](./docs/tutorials/) (4 guides; external adoption welcome)

---

## Roadmap

| Version | Focus |
|---------|-------|
| **0.1** | Core + OpenAI + MCP adapters |
| **0.2** | Anthropic, Gemini, CLI, output schemas |
| **0.3** | Framework integrations (FastMCP, LangChain, Pydantic AI) |
| **0.4** | `toolschema init` MCP template, tutorials, MCP smoke tests |
| **1.0** | Stable API, Pre-PEP alignment guarantee |
| **Future** | `typing_extensions` backport of Standard Schema protocol for Python? |

---

## Contributing

We welcome contributors and AI-assisted PRs.

1. Read [Build plan](#build-plan-for-contributors--ai-agents) — pick a phase/task
2. Fork → branch → implement with tests
3. Run `uv run pytest && uv run ruff check .`
4. Open PR with snapshot diffs explained if golden files change

**Good first issues (create these on GitHub):**

- `feat: map TypedDict to JSON Schema`
- `feat: Google/NumPy docstring param parser`
- `feat: anthropic adapter`
- `test: parity fixture vs FastMCP for 5 tools`
- `docs: provider quirks (OpenAI strict vs MCP)`

---

## References

### Problem documentation

- [Pre-PEP: typing.tool + inspect.tool_schema()](https://discuss.python.org/t/pre-pep-discussion-typing-tool-inspect-tool-schema-close-the-zod-gap-for-python-agent-dev/107431) — May 2026
- [PEP 749 — annotationlib](https://peps.python.org/pep-0749/) — Python 3.14 runtime annotation tooling
- [PEP 593 — Annotated metadata](https://peps.python.org/pep-0593/)

### TypeScript (solved reference)

- [Standard Schema](https://standardschema.dev/schema)
- [Standard JSON Schema](https://standardschema.dev/json-schema)
- [Vercel AI SDK — Tools](https://ai-sdk.dev/docs/foundations/tools)
- [MCP TypeScript SDK — standardSchema.ts](https://github.com/modelcontextprotocol/typescript-sdk)

### Python ecosystem (partial solutions)

- [FastMCP — Tools](https://gofastmcp.com/servers/tools)
- [Pydantic AI — MCP Client](https://ai.pydantic.dev/mcp/client/)
- [ToolRegistry](https://github.com/Oaklight/ToolRegistry)
- [llm-rosetta](https://github.com/Oaklight/llm-rosetta)

### Related but different problems

- [MIF — Memory Interchange Format](https://varun29ankus.github.io/mif-spec/) (agent memory, not tool schema)
- [Portable AI Memory spec](https://github.com/portable-ai-memory/portable-ai-memory)

---

## License

MIT — see [LICENSE](LICENSE).

---

## One-liner for social / PyPI

> **toolschema** — Write a Python function. Get JSON Schema for any AI agent. Open source fix for Python's missing Zod.

---

<p align="center">
  <strong>Layer 1 was missing. We're building it.</strong><br>
  ⭐ Star this repo if you're tired of rewriting <code>@tool</code> decorators.
</p>
