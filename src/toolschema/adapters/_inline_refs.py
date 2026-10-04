"""Re-export $ref inlining from the schema utilities used by core and adapters."""

from toolschema._schema_utils import inline_refs

__all__ = ["inline_refs"]
