from __future__ import annotations

import collections.abc as collections_abc
import copy
import dataclasses
import enum
import importlib
import types
from contextvars import ContextVar
from typing import Annotated, Any, Literal, Union, get_args, get_origin, get_type_hints

from toolschema._fields import extract_annotated_metadata, merge_field_into_schema
from toolschema._schema_utils import hoist_defs, inline_refs, json_schema_default

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


def _load_final_markers() -> frozenset[Any]:
    found: set[Any] = set()
    for module_name in ("typing", "typing_extensions"):
        try:
            module = importlib.import_module(module_name)
        except ImportError:
            continue
        marker = getattr(module, "Final", None)
        if marker is not None:
            found.add(marker)
    return frozenset(found)


_FINAL_MARKERS = _load_final_markers()
_SEQUENCE_ORIGINS = frozenset(
    {
        list,
        collections_abc.Sequence,
        collections_abc.MutableSequence,
    }
)
_SET_ORIGINS = frozenset(
    {
        set,
        frozenset,
        collections_abc.Set,
        collections_abc.MutableSet,
    }
)
_MAPPING_ORIGINS = frozenset(
    {
        dict,
        collections_abc.Mapping,
        collections_abc.MutableMapping,
    }
)


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


class _StructState:
    """Names and schemas for structured types currently being converted.

    A type that refers to itself, or to another type still on the stack, cannot
    be inlined. Those cycles become ``$ref`` plus ``$defs``. A nested type that
    is not part of a cycle stays inlined, which is what existing schemas emit.
    """

    def __init__(self) -> None:
        self.building: dict[Any, str] = {}
        self.built: dict[Any, dict[str, Any]] = {}
        self.referenced: set[Any] = set()
        self.used_names: set[str] = set()


_STRUCT_STATE: ContextVar[_StructState | None] = ContextVar("toolschema_struct_state", default=None)


def _definition_name(tp: Any, state: _StructState) -> str:
    base = getattr(tp, "__name__", None)
    if not isinstance(base, str) or not base:
        base = "Type"
    candidate = base
    index = 2
    while candidate in state.used_names:
        candidate = f"{base}_{index}"
        index += 1
    state.used_names.add(candidate)
    return candidate


def _structured(tp: Any, build: collections_abc.Callable[[], dict[str, Any]]) -> dict[str, Any]:
    """Convert one structured type, emitting ``$ref`` when it is re-entered."""
    state = _STRUCT_STATE.get()
    token = None
    if state is None:
        state = _StructState()
        token = _STRUCT_STATE.set(state)
    try:
        if tp in state.building:
            state.referenced.add(tp)
            return {"$ref": f"#/$defs/{state.building[tp]}"}
        cached = state.built.get(tp)
        if cached is not None:
            return copy.deepcopy(cached)
        state.building[tp] = _definition_name(tp, state)
        try:
            body = build()
        finally:
            name = state.building.pop(tp)
        if tp in state.referenced:
            result: dict[str, Any] = {"$ref": f"#/$defs/{name}", "$defs": {name: body}}
        else:
            result = body
        state.built[tp] = result
        return copy.deepcopy(result)
    finally:
        if token is not None:
            _STRUCT_STATE.reset(token)


def _typeddict_to_schema(tp: type[Any]) -> dict[str, Any]:
    return _structured(tp, lambda: _typeddict_body(tp))


def _typeddict_body(tp: type[Any]) -> dict[str, Any]:
    # include_extras keeps Annotated/Field. `__total__` is only this class's
    # flag, so inherited required keys live on `__required_keys__`. That set is
    # wrong for Required/NotRequired when annotations are postponed (the runtime
    # sees a string and falls back to `total`), so explicit markers on the
    # resolved hints override it.
    hints = get_type_hints(tp, include_extras=True)
    properties = {name: _type_to_schema(annotation) for name, annotation in hints.items()}
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
    return _structured(tp, lambda: _dataclass_body(tp))


def _dataclass_body(tp: type[Any]) -> dict[str, Any]:
    hints = get_type_hints(tp, include_extras=True)
    properties: dict[str, Any] = {}
    required: list[str] = []
    for field in dataclasses.fields(tp):
        annotation = hints.get(field.name, Any)
        properties[field.name] = _type_to_schema(annotation)
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


def _is_namedtuple(tp: Any) -> bool:
    return (
        isinstance(tp, type)
        and issubclass(tp, tuple)
        and hasattr(tp, "_fields")
        and hasattr(tp, "_field_defaults")
    )


def _namedtuple_to_schema(tp: type[Any]) -> dict[str, Any]:
    return _structured(tp, lambda: _namedtuple_body(tp))


def _namedtuple_body(tp: type[Any]) -> dict[str, Any]:
    hints = get_type_hints(tp, include_extras=True)
    defaults = getattr(tp, "_field_defaults", {})
    properties: dict[str, Any] = {}
    required: list[str] = []
    for name in tp._fields:
        properties[name] = _type_to_schema(hints.get(name, Any))
        if name in defaults:
            properties[name] = {
                **properties[name],
                "default": json_schema_default(defaults[name]),
            }
        else:
            required.append(name)
    schema: dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        schema["required"] = required
    return schema


def _array_schema(item_type: Any, *, unique: bool = False) -> dict[str, Any]:
    schema: dict[str, Any] = {"type": "array", "items": _type_to_schema(item_type)}
    if unique:
        schema["uniqueItems"] = True
    return schema


def _is_union(tp: Any) -> bool:
    return get_origin(tp) is Union or isinstance(tp, types.UnionType)


def _includes_none(tp: Any) -> bool:
    """Return whether this annotation already accepts null."""
    if tp is type(None):
        return True
    if _is_union(tp):
        return any(_includes_none(arg) for arg in get_args(tp))
    origin = get_origin(tp)
    wrappers = _FINAL_MARKERS | _REQUIREDNESS_MARKERS
    if origin is Annotated or origin in wrappers:
        args = get_args(tp)
        return bool(args) and _includes_none(args[0])
    return False


def _collapse_redundant_none(tp: Any) -> Any:
    """Drop an outer Optional that repeats null already present inside.

    On Python 3.10, postponed evaluation makes ``get_type_hints`` rewrite
    ``Annotated[str | None, Field(...)]`` as
    ``Optional[Annotated[str | None, Field(...)]]``. ``Union`` flattening
    does not remove that wrapper, because ``Annotated`` is not itself a
    union. The extra branch nests constraints such as ``minLength`` inside
    ``anyOf``. Python 3.11+ leaves the annotation unchanged.
    """
    if not _is_union(tp):
        return tp
    args = get_args(tp)
    if type(None) not in args:
        return tp
    non_none = [arg for arg in args if arg is not type(None)]
    if len(non_none) == 1 and _includes_none(non_none[0]):
        return non_none[0]
    return tp


def type_to_schema(tp: Any) -> dict[str, Any]:
    """Convert a Python type annotation to a JSON Schema 2020-12 fragment.

    ``$defs`` are lifted to this fragment so ``#/$defs/`` still resolves when
    the fragment is used on its own. Callers that embed it in a larger
    document have to hoist again.
    """
    return hoist_defs(_type_to_schema(tp))


def _type_to_schema(tp: Any) -> dict[str, Any]:
    tp = _collapse_redundant_none(tp)
    origin = get_origin(tp)
    args = get_args(tp)

    if origin in _FINAL_MARKERS or origin in _REQUIREDNESS_MARKERS:
        if not args:
            raise TypeError(f"Unsupported type annotation: {tp!r}")
        return _type_to_schema(args[0])

    if origin is Annotated:
        base_type, extras = extract_annotated_metadata(args)
        schema = _type_to_schema(base_type)
        return merge_field_into_schema(schema, extras)

    if origin is Union or isinstance(tp, types.UnionType):
        non_none = [a for a in args if a is not type(None)]
        if not non_none:
            return {"type": "null"}
        if len(non_none) == 1 and type(None) in args:
            inner = _type_to_schema(non_none[0])
            return {"anyOf": [inner, {"type": "null"}]}
        schemas = [_type_to_schema(a) for a in args if a is not type(None)]
        if type(None) in args:
            schemas.append({"type": "null"})
        if len(schemas) == 1:
            return schemas[0]
        return {"anyOf": schemas}

    if origin is tuple:
        if len(args) == 2 and args[1] is Ellipsis:
            return {"type": "array", "items": _type_to_schema(args[0])}
        if args:
            return {
                "type": "array",
                "prefixItems": [_type_to_schema(arg) for arg in args],
                "minItems": len(args),
                "maxItems": len(args),
            }
        return {"type": "array", "maxItems": 0}

    if origin in _SEQUENCE_ORIGINS:
        item_type = args[0] if args else Any
        return _array_schema(item_type)

    if origin in _SET_ORIGINS:
        item_type = args[0] if args else Any
        return _array_schema(item_type, unique=True)

    if origin in _MAPPING_ORIGINS:
        if len(args) == 2 and args[0] is str:
            return {
                "type": "object",
                "additionalProperties": _type_to_schema(args[1]),
            }
        if not args:
            return {"type": "object"}
        raise TypeError(f"Unsupported mapping type (only str keys are supported): {tp!r}")

    if origin is Literal:
        return {"enum": [json_schema_default(value) for value in args]}

    if isinstance(tp, type) and issubclass(tp, enum.Enum):
        return {"enum": [json_schema_default(member) for member in tp]}

    if isinstance(tp, type) and _is_typeddict(tp):
        return _typeddict_to_schema(tp)

    if isinstance(tp, type) and dataclasses.is_dataclass(tp):
        return _dataclass_to_schema(tp)

    if _is_namedtuple(tp):
        return _namedtuple_to_schema(tp)

    if isinstance(tp, type) and hasattr(tp, "model_json_schema"):
        return _normalize_pydantic_schema(tp.model_json_schema())

    if tp is str or tp is bytes or tp is bytearray:
        if tp is str:
            return {"type": "string"}
        return {"type": "string", "contentEncoding": "base64"}
    if tp is int:
        return {"type": "integer"}
    if tp is float:
        return {"type": "number"}
    if tp is bool:
        return {"type": "boolean"}
    if tp is dict or tp is collections_abc.Mapping or tp is collections_abc.MutableMapping:
        return {"type": "object"}
    if tp is list or tp in (collections_abc.Sequence, collections_abc.MutableSequence):
        return {"type": "array"}
    if tp in (set, frozenset, collections_abc.Set, collections_abc.MutableSet):
        return {"type": "array", "uniqueItems": True}
    if tp is type(None):
        return {"type": "null"}
    if tp is Any:
        return {}

    supertype = getattr(tp, "__supertype__", None)
    if supertype is not None:
        return _type_to_schema(supertype)

    raise TypeError(f"Unsupported type annotation: {tp!r}")
