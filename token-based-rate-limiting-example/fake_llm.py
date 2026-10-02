"""A stand-in for an LLM provider, so the example runs without an API key.

It speaks a small part of the OpenAI-style Chat Completions API and counts
tokens with a real tokenizer (tiktoken). Run: uvicorn fake_llm:app --port 9000
"""
import json

import tiktoken
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

app = FastAPI(title="Fake LLM")
enc = tiktoken.get_encoding("o200k_base")

ANSWER = (
    "Rate limits protect an API from overload and keep costs predictable. "
    "A token budget is fairer than a request count for LLM traffic, because "
    "one long prompt can cost as much as a hundred short ones. "
) * 20


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str = "fake-model"
    messages: list[Message]
    max_tokens: int = 256
    stream: bool = False


def reply_tokens(req: ChatRequest) -> list[int]:
    # The reply is up to 120 tokens long, and never longer than max_tokens.
    return enc.encode(ANSWER)[: min(req.max_tokens, 120)]


@app.post("/v1/chat/completions")
def chat(req: ChatRequest):
    prompt_tokens = sum(len(enc.encode(m.content)) for m in req.messages)
    tokens = reply_tokens(req)
    usage = {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": len(tokens),
        "total_tokens": prompt_tokens + len(tokens),
    }
    if not req.stream:
        return {
            "model": req.model,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": enc.decode(tokens)}}],
            "usage": usage,
        }

    def events():
        for i in range(0, len(tokens), 20):
            chunk = {"choices": [{"index": 0, "delta": {"content": enc.decode(tokens[i:i + 20])}}]}
            yield f"data: {json.dumps(chunk)}\n\n"
        # Like OpenAI with stream_options.include_usage, the last chunk carries usage.
        yield f"data: {json.dumps({'choices': [], 'usage': usage})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")
