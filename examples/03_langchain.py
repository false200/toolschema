"""LangChain agent-style demo using toolschema-generated schemas.

Requires: uv sync --extra langchain

This example simulates a one-step tool-calling agent loop without calling an LLM API.
"""

from __future__ import annotations

import json

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from toolschema import schema
from toolschema.integrations.langchain import from_toolschema


def multiply(a: int, b: int) -> int:
    """Multiply two integers."""
    return a * b


def main() -> None:
    try:
        from langchain_core.tools import StructuredTool
    except ImportError as exc:
        raise SystemExit("Install toolschema[langchain] to run this example") from exc

    definition = schema(multiply)
    tool = from_toolschema(definition, multiply)
    native_tool = StructuredTool.from_function(multiply)

    user_question = "What is 6 times 7?"
    messages: list[HumanMessage | AIMessage | ToolMessage] = [
        HumanMessage(content=user_question),
    ]

    # Simulated model tool call (normally produced by an LLM)
    tool_call = {
        "name": tool.name,
        "args": {"a": 6, "b": 7},
        "id": "call_multiply_1",
    }
    messages.append(
        AIMessage(
            content="",
            tool_calls=[tool_call],
        )
    )

    result = tool.invoke(tool_call["args"])
    messages.append(ToolMessage(content=str(result), tool_call_id=tool_call["id"]))

    print("User:", user_question)
    print("Tool schema (toolschema):", json.dumps(definition.to_openai()["function"]["parameters"]))
    print("Tool schema (langchain native):", json.dumps(native_tool.args_schema.model_json_schema()))
    print("Tool result:", result)
    print("Conversation tail:", [type(m).__name__ for m in messages])


if __name__ == "__main__":
    main()
