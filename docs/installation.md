# Installation

## Requirements

- **Python 3.10+**
- No framework dependencies for the core package

## PyPI

```bash
pip install toolschema
```

## Optional extras

| Extra | Install command | What you get |
|-------|-----------------|--------------|
| `fastmcp` | `pip install toolschema[fastmcp]` | FastMCP MCP server integration |
| `langchain` | `pip install toolschema[langchain]` | LangChain `StructuredTool` bridge |
| `openai-agents` | `pip install toolschema[openai-agents]` | OpenAI Agents SDK `FunctionTool` |
| `pydantic-ai` | `pip install toolschema[pydantic-ai]` | Pydantic AI `Tool.from_schema` |
| `pydantic` | `pip install toolschema[pydantic]` | Pydantic `BaseModel` as parameter types |
| `dev` | `pip install toolschema[dev]` | pytest, ruff, coverage |
| `all` | `pip install toolschema[all]` | all integrations + dev tools |

## From source

```bash
git clone https://github.com/false200/toolschema.git
cd toolschema
pip install -e ".[all]"
```

With [uv](https://docs.astral.sh/uv/):

```bash
uv sync --extra dev --extra fastmcp --extra langchain --extra openai-agents --extra pydantic-ai
```

## Verify install

```bash
python -c "import toolschema; print(toolschema.__version__)"
toolschema inspect toolschema:schema --format mcp  # needs a callable target
```

Or run the verification script:

```bash
python examples/verify_package.py
```

## Documentation (local)

```bash
pip install mkdocs mkdocs-material
mkdocs serve
```

Open http://127.0.0.1:8000
