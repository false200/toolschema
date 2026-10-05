from __future__ import annotations

import base64
import copy
import enum
import os
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any
from uuid import UUID


def json_schema_default(value: Any) -> Any:
    """Return a JSON-compatible copy of a Python default.

    The result has to be JSON and has to match the values this library puts
    in ``enum``. Containers are always copied so a later ``validate()`` cannot
    mutate the function's default object. Enum members are written as their
    values. Tuples, sets, and frozensets are written as arrays.
    """
    if isinstance(value, enum.Enum):
        return json_schema_default(value.value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, time):
        return value.isoformat()
    if isinstance(value, Decimal):
        integral = value.to_integral_value()
        if value == integral:
            return int(integral)
        return float(value)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, os.PathLike) and not isinstance(value, (str, bytes)):
        rendered = os.fspath(value)
        if isinstance(rendered, bytes):
            return rendered.decode("utf-8", "surrogateescape")
        return rendered
    if isinstance(value, (bytes, bytearray)):
        try:
            return bytes(value).decode("utf-8")
        except UnicodeDecodeError:
            return base64.b64encode(bytes(value)).decode("ascii")
    if isinstance(value, (set, frozenset)):
        items = [json_schema_default(item) for item in value]
        try:
            return sorted(items)
        except TypeError:
            return items
    if isinstance(value, tuple):
        return [json_schema_default(item) for item in value]
    if isinstance(value, list):
        return [json_schema_default(item) for item in value]
    if isinstance(value, dict):
        return {key: json_schema_default(item) for key, item in value.items()}
    return value


def copy_json_value(value: Any) -> Any:
    """Deep-copy a JSON value so callers cannot share mutable defaults."""
    if isinstance(value, list):
        return [copy_json_value(item) for item in value]
    if isinstance(value, dict):
        return {key: copy_json_value(item) for key, item in value.items()}
    return value


def strip_canonical_meta(schema: dict[str, Any]) -> dict[str, Any]:
    """Remove JSON Schema dialect metadata not used by provider payloads."""
    result = copy.deepcopy(schema)
    result.pop("$schema", None)
    return result


def _resolve_ref(ref: str, defs: dict[str, Any]) -> dict[str, Any]:
    if not ref.startswith("#/$defs/"):
        raise ValueError(f"Unsupported $ref format: {ref!r}")
    key = ref.removeprefix("#/$defs/")
    if key not in defs:
        raise ValueError(f"Unresolved $ref: {ref!r}")
    return copy.deepcopy(defs[key])


def _inline_node(node: Any, defs: dict[str, Any], resolving: set[str]) -> Any:
    if isinstance(node, dict):
        if "$ref" in node:
            ref = node["$ref"]
            key = ref.removeprefix("#/$defs/")
            if key in resolving:
                raise ValueError(f"Circular $ref detected: {ref!r}")
            resolving = resolving | {key}
            resolved = _inline_node(_resolve_ref(ref, defs), defs, resolving)
            extras = {k: v for k, v in node.items() if k != "$ref"}
            if extras:
                if not isinstance(resolved, dict):
                    return resolved
                return {**resolved, **extras}
            return resolved

        return {k: _inline_node(v, defs, resolving) for k, v in node.items()}

    if isinstance(node, list):
        return [_inline_node(item, defs, resolving) for item in node]

    return node


def inline_refs(schema: dict[str, Any]) -> dict[str, Any]:
    """Flatten JSON Schema $ref pointers using local $defs."""
    cloned = copy.deepcopy(schema)
    defs = cloned.pop("$defs", {})
    if not isinstance(defs, dict) or not defs:
        return cloned
    return _inline_node(cloned, defs, set())


def hoist_defs(schema: dict[str, Any]) -> dict[str, Any]:
    """Move nested ``$defs`` to this document so ``#/$defs/`` resolves.

    Pydantic emits ``{"$ref": "#/$defs/Name", "$defs": {...}}``. ``#/`` is the
    document root. The fragment is valid alone and broken once it is nested
    under ``properties`` or ``items``. Identical definitions are shared. A
    name clash with a different schema renames that whole group and rewrites
    the ``$ref`` values that pointed at it.
    """
    collected = _absorb_defs(schema)
    if collected:
        schema["$defs"] = collected
    else:
        schema.pop("$defs", None)
    return schema


def _absorb_defs(node: Any) -> dict[str, Any]:
    if isinstance(node, list):
        merged: dict[str, Any] = {}
        for item in node:
            _merge_def_group(merged, _absorb_defs(item), item)
        return merged
    if not isinstance(node, dict):
        return {}

    local = node.pop("$defs", None)
    if not isinstance(local, dict):
        local = {}
    for value in list(node.values()):
        _merge_def_group(local, _absorb_defs(value), value)
    for definition in list(local.values()):
        _merge_def_group(local, _absorb_defs(definition), definition)
    return local


def _merge_def_group(destination: dict[str, Any], incoming: dict[str, Any], scope: Any) -> None:
    if not incoming:
        return
    conflict = any(
        name in destination and destination[name] != definition
        for name, definition in incoming.items()
    )
    if not conflict:
        for name, definition in incoming.items():
            destination.setdefault(name, definition)
        return

    taken = set(destination) | set(incoming)
    rename: dict[str, str] = {}
    for name in incoming:
        index = 2
        candidate = f"{name}_{index}"
        while candidate in taken:
            index += 1
            candidate = f"{name}_{index}"
        taken.add(candidate)
        rename[name] = candidate
        destination[candidate] = incoming[name]
    _rewrite_def_refs(scope, rename)
    for definition in incoming.values():
        _rewrite_def_refs(definition, rename)


def _rewrite_def_refs(node: Any, rename: dict[str, str]) -> None:
    if isinstance(node, list):
        for item in node:
            _rewrite_def_refs(item, rename)
        return
    if not isinstance(node, dict):
        return
    ref = node.get("$ref")
    if isinstance(ref, str) and ref.startswith("#/$defs/"):
        renamed = rename.get(ref.removeprefix("#/$defs/"))
        if renamed is not None:
            node["$ref"] = f"#/$defs/{renamed}"
    for value in node.values():
        _rewrite_def_refs(value, rename)
