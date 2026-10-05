from __future__ import annotations

from typing import Annotated

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


def test_validate_complex_constraints() -> None:
    import complex_fixtures

    tool = schema(complex_fixtures.search_products)
    ok = tool.validate({"query": "laptop", "category": "computers"})
    assert isinstance(ok, ValidationSuccess)

    bad = tool.validate({"query": "", "category": "computers"})
    assert isinstance(bad, ValidationFailure)


def test_validate_const_keyword() -> None:
    """``const`` is an assertion, including when it sits next to ``type``."""
    parameters = {
        "type": "object",
        "properties": {
            "kind": {"const": "a", "type": "string"},
        },
        "required": ["kind"],
        "additionalProperties": False,
    }
    assert isinstance(validate_arguments({"kind": "a"}, parameters), ValidationSuccess)

    rejected = validate_arguments({"kind": "nope"}, parameters)
    assert isinstance(rejected, ValidationFailure)
    assert any(issue.kind is ValidationIssueKind.CONST for issue in rejected.issues)
    assert any(issue.path == ("kind",) for issue in rejected.issues)

    numbered = {
        "type": "object",
        "properties": {"n": {"const": 1, "type": "integer"}},
        "required": ["n"],
        "additionalProperties": False,
    }
    assert isinstance(validate_arguments({"n": 1}, numbered), ValidationSuccess)
    fractional = validate_arguments({"n": 1.0}, numbered)
    assert isinstance(fractional, ValidationFailure)
    assert any(issue.kind is ValidationIssueKind.TYPE for issue in fractional.issues)

    bare_number = {
        "type": "object",
        "properties": {"n": {"const": 1}},
        "required": ["n"],
        "additionalProperties": False,
    }
    assert isinstance(validate_arguments({"n": 1.0}, bare_number), ValidationSuccess)
    boolean = validate_arguments({"n": True}, bare_number)
    assert isinstance(boolean, ValidationFailure)
    assert any(issue.kind is ValidationIssueKind.CONST for issue in boolean.issues)

    flags = {
        "type": "object",
        "properties": {"ok": {"const": True, "type": "boolean"}},
        "required": ["ok"],
        "additionalProperties": False,
    }
    assert isinstance(validate_arguments({"ok": True}, flags), ValidationSuccess)
    assert isinstance(validate_arguments({"ok": 1}, flags), ValidationFailure)
    assert isinstance(validate_arguments({"ok": False}, flags), ValidationFailure)

    nulls = {
        "type": "object",
        "properties": {"value": {"const": None}},
        "required": ["value"],
        "additionalProperties": False,
    }
    assert isinstance(validate_arguments({"value": None}, nulls), ValidationSuccess)
    assert isinstance(validate_arguments({"value": "null"}, nulls), ValidationFailure)

    structured = {
        "type": "object",
        "properties": {
            "payload": {"const": {"n": 1, "items": [True, "a"]}},
        },
        "required": ["payload"],
        "additionalProperties": False,
    }
    assert isinstance(
        validate_arguments({"payload": {"items": [True, "a"], "n": 1.0}}, structured),
        ValidationSuccess,
    )
    reordered_array = validate_arguments(
        {"payload": {"n": 1, "items": ["a", True]}},
        structured,
    )
    assert isinstance(reordered_array, ValidationFailure)
    integer_for_bool = validate_arguments(
        {"payload": {"n": 1, "items": [1, "a"]}},
        structured,
    )
    assert isinstance(integer_for_bool, ValidationFailure)

    limited = {
        "type": "object",
        "properties": {"name": {"const": "ab", "minLength": 3, "type": "string"}},
        "required": ["name"],
        "additionalProperties": False,
    }
    too_short = validate_arguments({"name": "ab"}, limited)
    assert isinstance(too_short, ValidationFailure)
    assert any(issue.kind is ValidationIssueKind.CONSTRAINT for issue in too_short.issues)

    tags = {
        "type": "object",
        "properties": {
            "tags": {"type": "array", "items": {"const": "a"}},
        },
        "required": ["tags"],
        "additionalProperties": False,
    }
    assert isinstance(validate_arguments({"tags": ["a", "a"]}, tags), ValidationSuccess)
    bad_tag = validate_arguments({"tags": ["a", "b"]}, tags)
    assert isinstance(bad_tag, ValidationFailure)
    assert any(issue.path == ("tags", 1) for issue in bad_tag.issues)


def test_validate_const_beside_anyof() -> None:
    parameters = {
        "type": "object",
        "properties": {
            "value": {
                "anyOf": [{"type": "string"}, {"type": "integer"}],
                "const": "a",
            }
        },
        "required": ["value"],
        "additionalProperties": False,
    }
    assert isinstance(validate_arguments({"value": "a"}, parameters), ValidationSuccess)

    other_string = validate_arguments({"value": "b"}, parameters)
    assert isinstance(other_string, ValidationFailure)
    assert any(issue.kind is ValidationIssueKind.CONST for issue in other_string.issues)

    other_branch = validate_arguments({"value": 1}, parameters)
    assert isinstance(other_branch, ValidationFailure)


def test_validate_const_discriminated_union() -> None:
    """Pydantic emits ``const`` for a one-value ``Literal`` on each union arm."""
    parameters = {
        "type": "object",
        "properties": {
            "item": {
                "anyOf": [
                    {
                        "type": "object",
                        "properties": {
                            "kind": {"const": "a", "type": "string"},
                            "x": {"type": "integer"},
                        },
                        "required": ["kind", "x"],
                        "additionalProperties": False,
                    },
                    {
                        "type": "object",
                        "properties": {
                            "kind": {"const": "b", "type": "string"},
                            "y": {"type": "string"},
                        },
                        "required": ["kind", "y"],
                        "additionalProperties": False,
                    },
                ]
            }
        },
        "required": ["item"],
        "additionalProperties": False,
    }
    assert isinstance(
        validate_arguments({"item": {"kind": "a", "x": 1}}, parameters),
        ValidationSuccess,
    )
    assert isinstance(
        validate_arguments({"item": {"kind": "b", "y": "hi"}}, parameters),
        ValidationSuccess,
    )

    wrong_tag = validate_arguments({"item": {"kind": "nope", "x": 1}}, parameters)
    assert isinstance(wrong_tag, ValidationFailure)

    other_arm = validate_arguments({"item": {"kind": "a", "y": "hi"}}, parameters)
    assert isinstance(other_arm, ValidationFailure)


def test_validate_pydantic_literal_const() -> None:
    pytest = __import__("pytest")
    pydantic = pytest.importorskip("pydantic")
    from typing import Literal

    class A(pydantic.BaseModel):
        kind: Literal["a"]
        x: int

    class B(pydantic.BaseModel):
        kind: Literal["b"]
        y: str

    def handle(item: A | B) -> str:
        """Handle a tagged item."""
        return item.kind

    handle.__annotations__ = {"item": A | B, "return": str}
    tool = schema(handle)
    kind_a = tool.parameters["properties"]["item"]["anyOf"][0]["properties"]["kind"]
    assert kind_a["const"] == "a"

    assert isinstance(tool.validate({"item": {"kind": "a", "x": 1}}), ValidationSuccess)
    assert isinstance(tool.validate({"item": {"kind": "b", "y": "hi"}}), ValidationSuccess)

    wrong_tag = tool.validate({"item": {"kind": "nope", "x": 1}})
    assert isinstance(wrong_tag, ValidationFailure)

    swapped = tool.validate({"item": {"kind": "a", "y": "hi"}})
    assert isinstance(swapped, ValidationFailure)
