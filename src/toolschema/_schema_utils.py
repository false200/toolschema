from __future__ import annotations

import copy
import enum
from typing import Any


def json_schema_default(value: Any) -> Any:
    """Return a JSON-compatible form of a Python default.

    JSON Schema ``default`` has to be a JSON value, and it has to match the
    ``enum`` this library emits (member values, not members). A plain ``Enum``
    member is not JSON-serializable, and ``validate()`` rejects it because the
    member is not in that value list. Tuples are written as arrays. Lists and
    dicts are walked only when a nested value actually changes.
    """
    if isinstance(value, enum.Enum):
        return json_schema_default(value.value)
    if isinstance(value, tuple):
        return [json_schema_default(item) for item in value]
    if isinstance(value, list):
        converted = [json_schema_default(item) for item in value]
        if all(new is old for new, old in zip(converted, value, strict=True)):
            return value
        return converted
    if isinstance(value, dict):
        converted = {key: json_schema_default(item) for key, item in value.items()}
        if all(new is old for new, old in zip(converted.values(), value.values(), strict=True)):
            return value
        return converted
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
    if not defs:
        return cloned
    return _inline_node(cloned, defs, set())
