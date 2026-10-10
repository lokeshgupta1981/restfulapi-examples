"""Two fake OpenAI-compatible providers for testing the fallback logic without API keys.

Port 8101 behaves like a free tier that is out of quota: every request gets HTTP 429.
Port 8102 answers the first request with HTTP 429 and Retry-After: 2, then succeeds.
Run with:  uvicorn mock_provider:busy --port 8101  and  uvicorn mock_provider:flaky --port 8102
"""
import time

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


def completion(model, text):
    return {"id": "chatcmpl-mock", "object": "chat.completion", "created": int(time.time()), "model": model,
            "choices": [{"index": 0, "finish_reason": "stop",
                         "message": {"role": "assistant", "content": text}}],
            "usage": {"prompt_tokens": 12, "completion_tokens": 9, "total_tokens": 21}}


def too_many(retry_after):
    return JSONResponse({"error": {"message": "Rate limit reached, requests per day (RPD): limit 50",
                                   "type": "rate_limit_error", "code": "rate_limit_exceeded"}},
                        status_code=429, headers={"retry-after": str(retry_after)})


busy = FastAPI()


@busy.post("/v1/chat/completions")
async def busy_chat(request: Request):
    return too_many(3600)


flaky = FastAPI()
calls = {"count": 0}


@flaky.post("/v1/chat/completions")
async def flaky_chat(request: Request):
    body = await request.json()
    calls["count"] += 1
    if calls["count"] == 1:
        return too_many(2)
    return completion(body["model"], "HTTP 429 means the client sent too many requests.")
