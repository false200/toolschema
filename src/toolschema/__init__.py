"""toolschema — function to JSON Schema for AI agent tools."""

from toolschema._decorator import tool
from toolschema._fields import Field
from toolschema._introspect import schema
from toolschema._ir import ToolDefinition
from toolschema._standard import JSONSchemaOptions, StandardSchemaHost
from toolschema._validate import (
    ValidationFailure,
    ValidationIssue,
    ValidationResult,
    ValidationSuccess,
)

__version__ = "1.0.0"

__all__ = [
    "tool",
    "schema",
    "Field",
    "ToolDefinition",
    "JSONSchemaOptions",
    "StandardSchemaHost",
    "ValidationFailure",
    "ValidationIssue",
    "ValidationResult",
    "ValidationSuccess",
    "__version__",
]
