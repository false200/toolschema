from __future__ import annotations

import dataclasses
import enum
import importlib
import types
from typing import Annotated, Any, Literal, Union, get_args, get_origin, get_type_hints

from toolschema._fields import extract_annotated_metadata, merge_field_into_schema
from toolschema._schema_utils import inline_refs, json_schema_default

JSON_SCHEMA_2020_12 = "https://json-schema.org/draft/2020-12/schema"


def _load_marker_groups() -> tuple[frozenset[Any], frozenset[Any], frozenset[Any]]:
    """Collect Required, NotRequired, and ReadOnly special forms.

    Python 3.10 exposes Required and NotRequired from typing_extensions.
    ReadOnly arrived in 3.13 (and typing_extensions).
    """
    required: set[Any] = set()
    optional: set[Any] = set()
    readonly: set[Any] = set()
    groups = {"Required": required, "NotRequired": optional, "ReadOnly": readonly}
    for module_name in ("typing", "typing_extensions"):
        try:
            module = importlib.import_module(module_name)
        except ImportError:
            continue
        for name, bucket in groups.items():
            marker = getattr(module, name, None)
            if marker is not None:
                bucket.add(marker)
    return frozenset(required), frozenset(optional), frozenset(readonly)


_REQUIRED_MARKERS, _NOT_REQUIRED_MARKERS, _READONLY_MARKERS = _load_marker_groups()
_REQUIREDNESS_MARKERS = _REQUIRED_MARKERS | _NOT_REQUIRED_MARKERS | _READONLY_MARKERS


def _explicit_requiredness(annotation: Any) -> bool | None:
    """Return True for Required, False for NotRequired, None if unspecified.

    Annotated and ReadOnly wrappers are peeled so the marker is visible.
    Postponed annotations must already be resolved by get_type_hints.
    """
    current = annotation
    while True:
        origin = get_origin(current)
        if origin is Annotated or origin in _READONLY_MARKERS:
            args = get_args(current)
            if not args:
                return None
            current = args[0]
            continue
        if origin in _REQUIRED_MARKERS:
            return True
        if origin in _NOT_REQUIRED_MARKERS:
            return False
        return None


def _normalize_pydantic_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Normalize a Pydantic model_json_schema() payload to a property schema.

    Nested models are inlined into the property schema. Circular models keep
    ``$ref`` together with ``$defs``.
    """
    try:
        resolved = inline_refs(schema)
    except ValueError:
        resolved = schema
    drop = {"$schema", "title"}
    if "$defs" not in resolved:
        drop.add("$defs")
    return _strip_pydantic_node(resolved, drop)


def _strip_pydantic_node(schema: dict[str, Any], drop: set[str]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in schema.items():
        if key in drop:
            continue
        result[key] = _strip_pydantic_value(value, drop)
    if "properties" in result:
        result.setdefault("type", "object")
        result.setdefault("additionalProperties", False)
    return result


def _strip_pydantic_value(value: Any, drop: set[str]) -> Any:
    if isinstance(value, dict):
        return _strip_pydantic_node(value, drop)
    if isinstance(value, list):
        return [
            _strip_pydantic_value(item, drop) if isinstance(item, dict) else item for item in value
        ]
    return value


def _is_typeddict(tp: Any) -> bool:
    try:
        from typing_extensions import is_typeddict

        return is_typeddict(tp)
    except ImportError:
        return isinstance(tp, type) and hasattr(tp, "__annotations__") and hasattr(tp, "__total__")


def _typeddict_to_schema(tp: type[Any]) -> dict[str, Any]:
    # include_extras keeps Annotated/Field. `__total__` is only this class's
    # flag, so inherited required keys live on `__required_keys__`. That set is
    # wrong for Required/NotRequired when annotations are postponed (the runtime
    # sees a string and falls back to `total`), so explicit markers on the
    # resolved hints override it.
    hints = get_type_hints(tp, include_extras=True)
    properties = {name: type_to_schema(annotation) for name, annotation in hints.items()}
    if hasattr(tp, "__required_keys__"):
        required_keys = set(tp.__required_keys__)
    else:
        total = getattr(tp, "__total__", True)
        required_keys = set(hints) if total else set()
    # Python 3.10's typing.TypedDict can put one key in both
    # __required_keys__ and __optional_keys__ when a subclass redeclares it
    # and annotations are postponed. Totality breaks the tie unless a
    # Required or NotRequired marker is present.
    optional_keys = set(getattr(tp, "__optional_keys__", ()))
    own_total = bool(getattr(tp, "__total__", True))
    for name, annotation in hints.items():
        explicit = _explicit_requiredness(annotation)
        if explicit is True:
            required_keys.add(name)
        elif explicit is False:
            required_keys.discard(name)
        elif name in optional_keys and not own_total:
            required_keys.discard(name)
    required = [name for name in hints if name in required_keys]
    schema: dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        schema["required"] = required
    return schema


def _dataclass_to_schema(tp: type[Any]) -> dict[str, Any]:
    hints = get_type_hints(tp, include_extras=True)
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
                "default": json_schema_default(field.default),
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

    if origin in _REQUIREDNESS_MARKERS:
        if not args:
            raise TypeError(f"Unsupported type annotation: {tp!r}")
        return type_to_schema(args[0])

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
