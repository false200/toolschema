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


def merge_field_into_schema(base_schema: dict[str, Any], extras: dict[str, Any]) -> dict[str, Any]:
    """Merge Field / Annotated metadata into a JSON Schema fragment."""
    if not extras:
        return base_schema
    return {**base_schema, **extras}
