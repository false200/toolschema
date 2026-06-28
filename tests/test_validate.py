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


def test_validate_complex_constraints() -> None:
    import complex_fixtures

    tool = schema(complex_fixtures.search_products)
    ok = tool.validate({"query": "laptop", "category": "computers"})
    assert isinstance(ok, ValidationSuccess)

    bad = tool.validate({"query": "", "category": "computers"})
    assert isinstance(bad, ValidationFailure)
