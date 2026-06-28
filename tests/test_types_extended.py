from __future__ import annotations

import dataclasses
from typing import TypedDict

from toolschema import schema
from toolschema._types import type_to_schema


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


def test_function_with_dataclass_param() -> None:
    def greet(user: User) -> str:
        return f"Hello, {user.name}"

    tool = schema(greet)
    user_schema = tool.parameters["properties"]["user"]
    assert user_schema["properties"]["name"]["type"] == "string"
