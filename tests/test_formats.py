"""JSON Schema format checks follow RFC 3339 and RFC 4122, not Python parsers."""

from __future__ import annotations

import pytest

from toolschema._validate import ValidationFailure, ValidationSuccess, validate_arguments

# Drawn from the JSON Schema Test Suite draft 2020-12 optional format tests.
# Non-string values are covered once below, because format does not apply to
# them. Repeated per-month length checks are reduced to January, February,
# April, and December.
_DATE_TIME_CASES: tuple[tuple[str, bool], ...] = (
    ("1963-06-19T08:30:06.283185Z", True),
    ("1963-06-19T08:30:06Z", True),
    ("1937-01-01T12:00:27.87+00:20", True),
    ("1990-12-31T15:59:50.123-08:00", True),
    ("1998-12-31T23:59:60Z", True),
    ("1998-12-31T15:59:60.123-08:00", True),
    ("1998-12-31T23:59:61Z", False),
    ("1998-12-31T23:58:60Z", False),
    ("1998-12-31T22:59:60Z", False),
    ("1990-02-31T15:59:59.123-08:00", False),
    ("1990-12-31T15:59:59-24:00", False),
    ("1963-06-19T08:30:06.28123+01:00Z", False),
    ("1990-12-31T24:00:00Z", False),
    ("1990-12-31T15:60:00Z", False),
    ("1990-12-31T10:00:00+10:60", False),
    ("06/19/1963 08:30:06 PST", False),
    ("1963-06-19t08:30:06.283185z", True),
    ("2013-350T01:01:01", False),
    ("1963-6-19T08:30:06.283185Z", False),
    ("1963-06-1T08:30:06.283185Z", False),
    ("1963-06-1\u09eaT00:00:00Z", False),
    ("1963-06-11T0\u09ea:00:00Z", False),
    ("+11963-06-19T08:30:06.283185Z", False),
    ("1985-04-12T23:20:50+01", False),
    ("2016-12-31T24:59:60+01:00", False),
    ("1985-04-12T00:59:59.999999999999999Z", True),
    ("1985-04-12T23:20:50Z\n", False),
    ("1985-04-12T23:20Z", False),
    ("1985-04-12T23:20:50Ztail", False),
    ("1985-04-12T23:60:00+00:01", False),
    ("2021-02-28T00:00:00Z", True),
    ("2020-02-30T00:00:00Z", False),
    ("2021-02-29T00:00:00Z", False),
    ("2020-02-29T00:00:00Z", True),
    ("0100-02-29T00:00:00Z", False),
    ("0400-02-29T00:00:00Z", True),
    ("2100-02-29T00:00:00Z", False),
    # Python's fromisoformat accepts these; RFC 3339 does not.
    ("2020-01-01", False),
    ("20200101T000000", False),
    ("2020-01-01T00:00:00", False),
    ("2020-01-01 00:00:00Z", False),
)

_DATE_CASES: tuple[tuple[str, bool], ...] = (
    ("1963-06-19", True),
    ("2020-01-31", True),
    ("2020-01-32", False),
    ("2021-02-28", True),
    ("2020-02-30", False),
    ("2020-02-29", True),
    ("2021-02-29", False),
    ("2020-04-30", True),
    ("2020-04-31", False),
    ("2020-12-31", True),
    ("2020-12-32", False),
    ("06/19/1963", False),
    ("2013-350", False),
    ("1998-1-20", False),
    ("1998-01-1", False),
    ("1998-13-01", False),
    ("1963-06-1\u09ea", False),
    ("2020-0\u09ea-01", False),
    ("20230328", False),
    ("2023-W01", False),
    ("2023-W13-2", False),
    ("2022W527", False),
    ("2020-11-28T23:55:45Z", False),
    ("0100-02-29", False),
    ("0400-02-29", True),
    ("2100-02-29", False),
    (" 2024-01-15", False),
    ("2024-01-15 ", False),
    ("2024-00-15", False),
    ("2024-01-00", False),
    ("", False),
    ("2020 -01-01", False),
    ("2020-01-01X", False),
    ("2020-01-01Z", False),
    ("2020-01-01 00:00:00Z", False),
    ("0001-01-01", True),
    ("20-01-01", False),
    ("998-01-01", False),
    ("12020-01-01", False),
    ("+2020-01-01", False),
    ("-2020-01-01", False),
    ("\u09e8020-01-01", False),
    ("YYYY-01-01", False),
    ("2020-001-01", False),
    ("2020:01:01", False),
    ("2020.01.01", False),
    ("2020 01 01", False),
    ("2020-01/01", False),
    ("2020--01-01", False),
    ("2020-01--01", False),
    ("1582-10-10", True),
    ("2147483648-01-01", False),
    ("2020-01-0:", False),
    ("2020\u201301\u201301", False),
    ("2020-01-01\u0000", False),
)

_TIME_CASES: tuple[tuple[str, bool], ...] = (
    ("08:30:06Z", True),
    ("008:030:006Z", False),
    ("8:3:6Z", False),
    ("8:0030:6Z", False),
    ("23:59:60Z", True),
    ("22:59:60Z", False),
    ("23:58:60Z", False),
    ("23:59:60+00:00", True),
    ("22:59:60+00:00", False),
    ("23:58:60+00:00", False),
    ("01:29:60+01:30", True),
    ("23:29:60+23:30", True),
    ("23:59:60+01:00", False),
    ("23:59:60+00:30", False),
    ("15:59:60-08:00", True),
    ("00:29:60-23:30", True),
    ("23:59:60-01:00", False),
    ("23:59:60-00:30", False),
    ("23:20:50.52Z", True),
    ("08:30:06.283185Z", True),
    ("08:30:06+00:20", True),
    ("08:30:06-08:00", True),
    ("12:34:56-00:00", True),
    ("08:30:06-8:000", False),
    ("08:30:06z", True),
    ("24:00:00Z", False),
    ("00:60:00Z", False),
    ("00:00:61Z", False),
    ("01:02:03+24:00", False),
    ("01:02:03+00:60", False),
    ("01:02:03Z+00:30", False),
    ("08:30:06 PST", False),
    ("01:01:01,1111", False),
    ("12:00:00", False),
    ("12:00:00.52", False),
    ("1\u09e8:00:00Z", False),
    ("08:30:06#00:20", False),
    ("ab:cd:ef", False),
    ("2020-11-28T23:55:45Z", False),
    ("08:30:06+0130", False),
    ("08:30:06+01", False),
    ("08:30:06Z\n", False),
    ("24:59:00+01:00", False),
    ("23:60:00+00:01", False),
    ("00:59:59.999999999999999Z", True),
    ("08:30:06.Z", False),
    ("12:00Z", False),
    ("08:30:06,5Z", False),
    (" 08:30:06Z", False),
)

_UUID_CASES: tuple[tuple[str, bool], ...] = (
    ("2EB8AA08-AA98-11EA-B4AA-73B441D16380", True),
    ("2eb8aa08-aa98-11ea-b4aa-73b441d16380", True),
    ("2eb8aa08-AA98-11ea-B4Aa-73B441D16380", True),
    ("00000000-0000-0000-0000-000000000000", True),
    ("2eb8aa08-aa98-11ea-b4aa-73b441d1638", False),
    ("2eb8aa08-aa98-11ea-73b441d16380", False),
    ("2eb8aa08-aa98-11ea-b4ga-73b441d16380", False),
    ("2eb8aa08aa9811eab4aa73b441d16380", False),
    ("2eb8aa08aa98-11ea-b4aa73b441d16380", False),
    ("2eb8-aa08-aa98-11ea-b4aa73b44-1d16380", False),
    ("2eb8aa08aa9811eab4aa73b441d16380----", False),
    ("2eb8aa0-8aa98-11e-ab4aa7-3b441d16380", False),
    ("98d80576-482e-427f-8434-7f86890ab222", True),
    ("99c17cbb-656f-564a-940f-1a4568f03487", True),
    ("99c17cbb-656f-664a-940f-1a4568f03487", True),
    ("99c17cbb-656f-f64a-940f-1a4568f03487", True),
    ("urn:uuid:2eb8aa08-aa98-11ea-b4aa-73b441d16380", False),
    ("{2eb8aa08-aa98-11ea-b4aa-73b441d16380}", False),
    ("2eb8aa08-aa98-11ea-b4aa-73b441d16380-", False),
    ("\u09e8eb8aa08-aa98-11ea-b4aa-73b441d16380", False),
    ("2eb8aa08-aa98-11ea-b4aa-73b441d1_380", False),
    ("2eb8aa08-aa98-11ea-b4aa-73b441d16380\n", False),
    ("2eb8aa08-aa98-11ea-f4aa-73b441d16380", True),
)


def _parameters(format_name: str, *, typed: bool = True) -> dict[str, object]:
    value_schema: dict[str, object] = {"format": format_name}
    if typed:
        value_schema["type"] = "string"
    return {
        "type": "object",
        "properties": {"value": value_schema},
        "required": ["value"],
        "additionalProperties": False,
    }


@pytest.mark.parametrize(("value", "valid"), _DATE_TIME_CASES)
def test_date_time_format_matches_rfc3339(value: str, valid: bool) -> None:
    result = validate_arguments({"value": value}, _parameters("date-time"))
    assert isinstance(result, ValidationSuccess if valid else ValidationFailure)


@pytest.mark.parametrize(("value", "valid"), _DATE_CASES)
def test_date_format_matches_rfc3339(value: str, valid: bool) -> None:
    result = validate_arguments({"value": value}, _parameters("date"))
    assert isinstance(result, ValidationSuccess if valid else ValidationFailure)


@pytest.mark.parametrize(("value", "valid"), _TIME_CASES)
def test_time_format_matches_rfc3339(value: str, valid: bool) -> None:
    result = validate_arguments({"value": value}, _parameters("time"))
    assert isinstance(result, ValidationSuccess if valid else ValidationFailure)


@pytest.mark.parametrize(("value", "valid"), _UUID_CASES)
def test_uuid_format_matches_rfc4122(value: str, valid: bool) -> None:
    result = validate_arguments({"value": value}, _parameters("uuid"))
    assert isinstance(result, ValidationSuccess if valid else ValidationFailure)


def test_format_applies_only_to_strings_and_unknown_names_are_ignored() -> None:
    untyped = _parameters("date-time", typed=False)
    assert isinstance(validate_arguments({"value": 12}, untyped), ValidationSuccess)
    assert isinstance(validate_arguments({"value": None}, untyped), ValidationSuccess)

    email = _parameters("email")
    assert isinstance(validate_arguments({"value": "not-an-email"}, email), ValidationSuccess)

    rejected = validate_arguments({"value": "2020-01-01"}, _parameters("date-time"))
    assert isinstance(rejected, ValidationFailure)
    assert rejected.issues[0].kind.value == "constraint"
    assert "date-time" in rejected.issues[0].message
