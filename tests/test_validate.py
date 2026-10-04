from __future__ import annotations

import fixtures

from toolschema import schema
from toolschema._validate import ValidationFailure, ValidationSuccess


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


def test_validate_complex_constraints() -> None:
    import complex_fixtures

    tool = schema(complex_fixtures.search_products)
    ok = tool.validate({"query": "laptop", "category": "computers"})
    assert isinstance(ok, ValidationSuccess)

    bad = tool.validate({"query": "", "category": "computers"})
    assert isinstance(bad, ValidationFailure)
