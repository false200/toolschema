from __future__ import annotations

import fixtures

from toolschema import JSONSchemaOptions, schema


def test_standard_protocol_shape() -> None:
    tool = schema(fixtures.add)
    standard = tool.standard["~standard"]

    assert standard["version"] == 1
    assert standard["vendor"] == "toolschema"
    assert callable(standard["validate"])
    assert callable(standard["jsonSchema"]["input"])
    assert callable(standard["jsonSchema"]["output"])


def test_standard_json_schema_input() -> None:
    tool = schema(fixtures.add)
    payload = tool.standard["~standard"]["jsonSchema"]["input"](
        JSONSchemaOptions(target="draft-2020-12")
    )
    assert payload["type"] == "object"
    assert "$schema" not in payload
    assert payload["properties"]["a"]["type"] == "integer"


def test_standard_json_schema_output() -> None:
    tool = schema(fixtures.search_github)
    payload = tool.standard["~standard"]["jsonSchema"]["output"](
        JSONSchemaOptions(target="draft-2020-12")
    )
    assert payload == {"type": "array", "items": {"type": "object"}}


def test_standard_validate_delegates() -> None:
    tool = schema(fixtures.add)
    result = tool.standard["~standard"]["validate"]({"a": 4})
    assert result.value == {"a": 4, "b": 1}
    assert result.issues is None


def test_standard_json_schema_dict_options() -> None:
    tool = schema(fixtures.add)
    payload = tool.standard["~standard"]["jsonSchema"]["input"]({"target": "draft-07"})
    assert payload["properties"]["a"]["type"] == "integer"
