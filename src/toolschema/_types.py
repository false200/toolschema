from __future__ import annotations

import dataclasses
import enum
import types
from typing import Annotated, Any, Literal, Union, get_args, get_origin, get_type_hints

from toolschema._fields import extract_annotated_metadata, merge_field_into_schema

JSON_SCHEMA_2020_12 = "https://json-schema.org/draft/2020-12/schema"


def _normalize_pydantic_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Normalize a Pydantic model_json_schema() payload to a property schema."""
    result = {k: v for k, v in schema.items() if k not in {"$defs", "$schema", "title"}}
    properties = result.get("properties")
    if isinstance(properties, dict):
        result["properties"] = {
            name: {k: v for k, v in prop.items() if k != "title"}
            for name, prop in properties.items()
            if isinstance(prop, dict)
        }
    if "properties" in result:
        result.setdefault("type", "object")
        result.setdefault("additionalProperties", False)
    return result


def _is_typeddict(tp: Any) -> bool:
    try:
        from typing_extensions import is_typeddict

        return is_typeddict(tp)
    except ImportError:
        return isinstance(tp, type) and hasattr(tp, "__annotations__") and hasattr(tp, "__total__")


def _typeddict_to_schema(tp: type[Any]) -> dict[str, Any]:
    hints = get_type_hints(tp)
    total = getattr(tp, "__total__", True)
    properties = {name: type_to_schema(annotation) for name, annotation in hints.items()}
    required = list(hints.keys()) if total else []
    schema: dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        schema["required"] = required
    return schema


def _dataclass_to_schema(tp: type[Any]) -> dict[str, Any]:
    hints = get_type_hints(tp)
    properties: dict[str, Any] = {}
    required: list[str] = []
    for field in dataclasses.fields(tp):
        annotation = hints.get(field.name, Any)
        properties[field.name] = type_to_schema(annotation)
        if field.default is dataclasses.MISSING and field.default_factory is dataclasses.MISSING:
            required.append(field.name)
        elif field.default is not dataclasses.MISSING:
            properties[field.name] = {
                **properties[field.name],
                "default": field.default,
            }
    schema: dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        schema["required"] = required
    return schema


def type_to_schema(tp: Any) -> dict[str, Any]:
    """Convert a Python type annotation to a JSON Schema 2020-12 fragment."""
    origin = get_origin(tp)
    args = get_args(tp)

    if origin is Annotated:
        base_type, extras = extract_annotated_metadata(args)
        schema = type_to_schema(base_type)
        return merge_field_into_schema(schema, extras)

    if origin is Union or isinstance(tp, types.UnionType):
        non_none = [a for a in args if a is not type(None)]
        if not non_none:
            return {"type": "null"}
        if len(non_none) == 1 and type(None) in args:
            inner = type_to_schema(non_none[0])
            return {"anyOf": [inner, {"type": "null"}]}
        schemas = [type_to_schema(a) for a in args if a is not type(None)]
        if type(None) in args:
            schemas.append({"type": "null"})
        if len(schemas) == 1:
            return schemas[0]
        return {"anyOf": schemas}

    if origin is tuple:
        if len(args) == 2 and args[1] is Ellipsis:
            return {"type": "array", "items": type_to_schema(args[0])}
        if args:
            return {
                "type": "array",
                "prefixItems": [type_to_schema(arg) for arg in args],
                "minItems": len(args),
                "maxItems": len(args),
            }
        return {"type": "array"}

    if origin is list:
        item_type = args[0] if args else Any
        return {"type": "array", "items": type_to_schema(item_type)}

    if origin is dict:
        if len(args) == 2 and args[0] is str:
            return {
                "type": "object",
                "additionalProperties": type_to_schema(args[1]),
            }
        if not args:
            return {"type": "object"}
        raise TypeError(f"Unsupported dict type (only dict[str, T] supported): {tp!r}")

    if origin is Literal:
        values = list(args)
        if all(isinstance(v, str) for v in values):
            return {"enum": values}
        if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in values):
            return {"enum": values}
        if all(isinstance(v, bool) for v in values):
            return {"enum": values}
        return {"enum": values}

    if isinstance(tp, type) and issubclass(tp, enum.Enum):
        return {"enum": [member.value for member in tp]}

    if isinstance(tp, type) and _is_typeddict(tp):
        return _typeddict_to_schema(tp)

    if isinstance(tp, type) and dataclasses.is_dataclass(tp):
        return _dataclass_to_schema(tp)

    if isinstance(tp, type) and hasattr(tp, "model_json_schema"):
        return _normalize_pydantic_schema(tp.model_json_schema())

    if tp is str:
        return {"type": "string"}
    if tp is int:
        return {"type": "integer"}
    if tp is float:
        return {"type": "number"}
    if tp is bool:
        return {"type": "boolean"}
    if tp is dict:
        return {"type": "object"}
    if tp is type(None):
        return {"type": "null"}
    if tp is Any:
        return {}

    raise TypeError(f"Unsupported type annotation: {tp!r}")
