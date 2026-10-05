from __future__ import annotations

import json
from typing import Annotated, Any

import fixtures

from toolschema import Field, schema
from toolschema._validate import (
    ValidationFailure,
    ValidationIssueKind,
    ValidationSuccess,
    validate_arguments,
)


def test_validate_success_with_defaults() -> None:
    tool = schema(fixtures.add)
    result = tool.validate({"a": 2})
    assert isinstance(result, ValidationSuccess)
    assert result.value == {"a": 2, "b": 1}


def test_validate_success_all_required() -> None:
    tool = schema(fixtures.add)
    result = tool.validate({"a": 2, "b": 3})
    assert isinstance(result, ValidationSuccess)
    assert result.value == {"a": 2, "b": 3}


def test_validate_missing_required() -> None:
    tool = schema(fixtures.add)
    result = tool.validate({})
    assert isinstance(result, ValidationFailure)
    assert any(issue.path == ("a",) for issue in result.issues)


def test_validate_wrong_type() -> None:
    tool = schema(fixtures.add)
    result = tool.validate({"a": "x"})
    assert isinstance(result, ValidationFailure)
    assert any("integer" in issue.message for issue in result.issues)


def test_validate_additional_properties_rejected() -> None:
    tool = schema(fixtures.add)
    result = tool.validate({"a": 1, "extra": True})
    assert isinstance(result, ValidationFailure)
    assert any(issue.path == ("extra",) for issue in result.issues)


def test_validate_fixed_tuple_prefix_items() -> None:
    def pair(value: tuple[int, str]) -> str:
        """Format a pair."""
        return f"{value[0]}:{value[1]}"

    tool = schema(pair)
    ok = tool.validate({"value": [1, "a"]})
    assert isinstance(ok, ValidationSuccess)
    assert ok.value == {"value": [1, "a"]}

    swapped = tool.validate({"value": ["a", 1]})
    assert isinstance(swapped, ValidationFailure)
    assert any(issue.path == ("value", 0) for issue in swapped.issues)
    assert any(issue.path == ("value", 1) for issue in swapped.issues)

    short = tool.validate({"value": [1]})
    assert isinstance(short, ValidationFailure)
    assert any("minItems" in issue.message for issue in short.issues)

    long = tool.validate({"value": [1, "a", True]})
    assert isinstance(long, ValidationFailure)
    assert any("maxItems" in issue.message for issue in long.issues)

    boolean = tool.validate({"value": [True, "a"]})
    assert isinstance(boolean, ValidationFailure)
    assert any(issue.path == ("value", 0) for issue in boolean.issues)


def test_validate_tuple_nested_in_list() -> None:
    def rows(items: list[tuple[int, str]]) -> int:
        """Count rows."""
        return len(items)

    tool = schema(rows)
    ok = tool.validate({"items": [[1, "a"], [2, "b"]]})
    assert isinstance(ok, ValidationSuccess)

    bad = tool.validate({"items": [[1, 2]]})
    assert isinstance(bad, ValidationFailure)
    assert any(issue.path == ("items", 0, 1) for issue in bad.issues)


def test_validate_variadic_tuple_items() -> None:
    def coords(points: tuple[int, ...]) -> int:
        """Count points."""
        return len(points)

    tool = schema(coords)
    ok = tool.validate({"points": [1, 2, 3]})
    assert isinstance(ok, ValidationSuccess)

    bad = tool.validate({"points": [1, "x"]})
    assert isinstance(bad, ValidationFailure)
    assert any(issue.path == ("points", 1) for issue in bad.issues)


def test_validate_constraints_beside_anyof() -> None:
    """Field constraints on an optional annotation sit next to anyOf.

    JSON Schema applies those sibling keywords in addition to the branch
    match. ``""`` is a string, and it still violates ``minLength``.
    """

    def search(
        query: Annotated[str | None, Field(min_length=1, pattern=r"^[a-z]+$")] = None,
    ) -> str:
        """Search."""
        return query or ""

    tool = schema(search)
    prop = tool.parameters["properties"]["query"]
    assert prop["minLength"] == 1
    assert prop["pattern"] == r"^[a-z]+$"
    assert "anyOf" in prop

    omitted = tool.validate({})
    assert isinstance(omitted, ValidationSuccess)
    assert omitted.value == {"query": None}

    assert isinstance(tool.validate({"query": None}), ValidationSuccess)
    assert isinstance(tool.validate({"query": "ab"}), ValidationSuccess)

    empty = tool.validate({"query": ""})
    assert isinstance(empty, ValidationFailure)
    assert any(issue.kind is ValidationIssueKind.CONSTRAINT for issue in empty.issues)
    assert any(issue.path == ("query",) for issue in empty.issues)

    uppercase = tool.validate({"query": "AB"})
    assert isinstance(uppercase, ValidationFailure)
    assert any("pattern" in issue.message for issue in uppercase.issues)

    def set_limit(limit: Annotated[int | None, Field(ge=1, le=10)] = None) -> int:
        """Set a limit."""
        return limit or 0

    limits = schema(set_limit)
    assert isinstance(limits.validate({"limit": None}), ValidationSuccess)
    assert isinstance(limits.validate({"limit": 1}), ValidationSuccess)
    assert isinstance(limits.validate({"limit": 10}), ValidationSuccess)
    low = limits.validate({"limit": 0})
    assert isinstance(low, ValidationFailure)
    assert any(issue.kind is ValidationIssueKind.CONSTRAINT for issue in low.issues)
    high = limits.validate({"limit": 11})
    assert isinstance(high, ValidationFailure)

    def on_branch(
        query: Annotated[str, Field(min_length=1)] | None = None,
    ) -> str:
        """Search with the constraint inside the string branch."""
        return query or ""

    branched = schema(on_branch)
    assert isinstance(branched.validate({"query": ""}), ValidationFailure)
    assert isinstance(branched.validate({"query": None}), ValidationSuccess)


def test_validate_enum_beside_anyof() -> None:
    parameters = {
        "type": "object",
        "properties": {
            "value": {
                "anyOf": [{"type": "string"}, {"type": "integer"}],
                "enum": ["a", 1],
            }
        },
        "required": ["value"],
        "additionalProperties": False,
    }

    assert isinstance(validate_arguments({"value": "a"}, parameters), ValidationSuccess)
    assert isinstance(validate_arguments({"value": 1}, parameters), ValidationSuccess)

    rejected = validate_arguments({"value": "b"}, parameters)
    assert isinstance(rejected, ValidationFailure)
    assert any(issue.kind is ValidationIssueKind.ENUM for issue in rejected.issues)

    wrong_type = validate_arguments({"value": True}, parameters)
    assert isinstance(wrong_type, ValidationFailure)

    typed = {
        "type": "object",
        "properties": {
            "value": {
                "anyOf": [{"minLength": 1}],
                "type": "string",
            }
        },
        "required": ["value"],
        "additionalProperties": False,
    }
    assert isinstance(validate_arguments({"value": "ab"}, typed), ValidationSuccess)
    not_a_string = validate_arguments({"value": 1}, typed)
    assert isinstance(not_a_string, ValidationFailure)
    assert any(issue.kind == ValidationIssueKind.TYPE for issue in not_a_string.issues)


def test_validate_const() -> None:
    """JSON Schema ``const`` is exact equality, with JSON number rules.

    Booleans are not numbers. ``1`` and ``1.0`` are equal.
    """
    parameters = {
        "type": "object",
        "properties": {
            "kind": {"const": "a", "type": "string"},
            "flag": {"const": True},
            "count": {"type": "number", "const": 1},
            "pair": {"const": [1, {"ok": False}]},
        },
        "required": ["kind"],
        "additionalProperties": False,
    }

    ok = validate_arguments(
        {"kind": "a", "flag": True, "count": 1.0, "pair": [1.0, {"ok": False}]},
        parameters,
    )
    assert isinstance(ok, ValidationSuccess)

    wrong = validate_arguments({"kind": "nope"}, parameters)
    assert isinstance(wrong, ValidationFailure)
    assert any(
        issue.kind is ValidationIssueKind.CONST and issue.path == ("kind",)
        for issue in wrong.issues
    )

    boolean = validate_arguments({"kind": "a", "flag": 1, "count": True}, parameters)
    assert isinstance(boolean, ValidationFailure)
    assert any(
        issue.path == ("flag",) and issue.kind is ValidationIssueKind.CONST
        for issue in boolean.issues
    )
    assert any(
        issue.path == ("count",) and issue.kind is ValidationIssueKind.CONST
        for issue in boolean.issues
    )

    pair = validate_arguments({"kind": "a", "pair": [True, {"ok": False}]}, parameters)
    assert isinstance(pair, ValidationFailure)
    assert any(
        issue.path == ("pair",) and issue.kind is ValidationIssueKind.CONST for issue in pair.issues
    )


class _ConstA:
    @staticmethod
    def model_json_schema() -> dict[str, Any]:
        return {
            "title": "A",
            "type": "object",
            "properties": {
                "kind": {"const": "a", "title": "Kind", "type": "string"},
                "x": {"title": "X", "type": "integer"},
            },
            "required": ["kind", "x"],
        }


class _ConstB:
    @staticmethod
    def model_json_schema() -> dict[str, Any]:
        return {
            "title": "B",
            "type": "object",
            "properties": {
                "kind": {"const": "b", "title": "Kind", "type": "string"},
                "y": {"title": "Y", "type": "string"},
            },
            "required": ["kind", "y"],
        }


def test_validate_const_on_model_union() -> None:
    """Pydantic emits ``const`` for Literal fields. A model union must not accept every arm."""

    def take(item: _ConstA | _ConstB) -> str:
        """Take one variant."""
        return "ok"

    tool = schema(take)
    arms = tool.parameters["properties"]["item"]["anyOf"]
    assert arms[0]["properties"]["kind"]["const"] == "a"
    assert arms[1]["properties"]["kind"]["const"] == "b"
    assert "title" not in arms[0]

    assert isinstance(tool.validate({"item": {"kind": "a", "x": 1}}), ValidationSuccess)
    assert isinstance(tool.validate({"item": {"kind": "b", "y": "hi"}}), ValidationSuccess)

    wrong_kind = tool.validate({"item": {"kind": "nope", "x": 1}})
    assert isinstance(wrong_kind, ValidationFailure)

    wrong_shape = tool.validate({"item": {"kind": "a", "y": "hi"}})
    assert isinstance(wrong_shape, ValidationFailure)

    def take_one(item: _ConstA) -> str:
        """Take the first variant."""
        return "ok"

    one = schema(take_one)
    assert one.parameters["properties"]["item"]["properties"]["kind"]["const"] == "a"
    bad = one.validate({"item": {"kind": "nope", "x": 1}})
    assert isinstance(bad, ValidationFailure)
    assert any(
        issue.kind is ValidationIssueKind.CONST and issue.path == ("item", "kind")
        for issue in bad.issues
    )
    assert isinstance(one.validate({"item": {"kind": "a", "x": 1}}), ValidationSuccess)


def test_validate_pydantic_literal_uses_const() -> None:
    pytest = __import__("pytest")
    pydantic = pytest.importorskip("pydantic")
    from typing import Literal

    class LetterA(pydantic.BaseModel):
        kind: Literal["a"]
        x: int

    class LetterB(pydantic.BaseModel):
        kind: Literal["b"]
        y: str

    def take(item: Any) -> str:
        """Take one variant."""
        return ""

    take.__annotations__ = {"item": LetterA | LetterB, "return": str}
    tool = schema(take)
    encoded = json.dumps(tool.parameters)
    assert '"const": "a"' in encoded
    assert '"const": "b"' in encoded
    assert isinstance(tool.validate({"item": {"kind": "a", "x": 1}}), ValidationSuccess)
    assert isinstance(tool.validate({"item": {"kind": "b", "y": "hi"}}), ValidationSuccess)
    assert isinstance(tool.validate({"item": {"kind": "nope", "x": 1}}), ValidationFailure)
    assert isinstance(tool.validate({"item": {"kind": "a", "y": "hi"}}), ValidationFailure)


def test_validate_complex_constraints() -> None:
    import complex_fixtures

    tool = schema(complex_fixtures.search_products)
    ok = tool.validate({"query": "laptop", "category": "computers"})
    assert isinstance(ok, ValidationSuccess)

    bad = tool.validate({"query": "", "category": "computers"})
    assert isinstance(bad, ValidationFailure)
