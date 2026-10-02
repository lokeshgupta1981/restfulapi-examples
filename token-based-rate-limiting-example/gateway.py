"""REST API gateway with token-based rate limiting for LLM traffic.

Each API key gets a token bucket in Redis. Before a request goes to the LLM,
the gateway reserves (estimated input tokens + max_tokens). After the reply,
it refunds what the model did not use.

Run: uvicorn gateway:app --port 8080
"""
import json
import math
import os

import anyio
import httpx
import redis.asyncio as redis
import tiktoken
from fastapi import FastAPI, Header, Request
from fastapi.responses import JSONResponse, StreamingResponse

# Base URL of an OpenAI-style API, without the /v1 part.
UPSTREAM = os.environ.get("UPSTREAM_URL", "http://127.0.0.1:9000")
r = redis.Redis.from_url(os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0"))
enc = tiktoken.get_encoding("o200k_base")
app = FastAPI(title="LLM gateway")

# Tokens per minute for each API key. A real system loads this from a database.
PLANS = {"key-free": 2_000, "key-pro": 20_000}
MAX_TOKENS_DEFAULT = 256

# Token bucket in one atomic Lua script, so several gateway instances
# can share one budget. Redis TIME gives every instance the same clock.
# A positive delta takes tokens (only if enough are left); a negative delta
# refunds them. Both first add the tokens that refilled since the last update.
BUCKET = r.register_script("""
local cap   = tonumber(ARGV[1])
local rate  = tonumber(ARGV[2])         -- tokens added per second
local delta = tonumber(ARGV[3])
local t = redis.call('TIME')
local now = tonumber(t[1]) + tonumber(t[2]) / 1000000
local b = redis.call('HMGET', KEYS[1], 'tokens', 'ts')
local tokens = tonumber(b[1]) or cap
local ts = tonumber(b[2]) or now
tokens = math.min(cap, tokens + (now - ts) * rate)
local ok = 0
if delta <= 0 or tokens >= delta then
  tokens = math.min(cap, tokens - delta)
  ok = 1
end
redis.call('HSET', KEYS[1], 'tokens', tokens, 'ts', now)
redis.call('EXPIRE', KEYS[1], 3600)
return {ok, tostring(tokens)}
""")


async def take(bucket: str, cap: int, tokens: int) -> tuple[bool, float]:
    ok, left = await BUCKET(keys=[bucket], args=[cap, cap / 60, tokens])
    return bool(ok), float(left)


async def refund(bucket: str, cap: int, tokens: int) -> float:
    # Shielded, so a cancelled request (client gone) still gets its refund.
    with anyio.CancelScope(shield=True):
        _, left = await BUCKET(keys=[bucket], args=[cap, cap / 60, -max(0, tokens)])
    return float(left)


def estimate_input(messages: list[dict]) -> int:
    # Count the text with the tokenizer, plus a few tokens per message for roles.
    return sum(len(enc.encode(str(m.get("content", "")))) + 4 for m in messages)


def limit_headers(cap: int, remaining: float) -> dict:
    return {
        "x-ratelimit-limit-tokens": str(cap),
        "x-ratelimit-remaining-tokens": str(int(remaining)),
        "x-ratelimit-reset-tokens": f"{math.ceil((cap - remaining) / (cap / 60))}s",
    }


def problem(status: int, title: str, detail: str, headers: dict | None = None) -> JSONResponse:
    body = {"type": "about:blank", "title": title, "status": status, "detail": detail}
    return JSONResponse(body, status, headers=headers, media_type="application/problem+json")


def upstream_error(resp: httpx.Response | None) -> JSONResponse:
    if resp is not None and resp.status_code == 429:
        # Our own provider quota is used up: not this client's fault, so 503.
        retry = resp.headers.get("retry-after", "10")
        return problem(503, "Model busy", "The model provider is rate limiting us. Try again later.",
                       {"Retry-After": retry})
    return problem(502, "Bad Gateway", "The model provider did not answer correctly.")


@app.post("/v1/chat/completions")
async def chat(request: Request, authorization: str = Header("")):
    key = authorization.removeprefix("Bearer ").strip()
    if key not in PLANS:
        return problem(401, "Unauthorized", "Send a valid API key as a Bearer token.",
                       {"WWW-Authenticate": "Bearer"})
    cap = PLANS[key]

    try:
        body = await request.json()
        messages = body["messages"]
        max_tokens = body.pop("max_completion_tokens", None) or body.get("max_tokens", MAX_TOKENS_DEFAULT)
        if not isinstance(messages, list) or not isinstance(max_tokens, int) or max_tokens < 1:
            raise ValueError
    except (ValueError, KeyError, TypeError):
        return problem(400, "Bad Request", "Send JSON with a messages list and a positive max_tokens.")
    body["max_tokens"] = max_tokens

    reserved = estimate_input(messages) + max_tokens
    if reserved > cap:
        return problem(400, "Request too large",
                       f"This request needs up to {reserved} tokens, but your limit is {cap} per minute. "
                       "Lower max_tokens or shorten the prompt.")

    bucket = f"tpm:{key}"
    ok, left = await take(bucket, cap, reserved)
    if not ok:
        wait = math.ceil((reserved - left) / (cap / 60))
        return problem(429, "Token rate limit exceeded",
                       f"This request needs {reserved} tokens and {int(left)} are left. "
                       f"Retry in {wait} seconds.", limit_headers(cap, left) | {"Retry-After": str(wait)})

    http = httpx.AsyncClient(base_url=UPSTREAM, timeout=60)
    resp = None
    try:
        if body.get("stream"):
            body["stream_options"] = {"include_usage": True}
            req = http.build_request("POST", "/v1/chat/completions", json=body)
            resp = await http.send(req, stream=True)
        else:
            resp = await http.post("/v1/chat/completions", json=body)
        resp.raise_for_status()
    except httpx.HTTPError:
        if resp is not None:
            await resp.aclose()
        await http.aclose()
        await refund(bucket, cap, reserved)  # the model did no work
        return upstream_error(resp)

    if body.get("stream"):
        return StreamingResponse(relay(resp, http, body, bucket, cap, reserved),
                                 media_type="text/event-stream", headers=limit_headers(cap, left))

    await http.aclose()
    data = resp.json()
    used = data["usage"]["total_tokens"]
    left = await refund(bucket, cap, reserved - used)
    headers = limit_headers(cap, left) | {"x-tokens-reserved": str(reserved), "x-tokens-used": str(used)}
    return JSONResponse(data, headers=headers)


async def relay(resp: httpx.Response, http: httpx.AsyncClient, body: dict,
                bucket: str, cap: int, reserved: int):
    used = None
    text = ""
    try:
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
        # Runs when the stream ends or the client disconnects. Without a usage
        # chunk, charge the input estimate plus the tokens already streamed.
        await resp.aclose()
        await http.aclose()
        if used is None:
            used = estimate_input(body["messages"]) + len(enc.encode(text))
        await refund(bucket, cap, reserved - used)
