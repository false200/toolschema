from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import fixtures

from toolschema import Field, schema
from toolschema.adapters._inline_refs import inline_refs

SNAPSHOTS = Path(__file__).parent / "snapshots"


def _load_snapshot(name: str) -> dict:
    return json.loads((SNAPSHOTS / name).read_text(encoding="utf-8"))


def test_add_openai_snapshot() -> None:
    assert schema(fixtures.add).to_openai() == _load_snapshot("add_openai.json")


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
