"""Tool definitions for the {{project_name}} MCP server."""

from __future__ import annotations

from typing import Annotated

from toolschema import Field, tool


@tool
def greet(name: Annotated[str, Field(description="Name to greet", min_length=1)]) -> str:
    """Say hello to someone."""
    return f"Hello, {name}!"


@tool
def add(a: int, b: int = 1) -> int:
    """Add two integers."""
    return a + b
