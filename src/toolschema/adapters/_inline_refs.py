from __future__ import annotations

import copy
from typing import Any


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
