from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Literal

import fixtures

from toolschema import Field, ToolDefinition, ValidationFailure, ValidationSuccess, schema
from toolschema.adapters._inline_refs import inline_refs

SNAPSHOTS = Path(__file__).parent / "snapshots"


@dataclass
class _StrictItem:
    name: str
    note: str = "x"


def _take_strict_item(item: _StrictItem) -> None:
    """Take an item."""


def _load_snapshot(name: str) -> dict:
    return json.loads((SNAPSHOTS / name).read_text(encoding="utf-8"))


def test_add_openai_snapshot() -> None:
    assert schema(fixtures.add).to_openai() == _load_snapshot("add_openai.json")


def test_openai_strict_requires_nested_properties() -> None:
    item = schema(_take_strict_item).to_openai(strict=True)["function"]["parameters"]["properties"][
        "item"
    ]
    assert item["additionalProperties"] is False
    assert item["required"] == ["name", "note"]
    assert item["properties"]["note"]["default"] == "x"

    def labels(tags: dict[str, str]) -> None:
        """Label items."""

    tags = schema(labels).to_openai(strict=True)["function"]["parameters"]["properties"]["tags"]
    assert tags["additionalProperties"] == {"type": "string"}
    assert "required" not in tags


def test_add_openai_strict_snapshot() -> None:
    t = schema(fixtures.add)
    result = t.to_openai(strict=True)
    assert result == _load_snapshot("add_openai_strict.json")
    params = result["function"]["parameters"]
    assert params["additionalProperties"] is False
    assert set(params["required"]) == {"a", "b"}


def test_add_mcp_snapshot() -> None:
    result = schema(fixtures.add).to_mcp()
    assert result == _load_snapshot("add_mcp.json")
    assert "$ref" not in json.dumps(result)


def test_add_anthropic_snapshot() -> None:
    assert schema(fixtures.add).to_anthropic() == _load_snapshot("add_anthropic.json")


def test_add_gemini_snapshot() -> None:
    assert schema(fixtures.add).to_gemini() == _load_snapshot("add_gemini.json")


def test_gemini_tuple_uses_items_and_optional_is_nullable() -> None:
    def pair(value: tuple[int, str]) -> None:
        """Pair two values."""

    prop = schema(pair).to_gemini()["parameters"]["properties"]["value"]
    assert "prefixItems" not in prop
    assert prop["items"] == {"anyOf": [{"type": "INTEGER"}, {"type": "STRING"}]}
    assert prop["minItems"] == 2
    assert prop["maxItems"] == 2

    def same(value: tuple[int, int]) -> None:
        """Two ints."""

    same_prop = schema(same).to_gemini()["parameters"]["properties"]["value"]
    assert same_prop["items"] == {"type": "INTEGER"}

    def rows(items: list[tuple[int, str]]) -> None:
        """Rows of pairs."""

    nested = schema(rows).to_gemini()["parameters"]["properties"]["items"]["items"]
    assert nested["items"] == {"anyOf": [{"type": "INTEGER"}, {"type": "STRING"}]}

    def greet(name: str | None = None) -> None:
        """Greet."""

    optional = schema(greet).to_gemini()["parameters"]["properties"]["name"]
    assert optional["type"] == "STRING"
    assert optional["nullable"] is True
    assert optional["default"] is None
    assert "anyOf" not in optional
    assert "NULL" not in json.dumps(optional)

    def city(name: Annotated[str | None, Field(min_length=1)]) -> None:
        """City."""

    limited = schema(city).to_gemini()["parameters"]["properties"]["name"]
    assert limited["type"] == "STRING"
    assert limited["nullable"] is True
    assert limited["minLength"] == 1

    def either(value: int | str | None) -> None:
        """Either."""

    union = schema(either).to_gemini()["parameters"]["properties"]["value"]
    assert union["nullable"] is True
    assert union["anyOf"] == [{"type": "INTEGER"}, {"type": "STRING"}]

    closed = ToolDefinition(
        name="pair",
        description="Pair.",
        parameters={
            "type": "object",
            "properties": {
                "value": {
                    "type": "array",
                    "prefixItems": [{"type": "integer"}, {"type": "string"}],
                    "items": False,
                }
            },
            "required": ["value"],
        },
    )
    closed_prop = closed.to_gemini()["parameters"]["properties"]["value"]
    assert "prefixItems" not in closed_prop
    assert closed_prop["items"] == {"anyOf": [{"type": "INTEGER"}, {"type": "STRING"}]}
    assert closed_prop["maxItems"] == 2
    assert closed_prop.get("items") is not False


def test_gemini_literal_null_is_nullable() -> None:
    def choose(mode: Literal["a", None] = None, count: Literal[1, None] = None) -> None:
        """Choose."""

    tool = schema(choose)
    assert isinstance(tool.validate({}), ValidationSuccess)
    assert isinstance(tool.validate({"mode": "a", "count": 1}), ValidationSuccess)
    assert isinstance(tool.validate({"mode": "b"}), ValidationFailure)

    props = tool.to_gemini()["parameters"]["properties"]
    assert props["mode"] == {
        "type": "STRING",
        "enum": ["a"],
        "nullable": True,
        "default": None,
    }
    assert props["count"]["type"] == "INTEGER"
    assert props["count"]["enum"] == [1]
    assert props["count"]["nullable"] is True
    assert None not in props["count"]["enum"]


class _UnionChoice:
    @staticmethod
    def model_json_schema() -> dict:
        return {
            "oneOf": [{"type": "string"}, {"type": "integer"}],
            "allOf": [{"type": "object", "properties": {"n": {"type": "integer"}}}],
        }


def test_gemini_uppercases_union_keywords() -> None:
    def pick(value: _UnionChoice) -> None:
        """Pick one."""

    prop = schema(pick).to_gemini()["parameters"]["properties"]["value"]
    assert prop["oneOf"] == [{"type": "STRING"}, {"type": "INTEGER"}]
    assert prop["allOf"][0]["type"] == "OBJECT"
    assert prop["allOf"][0]["properties"]["n"]["type"] == "INTEGER"


def test_openai_strict_leaves_instance_values_alone() -> None:
    tool = ToolDefinition(
        name="record",
        description="Record a value.",
        parameters={
            "type": "object",
            "properties": {
                "meta": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                    "default": {"type": "object", "properties": {"a": 1}},
                    "const": {"type": "object", "properties": {"b": 2}},
                    "enum": [{"type": "object", "properties": {"c": 3}}],
                }
            },
            "additionalProperties": False,
            "required": ["meta"],
        },
    )
    meta = tool.to_openai(strict=True)["function"]["parameters"]["properties"]["meta"]
    assert meta["default"] == {"type": "object", "properties": {"a": 1}}
    assert meta["const"] == {"type": "object", "properties": {"b": 2}}
    assert meta["enum"] == [{"type": "object", "properties": {"c": 3}}]
    assert meta["additionalProperties"] is False
    assert meta["required"] == ["name"]


def test_search_github_mcp_snapshot() -> None:
    result = schema(fixtures.search_github).to_mcp()
    assert result == _load_snapshot("search_github_mcp.json")
    assert "outputSchema" in result
    assert "$ref" not in json.dumps(result)


def test_search_github_openai_snapshot() -> None:
    assert schema(fixtures.search_github).to_openai() == _load_snapshot("search_github_openai.json")


def test_mcp_no_ref_when_inline_refs_true() -> None:
    def fn(value: Annotated[str, Field(description="x")]) -> str:
        return value

    result = schema(fn).to_mcp(inline_refs=True)
    assert "$ref" not in json.dumps(result)


def test_inline_refs_flattens_defs() -> None:
    schema_with_ref = {
        "type": "object",
        "properties": {
            "item": {"$ref": "#/$defs/Item"},
        },
        "$defs": {
            "Item": {"type": "string", "minLength": 1},
        },
    }
    result = inline_refs(schema_with_ref)
    assert result == {
        "type": "object",
        "properties": {
            "item": {"type": "string", "minLength": 1},
        },
    }
    assert "$defs" not in result


def test_anthropic_moves_constraints_to_description() -> None:
    def fn(city: Annotated[str, Field(description="City", min_length=1)]) -> None:
        pass

    result = schema(fn).to_anthropic()
    prop = result["input_schema"]["properties"]["city"]
    assert "minLength" not in prop
    assert "min length 1" in prop["description"]


def test_output_schema_from_return_type() -> None:
    t = schema(fixtures.search_github)
    assert t.output == {"type": "array", "items": {"type": "object"}}
