"""REST API gateway with token-based rate limiting for LLM traffic.

Each API key gets a token bucket in Redis. Before a request goes to the LLM,
the gateway reserves (estimated input tokens + max_tokens). After the reply,
it refunds what the model did not use.

Run: uvicorn gateway:app --port 8080
"""
import json
import math
import os

import httpx
import redis.asyncio as redis
import tiktoken
from fastapi import FastAPI, Header, Request
from fastapi.responses import JSONResponse, StreamingResponse

UPSTREAM = os.environ.get("UPSTREAM_URL", "http://127.0.0.1:9000")
r = redis.Redis.from_url(os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0"))
enc = tiktoken.get_encoding("o200k_base")
app = FastAPI(title="LLM gateway")

# Tokens per minute for each API key. A real system loads this from a database.
PLANS = {"key-free": 2_000, "key-pro": 20_000}
MAX_TOKENS_DEFAULT = 256

# Token bucket in one atomic Lua script, so several gateway instances
# can share one budget. Redis TIME gives every instance the same clock.
TAKE = r.register_script("""
local cap  = tonumber(ARGV[1])
local rate = tonumber(ARGV[2])          -- tokens added per second
local cost = tonumber(ARGV[3])
local t = redis.call('TIME')
local now = tonumber(t[1]) + tonumber(t[2]) / 1000000
local b = redis.call('HMGET', KEYS[1], 'tokens', 'ts')
local tokens = tonumber(b[1]) or cap
local ts = tonumber(b[2]) or now
tokens = math.min(cap, tokens + (now - ts) * rate)
local ok = 0
if tokens >= cost then
  tokens = tokens - cost
  ok = 1
end
redis.call('HSET', KEYS[1], 'tokens', tokens, 'ts', now)
redis.call('EXPIRE', KEYS[1], 3600)
return {ok, tostring(tokens)}
""")

REFUND = r.register_script("""
local cap = tonumber(ARGV[1])
local tokens = tonumber(redis.call('HGET', KEYS[1], 'tokens') or cap)
tokens = math.min(cap, tokens + tonumber(ARGV[2]))
redis.call('HSET', KEYS[1], 'tokens', tokens)
return tostring(tokens)
""")


def estimate_input(messages: list[dict]) -> int:
    # Count the text with the tokenizer, plus a few tokens per message for roles.
    return sum(len(enc.encode(m.get("content", ""))) + 4 for m in messages)


def limit_headers(cap: int, remaining: float) -> dict:
    rate = cap / 60
    return {
        "x-ratelimit-limit-tokens": str(cap),
        "x-ratelimit-remaining-tokens": str(int(remaining)),
        "x-ratelimit-reset-tokens": f"{math.ceil((cap - remaining) / rate)}s",
    }


def problem(status: int, title: str, detail: str, headers: dict) -> JSONResponse:
    body = {"type": "about:blank", "title": title, "status": status, "detail": detail}
    return JSONResponse(body, status, headers=headers, media_type="application/problem+json")


@app.post("/v1/chat/completions")
async def chat(request: Request, authorization: str = Header("")):
    key = authorization.removeprefix("Bearer ").strip()
    if key not in PLANS:
        return problem(401, "Unauthorized", "Send a valid API key as a Bearer token.",
                       {"WWW-Authenticate": "Bearer"})
    cap = PLANS[key]
    body = await request.json()
    body.setdefault("max_tokens", MAX_TOKENS_DEFAULT)
    reserved = estimate_input(body.get("messages", [])) + body["max_tokens"]
    if reserved > cap:
        return problem(400, "Request too large",
                       f"This request needs up to {reserved} tokens, but your limit is {cap} per minute. "
                       "Lower max_tokens or shorten the prompt.", {})

    bucket = f"tpm:{key}"
    ok, left = await TAKE(keys=[bucket], args=[cap, cap / 60, reserved])
    left = float(left)
    if not ok:
        wait = math.ceil((reserved - left) / (cap / 60))
        headers = limit_headers(cap, left) | {"Retry-After": str(wait)}
        return problem(429, "Token rate limit exceeded",
                       f"This request needs {reserved} tokens and {int(left)} are left. "
                       f"Retry in {wait} seconds.", headers)

    if body.get("stream"):
        body["stream_options"] = {"include_usage": True}
        return StreamingResponse(stream(body, bucket, cap, reserved),
                                 media_type="text/event-stream", headers=limit_headers(cap, left))

    try:
        async with httpx.AsyncClient(base_url=UPSTREAM, timeout=60) as http:
            resp = await http.post("/v1/chat/completions", json=body)
        resp.raise_for_status()
    except httpx.HTTPError:
        await REFUND(keys=[bucket], args=[cap, reserved])  # the model did no work
        return problem(502, "Bad Gateway", "The model provider did not answer.", {})

    data = resp.json()
    used = data["usage"]["total_tokens"]
    left = float(await REFUND(keys=[bucket], args=[cap, reserved - used]))
    headers = limit_headers(cap, left) | {"x-tokens-reserved": str(reserved), "x-tokens-used": str(used)}
    return JSONResponse(data, headers=headers)


async def stream(body: dict, bucket: str, cap: int, reserved: int):
    used = None
    text = ""
    try:
        async with httpx.AsyncClient(base_url=UPSTREAM, timeout=60) as http:
            async with http.stream("POST", "/v1/chat/completions", json=body) as resp:
                async for line in resp.aiter_lines():
                    if line.startswith("data: {"):
                        chunk = json.loads(line[6:])
                        if chunk.get("usage"):
                            used = chunk["usage"]["total_tokens"]
                        for choice in chunk.get("choices", []):
                            text += choice["delta"].get("content", "")
                    if line:
                        yield line + "\n\n"
    finally:
        # Runs even if the client disconnects. Without a usage chunk,
        # charge the input estimate plus the tokens already streamed.
        if used is None:
            used = estimate_input(body["messages"]) + len(enc.encode(text))
        await REFUND(keys=[bucket], args=[cap, max(0, reserved - used)])
