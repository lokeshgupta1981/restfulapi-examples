"""REST API that streams LLM answers to clients as server-sent events.

POST /v1/answers/stream takes a question, calls an OpenAI-style LLM with
"stream": true, and relays the answer as clean SSE events:
  event: token  (one per piece of text)
  event: done   (finish reason and token usage)
  event: error  (the upstream failed after the stream started)
It also sends ": ping" comments while the model is quiet, and closes the
upstream request when the client disconnects, so no tokens are wasted.
Run: uvicorn app:app --port 9300
"""
import asyncio
import json
import logging
import os
import time
from pathlib import Path

import anyio
import httpx
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO, format="%(asctime)s.%(msecs)03d %(name)s: %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("gateway")
logging.getLogger("httpx").setLevel(logging.WARNING)  # hide one log line per upstream call

# Base URL of an OpenAI-style API, without the /v1 part.
UPSTREAM = os.environ.get("UPSTREAM_URL", "http://127.0.0.1:9301")
HEARTBEAT_SECONDS = float(os.environ.get("HEARTBEAT_SECONDS", "15"))

app = FastAPI(title="Answers API")
http = httpx.AsyncClient(base_url=UPSTREAM, timeout=httpx.Timeout(10, read=120))

SSE_HEADERS = {
    "Cache-Control": "no-cache",   # a cache must check with us before reusing anything
    "X-Accel-Buffering": "no",     # tell nginx to pass each event on at once
}


class AnswerRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    max_tokens: int = Field(default=200, ge=1, le=1000)
    model: str = "fake-model"


def sse(event: str, data: dict, event_id: int | None = None) -> str:
    # One SSE event: optional id, the event name, one data line, then a blank line.
    head = f"id: {event_id}\n" if event_id is not None else ""
    return f"{head}event: {event}\ndata: {json.dumps(data)}\n\n"


def problem(status: int, title: str, detail: str, headers: dict | None = None) -> JSONResponse:
    return JSONResponse({"title": title, "status": status, "detail": detail}, status,
                        headers=headers, media_type="application/problem+json")


@app.exception_handler(RequestValidationError)
async def bad_request(request: Request, exc: RequestValidationError):
    first = exc.errors()[0]
    return problem(422, "Invalid request", f"{'.'.join(map(str, first['loc']))}: {first['msg']}")


async def upstream_events(resp: httpx.Response):
    # Minimal SSE reader for the provider's stream: joins multi-line data,
    # accepts "data:" with or without a space, ignores comments.
    data = []
    async for line in resp.aiter_lines():
        if line == "":
            if data:
                yield "\n".join(data)
            data = []
        elif line.startswith("data:"):
            data.append(line[5:].removeprefix(" "))
    if data:
        yield "\n".join(data)


async def read_upstream(resp: httpx.Response, queue: asyncio.Queue) -> None:
    # Turn the provider's OpenAI-style chunks into simple (kind, value) items.
    try:
        async for payload in upstream_events(resp):
            if payload == "[DONE]":
                await queue.put(("end", None))
                return
            chunk = json.loads(payload)
            if "error" in chunk:  # some providers send an error object mid-stream
                await queue.put(("error", json.dumps(chunk["error"])))
                return
            if chunk.get("usage"):
                await queue.put(("usage", chunk["usage"]))
            for choice in chunk.get("choices", []):
                if text := choice["delta"].get("content"):
                    await queue.put(("token", text))
                if choice.get("finish_reason"):
                    await queue.put(("finish", choice["finish_reason"]))
        # The body ended without [DONE]: the answer is cut off.
        await queue.put(("error", "stream ended before [DONE]"))
    except (httpx.HTTPError, ValueError, KeyError) as exc:  # network error or a bad chunk
        await queue.put(("error", f"{type(exc).__name__}: {exc}"))


async def relay(resp: httpx.Response):
    queue: asyncio.Queue = asyncio.Queue()
    reader = asyncio.create_task(read_upstream(resp, queue))
    started = time.monotonic()
    sent = 0
    finish, usage = None, None
    completed = False
    try:
        while True:
            try:
                kind, value = await asyncio.wait_for(queue.get(), HEARTBEAT_SECONDS)
            except asyncio.TimeoutError:
                yield ": ping\n\n"  # a comment line keeps idle proxies from closing us
                continue
            if kind == "token":
                sent += 1
                yield sse("token", {"text": value}, sent)
            elif kind == "finish":
                finish = value
            elif kind == "usage":
                usage = value
            elif kind == "error":
                # HTTP 200 is already sent, so the failure becomes an event.
                yield sse("error", {"type": "upstream_error",
                                    "message": "The model stopped answering. Please retry.",
                                    "tokens_sent": sent})
                log.info("upstream failed after %d tokens: %s", sent, value)
                completed = True
                return
            elif kind == "end":
                yield sse("done", {"finish_reason": finish, "usage": usage})
                log.info("done: %d tokens in %.2fs, usage %s", sent, time.monotonic() - started, usage)
                completed = True
                return
    finally:
        if not completed:
            log.info("client disconnected after %d tokens, closing the upstream request", sent)
        reader.cancel()
        # When the client leaves, the server cancels this generator. The shield
        # lets the cleanup below finish even though a cancel is in progress.
        with anyio.CancelScope(shield=True):
            await asyncio.gather(reader, return_exceptions=True)
            await resp.aclose()


@app.post("/v1/answers/stream")
async def stream_answer(req: AnswerRequest):
    body = {
        "model": req.model,
        "messages": [{"role": "user", "content": req.question}],
        "max_completion_tokens": req.max_tokens,  # OpenAI's newer name for max_tokens
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    try:
        upstream = http.build_request("POST", "/v1/chat/completions", json=body)
        resp = await http.send(upstream, stream=True)
    except httpx.HTTPError:
        return problem(502, "Bad Gateway", "The model provider cannot be reached.")
    if resp.status_code != 200:
        # Nothing is streamed yet, so a normal HTTP error status still works.
        code, retry_after = resp.status_code, resp.headers.get("retry-after")
        await resp.aclose()
        if code in (429, 503, 529):  # busy or rate limited: worth retrying later
            headers = {"Retry-After": retry_after} if retry_after else None
            return problem(503, "Model unavailable",
                           f"The model provider answered HTTP {code}. Try again later.", headers)
        # Any other error is our bug or a bad request: retrying will not help.
        return problem(502, "Bad Gateway", f"The model provider answered HTTP {code}.")
    return StreamingResponse(relay(resp), media_type="text/event-stream", headers=SSE_HEADERS)


@app.get("/")
async def page():
    return FileResponse(Path(__file__).parent / "static" / "index.html")
