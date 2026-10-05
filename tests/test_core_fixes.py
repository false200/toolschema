"""Regression tests for schema, validation, and adapter bugs found by probing."""

from __future__ import annotations

import dataclasses
import enum
import json
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Annotated, Any, Final, Literal, NamedTuple, NewType, TypedDict
from uuid import UUID

from toolschema import Field, schema
from toolschema._types import type_to_schema
from toolschema._validate import ValidationFailure, ValidationSuccess, validate_arguments

_ITEMS = ["a"]
_NESTED = {"nums": [1]}
UserId = NewType("UserId", str)


class _Color(enum.Enum):
    RED = "red"


class _Point(NamedTuple):
    x: int
    y: str = "n"


@dataclasses.dataclass
class _User:
    name: str
    role: str = "admin"


_TAGS = {"b", "a"}


class _City(TypedDict):
    city: Annotated[str, Field(min_length=2, description="City")]


def test_enum_rejects_bool_and_accepts_numeric_one() -> None:
    def choose(n: Literal[0, 1]) -> None:
        """Choose."""

    tool = schema(choose)
    assert isinstance(tool.validate({"n": True}), ValidationFailure)
    assert isinstance(tool.validate({"n": False}), ValidationFailure)
    assert isinstance(tool.validate({"n": 1}), ValidationSuccess)
    assert isinstance(tool.validate({"n": 1.0}), ValidationSuccess)


def test_empty_tuple_is_an_empty_array() -> None:
    def empty(value: tuple[()]) -> None:
        """Empty."""

    prop = schema(empty).parameters["properties"]["value"]
    assert prop["maxItems"] == 0
    assert isinstance(schema(empty).validate({"value": []}), ValidationSuccess)
    assert isinstance(schema(empty).validate({"value": [1]}), ValidationFailure)


def test_mutable_defaults_are_not_shared() -> None:
    def collect(items: list[str] = _ITEMS, payload: dict[str, list[int]] = _NESTED) -> None:
        """Collect."""

    tool = schema(collect)
    assert tool.parameters["properties"]["items"]["default"] is not _ITEMS
    first = tool.validate({})
    assert isinstance(first, ValidationSuccess)
    first.value["items"].append("z")
    first.value["payload"]["nums"].append(9)
    second = tool.validate({})
    assert isinstance(second, ValidationSuccess)
    assert second.value == {"items": ["a"], "payload": {"nums": [1]}}
    assert _ITEMS == ["a"]
    assert _NESTED == {"nums": [1]}


def test_non_json_defaults_are_serialized() -> None:
    def record(
        tags: list[str] = _TAGS,
        when: str = datetime(2020, 1, 1),
        day: str = date(2020, 1, 2),
        amount: float = Decimal("1.5"),
        whole: int = Decimal("2"),
        uid: str = UUID("12345678-1234-5678-1234-567812345678"),
        path: str = Path("/tmp/x"),
        blob: str = b"hi",
        color: Literal[_Color.RED] = _Color.RED,
    ) -> None:
        """Record."""

    props = schema(record).parameters["properties"]
    json.dumps(schema(record).parameters)
    assert props["tags"]["default"] == ["a", "b"]
    assert props["when"]["default"] == "2020-01-01T00:00:00"
    assert props["day"]["default"] == "2020-01-02"
    assert props["amount"]["default"] == 1.5
    assert props["whole"]["default"] == 2
    assert props["uid"]["default"] == "12345678-1234-5678-1234-567812345678"
    assert props["path"]["default"] == "/tmp/x"
    assert props["blob"]["default"] == "hi"
    assert props["color"] == {"enum": ["red"], "default": "red"}


def test_invalid_pattern_is_a_validation_issue() -> None:
    def match(value: Annotated[str, Field(pattern="[")]) -> None:
        """Match."""

    result = schema(match).validate({"value": "a"})
    assert isinstance(result, ValidationFailure)
    assert any("pattern" in issue.message for issue in result.issues)


def test_common_aliases_and_containers() -> None:
    assert type_to_schema(list) == {"type": "array"}
    assert type_to_schema(set[str])["uniqueItems"] is True
    assert type_to_schema(Sequence[int]) == {"type": "array", "items": {"type": "integer"}}
    assert type_to_schema(Mapping[str, int]) == {
        "type": "object",
        "additionalProperties": {"type": "integer"},
    }
    assert type_to_schema(bytes) == {"type": "string", "contentEncoding": "base64"}
    assert type_to_schema(UserId) == {"type": "string"}
    assert type_to_schema(Final[int]) == {"type": "integer"}
    named = type_to_schema(_Point)
    assert named["required"] == ["x"]
    assert named["properties"]["y"]["default"] == "n"


def test_constraints_emitted_by_models_are_enforced() -> None:
    parameters = {
        "type": "object",
        "properties": {
            "n": {"type": "integer", "multipleOf": 2},
            "tags": {"type": "array", "uniqueItems": True},
            "when": {"type": "string", "format": "date-time"},
            "value": {"type": ["string", "null"]},
            "pair": {
                "prefixItems": [{"type": "integer"}, {"type": "string"}],
                "minItems": 2,
                "maxItems": 2,
            },
        },
        "required": ["n", "tags", "when", "value", "pair"],
        "additionalProperties": False,
    }
    assert isinstance(
        validate_arguments(
            {
                "n": 2,
                "tags": [1, 2],
                "when": "2020-01-01T00:00:00Z",
                "value": None,
                "pair": [1, "a"],
            },
            parameters,
        ),
        ValidationSuccess,
    )
    assert isinstance(
        validate_arguments(
            {"n": 3, "tags": [1], "when": "2020-01-01T00:00:00Z", "value": None, "pair": [1, "a"]},
            parameters,
        ),
        ValidationFailure,
    )
    assert isinstance(
        validate_arguments(
            {
                "n": 2,
                "tags": [1, 1],
                "when": "2020-01-01T00:00:00Z",
                "value": None,
                "pair": [1, "a"],
            },
            parameters,
        ),
        ValidationFailure,
    )
    assert isinstance(
        validate_arguments(
            {"n": 2, "tags": [1], "when": "not-a-date", "value": None, "pair": [1, "a"]},
            parameters,
        ),
        ValidationFailure,
    )
    assert isinstance(
        validate_arguments(
            {"n": 2, "tags": [1], "when": "2020-01-01T00:00:00Z", "value": 1, "pair": [1, "a"]},
            parameters,
        ),
        ValidationFailure,
    )
    assert isinstance(
        validate_arguments(
            {"n": 2, "tags": [1], "when": "2020-01-01T00:00:00Z", "value": None, "pair": ["a", 1]},
            parameters,
        ),
        ValidationFailure,
    )


def test_nested_dataclass_default_is_filled() -> None:
    def greet(user: _User) -> str:
        """Greet."""
        return user.name

    result = schema(greet).validate({"user": {"name": "Ada"}})
    assert isinstance(result, ValidationSuccess)
    assert result.value["user"]["role"] == "admin"


def test_self_parameter_is_kept_on_functions_and_dropped_on_methods() -> None:
    def configure(self: str, value: int) -> None:
        """Configure."""

    assert "self" in schema(configure).parameters["properties"]

    class Box:
        def run(self, name: str) -> str:
            """Run."""
            return name

    properties = schema(Box.run).parameters["properties"]
    assert "self" not in properties
    assert "name" in properties


def test_gemini_enum_has_a_type_and_anthropic_walks_nested_constraints() -> None:
    def choose(mode: Literal["a", "b"]) -> None:
        """Choose."""

    gemini = schema(choose).to_gemini()["parameters"]["properties"]["mode"]
    assert gemini["type"] == "STRING"
    assert gemini["enum"] == ["a", "b"]

    def save(user: _City) -> None:
        """Save."""

    prop = schema(save).to_anthropic()["input_schema"]["properties"]["user"]["properties"]["city"]
    assert "minLength" not in prop
    assert "min length 2" in prop["description"]


class _StringNode:
    @staticmethod
    def model_json_schema() -> dict[str, Any]:
        return {
            "$ref": "#/$defs/Node",
            "title": "Node",
            "$defs": {
                "Node": {
                    "title": "Node",
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "title": "Name"},
                        "child": {"$ref": "#/$defs/Node"},
                    },
                    "required": ["name"],
                }
            },
        }


class _IntNode:
    @staticmethod
    def model_json_schema() -> dict[str, Any]:
        return {
            "$ref": "#/$defs/Node",
            "$defs": {
                "Node": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "integer"},
                        "child": {"$ref": "#/$defs/Node"},
                    },
                    "required": ["name"],
                }
            },
        }


def test_circular_refs_resolve_and_colliding_names_are_renamed() -> None:
    def walk(node: _StringNode, other: _IntNode) -> None:
        """Walk."""

    tool = schema(walk)
    params = tool.parameters
    assert params["properties"]["node"]["$ref"] == "#/$defs/Node"
    assert params["properties"]["other"]["$ref"] == "#/$defs/Node_2"
    assert "$defs" not in params["properties"]["node"]
    assert params["$defs"]["Node"]["properties"]["child"]["$ref"] == "#/$defs/Node"
    assert params["$defs"]["Node_2"]["properties"]["child"]["$ref"] == "#/$defs/Node_2"
    assert "title" not in json.dumps(params)

    ok = tool.validate({"node": {"name": "a", "child": {"name": "b"}}, "other": {"name": 1}})
    assert isinstance(ok, ValidationSuccess)
    bad = tool.validate({"node": {"name": 1}, "other": {"name": 1}})
    assert isinstance(bad, ValidationFailure)
    json.dumps(tool.to_mcp())


def test_pydantic_recursive_model_ref_resolves() -> None:
    pytest = __import__("pytest")
    pydantic = pytest.importorskip("pydantic")

    class Node(pydantic.BaseModel):
        name: str
        child: Node | None = None

    def walk(node: Node) -> str:
        """Walk."""
        return node.name

    walk.__annotations__ = {"node": Node, "return": str}
    tool = schema(walk)
    assert tool.parameters["properties"]["node"]["$ref"] == "#/$defs/Node"
    assert "Node" in tool.parameters["$defs"]
    assert isinstance(tool.validate({"node": {"name": 1}}), ValidationFailure)
    present = tool.validate({"node": {"name": "a", "child": {"name": "b", "child": None}}})
    assert isinstance(present, ValidationSuccess)
