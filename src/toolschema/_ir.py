from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from toolschema._standard import StandardSchemaHost, build_standard_schema
from toolschema._validate import ValidationResult, validate_arguments


@dataclass(frozen=True)
class ToolDefinition:
    """Intermediate representation of a tool derived from a Python function."""

    name: str
    description: str
    parameters: dict[str, Any]
    output: dict[str, Any] | None = None

    def to_json_schema(self) -> dict[str, Any]:
        """Return canonical tool record with JSON Schema 2020-12 parameters."""
        result: dict[str, Any] = {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }
        if self.output is not None:
            result["output"] = self.output
        return result

    def validate(self, args: Any) -> ValidationResult:
        """Validate tool arguments against the canonical parameters schema."""
        return validate_arguments(args, self.parameters)

    @property
    def standard(self) -> StandardSchemaHost:
        """Standard Schema + Standard JSON Schema protocol host."""
        return build_standard_schema(
            parameters=self.parameters,
            output=self.output,
            validate=self.validate,
        )

    def to_openai(self, *, strict: bool = False) -> dict[str, Any]:
        from toolschema.adapters.openai import to_openai

        return to_openai(self, strict=strict)

    def to_anthropic(self) -> dict[str, Any]:
        from toolschema.adapters.anthropic import to_anthropic

        return to_anthropic(self)

    def to_mcp(self, *, inline_refs: bool = True) -> dict[str, Any]:
        from toolschema.adapters.mcp import to_mcp

        return to_mcp(self, inline_refs=inline_refs)

    def to_gemini(self) -> dict[str, Any]:
        from toolschema.adapters.gemini import to_gemini

        return to_gemini(self)
