from __future__ import annotations

from collections.abc import Callable
from typing import Any

from toolschema._ir import ToolDefinition
from toolschema._schema_utils import strip_canonical_meta


def from_toolschema(tool: ToolDefinition, fn: Callable[..., Any]) -> Any:
    """Create a LangChain StructuredTool from a ToolDefinition."""
    try:
        from langchain_core.tools import StructuredTool
    except ImportError as exc:
        raise ImportError(
            "langchain-core is required for from_toolschema. "
            "Install with: pip install toolschema[langchain]"
        ) from exc

    return StructuredTool.from_function(
        fn,
        name=tool.name,
        description=tool.description,
        args_schema=strip_canonical_meta(tool.parameters),
        infer_schema=False,
    )
