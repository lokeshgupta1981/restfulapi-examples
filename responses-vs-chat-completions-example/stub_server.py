"""A local stub of two OpenAI API styles, so the demos run without an API key.

POST /v1/chat/completions   Chat Completions shape (messages in, choices out)
POST /v1/responses          Responses shape (input items in, output items out)
GET  /v1/responses/{id}     read a stored response

The "model" is a few fixed rules for an order-support assistant:
  - a user message with an order id (A-1001) and a get_order_status tool -> call the tool
  - a tool result as the last item -> answer from the tool result
  - a question about delivery -> answer only if an earlier tool result is in the context
Request and response fields follow the OpenAI API reference. Token counts are word counts.

Run: uvicorn stub_server:app --host 127.0.0.1 --port 8000
"""

import json
import re
import time
from itertools import count

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

app = FastAPI()
MODEL = "stub-model-1"
ORDERS = {"A-1001": {"order_id": "A-1001", "status": "shipped", "eta": "2026-10-14"}}
STORED: dict[str, dict] = {}  # response id -> {"context": [...], "response": {...}}
_ids = count(1)


def new_id(prefix: str) -> str:
    return f"{prefix}{next(_ids):03d}"


def tokens(text: str) -> int:
    return len(text.split())


# ------------------------------------------------------------- the "model"
# Both endpoints convert their input to one neutral list of turns:
#   {"kind": "user" | "assistant", "text": ...}
#   {"kind": "call", "call_id": ..., "name": ..., "arguments": "..."}
#   {"kind": "result", "call_id": ..., "output": "..."}

def decide(turns: list[dict], tool_names: set[str]) -> dict:
    """Return {"text": ...} or {"call": {"name": ..., "arguments": ...}}."""
    last = turns[-1]
    if last["kind"] == "result":
        order = json.loads(last["output"])
        return {"text": f"Order {order['order_id']} is {order['status']}. It should arrive on {order['eta']}."}
    question = last.get("text", "")
    order_id = re.search(r"A-\d{4}", question)
    if order_id and "get_order_status" in tool_names:
        return {"call": {"name": "get_order_status", "arguments": json.dumps({"order_id": order_id.group(0)})}}
    if "deliver" in question.lower() or "arrive" in question.lower():
        results = [json.loads(t["output"]) for t in turns if t["kind"] == "result"]
        if results:
            return {"text": f"The delivery date for order {results[-1]['order_id']} is {results[-1]['eta']}."}
        return {"text": "I do not know which order you mean. Please send the order id."}
    return {"text": "Hello! Send me an order id, for example A-1001, and I will check its status."}


def words(text: str) -> list[str]:
    parts = text.split(" ")
    return [p if i == len(parts) - 1 else p + " " for i, p in enumerate(parts)]


def sse(data: dict | str, event: str | None = None) -> str:
    body = data if isinstance(data, str) else json.dumps(data)
    return (f"event: {event}\n" if event else "") + f"data: {body}\n\n"


# ------------------------------------------------------------- Chat Completions

def chat_turns(messages: list[dict]) -> list[dict]:
    turns = []
    for m in messages:
        if m["role"] == "user":
            turns.append({"kind": "user", "text": m["content"]})
        elif m["role"] == "assistant":
            for c in m.get("tool_calls") or []:
                turns.append({"kind": "call", "call_id": c["id"], "name": c["function"]["name"],
                              "arguments": c["function"]["arguments"]})
            if m.get("content"):
                turns.append({"kind": "assistant", "text": m["content"]})
        elif m["role"] == "tool":
            turns.append({"kind": "result", "call_id": m["tool_call_id"], "output": m["content"]})
    return turns  # system and developer messages carry instructions, the stub ignores them


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    tool_names = {t["function"]["name"] for t in body.get("tools", [])}
    decision = decide(chat_turns(body["messages"]), tool_names)
    prompt_tokens = sum(tokens(json.dumps(m)) for m in body["messages"])
    completion_id, created = new_id("chatcmpl-"), int(time.time())

    if "call" in decision:
        call = {"id": new_id("call_"), "type": "function",
                "function": {"name": decision["call"]["name"], "arguments": decision["call"]["arguments"]}}
        message = {"role": "assistant", "content": None, "refusal": None, "annotations": [], "tool_calls": [call]}
        finish_reason, completion_tokens = "tool_calls", tokens(call["function"]["arguments"])
    else:
        message = {"role": "assistant", "content": decision["text"], "refusal": None, "annotations": []}
        finish_reason, completion_tokens = "stop", tokens(decision["text"])

    if body.get("stream"):
        def chunks():
            base = {"id": completion_id, "object": "chat.completion.chunk", "created": created, "model": MODEL}
            yield sse({**base, "choices": [{"index": 0, "delta": {"role": "assistant", "content": ""},
                                            "logprobs": None, "finish_reason": None}]})
            if "call" in decision:
                yield sse({**base, "choices": [{"index": 0, "delta": {"tool_calls": [{"index": 0, **call}]},
                                                "logprobs": None, "finish_reason": None}]})
            else:
                for piece in words(decision["text"]):
                    yield sse({**base, "choices": [{"index": 0, "delta": {"content": piece},
                                                    "logprobs": None, "finish_reason": None}]})
            yield sse({**base, "choices": [{"index": 0, "delta": {}, "logprobs": None,
                                            "finish_reason": finish_reason}]})
            yield sse("[DONE]")
        return StreamingResponse(chunks(), media_type="text/event-stream")

    return {"id": completion_id, "object": "chat.completion", "created": created, "model": MODEL,
            "choices": [{"index": 0, "message": message, "logprobs": None, "finish_reason": finish_reason}],
            "usage": {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens,
                      "total_tokens": prompt_tokens + completion_tokens}}


# ------------------------------------------------------------- Responses

def input_items(value) -> list[dict]:
    if isinstance(value, str):
        return [{"type": "message", "role": "user", "content": value}]
    return [{"type": "message", **item} if "role" in item and "type" not in item else item for item in value]


def item_turns(items: list[dict]) -> list[dict]:
    turns = []
    for item in items:
        if item["type"] == "message":
            content = item["content"]
            text = content if isinstance(content, str) else "".join(p.get("text", "") for p in content)
            turns.append({"kind": "user" if item["role"] == "user" else "assistant", "text": text})
        elif item["type"] == "function_call":
            turns.append({"kind": "call", "call_id": item["call_id"], "name": item["name"],
                          "arguments": item["arguments"]})
        elif item["type"] == "function_call_output":
            turns.append({"kind": "result", "call_id": item["call_id"], "output": item["output"]})
    return turns


def response_object(resp_id: str, body: dict, output: list[dict], status: str, usage: dict | None) -> dict:
    return {"id": resp_id, "object": "response", "created_at": int(time.time()), "status": status,
            "error": None, "incomplete_details": None, "instructions": body.get("instructions"),
            "max_output_tokens": None, "model": MODEL, "output": output, "parallel_tool_calls": True,
            "previous_response_id": body.get("previous_response_id"), "store": body.get("store", True),
            "temperature": 1.0, "text": body.get("text", {"format": {"type": "text"}}), "tool_choice": "auto",
            "tools": body.get("tools", []), "top_p": 1.0, "truncation": "disabled", "usage": usage,
            "metadata": {}}


@app.post("/v1/responses")
async def responses(request: Request):
    body = await request.json()
    history: list[dict] = []
    previous = body.get("previous_response_id")
    if previous:
        if previous not in STORED:
            return JSONResponse({"error": {"message": f"Previous response with id '{previous}' not found.",
                                           "type": "invalid_request_error", "param": "previous_response_id",
                                           "code": "previous_response_not_found"}}, status_code=400)
        history = STORED[previous]["context"]  # earlier input and output items, not the instructions
    new_items = input_items(body["input"])
    context = history + new_items
    tool_names = {t["name"] for t in body.get("tools", []) if t["type"] == "function"}
    decision = decide(item_turns(context), tool_names)
    resp_id = new_id("resp_")

    if "call" in decision:
        item = {"type": "function_call", "id": new_id("fc_"), "call_id": new_id("call_"),
                "name": decision["call"]["name"], "arguments": decision["call"]["arguments"], "status": "completed"}
        out_tokens = tokens(item["arguments"])
    else:
        item = {"type": "message", "id": new_id("msg_"), "status": "completed", "role": "assistant",
                "content": [{"type": "output_text", "text": decision["text"], "annotations": [], "logprobs": []}]}
        out_tokens = tokens(decision["text"])
    in_tokens = sum(tokens(json.dumps(i)) for i in context)  # the whole chain counts as input
    usage = {"input_tokens": in_tokens, "input_tokens_details": {"cached_tokens": 0},
             "output_tokens": out_tokens, "output_tokens_details": {"reasoning_tokens": 0},
             "total_tokens": in_tokens + out_tokens}
    final = response_object(resp_id, body, [item], "completed", usage)
    if body.get("store", True):
        STORED[resp_id] = {"context": context + [item], "response": final}

    if body.get("stream"):
        def events():
            seq = count(0)
            yield sse({"type": "response.created", "response": response_object(resp_id, body, [], "in_progress", None),
                       "sequence_number": next(seq)}, "response.created")
            if item["type"] == "function_call":
                yield sse({"type": "response.output_item.added", "output_index": 0,
                           "item": {**item, "arguments": "", "status": "in_progress"},
                           "sequence_number": next(seq)}, "response.output_item.added")
                yield sse({"type": "response.function_call_arguments.delta", "item_id": item["id"], "output_index": 0,
                           "delta": item["arguments"], "sequence_number": next(seq)},
                          "response.function_call_arguments.delta")
                yield sse({"type": "response.function_call_arguments.done", "item_id": item["id"], "output_index": 0,
                           "arguments": item["arguments"], "sequence_number": next(seq)},
                          "response.function_call_arguments.done")
            else:
                text = item["content"][0]["text"]
                yield sse({"type": "response.output_item.added", "output_index": 0,
                           "item": {**item, "status": "in_progress", "content": []},
                           "sequence_number": next(seq)}, "response.output_item.added")
                yield sse({"type": "response.content_part.added", "item_id": item["id"], "output_index": 0,
                           "content_index": 0, "part": {"type": "output_text", "text": "", "annotations": [],
                                                        "logprobs": []},
                           "sequence_number": next(seq)}, "response.content_part.added")
                for piece in words(text):
                    yield sse({"type": "response.output_text.delta", "item_id": item["id"], "output_index": 0,
                               "content_index": 0, "delta": piece, "sequence_number": next(seq), "logprobs": []},
                              "response.output_text.delta")
                yield sse({"type": "response.output_text.done", "item_id": item["id"], "output_index": 0,
                           "content_index": 0, "text": text, "sequence_number": next(seq), "logprobs": []},
                          "response.output_text.done")
                yield sse({"type": "response.content_part.done", "item_id": item["id"], "output_index": 0,
                           "content_index": 0, "part": item["content"][0], "sequence_number": next(seq)},
                          "response.content_part.done")
            yield sse({"type": "response.output_item.done", "output_index": 0, "item": item,
                       "sequence_number": next(seq)}, "response.output_item.done")
            yield sse({"type": "response.completed", "response": final, "sequence_number": next(seq)},
                      "response.completed")
        return StreamingResponse(events(), media_type="text/event-stream")
    return final


@app.get("/v1/responses/{resp_id}")
async def get_response(resp_id: str):
    if resp_id not in STORED:
        raise HTTPException(404, "not found")
    return STORED[resp_id]["response"]
