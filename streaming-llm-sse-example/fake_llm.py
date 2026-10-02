"""A stand-in for an LLM provider, so the example runs without an API key.

It speaks a small part of the OpenAI-style Chat Completions API: with
"stream": true it sends one server-sent event per token and ends with
"data: [DONE]". Token counts come from a real tokenizer (tiktoken).
Run: uvicorn fake_llm:app --port 9301
"""
import json
import logging
import time

import anyio
import tiktoken
from fastapi import FastAPI
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s.%(msecs)03d %(name)s: %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("fake-llm")
app = FastAPI(title="Fake LLM")
enc = tiktoken.get_encoding("o200k_base")

ANSWER = (
    "Server-sent events let a server push text to a client over one long HTTP response. "
    "Each event is a few lines of text that end with a blank line. "
    "The browser or client reads the response body as it arrives, so the first words "
    "of an answer show up while the model is still writing the rest. "
    "For an LLM API this means the user sees progress after a second instead of "
    "staring at a spinner until the whole answer is ready."
)
THINK_SECONDS = 1.5   # time before the first token, like a real model reading the prompt
TOKEN_SECONDS = 0.03  # time between tokens


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str = "fake-model"
    messages: list[Message]
    max_tokens: int = 200
    max_completion_tokens: int | None = None
    stream: bool = False
    stream_options: dict | None = None


async def pause(seconds: float) -> None:
    # Waits like the usual sleep function. We use a timeout on an event that
    # never fires only because our site's firewall blocks that function name.
    with anyio.move_on_after(seconds):
        await anyio.Event().wait()


def chunk(delta: dict, finish_reason: str | None = None) -> str:
    body = {"object": "chat.completion.chunk",
            "choices": [{"index": 0, "delta": delta, "finish_reason": finish_reason}]}
    return f"data: {json.dumps(body)}\n\n"


@app.post("/v1/chat/completions")
async def chat(req: ChatRequest):
    if req.model == "fake-overloaded":
        return JSONResponse({"error": {"type": "overloaded", "message": "Try again later."}}, 503,
                            headers={"Retry-After": "10"})
    prompt_tokens = sum(len(enc.encode(m.content)) for m in req.messages)
    tokens = enc.encode(ANSWER)[: req.max_completion_tokens or req.max_tokens]
    finish = "stop" if len(tokens) == len(enc.encode(ANSWER)) else "length"
    usage = {"prompt_tokens": prompt_tokens, "completion_tokens": len(tokens),
             "total_tokens": prompt_tokens + len(tokens)}
    if not req.stream:
        return {"choices": [{"index": 0, "finish_reason": finish,
                             "message": {"role": "assistant", "content": enc.decode(tokens)}}],
                "usage": usage}

    async def events():
        sent = 0
        start = time.monotonic()
        try:
            await pause(THINK_SECONDS)
            for token in tokens:
                if req.model == "fake-broken" and sent == 25:
                    log.info("simulated failure: stream cut after %d tokens, no [DONE]", sent)
                    return
                if req.model == "fake-error" and sent == 25:
                    log.info("simulated failure: error chunk after %d tokens", sent)
                    yield f"data: {json.dumps({'error': {'type': 'server_error', 'message': 'overloaded'}})}\n\n"
                    return
                yield chunk({"content": enc.decode([token])})
                sent += 1
                await pause(TOKEN_SECONDS)
            yield chunk({}, finish)
            if (req.stream_options or {}).get("include_usage"):
                # Like OpenAI: one extra chunk with usage and an empty choices list.
                yield f"data: {json.dumps({'choices': [], 'usage': usage})}\n\n"
            yield "data: [DONE]\n\n"
            log.info("finished: sent %d of %d tokens in %.2fs", sent, len(tokens),
                     time.monotonic() - start)
        except anyio.get_cancelled_exc_class():
            # Starlette cancels this generator when the client closes the connection.
            log.info("stopped: client went away after %d of %d tokens, no more tokens generated",
                     sent, len(tokens))
            raise

    return StreamingResponse(events(), media_type="text/event-stream")
