"""Export one function to multiple provider formats."""

from toolschema import schema, tool


@tool
def get_weather(city: str, units: str = "celsius") -> dict:
    """Get current weather for a city."""
    return {"city": city, "units": units, "temp": 22}


if __name__ == "__main__":
    definition = schema(get_weather)
    formats = {
        "canonical": definition.to_json_schema(),
        "openai": definition.to_openai(),
        "openai_strict": definition.to_openai(strict=True),
        "anthropic": definition.to_anthropic(),
        "mcp": definition.to_mcp(),
        "gemini": definition.to_gemini(),
    }
    for name, payload in formats.items():
        print(f"\n=== {name} ===")
        print(payload)
