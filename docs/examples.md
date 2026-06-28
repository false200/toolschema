# Examples

Runnable scripts in the `examples/` directory.

## Run any example

```bash
pip install toolschema[all]
cd toolschema
python examples/01_basic.py
```

## Catalog

| Script | Level | Description |
|--------|-------|-------------|
| `01_basic.py` | Beginner | `@tool`, `schema()`, print canonical/OpenAI/MCP JSON |
| `02_mcp_server.py` | Beginner | FastMCP stdio server; `--check` smoke test |
| `03_langchain.py` | Intermediate | LangChain `from_toolschema` + invoke |
| `04_multi_provider.py` | Intermediate | One function → all provider formats |
| `demo_tools.py` | Beginner | Reusable tools module pattern |
| `verify_package.py` | Beginner | End-to-end install verification |
| `deep_agents_demo.py` | Advanced | Cross-framework deep integration demo |

Source: [github.com/false200/toolschema/tree/main/examples](https://github.com/false200/toolschema/tree/main/examples)

## Quick commands

```bash
# Basic schema output
python examples/01_basic.py

# MCP smoke test (no server)
python examples/02_mcp_server.py --check

# MCP server (stdio — for Claude Desktop)
python examples/02_mcp_server.py

# LangChain roundtrip
python examples/03_langchain.py

# All adapters side by side
python examples/04_multi_provider.py

# Full package verification
python examples/verify_package.py

# All frameworks + MCP stdio
python examples/deep_agents_demo.py
```

## Pattern — reusable tools module

`demo_tools.py` shows the recommended project layout:

```
myproject/
├── my_tools.py      # @tool functions only
├── server.py        # register_tool / from_toolschema
└── tests/
```

```python
# consumer.py
from my_tools import greet
from toolschema import schema

definition = schema(greet)
```

## Tests as examples

Complex real-world tools live in `tests/complex_fixtures.py`:

- `search_products` — enums, optional fields, Field constraints, dict filters
- `book_flight` — regex patterns, literals

Used by `test_complex_e2e.py` and `test_deep_agents.py`.
