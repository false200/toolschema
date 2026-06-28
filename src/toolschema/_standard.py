from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Literal

from toolschema._schema_utils import strip_canonical_meta
from toolschema._validate import ValidationResult

STANDARD_VERSION = 1
STANDARD_VENDOR = "toolschema"

JSONSchemaTarget = Literal["draft-2020-12", "draft-07", "openapi-3.0"]


@dataclass(frozen=True)
class JSONSchemaOptions:
    target: JSONSchemaTarget = "draft-2020-12"
    library_options: dict[str, Any] | None = None


@dataclass(frozen=True)
class StandardSchemaProps:
    """Standard Schema + Standard JSON Schema properties for ecosystem interop."""

    version: int
    vendor: str
    validate: Callable[[Any], ValidationResult]
    json_schema_input: Callable[[JSONSchemaOptions], dict[str, Any]]
    json_schema_output: Callable[[JSONSchemaOptions], dict[str, Any]]

    def to_mapping(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "vendor": self.vendor,
            "validate": self.validate,
            "jsonSchema": {
                "input": self.json_schema_input,
                "output": self.json_schema_output,
            },
        }


class StandardSchemaHost(Mapping[str, Any]):
    """Mapping host exposing the ``~standard`` Standard Schema protocol key."""

    def __init__(self, props: StandardSchemaProps) -> None:
        self._props = props

    def __getitem__(self, key: str) -> Any:
        if key == "~standard":
            return self._props.to_mapping()
        raise KeyError(key)

    def __iter__(self):
        yield "~standard"

    def __len__(self) -> int:
        return 1


def build_standard_schema(
    *,
    parameters: dict[str, Any],
    output: dict[str, Any] | None,
    validate: Callable[[Any], ValidationResult],
) -> StandardSchemaHost:
    def json_schema_input(
        options: JSONSchemaOptions | dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        opts = _coerce_options(options)
        _ensure_target(opts.target)
        return strip_canonical_meta(parameters)

    def json_schema_output(
        options: JSONSchemaOptions | dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        opts = _coerce_options(options)
        _ensure_target(opts.target)
        if output is None:
            raise ValueError("Tool has no output schema")
        return strip_canonical_meta(output)

    props = StandardSchemaProps(
        version=STANDARD_VERSION,
        vendor=STANDARD_VENDOR,
        validate=validate,
        json_schema_input=json_schema_input,
        json_schema_output=json_schema_output,
    )
    return StandardSchemaHost(props)


def _coerce_options(options: JSONSchemaOptions | dict[str, Any] | None) -> JSONSchemaOptions:
    if options is None:
        return JSONSchemaOptions()
    if isinstance(options, JSONSchemaOptions):
        return options
    return JSONSchemaOptions(
        target=options.get("target", "draft-2020-12"),
        library_options=options.get("libraryOptions"),
    )


def _ensure_target(target: str) -> None:
    if target not in {"draft-2020-12", "draft-07", "openapi-3.0"}:
        raise ValueError(f"Unsupported JSON Schema target: {target!r}")
