"""Sample tools module — import this from other scripts to test toolschema."""

from __future__ import annotations

from typing import Annotated, Literal

from toolschema import Field, schema, tool


@tool
def greet(name: str) -> str:
    """Say hello to someone."""
    return f"Hello, {name}!"


@tool
def add(a: int, b: int = 1) -> int:
    """Add two integers."""
    return a + b


@tool
def search_items(
    query: Annotated[str, Field(description="Search text", min_length=1)],
    limit: int = 10,
    sort: Literal["relevance", "date"] = "relevance",
) -> list[dict]:
    """Search a catalog and return matching items."""
    return [{"query": query, "limit": limit, "sort": sort}]


def get_tool_definitions():
    """Return ToolDefinition objects for every @tool in this module."""
    return {
        "greet": schema(greet),
        "add": schema(add),
        "search_items": schema(search_items),
    }
