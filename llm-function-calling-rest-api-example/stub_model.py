"""A local stub that answers POST /v1/chat/completions in the Chat Completions format.

It is not a language model. It matches the demo prompts with regular expressions and
returns fixed tool calls, so the client loop can be run without an API key.
After tool results arrive, it builds the final answer from a text template.
"""
import hashlib
import json
import re
import time

from fastapi import FastAPI, Header, HTTPException, Request

app = FastAPI(title="Stub Chat Completions server")


def call_id(prompt: str, index: int) -> str:
    return "call_" + hashlib.sha256(f"{prompt}:{index}".encode()).hexdigest()[:24]


def tool_call(prompt: str, index: int, name: str, arguments: dict) -> dict:
    return {"id": call_id(prompt, index), "type": "function",
            "function": {"name": name, "arguments": json.dumps(arguments)}}


def plan_tool_calls(prompt: str) -> list[dict]:
    text = prompt.lower()
    numbers = [int(n) for n in re.findall(r"\b\d{3,6}\b", text)]
    if "cancel" in text and numbers:
        return [tool_call(prompt, 0, "cancel_order",
                          {"order_id": numbers[0], "reason": "Customer ordered the wrong size"})]
    if ("shipment" in text or "parcel" in text or "where are" in text) and numbers:
        return [tool_call(prompt, i, "get_shipment", {"order_id": n}) for i, n in enumerate(numbers)]
    if "order twelve" in text:
        return [tool_call(prompt, 0, "get_order", {"order_id": "twelve"})]
    if numbers:
        return [tool_call(prompt, 0, "get_order", {"order_id": numbers[0]})]
    return []


def describe(name: str, args: dict, result: dict) -> str:
    order_id = args.get("order_id")
    if result.get("ok"):
        data = result["data"]
        if name == "get_order":
            return f"Order {order_id} is {data['status']} (total {data['total']} {data['currency']})."
        if name == "get_shipment":
            if data["carrier"] is None:
                return f"Order {order_id} has not shipped yet."
            return (f"Order {order_id} ships with {data['carrier']}, tracking {data['tracking_number']}, "
                    f"expected {data['eta']}.")
        if name == "cancel_order":
            return f"Order {order_id} is cancelled."
    error = result.get("error")
    if error == "not_found":
        return f"I could not find order {order_id}. Please check the order number."
    if error == "rate_limited":
        return (f"I could not get the shipment for order {order_id} right now; "
                f"please try again in about {result.get('retry_after_seconds')} seconds.")
    if error == "invalid_arguments":
        return "I need the numeric order ID, for example 1001."
    if error == "conflict":
        return result.get("message", "That action is not possible for this order.")
    if error == "declined_by_user":
        return f"OK, I did not cancel order {order_id}."
    return f"The {name} call failed ({error})."


def final_answer(messages: list) -> str:
    calls = {}
    for message in messages:
        for call in message.get("tool_calls") or []:
            calls[call["id"]] = call["function"]
    last_assistant = max(i for i, m in enumerate(messages) if m["role"] == "assistant")
    parts = []
    for message in messages[last_assistant + 1:]:
        function = calls[message["tool_call_id"]]
        args = json.loads(function["arguments"])
        parts.append(describe(function["name"], args, json.loads(message["content"])))
    return " ".join(parts)


@app.post("/v1/chat/completions")
async def chat_completions(request: Request, authorization: str | None = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    body = await request.json()
    messages = body["messages"]
    tool_names = {t["function"]["name"] for t in body.get("tools", [])}
    prompt = next(m["content"] for m in messages if m["role"] == "user")

    if messages[-1]["role"] == "tool":
        message = {"role": "assistant", "content": final_answer(messages)}
        finish_reason = "stop"
    else:
        calls = [c for c in plan_tool_calls(prompt) if c["function"]["name"] in tool_names]
        if calls:
            message = {"role": "assistant", "content": None, "tool_calls": calls}
            finish_reason = "tool_calls"
        else:
            message = {"role": "assistant", "content": "I can look up, track and cancel orders."}
            finish_reason = "stop"

    return {
        "id": "chatcmpl-stub-" + hashlib.sha256(json.dumps(messages).encode()).hexdigest()[:12],
        "object": "chat.completion",
        "created": int(time.time()),
        "model": body.get("model", "stub-model"),
        "choices": [{"index": 0, "message": message, "finish_reason": finish_reason}],
    }
