"""Chat Completions: one tool call, a follow-up turn and a streamed answer.

The client keeps the conversation. Every request sends the full messages list.
"""

import json
import os

from openai import OpenAI

client = OpenAI(base_url=os.getenv("OPENAI_BASE_URL", "http://127.0.0.1:8000/v1"),
                api_key=os.getenv("OPENAI_API_KEY", "stub-key"))
MODEL = os.getenv("MODEL", "stub-model-1")

# Chat Completions nests the function definition under "function".
tools = [{
    "type": "function",
    "function": {
        "name": "get_order_status",
        "description": "Get the status and delivery date of an order.",
        "parameters": {"type": "object", "properties": {"order_id": {"type": "string"}},
                       "required": ["order_id"], "additionalProperties": False},
        "strict": True,
    },
}]


def get_order_status(order_id: str) -> dict:
    return {"order_id": order_id, "status": "shipped", "eta": "2026-10-14"}


print("== 1. The model asks for a tool call")
messages = [
    {"role": "developer", "content": "You answer questions about orders."},
    {"role": "user", "content": "What is the status of order A-1001?"},
]
completion = client.chat.completions.create(model=MODEL, messages=messages, tools=tools)
choice = completion.choices[0]
print("finish_reason:", choice.finish_reason)
tool_call = choice.message.tool_calls[0]
print("tool call:", tool_call.id, tool_call.function.name, tool_call.function.arguments)

print("\n== 2. We run the tool and send the result back")
messages.append(choice.message.model_dump(exclude_none=True))  # the assistant message with tool_calls
arguments = json.loads(tool_call.function.arguments)
messages.append({"role": "tool", "tool_call_id": tool_call.id,
                 "content": json.dumps(get_order_status(**arguments))})
completion = client.chat.completions.create(model=MODEL, messages=messages, tools=tools)
print("answer:", completion.choices[0].message.content)
messages.append({"role": "assistant", "content": completion.choices[0].message.content})
print("messages sent so far:", len(messages))

print("\n== 3. A follow-up question, with and without the history")
follow_up = {"role": "user", "content": "When will it arrive?"}
with_history = client.chat.completions.create(model=MODEL, messages=messages + [follow_up])
print("with history:   ", with_history.choices[0].message.content)
without_history = client.chat.completions.create(model=MODEL, messages=[follow_up])
print("without history:", without_history.choices[0].message.content)
print("usage with history:", with_history.usage.prompt_tokens, "prompt tokens")

print("\n== 4. Streaming")
stream = client.chat.completions.create(model=MODEL, messages=messages + [follow_up], stream=True)
for chunk in stream:
    delta = chunk.choices[0].delta
    if delta.content:
        print(repr(delta.content), end=" ")
    if chunk.choices[0].finish_reason:
        print("\nfinish_reason:", chunk.choices[0].finish_reason)
