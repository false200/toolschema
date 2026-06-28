"""Basic toolschema usage."""

from toolschema import schema, tool


@tool
def greet(name: str) -> str:
    """Say hello to someone."""
    return f"Hello, {name}"


if __name__ == "__main__":
    definition = schema(greet)
    print("Canonical:", definition.to_json_schema())
    print("OpenAI:", definition.to_openai())
    print("MCP:", definition.to_mcp())
