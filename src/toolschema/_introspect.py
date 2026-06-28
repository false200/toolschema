from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, get_type_hints

from toolschema._ir import ToolDefinition
from toolschema._types import JSON_SCHEMA_2020_12, type_to_schema


@dataclass(frozen=True)
class ToolMeta:
    """Metadata attached by the @tool decorator."""

    name: str | None = None
    description: str | None = None


def _unwrap_tool(fn: Callable[..., Any]) -> tuple[Callable[..., Any], ToolMeta | None]:
    meta = getattr(fn, "_toolschema", None)
    if meta is not None:
        wrapped = getattr(fn, "__wrapped__", fn)
        return wrapped, meta
    return fn, None


def _parse_docstring_description(doc: str | None) -> str:
    if not doc:
        return ""
    paragraphs = doc.strip().split("\n\n")
    return paragraphs[0].strip().replace("\n", " ")


def _build_parameters_schema(fn: Callable[..., Any]) -> dict[str, Any]:
    hints = get_type_hints(fn, include_extras=True)
    sig = inspect.signature(fn)

    properties: dict[str, Any] = {}
    required: list[str] = []

    for name, param in sig.parameters.items():
        if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
            continue
        if name in ("self", "cls"):
            continue

        annotation = hints.get(name, Any)
        prop_schema = type_to_schema(annotation)

        if param.default is not inspect.Parameter.empty:
            prop_schema = {**prop_schema, "default": param.default}
        else:
            required.append(name)

        properties[name] = prop_schema

    schema: dict[str, Any] = {
        "$schema": JSON_SCHEMA_2020_12,
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        schema["required"] = required
    return schema


def _build_output_schema(fn: Callable[..., Any]) -> dict[str, Any] | None:
    hints = get_type_hints(fn, include_extras=True)
    return_type = hints.get("return", inspect.Signature.empty)
    if return_type is inspect.Signature.empty or return_type is None or return_type is type(None):
        return None
    return type_to_schema(return_type)


def schema(fn: Callable[..., Any]) -> ToolDefinition:
    """Build a ToolDefinition from a Python function's signature and annotations."""
    target, meta = _unwrap_tool(fn)

    name = (meta.name if meta and meta.name else None) or target.__name__
    description = (
        meta.description
        if meta and meta.description is not None
        else _parse_docstring_description(target.__doc__)
    )

    return ToolDefinition(
        name=name,
        description=description,
        parameters=_build_parameters_schema(target),
        output=_build_output_schema(target),
    )
