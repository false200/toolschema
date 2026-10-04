from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import Annotated, Literal

import fixtures

from toolschema import Field, schema, tool
from toolschema._validate import ValidationSuccess


class _Color(str, Enum):
    RED = "red"
    GREEN = "green"


class _PlainColor(Enum):
    RED = "red"
    BLUE = "blue"


def _paint(
    color: _PlainColor = _PlainColor.RED,
    colors: tuple[_PlainColor, ...] = (_PlainColor.RED, _PlainColor.BLUE),
) -> str:
    """Paint a surface."""
    return color.value


def test_primitive_params() -> None:
    def fn(a: str, b: int, c: float, d: bool) -> None:
        pass

    t = schema(fn)
    props = t.parameters["properties"]
    assert props["a"]["type"] == "string"
    assert props["b"]["type"] == "integer"
    assert props["c"]["type"] == "number"
    assert props["d"]["type"] == "boolean"


def test_defaults_and_required() -> None:
    t = schema(fixtures.add)
    assert t.name == "add"
    assert t.parameters["properties"]["a"]["type"] == "integer"
    assert "b" not in t.parameters.get("required", [])
    assert t.parameters["properties"]["b"]["default"] == 1
    assert t.parameters["required"] == ["a"]


def test_optional_none() -> None:
    def fn(value: str | None) -> None:
        pass

    t = schema(fn)
    prop = t.parameters["properties"]["value"]
    assert prop == {"anyOf": [{"type": "string"}, {"type": "null"}]}


def test_list_and_dict() -> None:
    def fn(items: list[int], tags: dict[str, str]) -> None:
        pass

    t = schema(fn)
    props = t.parameters["properties"]
    assert props["items"] == {"type": "array", "items": {"type": "integer"}}
    assert props["tags"] == {
        "type": "object",
        "additionalProperties": {"type": "string"},
    }


def test_plain_enum_default_is_json_value() -> None:
    tool_def = schema(_paint)
    props = tool_def.parameters["properties"]
    assert props["color"] == {"enum": ["red", "blue"], "default": "red"}
    assert type(props["color"]["default"]) is str
    assert props["colors"]["default"] == ["red", "blue"]
    assert type(props["colors"]["default"]) is list

    json.dumps(tool_def.to_openai())
    json.dumps(tool_def.to_json_schema())

    omitted = tool_def.validate({})
    assert isinstance(omitted, ValidationSuccess)
    assert omitted.value == {"color": "red", "colors": ["red", "blue"]}


def test_literal_enum() -> None:
    def fn(mode: Literal["a", "b"], color: _Color) -> None:
        pass

    t = schema(fn)
    props = t.parameters["properties"]
    assert props["mode"] == {"enum": ["a", "b"]}
    assert props["color"] == {"enum": ["red", "green"]}


def test_annotated_field_descriptions() -> None:
    def fn(
        city: Annotated[str, Field(description="City name", min_length=1)],
        region: Annotated[str, "Region name"],
    ) -> None:
        pass

    t = schema(fn)
    props = t.parameters["properties"]
    assert props["city"] == {
        "type": "string",
        "description": "City name",
        "minLength": 1,
    }
    assert props["region"] == {
        "type": "string",
        "description": "Region name",
    }


def test_docstring_description() -> None:
    t = schema(fixtures.add)
    assert t.description == "Add two numbers."


def test_tool_decorator() -> None:
    @tool
    def greet(name: str) -> str:
        """Say hello."""
        return f"Hello, {name}"

    assert greet("world") == "Hello, world"
    t = schema(greet)
    assert t.name == "greet"
    assert "name" in t.parameters["properties"]


def test_tool_decorator_overrides() -> None:
    @tool(name="custom_greet", description="Custom hello.")
    def greet(name: str) -> str:
        """Original docstring."""
        return f"Hello, {name}"

    t = schema(greet)
    assert t.name == "custom_greet"
    assert t.description == "Custom hello."


def test_snapshot_search_github_schema() -> None:
    t = schema(fixtures.search_github)
    snapshot_path = Path(__file__).parent / "snapshots" / "search_github_canonical.json"
    expected = json.loads(snapshot_path.read_text(encoding="utf-8"))
    assert t.to_json_schema() == expected


def test_type_to_schema_primitives() -> None:
    from toolschema._types import type_to_schema

    assert type_to_schema(str) == {"type": "string"}
    assert type_to_schema(int) == {"type": "integer"}
    assert type_to_schema(float) == {"type": "number"}
    assert type_to_schema(bool) == {"type": "boolean"}


def test_type_to_schema_unsupported() -> None:
    import pytest

    from toolschema._types import type_to_schema

    with pytest.raises(TypeError, match="Unsupported"):
        type_to_schema(complex)


def test_pydantic_model_duck_type() -> None:
    pytest = __import__("pytest")
    pydantic = pytest.importorskip("pydantic")
    from toolschema._types import type_to_schema

    class User(pydantic.BaseModel):
        name: str
        age: int

    schema = type_to_schema(User)
    assert schema["type"] == "object"
    assert schema["properties"]["name"] == {"type": "string"}
    assert schema["properties"]["age"] == {"type": "integer"}


def test_pydantic_nested_model_is_inlined() -> None:
    pytest = __import__("pytest")
    pydantic = pytest.importorskip("pydantic")
    from toolschema._types import type_to_schema
    from toolschema._validate import ValidationFailure, ValidationSuccess

    class Address(pydantic.BaseModel):
        city: str

    class User(pydantic.BaseModel):
        name: str
        address: Address
        tags: list[Address] = []

    result = type_to_schema(User)
    encoded = json.dumps(result)
    assert "$ref" not in encoded
    assert "$defs" not in result
    assert "title" not in encoded
    address = result["properties"]["address"]
    assert address["properties"]["city"] == {"type": "string"}
    assert address["required"] == ["city"]
    assert address["additionalProperties"] is False
    assert result["properties"]["tags"]["items"]["properties"]["city"] == {"type": "string"}

    def greet(user):
        """Greet a user."""
        return user.name

    greet.__annotations__ = {"user": User, "return": str}
    tool = schema(greet)
    missing = tool.validate({"user": {"name": "Ada"}})
    assert isinstance(missing, ValidationFailure)
    present = tool.validate({"user": {"name": "Ada", "address": {"city": "Paris"}}})
    assert isinstance(present, ValidationSuccess)
    assert "$ref" not in json.dumps(tool.to_mcp())


def test_pydantic_recursive_model_keeps_defs() -> None:
    pytest = __import__("pytest")
    pydantic = pytest.importorskip("pydantic")
    from toolschema._types import type_to_schema

    class Node(pydantic.BaseModel):
        name: str
        child: Node | None = None

    result = type_to_schema(Node)
    assert result["$ref"] == "#/$defs/Node"
    node = result["$defs"]["Node"]
    assert node["properties"]["name"] == {"type": "string"}
    assert node["additionalProperties"] is False
    assert "title" not in json.dumps(result)
