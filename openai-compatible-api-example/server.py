"""A minimal OpenAI-compatible server for the Chat Completions API.

GET  /v1/models              list models
GET  /v1/models/{model}      one model
POST /v1/chat/completions    chat completion, with stream and stream_options.include_usage

The "model" echoes the last user message in upper case, so the output is predictable.
Errors use the OpenAI error body {"error": {"message", "type", "param", "code"}}.
Rate limit: 10 requests per 10-second window per API key, with Retry-After and x-ratelimit-* headers.

Set LENIENT=1 to ignore unsupported parameters (such as n > 1) instead of rejecting them,
which is what several compatible providers do.

Run: uvicorn server:app --host 127.0.0.1 --port 8000
"""

import json
import math
import os
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

app = FastAPI()
API_KEYS = {"demo-key", "burst-key"}  # demo keys, a real server checks hashed keys
MODELS = {"echo-1": 1767225600, "echo-1-mini": 1767225600}  # model id -> created (unix seconds)
LENIENT = os.getenv("LENIENT") == "1"
WINDOW_SECONDS, WINDOW_REQUESTS = 10, 10
windows: dict[str, tuple[float, int]] = {}  # api key -> (window start, requests in window)


def error(status: int, message: str, error_type: str, code: str | None = None,
          param: str | None = None, headers: dict | None = None) -> JSONResponse:
    body = {"error": {"message": message, "type": error_type, "param": param, "code": code}}
    return JSONResponse(body, status_code=status, headers=headers)


def check_key(request: Request) -> tuple[str | None, JSONResponse | None]:
    auth = request.headers.get("Authorization", "")
    key = auth.removeprefix("Bearer ") if auth.startswith("Bearer ") else None
    if key not in API_KEYS:
        return None, error(401, "Incorrect API key provided.", "invalid_request_error", "invalid_api_key")
    return key, None


def rate_limit(key: str) -> tuple[dict, JSONResponse | None]:
    now = time.time()
    start, used = windows.get(key, (now, 0))
    if now - start >= WINDOW_SECONDS:
        start, used = now, 0
    reset = WINDOW_SECONDS - (now - start)
    headers = {"x-ratelimit-limit-requests": str(WINDOW_REQUESTS),
               "x-ratelimit-reset-requests": f"{reset:.0f}s"}
    if used >= WINDOW_REQUESTS:
        headers["x-ratelimit-remaining-requests"] = "0"
        headers["Retry-After"] = str(math.ceil(reset))
        return headers, error(429, "Rate limit reached for requests.", "rate_limit_error", "rate_limit_exceeded",
                              headers=headers)
    windows[key] = (start, used + 1)
    headers["x-ratelimit-remaining-requests"] = str(WINDOW_REQUESTS - used - 1)
    return headers, None


@app.get("/v1/models")
async def list_models(request: Request):
    _, failure = check_key(request)
    if failure:
        return failure
    return {"object": "list", "data": [{"id": m, "object": "model", "created": c, "owned_by": "demo"}
                                       for m, c in MODELS.items()]}


@app.get("/v1/models/{model}")
async def get_model(model: str, request: Request):
    _, failure = check_key(request)
    if failure:
        return failure
    if model not in MODELS:
        return error(404, f"The model '{model}' does not exist", "invalid_request_error", "model_not_found", "model")
    return {"id": model, "object": "model", "created": MODELS[model], "owned_by": "demo"}


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    key, failure = check_key(request)
    if failure:
        return failure
    headers, failure = rate_limit(key)
    if failure:
        return failure
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return error(400, "We could not parse the JSON body of your request.", "invalid_request_error")
    if not isinstance(body.get("messages"), list) or not body["messages"]:
        return error(400, "Missing required parameter: 'messages'.", "invalid_request_error",
                     "missing_required_parameter", "messages")
    model = body.get("model")
    if model not in MODELS:
        return error(404, f"The model '{model}' does not exist", "invalid_request_error", "model_not_found", "model")
    if body.get("n", 1) != 1 and not LENIENT:
        return error(400, "This server supports only n=1.", "invalid_request_error", "unsupported_value", "n")

    question = next((m.get("content") for m in reversed(body["messages"]) if m.get("role") == "user"), "")
    answer = f"You said: {str(question).upper()}"
    prompt_tokens = sum(len(str(m.get("content", "")).split()) for m in body["messages"])
    completion_tokens = len(answer.split())
    usage = {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens,
             "total_tokens": prompt_tokens + completion_tokens}
    completion_id, created = f"chatcmpl-{uuid.uuid4().hex[:12]}", int(time.time())
    headers["x-request-id"] = f"req_{uuid.uuid4().hex[:12]}"

    if body.get("stream"):
        include_usage = bool((body.get("stream_options") or {}).get("include_usage"))

        def chunk(choices: list, usage_value=None) -> str:
            data = {"id": completion_id, "object": "chat.completion.chunk", "created": created, "model": model,
                    "choices": choices}
            if include_usage:
                data["usage"] = usage_value  # null on every chunk except the last one
            return f"data: {json.dumps(data)}\n\n"

        def events():
            yield chunk([{"index": 0, "delta": {"role": "assistant", "content": ""}, "finish_reason": None}])
            words = answer.split(" ")
            for i, word in enumerate(words):
                piece = word if i == len(words) - 1 else word + " "
                yield chunk([{"index": 0, "delta": {"content": piece}, "finish_reason": None}])
            yield chunk([{"index": 0, "delta": {}, "finish_reason": "stop"}])
            if include_usage:
                yield chunk([], usage)  # OpenAI sends usage in an extra chunk with an empty choices array
            yield "data: [DONE]\n\n"
        return StreamingResponse(events(), media_type="text/event-stream", headers=headers)

    return JSONResponse({
        "id": completion_id, "object": "chat.completion", "created": created, "model": model,
        "choices": [{"index": 0, "message": {"role": "assistant", "content": answer}, "finish_reason": "stop"}],
        "usage": usage,
    }, headers=headers)
