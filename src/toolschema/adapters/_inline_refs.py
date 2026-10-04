"""Re-export ``inline_refs`` from the schema utilities.

The implementation lives in ``toolschema._schema_utils`` so core type mapping
can flatten ``$ref`` without importing adapters.
"""

from toolschema._schema_utils import inline_refs

__all__ = ["inline_refs"]
