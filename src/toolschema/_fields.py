from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Field:
    """Metadata for Annotated type hints, mapped to JSON Schema constraints."""

    description: str | None = None
    min_length: int | None = None
    max_length: int | None = None
    ge: int | float | None = None
    le: int | float | None = None
    gt: int | float | None = None
    lt: int | float | None = None
    pattern: str | None = None


def field_to_schema_extras(field: Field) -> dict[str, Any]:
    """Convert Field metadata to JSON Schema keyword fragments."""
    extras: dict[str, Any] = {}
    if field.description is not None:
        extras["description"] = field.description
    if field.min_length is not None:
        extras["minLength"] = field.min_length
    if field.max_length is not None:
        extras["maxLength"] = field.max_length
    if field.ge is not None:
        extras["minimum"] = field.ge
    if field.le is not None:
        extras["maximum"] = field.le
    if field.gt is not None:
        extras["exclusiveMinimum"] = field.gt
    if field.lt is not None:
        extras["exclusiveMaximum"] = field.lt
    if field.pattern is not None:
        extras["pattern"] = field.pattern
    return extras


def extract_annotated_metadata(metadata: tuple[Any, ...]) -> tuple[type[Any], dict[str, Any]]:
    """Extract base type and merged schema extras from Annotated metadata."""
    if not metadata:
        return object, {}

    base_type = metadata[0] if isinstance(metadata[0], type) else metadata[0]
    extras: dict[str, Any] = {}

    for item in metadata[1:]:
        if isinstance(item, Field):
            extras.update(field_to_schema_extras(item))
        elif isinstance(item, str):
            if "description" not in extras:
                extras["description"] = item

    return base_type, extras


def _variable_arrays(schema: dict[str, Any]) -> list[dict[str, Any]] | None:
    """Arrays whose length is not already fixed by ``prefixItems``.

    ``minLength`` does not apply to arrays. A tuple schema already has
    ``minItems`` and ``maxItems``, so those stay as they are.
    """
    if schema.get("type") == "array" and "prefixItems" not in schema:
        return [schema]
    branches = schema.get("anyOf")
    if not isinstance(branches, list):
        return None
    arrays: list[dict[str, Any]] = []
    for branch in branches:
        if not isinstance(branch, dict) or branch.get("type") == "null":
            continue
        if branch.get("type") != "array" or "prefixItems" in branch:
            return None
        arrays.append(branch)
    return arrays or None


def merge_field_into_schema(base_schema: dict[str, Any], extras: dict[str, Any]) -> dict[str, Any]:
    """Merge Field / Annotated metadata into a JSON Schema fragment."""
    if not extras:
        return base_schema
    arrays = _variable_arrays(base_schema)
    if not arrays or ("minLength" not in extras and "maxLength" not in extras):
        return {**base_schema, **extras}

    extras = dict(extras)
    length: dict[str, Any] = {}
    if "minLength" in extras:
        length["minItems"] = extras.pop("minLength")
    if "maxLength" in extras:
        length["maxItems"] = extras.pop("maxLength")
    if base_schema.get("type") == "array":
        return {**base_schema, **length, **extras}

    branches: list[Any] = []
    for branch in base_schema["anyOf"]:
        variable_array = (
            isinstance(branch, dict)
            and branch.get("type") == "array"
            and "prefixItems" not in branch
        )
        branches.append({**branch, **length} if variable_array else branch)
    return {**base_schema, "anyOf": branches, **extras}
