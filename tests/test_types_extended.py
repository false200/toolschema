from __future__ import annotations

import dataclasses
import json
import sys
from enum import Enum
from typing import Annotated, TypedDict

from toolschema import Field, schema
from toolschema._types import type_to_schema
from toolschema._validate import ValidationFailure, ValidationSuccess

if sys.version_info >= (3, 11):
    from typing import NotRequired, Required
else:
    from typing_extensions import NotRequired, Required


class Point(TypedDict):
    x: int
    y: int


class PartialPoint(TypedDict, total=False):
    x: int
    y: int


@dataclasses.dataclass
class User:
    name: str
    age: int = 18


class _Swatch(Enum):
    RED = "red"
    BLUE = "blue"


@dataclasses.dataclass
class _Paint:
    color: _Swatch = _Swatch.RED


def test_typeddict_schema() -> None:
    result = type_to_schema(Point)
    assert result == {
        "type": "object",
        "properties": {
            "x": {"type": "integer"},
            "y": {"type": "integer"},
        },
        "additionalProperties": False,
        "required": ["x", "y"],
    }


def test_partial_typeddict_schema() -> None:
    result = type_to_schema(PartialPoint)
    assert result.get("required", []) == []


def test_dataclass_schema() -> None:
    result = type_to_schema(User)
    assert result["properties"]["name"] == {"type": "string"}
    assert result["properties"]["age"] == {"type": "integer", "default": 18}
    assert result["required"] == ["name"]


def test_union_schema() -> None:
    assert type_to_schema(int | str) == {
        "anyOf": [{"type": "integer"}, {"type": "string"}],
    }


def test_tuple_schema() -> None:
    assert type_to_schema(tuple[int, str]) == {
        "type": "array",
        "prefixItems": [{"type": "integer"}, {"type": "string"}],
        "minItems": 2,
        "maxItems": 2,
    }


def test_function_with_typeddict_param() -> None:
    def locate(point: Point) -> str:
        return f"{point['x']},{point['y']}"

    tool = schema(locate)
    point_schema = tool.parameters["properties"]["point"]
    assert point_schema["type"] == "object"
    assert point_schema["required"] == ["x", "y"]


def test_dataclass_enum_default_is_json_value() -> None:
    result = type_to_schema(_Paint)
    assert result["properties"]["color"]["default"] == "red"
    assert type(result["properties"]["color"]["default"]) is str
    json.dumps(result)

    def use(paint: _Paint) -> str:
        """Apply a paint."""
        return paint.color.value

    json.dumps(schema(use).to_mcp())


def test_function_with_dataclass_param() -> None:
    def greet(user: User) -> str:
        return f"Hello, {user.name}"

    tool = schema(greet)
    user_schema = tool.parameters["properties"]["user"]
    assert user_schema["properties"]["name"]["type"] == "string"


class _Account(TypedDict):
    id: int
    name: str
    nickname: NotRequired[str]


class _AccountUpdate(_Account, total=False):
    extra: str


class _Loose(TypedDict, total=False):
    id: Required[int]
    note: str


class _LooseChild(_Loose):
    name: str


class _MovieBase(TypedDict):
    title: str
    year: NotRequired[int]


class _MovieOverride(_MovieBase, total=False):
    year: int


class _MovieOverrideRequired(_MovieBase, total=False):
    year: Required[int]


class _Movie(TypedDict):
    title: str
    year: NotRequired[int]


class _Draft(TypedDict, total=False):
    title: str
    id: Required[int]


class _LabeledPoint(TypedDict):
    x: Annotated[int, Field(description="X coordinate", ge=0)]
    note: NotRequired[Annotated[str, Field(description="Note", min_length=1)]]
    code: Annotated[NotRequired[str], "Code"]


@dataclasses.dataclass
class _Profile:
    name: Annotated[str, Field(description="Full name", min_length=1)]
    age: int = 18


def test_typeddict_subclass_keeps_inherited_required_keys() -> None:
    result = type_to_schema(_AccountUpdate)
    assert result["required"] == ["id", "name"]
    assert "nickname" in result["properties"]
    assert "extra" in result["properties"]
    assert "nickname" not in result["required"]
    assert "extra" not in result["required"]

    child = type_to_schema(_LooseChild)
    assert child["required"] == ["id", "name"]
    assert "note" not in child["required"]

    def save(account: _AccountUpdate) -> None:
        """Save an account."""

    missing = schema(save).validate({"account": {"nickname": "ada"}})
    assert isinstance(missing, ValidationFailure)
    assert any(issue.path == ("account", "id") for issue in missing.issues)

    ok = schema(save).validate({"account": {"id": 1, "name": "Ada"}})
    assert isinstance(ok, ValidationSuccess)


def test_typeddict_not_required_and_required() -> None:
    movie = type_to_schema(_Movie)
    assert movie["required"] == ["title"]
    assert movie["properties"]["year"] == {"type": "integer"}

    draft = type_to_schema(_Draft)
    assert draft["required"] == ["id"]
    assert "title" not in draft["required"]

    # Redeclaring a NotRequired key without a marker uses the subclass total.
    overridden = type_to_schema(_MovieOverride)
    assert overridden["required"] == ["title"]
    assert overridden["properties"]["year"] == {"type": "integer"}

    forced = type_to_schema(_MovieOverrideRequired)
    assert forced["required"] == ["title", "year"]


def test_typeddict_annotated_fields_keep_metadata() -> None:
    result = type_to_schema(_LabeledPoint)
    assert result["required"] == ["x"]
    assert result["properties"]["x"] == {
        "type": "integer",
        "description": "X coordinate",
        "minimum": 0,
    }
    assert result["properties"]["note"] == {
        "type": "string",
        "description": "Note",
        "minLength": 1,
    }
    assert result["properties"]["code"] == {"type": "string", "description": "Code"}


def test_dataclass_annotated_fields_keep_metadata() -> None:
    result = type_to_schema(_Profile)
    assert result["properties"]["name"] == {
        "type": "string",
        "description": "Full name",
        "minLength": 1,
    }
    assert result["properties"]["age"] == {"type": "integer", "default": 18}
    assert result["required"] == ["name"]


def test_readonly_wrapper_is_unwrapped_when_available() -> None:
    import typing

    import pytest

    read_only = getattr(typing, "ReadOnly", None)
    if read_only is None:
        typing_extensions = pytest.importorskip("typing_extensions")
        read_only = getattr(typing_extensions, "ReadOnly", None)
        if read_only is None:
            pytest.skip("ReadOnly is not available")

    assert type_to_schema(read_only[int]) == {"type": "integer"}
