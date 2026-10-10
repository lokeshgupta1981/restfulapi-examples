"""Local stand-in for three LLM APIs with structured outputs.

The endpoints accept the request shape of each vendor and answer in the
documented response shape, so client.py runs without an API key:

  POST /v1/responses          OpenAI Responses API, text.format json_schema
  POST /v1/messages           Anthropic Messages API, output_config.format json_schema
  POST /v1beta/interactions   Gemini Interactions API, response_format with a schema

There is no model behind it. A few regular expressions pull the events out of
the email, which is enough to show the response handling. The request header
X-Stub-Scenario picks a failure case: "refusal", "drift" (JSON that ignores
the schema, as a server without strict mode can return) or "wrong-date" (valid
JSON with a date that is not in the email). A low token limit
in the request produces a truncated answer. The stub counts 4 characters as
one token.
"""
import json
import math
import re

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI(title="Structured outputs stub")
CHARS_PER_TOKEN = 4


def fake_model(text: str) -> dict:
    """Rule-based extraction that plays the role of the model."""
    events = []
    for sentence in re.split(r"(?<=\.)\s+", text):
        date = re.search(r"\d{4}-\d{2}-\d{2}", sentence)
        if not date:
            continue
        title = re.search(r"[Tt]he ([A-Za-z0-9 ]+?) (?:moves to|with|is on|by)", sentence)
        time = re.search(r"at (\d{2}:\d{2})", sentence)
        people = re.search(r"with ([A-Z][a-z]+(?: and [A-Z][a-z]+)*)", sentence)
        name = title.group(1) if title else "Event"
        kind = "call" if "call" in name else "deadline" if " by " in sentence else "meeting"
        events.append({
            "title": name[0].upper() + name[1:],
            "kind": kind,
            "date": date.group(0),
            "start_time": time.group(1) if time else None,
            "attendees": people.group(1).split(" and ") if people else [],
        })
    return {"events": events}


def drifted_answer() -> dict:
    """JSON that a server without schema enforcement might return."""
    return {"events": [{"title": "Sprint review", "kind": "Meeting", "date": "14/10/2026",
                        "start_time": "15:00", "attendees": "Ana, Raj"}]}


def order_like_schema(value, schema):
    """Write object keys in the order of the schema, as constrained decoding does."""
    if isinstance(value, dict) and "properties" in schema:
        return {key: order_like_schema(value[key], schema["properties"][key])
                for key in schema["properties"] if key in value}
    if isinstance(value, list) and isinstance(schema.get("items"), dict):
        return [order_like_schema(item, schema["items"]) for item in value]
    return value


def generate(prompt: str, schema: dict, scenario: str, max_tokens: int | None):
    """Return (text, truncated, input_tokens, output_tokens)."""
    answer = drifted_answer() if scenario == "drift" else order_like_schema(fake_model(prompt), schema)
    if scenario == "wrong-date":
        answer["events"][0]["date"] = "2026-10-15"  # schema-valid, but not what the email says
    text = json.dumps(answer, separators=(",", ":"))
    input_tokens = math.ceil(len(prompt) / CHARS_PER_TOKEN)
    output_tokens = math.ceil(len(text) / CHARS_PER_TOKEN)
    if max_tokens is not None and output_tokens > max_tokens:
        return text[: max_tokens * CHARS_PER_TOKEN], True, input_tokens, max_tokens
    return text, False, input_tokens, output_tokens


def prompt_text(value) -> str:
    """Accept a plain string or a list of {role, content} messages."""
    if isinstance(value, str):
        return value
    return "\n".join(m["content"] for m in value if isinstance(m.get("content"), str))


@app.post("/v1/responses")
async def openai_responses(request: Request):
    body = await request.json()
    scenario = request.headers.get("X-Stub-Scenario", "ok")
    schema = body["text"]["format"]["schema"]
    prompt = prompt_text(body["input"])
    if scenario == "refusal":
        content = [{"type": "refusal", "refusal": "I'm sorry, I cannot assist with that request."}]
        status, details, out_tokens = "completed", None, 11
    else:
        text, cut, in_tokens, out_tokens = generate(prompt, schema, scenario, body.get("max_output_tokens"))
        content = [{"type": "output_text", "text": text, "annotations": []}]
        status = "incomplete" if cut else "completed"
        details = {"reason": "max_output_tokens"} if cut else None
    return {
        "id": "resp_stub_001", "object": "response", "status": status,
        "incomplete_details": details, "model": body["model"],
        "output": [{"id": "msg_stub_001", "type": "message", "status": status,
                    "role": "assistant", "content": content}],
        "usage": {"input_tokens": math.ceil(len(prompt) / CHARS_PER_TOKEN), "output_tokens": out_tokens},
    }


@app.post("/v1/messages")
async def anthropic_messages(request: Request):
    body = await request.json()
    scenario = request.headers.get("X-Stub-Scenario", "ok")
    schema = body["output_config"]["format"]["schema"]
    prompt = prompt_text(body["messages"])
    stop_details = None
    if scenario == "refusal":
        text, stop_reason, out_tokens = "I can't help with that request.", "refusal", 9
        stop_details = {"type": "refusal", "category": None, "explanation": None}
    else:
        text, cut, in_tokens, out_tokens = generate(prompt, schema, scenario, body["max_tokens"])
        stop_reason = "max_tokens" if cut else "end_turn"
    return {
        "id": "msg_stub_001", "type": "message", "role": "assistant", "model": body["model"],
        "content": [{"type": "text", "text": text}],
        "stop_reason": stop_reason, "stop_details": stop_details, "stop_sequence": None,
        "usage": {"input_tokens": math.ceil(len(prompt) / CHARS_PER_TOKEN), "output_tokens": out_tokens},
    }


@app.post("/v1beta/interactions")
async def gemini_interactions(request: Request):
    body = await request.json()
    scenario = request.headers.get("X-Stub-Scenario", "ok")
    if scenario == "refusal":
        # The Interactions API reference documents no refusal content type, so the stub has none.
        return JSONResponse({"error": "the stub has no refusal case for the Interactions API"}, status_code=400)
    response_format = body["response_format"]
    if isinstance(response_format, list):
        response_format = response_format[0]
    max_tokens = body.get("generation_config", {}).get("max_output_tokens")
    prompt = prompt_text(body["input"])
    text, cut, in_tokens, out_tokens = generate(prompt, response_format["schema"], scenario, max_tokens)
    return {
        "id": "int_stub_001", "object": "interaction", "model": body["model"],
        "status": "incomplete" if cut else "completed",
        "steps": [{"type": "model_output", "content": [{"type": "text", "text": text}]}],
        "usage": {"total_input_tokens": in_tokens, "total_output_tokens": out_tokens,
                  "total_tokens": in_tokens + out_tokens},
    }
