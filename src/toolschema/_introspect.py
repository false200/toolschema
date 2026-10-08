from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, get_type_hints

from toolschema._ir import ToolDefinition
from toolschema._schema_utils import hoist_defs, json_schema_default
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


def _unwraps_to(candidate: Any, target: Any) -> bool:
    """Return whether ``candidate`` is ``target`` or wraps it via ``__wrapped__``."""
    seen: set[int] = set()
    current = candidate
    while current is not None and id(current) not in seen:
        if current is target:
            return True
        seen.add(id(current))
        current = getattr(current, "__wrapped__", None)
    return False


def _defining_class(fn: Callable[..., Any]) -> type | None:
    """Return the class that defined ``fn``, when that class lives in a module.

    A class created inside a function has ``<locals>`` in its qualified name.
    The class object cannot be loaded from the module, so the caller falls
    back to the qualified-name heuristic.
    """
    qualname = getattr(fn, "__qualname__", "")
    if not isinstance(qualname, str):
        return None
    parts = qualname.split(".")
    if len(parts) < 2 or "<locals>" in parts:
        return None
    module = inspect.getmodule(fn)
    if module is None:
        return None
    obj: Any = getattr(module, parts[0], None)
    for part in parts[1:-1]:
        if not isinstance(obj, type):
            return None
        obj = getattr(obj, part, None)
    if isinstance(obj, type):
        return obj
    return None


def _defined_member(owner: type, fn: Callable[..., Any]) -> Any | None:
    """Return the class attribute that is ``fn``, without invoking descriptors."""
    attr_name = getattr(fn, "__name__", None)
    if not isinstance(attr_name, str):
        return None
    member = inspect.getattr_static(owner, attr_name, None)
    candidate = member.__func__ if isinstance(member, (staticmethod, classmethod)) else member
    if _unwraps_to(candidate, fn):
        return member
    return None


def _is_receiver(fn: Callable[..., Any], name: str, index: int, param: inspect.Parameter) -> bool:
    """Return whether this parameter is the implicit ``self`` or ``cls``.

    A plain function may take a real argument named ``self``. Only the first
    positional parameter of an instance method or classmethod is dropped.
    ``staticmethod`` keeps that parameter: it is an ordinary argument, even
    when it is named ``self`` or ``cls``.
    """
    if index != 0 or name not in {"self", "cls"}:
        return False
    positional = (
        inspect.Parameter.POSITIONAL_ONLY,
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
    )
    if param.kind not in positional:
        return False
    if isinstance(fn, staticmethod):
        return False
    if isinstance(fn, classmethod):
        return True

    owner = _defining_class(fn)
    if owner is not None:
        member = _defined_member(owner, fn)
        if member is not None:
            return not isinstance(member, staticmethod)

    parts = getattr(fn, "__qualname__", "").split(".")
    if len(parts) < 2:
        return False
    return parts[-2] != "<locals>"


def _build_parameters_schema(fn: Callable[..., Any]) -> dict[str, Any]:
    hints = get_type_hints(fn, include_extras=True)
    sig = inspect.signature(fn)

    properties: dict[str, Any] = {}
    required: list[str] = []

    for index, (name, param) in enumerate(sig.parameters.items()):
        if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
            continue
        if _is_receiver(fn, name, index, param):
            continue

        annotation = hints.get(name, Any)
        prop_schema = type_to_schema(annotation)

        if param.default is not inspect.Parameter.empty:
            prop_schema = {**prop_schema, "default": json_schema_default(param.default)}
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
    return hoist_defs(schema)


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
