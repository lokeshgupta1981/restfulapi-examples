"""Responses API: the same tool call, follow-up turn and streamed answer.

The server keeps the conversation. Each request sends only the new items
and points at the previous response with previous_response_id.
"""

import json
import os

from openai import OpenAI

client = OpenAI(base_url=os.getenv("OPENAI_BASE_URL", "http://127.0.0.1:8000/v1"),
                api_key=os.getenv("OPENAI_API_KEY", "stub-key"))
MODEL = os.getenv("MODEL", "stub-model-1")
INSTRUCTIONS = "You answer questions about orders."

# Responses puts name and parameters at the top level of the tool.
tools = [{
    "type": "function",
    "name": "get_order_status",
    "description": "Get the status and delivery date of an order.",
    "parameters": {"type": "object", "properties": {"order_id": {"type": "string"}},
                   "required": ["order_id"], "additionalProperties": False},
    "strict": True,
}]


def get_order_status(order_id: str) -> dict:
    return {"order_id": order_id, "status": "shipped", "eta": "2026-10-14"}


print("== 1. The model asks for a tool call")
response = client.responses.create(model=MODEL, instructions=INSTRUCTIONS, tools=tools,
                                   input="What is the status of order A-1001?")
call = next(item for item in response.output if item.type == "function_call")
print("output item types:", [item.type for item in response.output])
print("function_call:", call.call_id, call.name, call.arguments)

print("\n== 2. We run the tool and send only the result")
arguments = json.loads(call.arguments)
response = client.responses.create(
    model=MODEL, instructions=INSTRUCTIONS, tools=tools,
    previous_response_id=response.id,
    input=[{"type": "function_call_output", "call_id": call.call_id,
            "output": json.dumps(get_order_status(**arguments))}],
)
print("answer:", response.output_text)
print("response id:", response.id)

print("\n== 3. A follow-up question, with and without previous_response_id")
with_state = client.responses.create(model=MODEL, instructions=INSTRUCTIONS,
                                     previous_response_id=response.id, input="When will it arrive?")
print("with previous_response_id:   ", with_state.output_text)
without_state = client.responses.create(model=MODEL, instructions=INSTRUCTIONS, input="When will it arrive?")
print("without previous_response_id:", without_state.output_text)
print("usage with previous_response_id:", with_state.usage.input_tokens, "input tokens")

print("\n== 4. Streaming")
stream = client.responses.create(model=MODEL, instructions=INSTRUCTIONS,
                                 previous_response_id=response.id, input="When will it arrive?", stream=True)
for event in stream:
    if event.type == "response.output_text.delta":
        print(repr(event.delta), end=" ")
    elif event.type == "response.completed":
        print("\nresponse.completed, status:", event.response.status)
    else:
        print(f"[{event.type}]", end=" ")
