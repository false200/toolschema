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
